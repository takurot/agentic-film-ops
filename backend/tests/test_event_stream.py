import json

import pytest
from fastapi.testclient import TestClient

from app.api import analysis_events_sse
from app.db import create_db_engine, init_db
from app.events import (
    AgentEvent,
    AnalysisEventBus,
    current_event_channel,
    default_event_bus,
)
from app.main import app
from app.workflow import Analysis, Incident
from mcp_common.events import MCPCallEvent, default_event_sink


def seed_test_incident(engine) -> str:
    from datetime import datetime

    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        incident = Incident(
            incident_id="INC-TEST-001",
            type="WEATHER_ALERT",
            scene_id="SC-042",
            headline="Rain risk test",
            detail="Heavy rain test",
            detected_at=datetime(2026, 9, 2, 14, 0),
            resolved=False,
        )
        db.merge(incident)
        db.commit()
        return incident.incident_id
    finally:
        db.close()


@pytest.fixture
def test_db(tmp_path):
    engine = create_db_engine(tmp_path / "test.db")
    init_db(bind=engine)

    def override_db():
        from sqlalchemy.orm import sessionmaker

        db = sessionmaker(bind=engine)()
        try:
            yield db
        finally:
            db.close()

    from app.db import get_db_session

    app.dependency_overrides[get_db_session] = override_db
    try:
        yield engine
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_event_bus_history_and_replay():
    bus = AnalysisEventBus(max_history_per_channel=5)
    channel = "analysis-123"

    event1 = AgentEvent.create(
        agent="ActorAgent",
        type="ACTOR_AVAILABILITY",
        status="THINKING",
        message="Checking calendar",
        resource="ACT-001",
    )
    event2 = AgentEvent.create(
        agent="ActorAgent",
        type="EXTERNAL_REQUEST",
        status="WAITING_EXTERNAL",
        message="Contacting manager",
        resource="ACT-001",
    )

    bus.publish(channel, event1)
    bus.publish(channel, event2)

    assert bus.get_history(channel) == [event1, event2]

    # Replay on subscribe
    queue = bus.subscribe(channel, replay_history=True)
    assert queue.qsize() == 2
    assert queue.get_nowait() == event1
    assert queue.get_nowait() == event2

    assert bus.subscriber_count(channel) == 1
    bus.unsubscribe(channel, queue)
    assert bus.subscriber_count(channel) == 0


def test_mcp_bridge_routes_with_contextvar():
    channel = "analysis-mcp-test"
    queue = default_event_bus.subscribe(channel)

    # Without contextvar, event is not routed to this specific channel
    mcp_event1 = MCPCallEvent.create(
        server="weather",
        tool="get_forecast",
        status="QUERYING_MCP",
        message="Calling get_forecast",
        resource="LOC-003",
    )
    default_event_sink.publish(mcp_event1)
    assert queue.empty()

    # With contextvar set, event is routed automatically
    token = current_event_channel.set(channel)
    try:
        mcp_event2 = MCPCallEvent.create(
            server="weather",
            tool="get_forecast",
            status="RESPONSE_RECEIVED",
            message="get_forecast completed",
            resource="LOC-003",
        )
        default_event_sink.publish(mcp_event2)
        assert not queue.empty()
        received = queue.get_nowait()
        assert received.tool == "get_forecast"
    finally:
        current_event_channel.reset(token)
        default_event_bus.unsubscribe(channel, queue)


def test_sse_endpoint_404_for_unknown_analysis(test_db):
    client = TestClient(app)
    response = client.get("/api/analyses/AN-NONEXISTENT/events/stream")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sse_generator_streams_and_replays_events(test_db):
    from sqlalchemy.orm import sessionmaker

    db = sessionmaker(bind=test_db)()
    try:
        analysis_id = "AN-SSE-001"
        analysis = Analysis(
            analysis_id=analysis_id,
            incident_id="INC-001",
            status="ANALYZING",
        )
        db.merge(analysis)
        db.commit()

        # Emit an event prior to stream start (to test history replay)
        event1 = AgentEvent.create(
            agent="WeatherAgent",
            type="WEATHER_ALERT",
            status="ANALYZING",
            message="Rain detected",
            resource="LOC-003",
        )
        default_event_bus.publish(analysis_id, event1)

        # Call the endpoint directly
        streaming_res = await analysis_events_sse(analysis_id, db=db)
        assert streaming_res.media_type == "text/event-stream"
        assert streaming_res.headers["Cache-Control"] == "no-cache"

        gen = streaming_res.body_iterator
        first_chunk = await anext(gen)
        assert first_chunk.startswith("data: ")
        data = json.loads(first_chunk[6:].strip())
        assert data["agent"] == "WeatherAgent"
        assert data["status"] == "ANALYZING"

        # Emit a second event live
        event2 = MCPCallEvent.create(
            server="weather",
            tool="get_forecast",
            status="RESPONSE_RECEIVED",
            message="Forecast updated",
            resource="LOC-003",
        )
        default_event_bus.publish(analysis_id, event2)

        second_chunk = await anext(gen)
        assert second_chunk.startswith("data: ")
        data2 = json.loads(second_chunk[6:].strip())
        assert data2["type"] == "MCP_CALL"
        assert data2["tool"] == "get_forecast"

        # Close generator and ensure unsubscribe
        await gen.aclose()
        assert default_event_bus.subscriber_count(analysis_id) == 0
    finally:
        db.close()


from app.workflow import AnalysisEngine, AnalysisOutcome, get_analysis_engine


class StubEventStreamEngine(AnalysisEngine):
    async def run_analysis(self, incident, analysis_id: str) -> AnalysisOutcome:
        return AnalysisOutcome(status="COMPLETED", options=[], explainability=None)

    async def execute_plan(
        self, analysis_id: str, option: dict, incident_id: str, db=None
    ) -> list[str]:
        return []


def test_websocket_endpoint_streams_mcp_and_agent_events(test_db):
    app.dependency_overrides[get_analysis_engine] = lambda: StubEventStreamEngine()
    client = TestClient(app)
    incident_id = seed_test_incident(test_db)
    analysis_id = client.post(f"/api/incidents/{incident_id}/analyze").json()["analysis_id"]

    event1 = AgentEvent.create(
        agent="EquipmentAgent",
        type="EQUIPMENT_RESERVATION",
        status="QUERYING_MCP",
        message="Checking Alexa 35 availability",
        resource="EQ-001",
    )
    event2 = MCPCallEvent.create(
        server="equipment",
        tool="check_availability",
        status="RESPONSE_RECEIVED",
        message="check_availability completed",
        resource="EQ-001",
    )

    with client.websocket_connect(f"/api/analyses/{analysis_id}/events") as ws:
        default_event_bus.publish(analysis_id, event1)
        default_event_bus.publish(analysis_id, event2)

        recv1 = ws.receive_json()
        assert recv1["agent"] == "EquipmentAgent"
        assert recv1["status"] == "QUERYING_MCP"

        recv2 = ws.receive_json()
        assert recv2["type"] == "MCP_CALL"
        assert recv2["server"] == "equipment"
        assert recv2["tool"] == "check_availability"

    app.dependency_overrides.clear()
