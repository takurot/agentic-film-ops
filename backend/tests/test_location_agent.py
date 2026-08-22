"""Unit tests for the Location Agent (SPEC §6.3, Issue #12).

Mirrors `test_actor_agent.py`'s DB-seeding/fixture pattern for the Location
MCP this Agent wraps, adapted for two differences confirmed by reading
`app/mcp_servers/location.py`:
- `contact_location_manager()` is synchronous (no WAITING/poll-until-
  RESPONSE_RECEIVED pattern like Actor MCP) -- so no polling/timeout tests.
- `propose_alternative()` (the rain-scenario AC) has no Actor-MCP analog;
  its candidate *selection* is deterministic (SPEC §9.6's "small Constraint
  Solver, not fake numbers" precedent for structured-data judgment calls),
  with Gemini used only to write the natural-language justification.
"""

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine

import app.db as db_module
from app.agents.location import (
    AGENT_NAME,
    LocationAgent,
    LocationAgentConfig,
    LocationAlternativeResult,
    ManagerResponse,
)
from app.db import get_session, init_db
from app.events import AnalysisEventBus
from app.gemini_client import GeminiResponseValidationError, GeminiUnavailableError
from app.mcp_servers import location
from app.seed import SCENE_42_BLOCK, seed_scene_42

ANALYSIS_ID = "AN-001"

# LOC-003 (rooftop) is busy 2026-09-02T14:00-18:00 (SC-042) per seed data.
CONFLICTING_WINDOW = ("2026-09-02T15:00", "2026-09-02T19:00")
NON_CONFLICTING_WINDOW = ("2026-09-05T09:00", "2026-09-05T12:00")

VALID_MANAGER_JSON = '{"status": "AVAILABLE", "notes": ["Confirmed for the rescheduled window"]}'


def make_gemini_stub(response_text: str | None = None, side_effect=None) -> AsyncMock:
    stub = AsyncMock()
    if side_effect is not None:
        stub.generate_content = AsyncMock(side_effect=side_effect)
    else:
        fake_response = type("FakeResponse", (), {"text": response_text})()
        stub.generate_content = AsyncMock(return_value=fake_response)
    return stub


@pytest.fixture
def seeded_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(engine)
    with get_session(engine) as db:
        seed_scene_42(db)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def zero_mcp_latency(monkeypatch):
    """Location MCP's own artificial per-tool latency (contact_location_manager
    is configured slower than the default) would otherwise make every test
    here slow; zero it out the same way `test_actor_agent.py` does."""
    monkeypatch.setattr(location.server.latency_config, "default_seconds", 0.0)
    monkeypatch.setattr(location.server.latency_config, "overrides", {})


@pytest.fixture
def event_bus() -> AnalysisEventBus:
    return AnalysisEventBus()


@pytest.fixture
def collected_events(event_bus):
    queue = event_bus.subscribe(ANALYSIS_ID)
    events = []

    async def drain():
        while not queue.empty():
            events.append(queue.get_nowait())

    return events, drain


# --- resolve_availability: happy path -------------------------------------


async def test_resolve_availability_skips_manager_contact_when_no_conflict(seeded_db, event_bus):
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        location_id="LOC-003",
        scene_id="SC-042",
        requested_start=NON_CONFLICTING_WINDOW[0],
        requested_end=NON_CONFLICTING_WINDOW[1],
    )

    assert result.location_id == "LOC-003"
    assert result.manager_contacted is False
    assert result.manager_reply is None
    assert result.availability["available"] is True
    gemini.generate_content.assert_not_awaited()


async def test_resolve_availability_contacts_manager_on_conflict_and_parses_reply(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        location_id="LOC-003",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert result.manager_contacted is True
    assert result.manager_reply == ManagerResponse(
        status="AVAILABLE",
        notes=["Confirmed for the rescheduled window"],
        raw_message=result.manager_reply.raw_message,
    )
    assert result.request_message is not None
    assert "SC-042" in result.request_message

    await drain()
    statuses = [e.status for e in events]
    assert statuses == [
        "QUEUED",
        "QUERYING_MCP",
        "THINKING",
        "WAITING_EXTERNAL",
        "RESPONSE_RECEIVED",
        "ANALYZING",
        "COMPLETED",
    ]
    assert all(e.agent == AGENT_NAME for e in events)
    assert all(e.resource == "LOC-003" for e in events)
    waiting_event = events[3]
    assert waiting_event.type == "EXTERNAL_REQUEST"
    other_event_types = {e.type for e in events if e.type != "EXTERNAL_REQUEST"}
    assert other_event_types == {"LOCATION_AVAILABILITY"}


async def test_resolve_availability_manager_reply_fails_closed_on_invalid_json_syntax(
    seeded_db, event_bus
):
    gemini = make_gemini_stub("not json at all")
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(GeminiResponseValidationError):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            location_id="LOC-003",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )


