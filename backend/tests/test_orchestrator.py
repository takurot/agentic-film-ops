"""End-to-end and unit tests for Production Orchestrator (SPEC §6.1, §3.2, §3.4, §8, §9, §11)."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.db import create_db_engine, get_db_session, get_session, init_db
from app.events import AnalysisEventBus
from app.main import app
from app.models import Actor, Scene
from app.orchestrator import ProductionOrchestrator
from app.seed import seed_scene_42
from app.workflow import AnalysisOutcome, Incident


def make_gemini_stub() -> AsyncMock:
    stub = AsyncMock()
    fake_response = AsyncMock()
    fake_response.text = (
        '{"status": "AVAILABLE", "window_start": "16:00", "window_end": "20:00", '
        '"constraints": ["Hard stop 20:00"]}'
    )
    stub.generate_content = AsyncMock(return_value=fake_response)
    return stub


@pytest.fixture
def isolated_db_engine(tmp_path, monkeypatch):
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
    def override_db():
        with get_session(isolated_db_engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    client = TestClient(app)
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


def test_api_end_to_end_closed_loop(orchestrator_client):
    """Test full closed-loop via HTTP REST API (analyze -> stream events -> approve -> executed)."""
    client, engine = orchestrator_client

    # 1. Start Analysis
    res_analyze = client.post("/api/incidents/INC-TEST-042/analyze")
    assert res_analyze.status_code == 200
    analysis_data = res_analyze.json()
    analysis_id = analysis_data["analysis_id"]
    assert analysis_data["status"] == "COMPLETED"
    assert len(analysis_data["options"]) >= 1

    # 2. Verify human approval gate: Incident is not yet resolved before decision
    with get_session(engine) as db:
        inc = db.get(Incident, "INC-TEST-042")
        assert inc.resolved is False

    # 3. Approve Option A
    res_decision = client.post(
        f"/api/analyses/{analysis_id}/decision",
        json={"decision": "APPROVE", "option_id": "OPTION_A"},
    )
    assert res_decision.status_code == 200
    decision_data = res_decision.json()
    assert decision_data["decision"] == "APPROVE"
    assert decision_data["execution_status"] == "COMPLETED"

    # 4. Verify incident resolved in DB and Production Resource Graph updated
    with get_session(engine) as db:
        inc = db.get(Incident, "INC-TEST-042")
        assert inc.resolved is True
        scene = db.get(Scene, "SC-042")
        assert scene.location_id == "LOC-STUDIO-B"
