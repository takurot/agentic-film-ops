"""Tests for the Dashboard <-> Orchestrator API contract (SPEC §3.4).

Each test builds its own FastAPI app/TestClient bound to an isolated
in-memory-backed engine (via dependency overrides), so no test touches the
real local dev database.
"""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db import create_db_engine, get_db_session, init_db
from app.main import app
from app.workflow import (
    AnalysisEngine,
    AnalysisOutcome,
    Incident,
    get_analysis_engine,
)


class FakeEngineWithOption(AnalysisEngine):
    async def run_analysis(self, incident: Incident, analysis_id: str) -> AnalysisOutcome:
        return AnalysisOutcome(
            status="COMPLETED",
            options=[
                {
                    "option_id": "A",
                    "label": "Move Scene 42 to Wednesday 16:00-20:00",
                    "cost_impact": 8400,
                    "schedule_delay_days": 0,
                    "risk": "LOW",
                }
            ],
            explainability="Both principal actors are available Wednesday afternoon.",
        )

    async def execute_plan(
        self,
        analysis_id: str,
        option: dict,
        incident_id: str,
        db: Any = None,
    ) -> list[str]:
        return ["Step 1: Confirmed", "Step 2: Completed"]


@pytest.fixture
def api_client(tmp_path):
    """A TestClient wired to an isolated DB, with the stub analysis engine."""
    engine = create_db_engine(tmp_path / "test.db")
    init_db(bind=engine)

    def override_db():
        from sqlalchemy.orm import sessionmaker

        db = sessionmaker(bind=engine)()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = override_db
    with TestClient(app) as test_client:
        yield test_client, engine
    app.dependency_overrides.clear()


def seed_incident(engine) -> str:
    from sqlalchemy.orm import sessionmaker

    db = sessionmaker(bind=engine)()
    incident = Incident(
        incident_id="INC-001",
        type="WEATHER_RISK",
        scene_id="SC-042",
        headline="Heavy rain probability: 92%",
        detail="Scene 42 — Rooftop Confrontation, tomorrow 14:00",
        detected_at=datetime(2026, 9, 1, 8, 0),
        resolved=False,
    )
    db.add(incident)
    db.commit()
    incident_id = incident.incident_id
    db.close()
    return incident_id


def test_health_reports_total_scenes_and_active_incidents(api_client):
    client, engine = api_client
    seed_incident(engine)

    response = client.get("/api/production/health")

    assert response.status_code == 200
    body = response.json()
    assert body["production_day_current"] == 27
    assert body["production_day_total"] == 54
    assert body["schedule_adherence_percent"] == 94.0
    assert body["budget_spent_usd"] == 12_400_000.0
    assert body["budget_total_usd"] == 20_000_000.0
    assert body["scenes_completed"] == 82
    assert body["scenes_total"] == 143
    assert body["overall_risk"] == "MEDIUM"
    assert body["active_incidents"] == 1
    assert len(body["today_scenes"]) == 3
    assert body["today_scenes"][0]["status"] == "COMPLETED"
    assert body["today_scenes"][2]["status"] == "SHOOTING"


def test_runtime_metadata_reports_the_backend_runtime(api_client):
    client, _engine = api_client

    response = client.get("/api/runtime")

    assert response.status_code == 200
    assert response.json() == {
        "mode": "RECORDED_REPLAY",
        "reasoning_provider": "recorded-fixture",
        "model": None,
        "mcp_transport": "in-process",
        "adk_enabled": False,
    }


def test_active_incidents_lists_only_unresolved(api_client):
    client, engine = api_client
    seed_incident(engine)

    response = client.get("/api/incidents/active")

    assert response.status_code == 200
    incidents = response.json()
    assert len(incidents) == 1
    assert incidents[0]["incident_id"] == "INC-001"
    assert incidents[0]["scene_id"] == "SC-042"


