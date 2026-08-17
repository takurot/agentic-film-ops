"""Tests for Demo reset mechanism (Issue #34, SPEC §2.2 / §13 Phase 4)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import create_db_engine, get_db_session, init_db
from app.events import AgentEvent, default_event_bus
from app.main import app
from app.models import Actor, Scene
from app.seed import reset_demo_state
from app.workflow import (
    Analysis,
    AnalysisEngine,
    AnalysisOutcome,
    Incident,
    get_analysis_engine,
)


class MockDemoEngine(AnalysisEngine):
    """Mock analysis engine for deterministic rehearsal testing."""

    async def run_analysis(self, incident: Incident, analysis_id: str) -> AnalysisOutcome:
        return AnalysisOutcome(
            status="COMPLETED",
            options=[
                {
                    "option_id": "OPT-A",
                    "label": "Option A: Move to Studio B",
                    "cost_impact": 8400,
                    "schedule_delay_days": 0,
                    "recommended": True,
                }
            ],
            explainability="Studio B available with zero delay.",
        )

    async def execute_plan(
        self,
        analysis_id: str,
        option: dict,
        incident_id: str,
        db=None,
    ) -> list[str]:
        if db is not None:
            incident = db.get(Incident, incident_id)
            if incident:
                incident.resolved = True
                db.commit()
        return [
            "actor.confirm_actor(ACT-001)",
            "equipment.reserve(EQ-001)",
            "location.confirm(LOC-STUDIO-B)",
            "calendar.update()",
            "budget.update()",
        ]


@pytest.fixture
def reset_test_env(tmp_path):
    engine = create_db_engine(tmp_path / "reset_test.db")
    init_db(bind=engine)

    def override_db():
        from sqlalchemy.orm import sessionmaker

        db = sessionmaker(bind=engine)()
        try:
            yield db
        finally:
            db.close()

    mock_engine = MockDemoEngine()
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: mock_engine

    yield engine, TestClient(app)

    app.dependency_overrides.clear()


def test_reset_restores_clean_baseline(reset_test_env):
    engine, _client = reset_test_env

    # 1. Initial reset
    summary = reset_demo_state(bind=engine)
    assert summary["status"] == "ok"
    assert summary["incident_id"] == "INC-20260902-001"

    # 2. Simulate dirty state from a prior run
    with engine.connect() as conn:
        from sqlalchemy.orm import Session

        session = Session(bind=conn)
        actor = session.get(Actor, "ACT-001")
        actor.status = "held_for_studio_b"

        incident = session.get(Incident, "INC-20260902-001")
        incident.resolved = True

        analysis = Analysis(
            analysis_id="AN-PRIOR-RUN",
            incident_id="INC-20260902-001",
            status="COMPLETED",
            options=[{"option_id": "OPT-A"}],
            decision="APPROVE",
            decided_option_id="OPT-A",
            execution_status="COMPLETED",
            execution_steps=["step1", "step2"],
        )
        session.add(analysis)
        session.commit()

    default_event_bus.publish(
        "AN-PRIOR-RUN",
        AgentEvent.create(
            agent="WeatherAgent",
            type="AGENT_PROGRESS",
            status="COMPLETED",
            message="Prior run event",
        ),
    )
    assert len(default_event_bus.get_history("AN-PRIOR-RUN")) > 0

    # 3. Call reset_demo_state
    reset_demo_state(bind=engine)

    # 4. Verify clean baseline
    with engine.connect() as conn:
        session = Session(bind=conn)
        # Incident is active & unresolved
        inc = session.get(Incident, "INC-20260902-001")
        assert inc is not None
        assert inc.resolved is False
        assert inc.scene_id == "SC-042"

        # Analyses table is completely cleared
        analyses = session.execute(select(Analysis)).scalars().all()
        assert len(analyses) == 0

        # Actor is back to confirmed with initial availability
        actor = session.get(Actor, "ACT-001")
        assert actor.status == "confirmed"
        assert len(actor.availability) == 2

        # Scene 42 is scheduled at rooftop
        scene = session.get(Scene, "SC-042")
        assert scene.location_id == "LOC-003"

    # Event bus history is cleared
    assert len(default_event_bus.get_history("AN-PRIOR-RUN")) == 0


def test_reset_endpoint_via_api(reset_test_env):
    _engine, client = reset_test_env

    # Call POST /api/demo/reset
    res = client.post("/api/demo/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["incident_id"] == "INC-20260902-001"

    # Verify active incidents list has the seeded incident
    incidents_res = client.get("/api/incidents/active")
    assert incidents_res.status_code == 200
    incidents = incidents_res.json()
    assert len(incidents) == 1
    assert incidents[0]["incident_id"] == "INC-20260902-001"
    assert incidents[0]["resolved"] is False


def test_full_demo_scenario_twice_in_a_row(reset_test_env):
    """Verifies SPEC §2.2 / §13 requirement: demo scenario can be run repeatedly without manual intervention."""
    _engine, client = reset_test_env

    for run in range(1, 3):
        # 1. Reset state
        reset_res = client.post("/api/demo/reset")
        assert reset_res.status_code == 200

        # 2. Check active incident
        inc_res = client.get("/api/incidents/active")
        assert inc_res.status_code == 200
        incidents = inc_res.json()
        assert len(incidents) == 1
        incident_id = incidents[0]["incident_id"]
        assert incident_id == "INC-20260902-001"

        # 3. Start AI impact analysis
        analyze_res = client.post(f"/api/incidents/{incident_id}/analyze")
        assert analyze_res.status_code == 200
        analysis = analyze_res.json()
        analysis_id = analysis["analysis_id"]
        assert analysis["status"] == "COMPLETED"
        assert len(analysis["options"]) == 1

        # 4. Submit Producer approval decision
        decision_res = client.post(
            f"/api/analyses/{analysis_id}/decision",
            json={"decision": "APPROVE", "option_id": "OPT-A"},
        )
        assert decision_res.status_code == 200
        decision_data = decision_res.json()
        assert decision_data["decision"] == "APPROVE"
        assert decision_data["execution_status"] == "COMPLETED"

        # 5. Verify execution
        exec_res = client.get(f"/api/analyses/{analysis_id}/execution")
        assert exec_res.status_code == 200
        exec_data = exec_res.json()
        assert exec_data["status"] == "COMPLETED"
        assert len(exec_data["steps"]) == 5

        # 6. Verify incident is resolved (active incidents is now empty)
        active_res = client.get("/api/incidents/active")
        assert active_res.status_code == 200
        assert len(active_res.json()) == 0