async def test_resolve_availability_manager_reply_fails_closed_on_schema_mismatch(
    seeded_db, event_bus
):
    gemini = make_gemini_stub('{"status": "MAYBE"}')
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(GeminiResponseValidationError):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            location_id="LOC-003",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )


async def test_resolve_availability_manager_reply_strips_markdown_code_fence(seeded_db, event_bus):
    fenced = f"```json\n{VALID_MANAGER_JSON}\n```"
    gemini = make_gemini_stub(fenced)
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        location_id="LOC-003",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert result.manager_reply.status == "AVAILABLE"


async def test_resolve_availability_unknown_location_id_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(ValueError, match="Unknown location_id"):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            location_id="LOC-DOES-NOT-EXIST",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )

    await drain()
    assert events[-1].status == "FAILED"
    assert "Unknown location_id" in events[-1].message


async def test_resolve_availability_mid_flow_failure_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events, monkeypatch
):
    """A failure at a *later* step (not just the first MCP call) must still
    be caught by the same FAILED-then-reraise wrapper."""
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    async def boom(*args, **kwargs):
        raise RuntimeError("location manager contact backend is down")

    monkeypatch.setattr(location, "contact_location_manager", boom)

    with pytest.raises(RuntimeError, match="location manager contact backend is down"):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            location_id="LOC-003",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )

    await drain()
    assert events[-1].status == "FAILED"


async def test_resolve_availability_gemini_unavailable_publishes_failed_and_sanitizes_message(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(side_effect=GeminiUnavailableError("boom"))
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(GeminiUnavailableError):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            location_id="LOC-003",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )

    await drain()
    assert events[-1].status == "FAILED"
    assert "boom" not in events[-1].message