def wait_for_analysis(client: TestClient, analysis_id: str, timeout: float = 2.0) -> dict:
    import time

    start = time.time()
    while time.time() - start < timeout:
        res = client.get(f"/api/analyses/{analysis_id}")
        if res.status_code == 200 and res.json()["status"] in ("COMPLETED", "FAILED"):
            return res.json()
        time.sleep(0.02)
    return client.get(f"/api/analyses/{analysis_id}").json()


def test_analyze_unknown_incident_returns_404(api_client):
    client, _engine = api_client

    response = client.post("/api/incidents/does-not-exist/analyze")

    assert response.status_code == 404


def test_analyze_with_not_implemented_engine_reports_failure(api_client):
    client, engine = api_client
    incident_id = seed_incident(engine)

    from app.workflow import AnalysisEngine, AnalysisOutcome

    class StubEngine(AnalysisEngine):
        async def run_analysis(self, incident: Incident, analysis_id: str) -> AnalysisOutcome:
            return AnalysisOutcome(
                status="FAILED",
                options=[],
                explainability="Stub failure message.",
            )

        async def execute_plan(
            self, analysis_id: str, option: dict, incident_id: str, db: Any = None
        ) -> list[str]:
            return []

    app.dependency_overrides[get_analysis_engine] = lambda: StubEngine()

    analyze_response = client.post(f"/api/incidents/{incident_id}/analyze")
    assert analyze_response.status_code == 202
    analysis_id = analyze_response.json()["analysis_id"]
    assert analyze_response.json()["status"] == "QUEUED"

    body = wait_for_analysis(client, analysis_id)
    assert body["status"] == "FAILED"
    assert body["options"] == []
    assert "Stub failure message" in body["explainability"]


def test_get_unknown_analysis_returns_404(api_client):
    client, _engine = api_client

    response = client.get("/api/analyses/does-not-exist")

    assert response.status_code == 404


def test_decision_with_no_feasible_options_is_rejected(api_client):
    client, engine = api_client

    from app.workflow import AnalysisEngine, AnalysisOutcome

    class EmptyOptionsEngine(AnalysisEngine):
        async def run_analysis(self, incident: Incident, analysis_id: str) -> AnalysisOutcome:
            return AnalysisOutcome(status="COMPLETED", options=[], explainability="None")

        async def execute_plan(
            self, analysis_id: str, option: dict, incident_id: str, db: Any = None
        ) -> list[str]:
            return []

    app.dependency_overrides[get_analysis_engine] = lambda: EmptyOptionsEngine()
    incident_id = seed_incident(engine)
    analyze_res = client.post(f"/api/incidents/{incident_id}/analyze")
    assert analyze_res.status_code == 202
    analysis_id = analyze_res.json()["analysis_id"]
    wait_for_analysis(client, analysis_id)

    response = client.post(
        f"/api/analyses/{analysis_id}/decision",
        json={"decision": "APPROVE", "option_id": "A"},
    )

    assert response.status_code == 409


