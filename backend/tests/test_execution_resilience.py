"""Unit and integration tests for resilient execution state machine (Issue #83, SPEC §3.4, §9.9, §9.10)."""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.db import create_db_engine, get_db_session, get_session, init_db
from app.main import app
from app.mcp_client import MCPError
from app.models import Scene
from app.orchestrator import ProductionOrchestrator
from app.seed import seed_scene_42
from app.workflow import (
    Analysis,
    Incident,
    get_analysis_engine,
)


class FailingMCPClient:
    """MCP client that allows injecting failures into specific tools."""

    def __init__(self, fail_tool: str | None = None) -> None:
        self.fail_tool = fail_tool
        self.call_history: list[tuple[str, str, dict[str, Any]]] = []

    async def start(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.call_history.append((server, tool, arguments))
        if self.fail_tool == tool:
            raise MCPError(f"Simulated failure in MCP tool {tool}")
        return {"status": "ok", "mock": True}


@pytest.fixture
def test_db_engine(tmp_path, monkeypatch):
    engine = create_db_engine(tmp_path / "resilience_test.db")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(bind=engine)
    with get_session(engine) as db:
        seed_scene_42(db)
        incident = Incident(
            incident_id="INC-RES-001",
            type="WEATHER_ALERT",
            scene_id="SC-042",
            headline="Rain threat",
            detail="Risk of rain",
            detected_at=datetime.now(),
            resolved=False,
        )
        db.add(incident)
        analysis = Analysis(
            analysis_id="AN-RES-001",
            incident_id="INC-RES-001",
            status="COMPLETED",
            options=[
                {
                    "option_id": "OPTION_A",
                    "target_scene_id": "SC-042",
                    "location_id": "LOC-STUDIO-B",
                    "start_time": "2026-09-02T16:00",
                    "end_time": "2026-09-02T20:00",
                    "recommended": True,
                },
                {
                    "option_id": "OPTION_B",
                    "target_scene_id": "SC-042",
                    "location_id": "LOC-STAGE-1",
                    "start_time": "2026-09-03T10:00",
                    "end_time": "2026-09-03T14:00",
                    "recommended": False,
                },
            ],
            execution_status="NOT_STARTED",
            execution_steps=[],
        )
        db.add(analysis)
        db.commit()
    return engine


@pytest.mark.parametrize(
    ("failing_tool", "expected_failed_step"),
    [
        ("confirm_location", "CONFIRM_LOCATION"),
        ("confirm_actor", "CONFIRM_ACTORS"),
        ("reserve_equipment", "RESERVE_EQUIPMENT"),
    ],
)
@pytest.mark.asyncio
async def test_step_failure_injection_persists_failed_status(
    test_db_engine, failing_tool, expected_failed_step
):
    """Verify that failure at any MCP step marks the state FAILED without trapping in IN_PROGRESS."""
    failing_mcp = FailingMCPClient(fail_tool=failing_tool)
    orch = ProductionOrchestrator(
        db_engine=test_db_engine,
        mcp_client=failing_mcp,
    )

    def override_db():
        with get_session(test_db_engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: orch

    with TestClient(app) as client:
        res = client.post(
            "/api/analyses/AN-RES-001/decision",
            json={"decision": "APPROVE", "option_id": "OPTION_A"},
        )
        assert res.status_code == 500
        assert "Execution failed" in res.json()["detail"]

        # Check DB state
        with get_session(test_db_engine) as db:
            analysis = db.get(Analysis, "AN-RES-001")
            assert analysis.execution_status == "FAILED"
            assert analysis.decision == "APPROVE"
            assert analysis.decided_option_id == "OPTION_A"

            # Check that incident is NOT marked resolved on failure
            incident = db.get(Incident, "INC-RES-001")
            assert incident.resolved is False

            # Check step records in execution_steps
            steps = analysis.execution_steps
            assert len(steps) > 0
            failed_step = next((s for s in steps if s.get("step_id") == expected_failed_step), None)
            assert failed_step is not None
            assert failed_step["status"] == "FAILED"
            assert failed_step["attempt"] >= 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_retry_skips_completed_steps_and_completes_execution(test_db_engine):
    """Verify that retrying a FAILED execution skips completed steps and finishes remaining ones."""
    # Step 1: Execute with failure on reserve_equipment (Step 3)
    failing_mcp = FailingMCPClient(fail_tool="reserve_equipment")
    orch = ProductionOrchestrator(
        db_engine=test_db_engine,
        mcp_client=failing_mcp,
    )

    def override_db():
        with get_session(test_db_engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: orch

    with TestClient(app) as client:
        res1 = client.post(
            "/api/analyses/AN-RES-001/decision",
            json={"decision": "APPROVE", "option_id": "OPTION_A"},
        )
        assert res1.status_code == 500

        with get_session(test_db_engine) as db:
            analysis = db.get(Analysis, "AN-RES-001")
            assert analysis.execution_status == "FAILED"
            # confirm_location (Step 1) and confirm_actor (Step 2) should be COMPLETED
            step_map = {s["step_id"]: s for s in analysis.execution_steps}
            assert step_map["CONFIRM_LOCATION"]["status"] == "COMPLETED"
            assert step_map["CONFIRM_ACTORS"]["status"] == "COMPLETED"
            assert step_map["RESERVE_EQUIPMENT"]["status"] == "FAILED"

        # Count MCP calls in first attempt
        loc_calls_attempt_1 = sum(
            1 for s, t, _ in failing_mcp.call_history if t == "confirm_location"
        )
        actor_calls_attempt_1 = sum(
            1 for s, t, _ in failing_mcp.call_history if t == "confirm_actor"
        )
        assert loc_calls_attempt_1 == 1
        assert actor_calls_attempt_1 >= 1

        # Step 2: Un-fail the MCP client and call retry (via same decision endpoint)
        failing_mcp.fail_tool = None
        failing_mcp.call_history.clear()

        res2 = client.post(
            "/api/analyses/AN-RES-001/decision",
            json={"decision": "APPROVE", "option_id": "OPTION_A"},
        )
        assert res2.status_code == 200
        data = res2.json()
        assert data["execution_status"] == "COMPLETED"

        # Verify that confirm_location and confirm_actor were SKIPPED on retry!
        loc_calls_retry = sum(1 for s, t, _ in failing_mcp.call_history if t == "confirm_location")
        actor_calls_retry = sum(1 for s, t, _ in failing_mcp.call_history if t == "confirm_actor")
        equip_calls_retry = sum(
            1 for s, t, _ in failing_mcp.call_history if t == "reserve_equipment"
        )

        assert loc_calls_retry == 0, "Completed CONFIRM_LOCATION should be skipped on retry"
        assert actor_calls_retry == 0, "Completed CONFIRM_ACTORS should be skipped on retry"
        assert equip_calls_retry >= 1, "Failed RESERVE_EQUIPMENT should be executed on retry"

        # Verify DB final state
        with get_session(test_db_engine) as db:
            analysis = db.get(Analysis, "AN-RES-001")
            assert analysis.execution_status == "COMPLETED"
            incident = db.get(Incident, "INC-RES-001")
            assert incident.resolved is True
            scene = db.get(Scene, "SC-042")
            assert scene.location_id == "LOC-STUDIO-B"

        # Verify execution schema returned by GET /api/analyses/AN-RES-001/execution has step_records
        exec_res = client.get("/api/analyses/AN-RES-001/execution")
        assert exec_res.status_code == 200
        exec_data = exec_res.json()
        assert exec_data["status"] == "COMPLETED"
        assert exec_data["step_records"] is not None
        assert len(exec_data["step_records"]) == 5
        assert all(r["status"] == "COMPLETED" for r in exec_data["step_records"])

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_idempotent_duplicate_approval_does_not_reexecute(test_db_engine):
    """Verify duplicate APPROVE request with identical idempotency key returns 200 with no re-execution."""
    mcp = FailingMCPClient(fail_tool=None)
    orch = ProductionOrchestrator(
        db_engine=test_db_engine,
        mcp_client=mcp,
    )

    def override_db():
        with get_session(test_db_engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: orch

    with TestClient(app) as client:
        # First request
        res1 = client.post(
            "/api/analyses/AN-RES-001/decision",
            headers={"Idempotency-Key": "idem-key-123"},
            json={
                "decision": "APPROVE",
                "option_id": "OPTION_A",
                "idempotency_key": "idem-key-123",
            },
        )
        assert res1.status_code == 200
        assert res1.json()["execution_status"] == "COMPLETED"
        first_call_count = len(mcp.call_history)
        assert first_call_count > 0

        # Duplicate request with same idempotency key
        res2 = client.post(
            "/api/analyses/AN-RES-001/decision",
            headers={"Idempotency-Key": "idem-key-123"},
            json={
                "decision": "APPROVE",
                "option_id": "OPTION_A",
                "idempotency_key": "idem-key-123",
            },
        )
        assert res2.status_code == 200
        assert res2.json()["execution_status"] == "COMPLETED"
        # Tool call count should not increase
        assert len(mcp.call_history) == first_call_count

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_conflicting_decision_rejected_with_409(test_db_engine):
    """Verify conflicting approval with a different option or decision is rejected with 409 Conflict."""
    mcp = FailingMCPClient(fail_tool=None)
    orch = ProductionOrchestrator(
        db_engine=test_db_engine,
        mcp_client=mcp,
    )

    def override_db():
        with get_session(test_db_engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: orch

    with TestClient(app) as client:
        # Initial approval with OPTION_A
        res1 = client.post(
            "/api/analyses/AN-RES-001/decision",
            json={"decision": "APPROVE", "option_id": "OPTION_A"},
        )
        assert res1.status_code == 200

        # Attempt to approve OPTION_B
        res_conflict_option = client.post(
            "/api/analyses/AN-RES-001/decision",
            json={"decision": "APPROVE", "option_id": "OPTION_B"},
        )
        assert res_conflict_option.status_code == 409
        assert "already decided" in res_conflict_option.json()["detail"]

        # Attempt to REJECT after APPROVE
        res_conflict_reject = client.post(
            "/api/analyses/AN-RES-001/decision",
            json={"decision": "REJECT"},
        )
        assert res_conflict_reject.status_code == 409

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rejection_preserves_pre_approval_invariants(test_db_engine):
    """Verify REJECT does not modify production resource graph or resolve the incident."""
    mcp = FailingMCPClient(fail_tool=None)
    orch = ProductionOrchestrator(
        db_engine=test_db_engine,
        mcp_client=mcp,
    )

    def override_db():
        with get_session(test_db_engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: orch

    with TestClient(app) as client:
        res = client.post(
            "/api/analyses/AN-RES-001/decision",
            json={"decision": "REJECT"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "REJECT"
        assert data["execution_status"] == "NOT_STARTED"
        assert len(mcp.call_history) == 0

        with get_session(test_db_engine) as db:
            scene = db.get(Scene, "SC-042")
            assert scene.location_id == "LOC-003"
            incident = db.get(Incident, "INC-RES-001")
            assert incident.resolved is False

    app.dependency_overrides.clear()