async def test_parse_step_honors_minimum_display_time(seeded_db, event_bus, monkeypatch):
    slept = []
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=lambda s: slept.append(s)))
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    config = LocationAgentConfig(parse_min_display_seconds=2.0)
    agent_ = LocationAgent(gemini_client=gemini, config=config, event_bus=event_bus)

    await agent_.resolve_availability(
        ANALYSIS_ID,
        location_id="LOC-003",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert slept
    assert slept[-1] == pytest.approx(2.0, abs=0.05)


# --- propose_alternative: rain-scenario AC ---------------------------------


async def test_propose_alternative_finds_and_proposes_studio_b_for_rooftop(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub("Studio B is indoor and unaffected by the rain forecast.")
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.propose_alternative(
        ANALYSIS_ID,
        location_id="LOC-003",
        scene_id="SC-042",
        requested_start=SCENE_42_BLOCK["start"],
        requested_end=SCENE_42_BLOCK["end"],
    )

    assert isinstance(result, LocationAlternativeResult)
    assert result.original_location_id == "LOC-003"
    assert result.proposed_location_id == "LOC-STUDIO-B"
    assert result.justification
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.id == "LOC-STUDIO-B"
    assert candidate.type == "indoor"
    assert candidate.weather_dependent is False
    assert candidate.available is True

    await drain()
    statuses = [e.status for e in events]
    assert statuses == [
        "QUEUED",
        "QUERYING_MCP",
        "QUERYING_MCP",
        "THINKING",
        "ANALYZING",
        "COMPLETED",
    ]
    assert all(e.agent == AGENT_NAME for e in events)
    # Search steps are about the original location; selection/completion are
    # about the proposed candidate.
    assert [e.resource for e in events] == [
        "LOC-003",
        "LOC-003",
        "LOC-003",
        "LOC-003",
        "LOC-STUDIO-B",
        "LOC-STUDIO-B",
    ]
    assert all(e.type == "LOCATION_ALTERNATIVE" for e in events)


async def test_propose_alternative_no_alternatives_found_completes_without_gemini_call(
    seeded_db, event_bus, collected_events
):
    """LOC-STUDIO-B has no alternatives of its own (excludes itself and
    other weather-dependent locations) -- exercises the zero-candidates
    branch using real seed data, not a monkeypatch."""
    events, drain = collected_events
    gemini = make_gemini_stub("unused")
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.propose_alternative(
        ANALYSIS_ID,
        location_id="LOC-STUDIO-B",
        scene_id="SC-042",
        requested_start=SCENE_42_BLOCK["start"],
        requested_end=SCENE_42_BLOCK["end"],
    )

    assert result.candidates == []
    assert result.proposed_location_id is None
    assert result.justification
    gemini.generate_content.assert_not_awaited()

    await drain()
    assert [e.status for e in events] == ["QUEUED", "QUERYING_MCP", "THINKING", "COMPLETED"]


async def test_propose_alternative_alternatives_found_but_none_available_completes_without_gemini_call(
    seeded_db, event_bus
):
    """LOC-STUDIO-B exists as a candidate for LOC-003 but is itself booked
    for the exact requested window -- exercises the found-but-unavailable
    branch via the real hold_location() tool, not a monkeypatch."""
    await location.hold_location(
        location_id="LOC-STUDIO-B",
        scene_id="SC-999",
        start=SCENE_42_BLOCK["start"],
        end=SCENE_42_BLOCK["end"],
    )
    gemini = make_gemini_stub("unused")
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.propose_alternative(
        ANALYSIS_ID,
        location_id="LOC-003",
        scene_id="SC-042",
        requested_start=SCENE_42_BLOCK["start"],
        requested_end=SCENE_42_BLOCK["end"],
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].available is False
    assert result.proposed_location_id is None
    gemini.generate_content.assert_not_awaited()


async def test_propose_alternative_unknown_location_id_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub("unused")
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(ValueError, match="Unknown location_id"):
        await agent_.propose_alternative(
            ANALYSIS_ID,
            location_id="LOC-DOES-NOT-EXIST",
            scene_id="SC-042",
            requested_start=SCENE_42_BLOCK["start"],
            requested_end=SCENE_42_BLOCK["end"],
        )

    await drain()
    assert events[-1].status == "FAILED"


async def test_propose_alternative_mid_flow_mcp_failure_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events, monkeypatch
):
    events, drain = collected_events
    gemini = make_gemini_stub("unused")
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    async def boom(*args, **kwargs):
        raise RuntimeError("resource graph is down")

    monkeypatch.setattr(location, "find_alternative_locations", boom)

    with pytest.raises(RuntimeError, match="resource graph is down"):
        await agent_.propose_alternative(
            ANALYSIS_ID,
            location_id="LOC-003",
            scene_id="SC-042",
            requested_start=SCENE_42_BLOCK["start"],
            requested_end=SCENE_42_BLOCK["end"],
        )

    await drain()
    assert events[-1].status == "FAILED"


async def test_propose_alternative_gemini_unavailable_publishes_failed_and_sanitizes_message(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(side_effect=GeminiUnavailableError("boom"))
    agent_ = LocationAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(GeminiUnavailableError):
        await agent_.propose_alternative(
            ANALYSIS_ID,
            location_id="LOC-003",
            scene_id="SC-042",
            requested_start=SCENE_42_BLOCK["start"],
            requested_end=SCENE_42_BLOCK["end"],
        )

    await drain()
    assert events[-1].status == "FAILED"
    assert "boom" not in events[-1].message


# --- MCP-exclusivity (AC #1) -----------------------------------------------


def test_location_agent_module_never_imports_the_db_layer_or_other_mcp_servers():
    """AC: 'Uses Location MCP exclusively for access/action.' Statically
    verifies the Agent module has no import of app.db/app.models/sqlalchemy
    or any other app.mcp_servers module -- all location data must flow
    through app.mcp_servers.location's tool functions.
    """
    source_path = Path(__file__).parent.parent / "app" / "agents" / "location.py"
    tree = ast.parse(source_path.read_text())
    imported_modules = set()
    # `from app.mcp_servers import location` imports specific names from the
    # `app.mcp_servers` package -- track those separately from whole-module
    # imports so importing the *location* submodule isn't mistaken for
    # importing "another" mcp_servers module.
    from_mcp_servers_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "app.mcp_servers":
                from_mcp_servers_names.update(alias.name for alias in node.names)
            else:
                imported_modules.add(node.module)

    assert "app.db" not in imported_modules
    assert "app.models" not in imported_modules
    assert not any(m == "sqlalchemy" or m.startswith("sqlalchemy.") for m in imported_modules)
    assert from_mcp_servers_names <= {"location"}
    other_mcp_servers = {
        m
        for m in imported_modules
        if m.startswith("app.mcp_servers") and m != "app.mcp_servers.location"
    }
    assert not other_mcp_servers


# --- config validation --------------------------------------------------------


def test_location_agent_config_rejects_negative_parse_min_display_seconds():
    with pytest.raises(ValueError):
        LocationAgentConfig(parse_min_display_seconds=-1)
