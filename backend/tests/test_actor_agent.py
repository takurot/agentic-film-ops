"""Unit tests for the Actor Agent (SPEC §6.2, Issue #10).

Mirrors `test_actor_mcp_server.py`'s DB-seeding/module-global-reset fixture
pattern for the Actor MCP this Agent wraps, and `test_gemini_client.py`'s
pattern for mocking Gemini calls (no real API calls here).
"""

import ast
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine

import app.db as db_module
from app.agents.actor import (
    AGENT_NAME,
    ActorAgent,
    ActorAgentConfig,
    ManagerAvailability,
)
from app.db import get_session, init_db
from app.events import AnalysisEventBus
from app.gemini_client import GeminiUnavailableError
from app.mcp_servers import actor
from app.models import Actor
from app.seed import seed_scene_42

ANALYSIS_ID = "AN-001"

# Emma Carter (ACT-001) is busy 2026-09-02T14:00-18:00 (SC-042) per seed data.
CONFLICTING_WINDOW = ("2026-09-02T15:00", "2026-09-02T19:00")
NON_CONFLICTING_WINDOW = ("2026-09-05T09:00", "2026-09-05T12:00")

VALID_MANAGER_JSON = (
    '{"status": "AVAILABLE", "window_start": "16:00", "window_end": "20:00", '
    '"constraints": ["Hard stop 20:00"]}'
)


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
        db.add(
            Actor(
                id="ACT-099",
                name="Unmanaged Extra",
                manager=None,
                availability=[],
                status="unconfirmed",
            )
        )
        db.commit()
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clear_contact_sessions():
    actor._contact_sessions.clear()
    yield
    actor._contact_sessions.clear()


@pytest.fixture(autouse=True)
def zero_manager_response_delay(monkeypatch):
    monkeypatch.setattr(actor, "_MANAGER_RESPONSE_DELAY_SECONDS", 0.0)


@pytest.fixture(autouse=True)
def zero_mcp_latency(monkeypatch):
    """The Actor MCP's own artificial per-tool latency (calendar 1.2s /
    contract 0.8s / etc.) would otherwise make every test here slow;
    zero it out the same way `_MANAGER_RESPONSE_DELAY_SECONDS` is zeroed.
    """
    monkeypatch.setattr(actor.server.latency_config, "default_seconds", 0.0)
    monkeypatch.setattr(actor.server.latency_config, "overrides", {})


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


async def test_resolve_availability_happy_path_contacts_manager_and_parses_reply(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = ActorAgent(gemini_client=gemini, config=ActorAgentConfig(), event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        actor_id="ACT-001",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert result.actor_id == "ACT-001"
    assert result.manager_contacted is True
    assert result.manager_reply == ManagerAvailability(
        status="AVAILABLE",
        window_start="16:00",
        window_end="20:00",
        constraints=["Hard stop 20:00"],
        raw_message=result.manager_reply.raw_message,
    )
    assert "4 PM" in result.manager_reply.raw_message
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
    assert all(e.resource == "ACT-001" for e in events)
    assert events[-1].message == "AVAILABLE_AFTER_16:00"
    waiting_event = events[3]
    assert waiting_event.type == "EXTERNAL_REQUEST"


async def test_resolve_availability_passes_through_contract_constraints(seeded_db, event_bus):
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        actor_id="ACT-002",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    # ACT-002 has no scripted contract terms -> MCP default fallback.
    assert result.constraints == {
        "actor_id": "ACT-002",
        "max_daily_hours": 12,
        "meal_break_after_hours": 6,
        "notes": "",
    }


async def test_resolve_availability_skips_manager_contact_when_no_conflict(seeded_db, event_bus):
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        actor_id="ACT-001",
        scene_id="SC-042",
        requested_start=NON_CONFLICTING_WINDOW[0],
        requested_end=NON_CONFLICTING_WINDOW[1],
    )

    assert result.manager_contacted is False
    assert result.manager_reply is None
    gemini.generate_content.assert_not_awaited()


# --- MCP-exclusivity (AC #1) -----------------------------------------------


def test_actor_agent_module_never_imports_the_db_layer_directly():
    """AC: 'Uses Actor MCP tools exclusively for access/action.' Statically
    verifies the Agent module has no import of app.db/app.models — all
    actor data must flow through app.mcp_servers.actor's tool functions.
    """
    source_path = Path(__file__).parent.parent / "app" / "agents" / "actor.py"
    tree = ast.parse(source_path.read_text())
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert "app.db" not in imported_modules
    assert "app.models" not in imported_modules


# --- Gemini parsing ---------------------------------------------------------


async def test_parse_manager_reply_falls_back_to_unknown_on_invalid_json_syntax(
    seeded_db, event_bus
):
    gemini = make_gemini_stub("not json at all")
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        actor_id="ACT-001",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert result.manager_reply.status == "UNKNOWN"
    assert result.manager_reply.raw_message


async def test_parse_manager_reply_falls_back_to_unknown_on_schema_mismatch(seeded_db, event_bus):
    # Valid JSON, but "status" isn't one of the allowed literal values.
    gemini = make_gemini_stub('{"status": "MAYBE"}')
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        actor_id="ACT-001",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert result.manager_reply.status == "UNKNOWN"


async def test_parse_manager_reply_strips_markdown_code_fence(seeded_db, event_bus):
    fenced = f"```json\n{VALID_MANAGER_JSON}\n```"
    gemini = make_gemini_stub(fenced)
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_availability(
        ANALYSIS_ID,
        actor_id="ACT-001",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert result.manager_reply.status == "AVAILABLE"
    assert result.manager_reply.window_start == "16:00"


async def test_gemini_unavailable_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(side_effect=GeminiUnavailableError("boom"))
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(GeminiUnavailableError):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            actor_id="ACT-001",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )

    await drain()
    assert events[-1].status == "FAILED"
    # The raw Gemini/provider error text must not leak into the Dashboard-facing message.
    assert "boom" not in events[-1].message


# --- MCP failure propagation (AC + SPEC §5) ---------------------------------


async def test_unknown_actor_id_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(ValueError, match="Unknown actor_id"):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            actor_id="ACT-DOES-NOT-EXIST",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )

    await drain()
    assert events[-1].status == "FAILED"
    assert "Unknown actor_id" in events[-1].message


