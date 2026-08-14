"""Unit/integration tests for the Weather Agent (SPEC §6.4, Issue #31).

`seeded_db` exercises the agent against the *real* Weather/Script MCP tool
functions and a seeded DB (proving Acceptance Criteria end-to-end through
the actual mock data, not just against monkeypatched stand-ins); a handful
of tests monkeypatch the agent module's imported MCP functions directly to
reach branches the real mock data can't (unknown scene, MCP failure, exact
threshold boundary).
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine, select

import app.agents.weather as weather_agent
import app.db as db_module
from app.agents.weather import DEFAULT_RAIN_PROBABILITY_THRESHOLD, WeatherAgent
from app.db import get_session, init_db
from app.events import AnalysisEventBus, scene_channel
from app.mcp_servers import script as script_mcp
from app.mcp_servers import weather as weather_mcp
from app.models import Scene
from app.seed import seed_scene_42
from app.workflow import Incident


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42 (SC-042, location LOC-003 —
    92% rain in the real Weather MCP mock) plus SC-099, a scene with no
    location, for the "nothing to monitor" branch.

    Zeroes out the Weather/Script MCP servers' simulated latency (SPEC §7)
    so this suite doesn't pay 3+ tool calls x 0.5s per test.
    """
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(engine)
    with get_session(engine) as db:
        seed_scene_42(db)
        db.add(
            Scene(
                scene_id="SC-099",
                name="Indoor pickup shot",
                type="indoor",
                duration_hours=1,
                scheduled=datetime(2026, 9, 3, 9, 0),
            )
        )
        db.commit()

    monkeypatch.setattr(weather_mcp.server.latency_config, "default_seconds", 0.0)
    monkeypatch.setattr(script_mcp.server.latency_config, "default_seconds", 0.0)

    yield engine
    engine.dispose()


def _subscribe(scene_id: str, event_bus: AnalysisEventBus | None = None):
    bus = event_bus or weather_agent.default_event_bus
    return bus, bus.subscribe(scene_channel(scene_id))


async def _drain(bus: AnalysisEventBus, channel: str, queue) -> list:
    events = []
    while not queue.empty():
        events.append(await queue.get())
    bus.unsubscribe(channel, queue)
    return events


# --- Acceptance Criteria: detects Scene 42 and raises an incident ---------


async def test_check_scene_detects_rain_and_creates_incident_for_scene_42(seeded_db):
    detection = await WeatherAgent().check_scene("SC-042")

    assert detection.incident is not None
    assert detection.incident.scene_id == "SC-042"
    assert detection.risk_level == "high"
    assert detection.rain_probability == 0.92

    with get_session(seeded_db) as db:
        rows = db.execute(select(Incident).where(Incident.scene_id == "SC-042")).scalars().all()
    assert len(rows) == 1


async def test_check_scene_incident_fields_are_well_formed(seeded_db):
    detection = await WeatherAgent().check_scene("SC-042")

    incident = detection.incident
    assert incident.incident_id.startswith("INC-")
    assert incident.type == "WEATHER"
    assert incident.headline
    assert "92%" in incident.detail
    assert isinstance(incident.detected_at, datetime)
    assert incident.resolved is False


async def test_default_threshold_matches_weather_mcp_high_risk_threshold():
    assert DEFAULT_RAIN_PROBABILITY_THRESHOLD == weather_mcp.HIGH_RISK_THRESHOLD


# --- Acceptance Criteria: threshold is configurable ------------------------


async def test_check_scene_respects_configurable_threshold_no_incident(seeded_db):
    detection = await WeatherAgent(rain_probability_threshold=0.99).check_scene("SC-042")

    assert detection.incident is None
    with get_session(seeded_db) as db:
        rows = db.execute(select(Incident).where(Incident.scene_id == "SC-042")).scalars().all()
    assert rows == []


# --- Acceptance Criteria: reports status transitions to the Event Stream ---


async def test_check_scene_publishes_status_sequence_ending_completed(seeded_db):
    bus, queue = _subscribe("SC-042")

    await WeatherAgent(event_bus=bus).check_scene("SC-042")

    events = await _drain(bus, scene_channel("SC-042"), queue)
    statuses = [e.status for e in events]
    assert statuses[0] == "QUEUED"
    assert statuses[-1] == "COMPLETED"
    assert "ANALYZING" in statuses
    assert all(e.agent == "WeatherAgent" for e in events)


async def test_check_scene_events_use_scene_id_as_resource(seeded_db):
    bus, queue = _subscribe("SC-042")

    await WeatherAgent(event_bus=bus).check_scene("SC-042")

    events = await _drain(bus, scene_channel("SC-042"), queue)
    assert all(e.resource == "SC-042" for e in events)


