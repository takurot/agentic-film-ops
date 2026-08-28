"""End-to-end and unit tests for Production Orchestrator (SPEC §6.1, §3.2, §3.4, §8, §9, §11)."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.db import create_db_engine, get_db_session, get_session, init_db
from app.events import AnalysisEventBus, current_event_channel
from app.main import app
from app.models import Actor, Scene
from app.orchestrator import ProductionOrchestrator
from app.seed import seed_scene_42
from app.workflow import AnalysisOutcome, Incident


def _script_result(*, equipment: list[str] | None = None):
    return SimpleNamespace(
        scene=SimpleNamespace(
            scheduled="2026-09-02T14:00",
            duration_hours=4,
            name="Rooftop confrontation",
        ),
        dependencies=SimpleNamespace(location="LOC-003", actors=[], equipment=equipment or []),
        continuity=SimpleNamespace(must_precede=[], must_follow=[], same_day_as=[]),
    )


def _location_result():
    candidate = SimpleNamespace(id="LOC-STUDIO-B", name="Studio B")
    return SimpleNamespace(proposed_location_id="LOC-STUDIO-B", candidates=[candidate])


def _budget_result():
    return SimpleNamespace(
        options=[
            SimpleNamespace(candidate_id=name, total_cost_impact=100.0)
            for name in ("OPTION_A", "OPTION_B", "OPTION_C")
        ]
    )


def make_gemini_stub() -> AsyncMock:
    stub = AsyncMock()

    async def generate(prompt: str):
        if "talent manager" in prompt:
            text = (
                '{"status": "AVAILABLE", "window_start": "16:00", '
                '"window_end": "20:00", "constraints": ["Hard stop 20:00"]}'
            )
        elif "equipment rental vendor" in prompt:
            text = '{"summary": "The requested equipment window is available."}'
        elif "location manager" in prompt:
            text = '{"status": "AVAILABLE", "notes": []}'
        elif "one-sentence justification" in prompt:
            text = "Studio B is an available indoor alternative."
        else:
            text = "Option A minimizes schedule delay and cost."
        return SimpleNamespace(text=text)

    stub.generate_content = AsyncMock(side_effect=generate)
    return stub


@pytest.mark.asyncio
async def test_orchestrator_fails_closed_when_a_domain_agent_fails(monkeypatch):
    monkeypatch.setattr("app.orchestrator.analyze_scene", AsyncMock(return_value=_script_result()))
    monkeypatch.setattr(
        "app.orchestrator.evaluate_cost_impact", AsyncMock(return_value=_budget_result())
    )
    location_agent = AsyncMock()
    location_agent.propose_alternative.side_effect = RuntimeError("private provider detail")
    schedule_agent = AsyncMock()
    schedule_agent.replan.return_value = SimpleNamespace(
        options=[], overall_explainability="must not be returned"
    )
    event_bus = AnalysisEventBus()
    queue = event_bus.subscribe("AN-FAIL")
    orchestrator = ProductionOrchestrator(
        gemini_client=make_gemini_stub(),
        event_bus=event_bus,
        location_agent=location_agent,
        schedule_agent=schedule_agent,
        runtime_mode="LIVE_GEMINI",
    )
    incident = Incident(
        incident_id="INC-FAIL",
        type="WEATHER",
        scene_id="SC-042",
        headline="Rain",
        detail="Rain",
        detected_at=datetime.now(),
        resolved=False,
    )

    outcome = await orchestrator.run_analysis(incident, "AN-FAIL")

    assert outcome.status == "FAILED"
    assert outcome.options == []
    assert "private provider detail" not in (outcome.explainability or "")
    schedule_agent.replan.assert_not_awaited()
    assert current_event_channel.get() is None
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert any("[LIVE_GEMINI]" in event.message for event in events)


@pytest.mark.asyncio
async def test_equipment_vendor_result_is_forwarded_to_constraint_solver(monkeypatch):
    monkeypatch.setattr(
        "app.orchestrator.analyze_scene",
        AsyncMock(return_value=_script_result(equipment=["EQ-001"])),
    )
    monkeypatch.setattr(
        "app.orchestrator.evaluate_cost_impact", AsyncMock(return_value=_budget_result())
    )
    location_agent = AsyncMock()
    location_agent.propose_alternative.return_value = _location_result()
    equipment_agent = AsyncMock()
    equipment_agent.resolve_reservation.return_value = SimpleNamespace(
        reserved=False, vendor_outcome="denied"
    )
    schedule_agent = AsyncMock()
    schedule_agent.replan.return_value = SimpleNamespace(
        options=[], overall_explainability="No feasible plan"
    )
    orchestrator = ProductionOrchestrator(
        gemini_client=make_gemini_stub(),
        location_agent=location_agent,
        equipment_agent=equipment_agent,
        schedule_agent=schedule_agent,
    )
    incident = Incident(
        incident_id="INC-EQUIPMENT",
        type="WEATHER",
        scene_id="SC-042",
        headline="Rain",
        detail="Rain",
        detected_at=datetime.now(),
        resolved=False,
    )

    outcome = await orchestrator.run_analysis(incident, "AN-EQUIPMENT")

    assert outcome.status == "COMPLETED"
    solver_input = schedule_agent.replan.await_args.args[1]
    assert solver_input.equipment[0].extension_available is False


@pytest.fixture
def isolated_db_engine(tmp_path, monkeypatch):
    from app.latency import get_latency_config

    monkeypatch.setenv("FILMOPS_LATENCY_SCALE", "0")
    monkeypatch.setattr("app.mcp_servers.actor._MANAGER_RESPONSE_DELAY_SECONDS", 0.0)
    get_latency_config(reload=True)
    engine = create_db_engine(tmp_path / "orchestrator_test.db")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(bind=engine)

    with get_session(engine) as db:
        seed_scene_42(db)

        # Create a test weather incident for Scene 42
        incident = Incident(
            incident_id="INC-TEST-042",
            type="WEATHER_ALERT",
            scene_id="SC-042",
            headline="Heavy Rain Alert for Shibuya Rooftop",
            detail="95% precipitation forecast at 14:00. Outdoor filming at high risk.",
            detected_at=datetime.now(),
            resolved=False,
        )
        db.add(incident)
        db.commit()
    return engine


@pytest.fixture
def orchestrator_client(isolated_db_engine):
    orch = ProductionOrchestrator(
        gemini_client=make_gemini_stub(),
        db_engine=isolated_db_engine,
    )

    def override_db():
        with get_session(isolated_db_engine) as session:
            yield session

    from app.workflow import get_analysis_engine

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: orch
    with TestClient(app) as client:
        yield client, isolated_db_engine
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_orchestrator_runs_full_analysis_pipeline(isolated_db_engine):
    """Verify ProductionOrchestrator runs the 6-stage closed loop analysis on Scene 42 incident."""
    event_bus = AnalysisEventBus()
    gemini_stub = make_gemini_stub()

    orchestrator = ProductionOrchestrator(
        gemini_client=gemini_stub,
        event_bus=event_bus,
        db_engine=isolated_db_engine,
    )

    with get_session(isolated_db_engine) as db:
        incident = db.get(Incident, "INC-TEST-042")
        assert incident is not None

        analysis_id = "AN-ORCH-001"
        queue = event_bus.subscribe(analysis_id)

        outcome: AnalysisOutcome = await orchestrator.run_analysis(incident, analysis_id)

        assert outcome.status == "COMPLETED"
        assert len(outcome.options) >= 2
        # Option A should be recommended: Move to Studio B Wed 16:00-20:00
        opt_a = outcome.options[0]
        assert opt_a["option_id"] == "OPTION_A"
        assert opt_a["recommended"] is True
        assert opt_a["location_id"] == "LOC-STUDIO-B"
        assert opt_a["schedule_delay_days"] == 0
        assert outcome.explainability is not None

        # Verify streamed events cover each agent's participation
        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        agents_in_events = {e.agent for e in events}
        assert "ProductionOrchestrator" in agents_in_events
        assert "ScriptAgent" in agents_in_events
        assert "ActorAgent" in agents_in_events
        assert "LocationAgent" in agents_in_events
        assert "EquipmentAgent" in agents_in_events
        assert "BudgetAgent" in agents_in_events
        assert "ScheduleAgent" in agents_in_events

        event_bus.unsubscribe(analysis_id, queue)


@pytest.mark.asyncio
async def test_orchestrator_execute_plan_on_approval(isolated_db_engine):
    """Verify execute_plan commits booking changes to the Production Resource Graph upon APPROVE."""
    event_bus = AnalysisEventBus()
    orchestrator = ProductionOrchestrator(
        gemini_client=make_gemini_stub(),
        event_bus=event_bus,
        db_engine=isolated_db_engine,
    )

    with get_session(isolated_db_engine) as db:
        incident = db.get(Incident, "INC-TEST-042")
        analysis_id = "AN-EXEC-001"

        outcome = await orchestrator.run_analysis(incident, analysis_id)
        assert len(outcome.options) > 0

        # Execute Option A
        steps = await orchestrator.execute_plan(
            analysis_id=analysis_id,
            option=outcome.options[0],
            incident_id="INC-TEST-042",
            db=db,
        )

        assert len(steps) >= 3
        # Check Scene was updated to Studio B and new time
        scene = db.get(Scene, "SC-042")
        assert scene.location_id == "LOC-STUDIO-B"
        assert scene.scheduled.strftime("%H:%M") == "16:00"

        # Check incident is marked resolved
        inc = db.get(Incident, "INC-TEST-042")
        assert inc.resolved is True

        # Check Actor booking state
        actor_emma = db.get(Actor, "ACT-001")
        assert actor_emma.status == "confirmed"
    assert current_event_channel.get() is None


@pytest.mark.asyncio
async def test_api_end_to_end_closed_loop(isolated_db_engine):
    """Test full closed-loop via HTTP REST API (analyze -> stream events -> approve -> executed)."""
    import asyncio

    from httpx import ASGITransport, AsyncClient

    orch = ProductionOrchestrator(
        gemini_client=make_gemini_stub(),
        db_engine=isolated_db_engine,
    )

    def override_db():
        with get_session(isolated_db_engine) as session:
            yield session

    from app.analysis_runner import AnalysisRunner, get_analysis_runner
    from app.workflow import get_analysis_engine

    runner = AnalysisRunner(bind=isolated_db_engine)

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_analysis_engine] = lambda: orch
    app.dependency_overrides[get_analysis_runner] = lambda: runner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Start Analysis
        res_analyze = await client.post("/api/incidents/INC-TEST-042/analyze")
        assert res_analyze.status_code == 202
        analysis_id = res_analyze.json()["analysis_id"]
        assert res_analyze.json()["status"] == "QUEUED"

        # Wait for async analysis to complete
        for _ in range(200):
            res = await client.get(f"/api/analyses/{analysis_id}")
            if res.json().get("status") in ("COMPLETED", "FAILED"):
                break
            await asyncio.sleep(0.05)

        analysis_data = (await client.get(f"/api/analyses/{analysis_id}")).json()
        assert analysis_data["status"] == "COMPLETED", f"Expected COMPLETED but got {analysis_data}"
        assert len(analysis_data["options"]) >= 1

        # 2. Verify human approval gate: Incident is not yet resolved before decision
        with get_session(isolated_db_engine) as db:
            inc = db.get(Incident, "INC-TEST-042")
            assert inc.resolved is False

        # 3. Approve Option A
        res_decision = await client.post(
            f"/api/analyses/{analysis_id}/decision",
            json={"decision": "APPROVE", "option_id": "OPTION_A"},
        )
        assert res_decision.status_code == 200
        decision_data = res_decision.json()
        assert decision_data["decision"] == "APPROVE"
        assert decision_data["execution_status"] == "COMPLETED"

        # 4. Verify incident resolved in DB and Production Resource Graph updated
        with get_session(isolated_db_engine) as db:
            inc = db.get(Incident, "INC-TEST-042")
            assert inc.resolved is True
            scene = db.get(Scene, "SC-042")
            assert scene.location_id == "LOC-STUDIO-B"

    app.dependency_overrides.clear()