def test_approve_with_a_valid_option_starts_execution(api_client):
    client, engine = api_client
    app.dependency_overrides[get_analysis_engine] = lambda: FakeEngineWithOption()
    incident_id = seed_incident(engine)
    analyze_res = client.post(f"/api/incidents/{incident_id}/analyze")
    assert analyze_res.status_code == 202
    analysis_id = analyze_res.json()["analysis_id"]
    wait_for_analysis(client, analysis_id)

    response = client.post(
        f"/api/analyses/{analysis_id}/decision",
        json={"decision": "APPROVE", "option_id": "A"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "APPROVE"
    assert body["decided_option_id"] == "A"
    assert body["execution_status"] == "COMPLETED"

    execution = client.get(f"/api/analyses/{analysis_id}/execution")
    assert execution.status_code == 200
    assert execution.json()["status"] == "COMPLETED"
    assert len(execution.json()["steps"]) == 2


def test_approve_with_an_unknown_option_id_is_rejected(api_client):
    client, engine = api_client
    app.dependency_overrides[get_analysis_engine] = lambda: FakeEngineWithOption()
    incident_id = seed_incident(engine)
    analyze_res = client.post(f"/api/incidents/{incident_id}/analyze")
    assert analyze_res.status_code == 202
    analysis_id = analyze_res.json()["analysis_id"]
    wait_for_analysis(client, analysis_id)

    response = client.post(
        f"/api/analyses/{analysis_id}/decision",
        json={"decision": "APPROVE", "option_id": "does-not-exist"},
    )

    assert response.status_code == 409


def test_reject_leaves_execution_not_started(api_client):
    client, engine = api_client
    app.dependency_overrides[get_analysis_engine] = lambda: FakeEngineWithOption()
    incident_id = seed_incident(engine)
    analyze_res = client.post(f"/api/incidents/{incident_id}/analyze")
    assert analyze_res.status_code == 202
    analysis_id = analyze_res.json()["analysis_id"]
    wait_for_analysis(client, analysis_id)

    response = client.post(f"/api/analyses/{analysis_id}/decision", json={"decision": "REJECT"})

    assert response.status_code == 200
    assert response.json()["decision"] == "REJECT"
    assert response.json()["execution_status"] == "NOT_STARTED"


def test_deciding_twice_is_rejected(api_client):
    client, engine = api_client
    app.dependency_overrides[get_analysis_engine] = lambda: FakeEngineWithOption()
    incident_id = seed_incident(engine)
    analyze_res = client.post(f"/api/incidents/{incident_id}/analyze")
    assert analyze_res.status_code == 202
    analysis_id = analyze_res.json()["analysis_id"]
    wait_for_analysis(client, analysis_id)
    client.post(f"/api/analyses/{analysis_id}/decision", json={"decision": "REJECT"})

    response = client.post(f"/api/analyses/{analysis_id}/decision", json={"decision": "REJECT"})

    assert response.status_code == 409


def test_execution_for_unknown_analysis_returns_404(api_client):
    client, _engine = api_client

    response = client.get("/api/analyses/does-not-exist/execution")

    assert response.status_code == 404


def test_events_websocket_streams_published_events(api_client):
    client, engine = api_client
    app.dependency_overrides[get_analysis_engine] = lambda: FakeEngineWithOption()
    incident_id = seed_incident(engine)
    analysis_id = client.post(f"/api/incidents/{incident_id}/analyze").json()["analysis_id"]

    from app.events import AgentEvent, default_event_bus

    with client.websocket_connect(f"/api/analyses/{analysis_id}/events") as websocket:
        default_event_bus.publish(
            analysis_id,
            AgentEvent(
                timestamp="14:07:13",
                agent="ActorAgent",
                type="EXTERNAL_REQUEST",
                status="WAITING_EXTERNAL",
                message="Contacting Emma Carter's manager",
                resource="ACT-001",
            ),
        )
        received_events = []
        while True:
            ev = websocket.receive_json()
            received_events.append(ev)
            if ev.get("agent") == "ActorAgent":
                break

    assert any(
        e.get("agent") == "ActorAgent" and e.get("status") == "WAITING_EXTERNAL"
        for e in received_events
    )


def test_events_websocket_also_streams_mcp_call_events(api_client):
    client, engine = api_client
    app.dependency_overrides[get_analysis_engine] = lambda: FakeEngineWithOption()
    incident_id = seed_incident(engine)
    analysis_id = client.post(f"/api/incidents/{incident_id}/analyze").json()["analysis_id"]

    from app.events import default_event_bus
    from mcp_common.events import MCPCallEvent

    with client.websocket_connect(f"/api/analyses/{analysis_id}/events") as websocket:
        default_event_bus.publish(
            analysis_id,
            MCPCallEvent.create(
                server="weather",
                tool="get_forecast",
                status="RESPONSE_RECEIVED",
                message="get_forecast completed",
                resource="LOC-003",
            ),
        )
        received_events = []
        while True:
            ev = websocket.receive_json()
            received_events.append(ev)
            if ev.get("type") == "MCP_CALL" and ev.get("tool") == "get_forecast":
                break

    assert any(
        e.get("type") == "MCP_CALL" and e.get("tool") == "get_forecast" for e in received_events
    )