# --- Idempotency -------------------------------------------------------------


async def test_check_scene_does_not_duplicate_incident_on_repeat_call(seeded_db):
    first = await WeatherAgent().check_scene("SC-042")
    second = await WeatherAgent().check_scene("SC-042")

    assert second.incident.incident_id == first.incident.incident_id
    with get_session(seeded_db) as db:
        rows = db.execute(select(Incident).where(Incident.scene_id == "SC-042")).scalars().all()
    assert len(rows) == 1


# --- Edge cases (mocked MCP calls to reach branches the mock data can't) ---


async def test_check_scene_with_no_location_completes_without_incident(seeded_db):
    detection = await WeatherAgent().check_scene("SC-099")

    assert detection.incident is None
    assert detection.rain_probability == 0.0


async def test_check_scene_unknown_scene_id_publishes_failed_and_raises(seeded_db):
    bus, queue = _subscribe("SC-404")

    with pytest.raises(ValueError, match="Unknown scene_id"):
        await WeatherAgent(event_bus=bus).check_scene("SC-404")

    events = await _drain(bus, scene_channel("SC-404"), queue)
    assert events[-1].status == "FAILED"


async def test_check_scene_mcp_failure_publishes_failed_and_raises(seeded_db, monkeypatch):
    async def boom(**kwargs):
        raise RuntimeError("weather service unavailable")

    monkeypatch.setattr(weather_agent, "get_forecast", boom)
    bus, queue = _subscribe("SC-042")

    with pytest.raises(RuntimeError, match="weather service unavailable"):
        await WeatherAgent(event_bus=bus).check_scene("SC-042")

    events = await _drain(bus, scene_channel("SC-042"), queue)
    assert events[-1].status == "FAILED"
    assert "weather service unavailable" in events[-1].message


async def test_check_scene_calls_subscribe_weather_alert(seeded_db, monkeypatch):
    calls = []
    original = weather_agent.subscribe_weather_alert

    async def spy(**kwargs):
        calls.append(kwargs)
        return await original(**kwargs)

    monkeypatch.setattr(weather_agent, "subscribe_weather_alert", spy)

    await WeatherAgent().check_scene("SC-042")

    assert calls == [{"location_id": "LOC-003"}]


async def test_check_scene_boundary_probability_equals_threshold_creates_incident(
    seeded_db, monkeypatch
):
    async def fake_get_scene(**kwargs):
        return {"scene_id": "SC-042", "name": "Rooftop confrontation", "location": "LOC-003"}

    async def fake_forecast(**kwargs):
        return {"location_id": "LOC-003", "rain_probability": 0.8}

    async def fake_risk(**kwargs):
        return {"location_id": "LOC-003", "risk_level": "high", "reason": "boundary case"}

    async def fake_subscribe(**kwargs):
        return {"location_id": "LOC-003", "subscribed": True}

    monkeypatch.setattr(weather_agent, "get_scene", fake_get_scene)
    monkeypatch.setattr(weather_agent, "get_forecast", fake_forecast)
    monkeypatch.setattr(weather_agent, "get_weather_risk", fake_risk)
    monkeypatch.setattr(weather_agent, "subscribe_weather_alert", fake_subscribe)

    detection = await WeatherAgent(rain_probability_threshold=0.8).check_scene("SC-042")

    assert detection.incident is not None


async def test_check_scene_below_threshold_returns_no_incident_with_risk_info(
    seeded_db, monkeypatch
):
    async def fake_get_scene(**kwargs):
        return {"scene_id": "SC-042", "name": "Rooftop confrontation", "location": "LOC-003"}

    async def fake_forecast(**kwargs):
        return {"location_id": "LOC-003", "rain_probability": 0.4}

    async def fake_risk(**kwargs):
        return {"location_id": "LOC-003", "risk_level": "low", "reason": "clear enough"}

    async def fake_subscribe(**kwargs):
        return {"location_id": "LOC-003", "subscribed": True}

    monkeypatch.setattr(weather_agent, "get_scene", fake_get_scene)
    monkeypatch.setattr(weather_agent, "get_forecast", fake_forecast)
    monkeypatch.setattr(weather_agent, "get_weather_risk", fake_risk)
    monkeypatch.setattr(weather_agent, "subscribe_weather_alert", fake_subscribe)

    detection = await WeatherAgent().check_scene("SC-042")

    assert detection.incident is None
    assert detection.risk_level == "low"
    assert detection.rain_probability == 0.4

    with get_session(seeded_db) as db:
        rows = db.execute(select(Incident).where(Incident.scene_id == "SC-042")).scalars().all()
    assert rows == []