async def test_contact_manager_failure_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events, monkeypatch
):
    """A failure at a *later* step (not just the first MCP call) must still
    be caught by the same FAILED-then-reraise wrapper."""
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    agent_ = ActorAgent(gemini_client=gemini, event_bus=event_bus)

    async def boom(*args, **kwargs):
        raise RuntimeError("manager contact backend is down")

    monkeypatch.setattr(actor, "contact_manager", boom)

    with pytest.raises(RuntimeError, match="manager contact backend is down"):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            actor_id="ACT-001",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )

    await drain()
    assert events[-1].status == "FAILED"


# --- polling / timeout -------------------------------------------------------


async def test_await_manager_response_times_out_without_real_sleep(
    seeded_db, event_bus, collected_events, monkeypatch
):
    events, drain = collected_events
    slept = []
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=lambda s: slept.append(s)))
    # Freeze the manager reply as permanently pending for this test only.
    monkeypatch.setattr(actor, "_MANAGER_RESPONSE_DELAY_SECONDS", 1_000_000.0)
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    config = ActorAgentConfig(poll_interval_seconds=1.0, max_wait_seconds=3.0)
    agent_ = ActorAgent(gemini_client=gemini, config=config, event_bus=event_bus)

    with pytest.raises(TimeoutError):
        await agent_.resolve_availability(
            ANALYSIS_ID,
            actor_id="ACT-001",
            scene_id="SC-042",
            requested_start=CONFLICTING_WINDOW[0],
            requested_end=CONFLICTING_WINDOW[1],
        )

    assert slept  # the loop actually waited (via mocked sleep), not busy-spun
    assert sum(slept) <= 4.0  # bounded, not unbounded
    await drain()
    assert events[-1].status == "FAILED"


# --- config validation --------------------------------------------------------


def test_actor_agent_config_rejects_non_positive_poll_interval():
    with pytest.raises(ValueError):
        ActorAgentConfig(poll_interval_seconds=0)


def test_actor_agent_config_rejects_non_positive_max_wait():
    with pytest.raises(ValueError):
        ActorAgentConfig(max_wait_seconds=-1)


# --- with_min_display_time floor applied to the parse step -------------------


async def test_parse_step_honors_minimum_display_time(seeded_db, event_bus, monkeypatch):
    slept = []
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=lambda s: slept.append(s)))
    gemini = make_gemini_stub(VALID_MANAGER_JSON)
    config = ActorAgentConfig(parse_min_display_seconds=2.0)
    agent_ = ActorAgent(gemini_client=gemini, config=config, event_bus=event_bus)

    await agent_.resolve_availability(
        ANALYSIS_ID,
        actor_id="ACT-001",
        scene_id="SC-042",
        requested_start=CONFLICTING_WINDOW[0],
        requested_end=CONFLICTING_WINDOW[1],
    )

    assert slept
    assert slept[-1] == pytest.approx(2.0, abs=0.05)
