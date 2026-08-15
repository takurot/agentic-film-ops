"""Unit tests for the Equipment Agent (SPEC §6.3, Issue #11).

Mirrors `test_actor_agent.py`'s DB-seeding/module-global-reset fixture
pattern for the Equipment MCP this Agent wraps, and `test_gemini_client.py`'s
pattern for mocking Gemini calls (no real API calls here).
"""

import ast
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine

import app.db as db_module
from app.agents.equipment import (
    AGENT_NAME,
    EquipmentAgent,
    EquipmentAgentConfig,
)
from app.db import get_session, init_db
from app.events import AnalysisEventBus
from app.gemini_client import GeminiUnavailableError
from app.mcp_servers import equipment
from app.seed import seed_scene_42

ANALYSIS_ID = "AN-001"

SC_042_START = "2026-09-02T14:00"
SC_042_END = "2026-09-02T18:00"

VALID_SUMMARY_JSON = '{"summary": "Vendor confirmed the booking is free."}'


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
def clear_vendor_requests():
    equipment._VENDOR_REQUESTS.clear()
    yield
    equipment._VENDOR_REQUESTS.clear()


@pytest.fixture(autouse=True)
def zero_mcp_latency(monkeypatch):
    """The Equipment MCP's own artificial per-tool latency (inventory 1.0s /
    contact-vendor 1.0s / vendor-wait 3.5s / default 0.5s) would otherwise
    make every test here slow; zero it out (mirrors `test_actor_agent.py`).
    """
    monkeypatch.setattr(equipment.server.latency_config, "default_seconds", 0.0)
    monkeypatch.setattr(equipment.server.latency_config, "overrides", {})


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


# --- resolve_reservation: happy path — new reservation on a free slot -------


async def test_resolve_reservation_happy_path_confirms_new_reservation(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-050",
        requested_start="2026-09-03T09:00",
        requested_end="2026-09-03T12:00",
    )

    assert result.equipment_id == "EQ-001"
    assert result.scene_id == "SC-050"
    assert result.availability_check["available"] is True
    assert result.availability_check["conflicts"] == []
    assert result.request_kind == "reservation"
    assert result.request_id
    assert result.vendor_outcome == "confirmed"
    assert result.vendor_reason == "Requested window is free; vendor confirmed the booking."
    assert result.vendor_summary == "Vendor confirmed the booking is free."
    assert result.reserved is True
    assert result.reservation == {
        "equipment_id": "EQ-001",
        "scene_id": "SC-050",
        "start": "2026-09-03T09:00",
        "end": "2026-09-03T12:00",
        "availability": [
            {"scene_id": "SC-042", "start": SC_042_START, "end": SC_042_END},
            {"scene_id": "SC-050", "start": "2026-09-03T09:00", "end": "2026-09-03T12:00"},
        ],
    }

    await drain()
    statuses = [e.status for e in events]
    assert statuses == [
        "QUEUED",
        "QUERYING_MCP",
        "THINKING",
        "QUERYING_MCP",
        "WAITING_EXTERNAL",
        "RESPONSE_RECEIVED",
        "QUERYING_MCP",
        "COMPLETED",
    ]
    assert all(e.agent == AGENT_NAME for e in events)
    assert all(e.resource == "EQ-001" for e in events)
    waiting_event = events[4]
    assert waiting_event.type == "EXTERNAL_REQUEST"
    response_event = events[5]
    assert response_event.type == "EXTERNAL_REQUEST"
    assert "confirmed" in response_event.message
    assert "Reserved EQ-001 for SC-050" in events[-1].message


# --- resolve_reservation: happy path — extension of scene's own booking -----


async def test_resolve_reservation_extends_scenes_own_booking(seeded_db, event_bus):
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-004",
        scene_id="SC-042",
        requested_start=SC_042_START,
        requested_end="2026-09-02T19:00",
    )

    assert result.request_kind == "extension"
    assert result.vendor_outcome == "confirmed"
    assert result.reserved is True
    assert result.reservation["availability"] == [
        {"scene_id": "SC-042", "start": SC_042_START, "end": "2026-09-02T19:00"}
    ]


# --- reservation vs. extension routing (AC #2 correctness) ------------------


async def test_resolve_reservation_routes_moved_start_as_reservation_not_extension(
    seeded_db, event_bus
):
    """A shifted start for a scene's own equipment slot must go through
    request_reservation() (whose upsert-by-scene_id in reserve_equipment
    handles a moved window correctly), not request_extension() (which
    silently reuses the *old* start and would misrepresent the requested
    window to the vendor)."""
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-042",
        requested_start="2026-09-02T16:00",  # moved later than SC_042_START
        requested_end="2026-09-02T20:00",
    )

    assert result.request_kind == "reservation"
    # Only conflict is SC-042's own prior block -> self-hold override applies.
    assert result.vendor_outcome == "denied"
    assert result.reserved is True
    assert result.reservation["availability"] == [
        {"scene_id": "SC-042", "start": "2026-09-02T16:00", "end": "2026-09-02T20:00"}
    ]


# --- self-conflict override (AC #2 correctness, denial vs. self-hold) -------


async def test_resolve_reservation_treats_self_only_conflict_as_non_blocking(
    seeded_db, event_bus, collected_events
):
    """Re-reserving a scene's own existing window (unshifted) triggers a
    vendor `denied` citing that scene's own booking (request_reservation has
    no exclude_scene_id) — this must not block the reservation."""
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-042",
        requested_start="2026-09-02T15:00",  # overlaps SC-042's own block, not its exact start
        requested_end="2026-09-02T19:00",
    )

    assert result.vendor_outcome == "denied"
    assert "SC-042" in result.vendor_reason
    assert result.reserved is True
    assert result.reservation is not None

    await drain()
    assert events[-1].status == "COMPLETED"


async def test_resolve_reservation_denies_when_conflict_is_a_different_scene(
    seeded_db, event_bus, collected_events
):
    """A genuine external conflict (a different scene's booking) must still
    be respected as a real denial — no self-hold override applies."""
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-099",
        requested_start="2026-09-02T15:00",
        requested_end="2026-09-02T16:00",
    )

    assert result.vendor_outcome == "denied"
    assert "SC-042" in result.vendor_reason
    assert result.reserved is False
    assert result.reservation is None

    await drain()
    assert events[-1].status == "COMPLETED"
    assert "Vendor denied" in events[-1].message


async def test_resolve_reservation_denies_extension_hitting_another_booking(
    seeded_db, event_bus, collected_events
):
    """request_extension() DOES exclude the caller's own scene_id, so a
    denial here is always a genuine external conflict — never a self-hold."""
    events, drain = collected_events
    await equipment.reserve_equipment(
        equipment_id="EQ-001", scene_id="SC-051", start=SC_042_END, end="2026-09-02T20:00"
    )
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-042",
        requested_start=SC_042_START,
        requested_end="2026-09-02T19:00",
    )

    assert result.request_kind == "extension"
    assert result.vendor_outcome == "denied"
    assert "SC-051" in result.vendor_reason
    assert result.reserved is False
    assert result.reservation is None

    await drain()
    assert events[-1].status == "COMPLETED"


# --- MCP-exclusivity (AC #1) -------------------------------------------------


def test_equipment_agent_module_never_imports_the_db_layer_directly():
    """AC: 'Uses Equipment MCP tools exclusively for access/action.'
    Statically verifies the Agent module has no import of app.db/app.models
    — all equipment data must flow through app.mcp_servers.equipment's tool
    functions."""
    source_path = Path(__file__).parent.parent / "app" / "agents" / "equipment.py"
    tree = ast.parse(source_path.read_text())
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert "app.db" not in imported_modules
    assert "app.models" not in imported_modules


# --- event schema conformance (AC #3, SPEC §8.1/§8.2) -----------------------


async def test_all_published_events_conform_to_spec_status_enum(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-050",
        requested_start="2026-09-03T09:00",
        requested_end="2026-09-03T12:00",
    )

    await drain()
    allowed_statuses = {
        "QUEUED",
        "THINKING",
        "QUERYING_MCP",
        "WAITING_EXTERNAL",
        "RESPONSE_RECEIVED",
        "ANALYZING",
        "COMPLETED",
        "FAILED",
    }
    assert all(e.status in allowed_statuses for e in events)
    assert all(e.resource == "EQ-001" for e in events)
    assert all(e.agent == AGENT_NAME for e in events)


# --- Gemini summarization -----------------------------------------------------


async def test_summarize_vendor_response_falls_back_to_raw_reason_on_invalid_json_syntax(
    seeded_db, event_bus
):
    gemini = make_gemini_stub("not json at all")
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-050",
        requested_start="2026-09-03T09:00",
        requested_end="2026-09-03T12:00",
    )

    assert result.vendor_summary == result.vendor_reason


async def test_summarize_vendor_response_falls_back_to_raw_reason_on_schema_mismatch(
    seeded_db, event_bus
):
    gemini = make_gemini_stub('{"not_summary": "oops"}')
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-050",
        requested_start="2026-09-03T09:00",
        requested_end="2026-09-03T12:00",
    )

    assert result.vendor_summary == result.vendor_reason


async def test_summarize_vendor_response_strips_markdown_code_fence(seeded_db, event_bus):
    fenced = f"```json\n{VALID_SUMMARY_JSON}\n```"
    gemini = make_gemini_stub(fenced)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    result = await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-050",
        requested_start="2026-09-03T09:00",
        requested_end="2026-09-03T12:00",
    )

    assert result.vendor_summary == "Vendor confirmed the booking is free."


async def test_gemini_unavailable_publishes_failed_and_reraises_with_sanitized_message(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(side_effect=GeminiUnavailableError("boom: raw provider detail"))
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(GeminiUnavailableError):
        await agent_.resolve_reservation(
            ANALYSIS_ID,
            equipment_id="EQ-001",
            scene_id="SC-050",
            requested_start="2026-09-03T09:00",
            requested_end="2026-09-03T12:00",
        )

    await drain()
    assert events[-1].status == "FAILED"
    # The raw Gemini/provider error text must not leak into the Dashboard-facing message.
    assert "boom" not in events[-1].message
    assert "raw provider detail" not in events[-1].message
    assert events[-1].message == "Equipment Agent failed: Gemini is unavailable"


# --- MCP failure propagation (AC + SPEC §5) ----------------------------------


async def test_unknown_equipment_id_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events
):
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    with pytest.raises(ValueError, match="Unknown equipment_id"):
        await agent_.resolve_reservation(
            ANALYSIS_ID,
            equipment_id="EQ-DOES-NOT-EXIST",
            scene_id="SC-050",
            requested_start="2026-09-03T09:00",
            requested_end="2026-09-03T12:00",
        )

    await drain()
    assert events[-1].status == "FAILED"
    assert "Unknown equipment_id" in events[-1].message


async def test_vendor_contact_failure_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events, monkeypatch
):
    """A failure at a *later* step (not just the first MCP call) must still
    be caught by the same FAILED-then-reraise wrapper."""
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    async def boom(*args, **kwargs):
        raise RuntimeError("rental vendor gateway is down")

    monkeypatch.setattr(equipment, "request_reservation", boom)

    with pytest.raises(RuntimeError, match="rental vendor gateway is down"):
        await agent_.resolve_reservation(
            ANALYSIS_ID,
            equipment_id="EQ-001",
            scene_id="SC-050",
            requested_start="2026-09-03T09:00",
            requested_end="2026-09-03T12:00",
        )

    await drain()
    assert events[-1].status == "FAILED"


async def test_get_vendor_response_failure_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events, monkeypatch
):
    """The WAITING beat's own MCP call (distinct from the contact call) must
    also be covered by the FAILED-then-reraise wrapper."""
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    async def boom(*args, **kwargs):
        raise RuntimeError("vendor response lookup backend is down")

    monkeypatch.setattr(equipment, "get_vendor_response", boom)

    with pytest.raises(RuntimeError, match="vendor response lookup backend is down"):
        await agent_.resolve_reservation(
            ANALYSIS_ID,
            equipment_id="EQ-001",
            scene_id="SC-050",
            requested_start="2026-09-03T09:00",
            requested_end="2026-09-03T12:00",
        )

    await drain()
    assert events[-1].status == "FAILED"


async def test_reserve_equipment_failure_publishes_failed_and_reraises(
    seeded_db, event_bus, collected_events, monkeypatch
):
    """A failure applying the confirmed reservation (last step) must also be
    caught, not just failures earlier in the flow."""
    events, drain = collected_events
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    agent_ = EquipmentAgent(gemini_client=gemini, event_bus=event_bus)

    async def boom(*args, **kwargs):
        raise RuntimeError("resource graph write failed")

    monkeypatch.setattr(equipment, "reserve_equipment", boom)

    with pytest.raises(RuntimeError, match="resource graph write failed"):
        await agent_.resolve_reservation(
            ANALYSIS_ID,
            equipment_id="EQ-001",
            scene_id="SC-050",
            requested_start="2026-09-03T09:00",
            requested_end="2026-09-03T12:00",
        )

    await drain()
    assert events[-1].status == "FAILED"


# --- config validation --------------------------------------------------------


def test_equipment_agent_config_rejects_negative_summary_min_display():
    with pytest.raises(ValueError):
        EquipmentAgentConfig(summary_min_display_seconds=-1)


# --- with_min_display_time floor applied to the summarize step ---------------


async def test_summarize_step_honors_minimum_display_time(seeded_db, event_bus, monkeypatch):
    import asyncio

    slept = []
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=lambda s: slept.append(s)))
    gemini = make_gemini_stub(VALID_SUMMARY_JSON)
    config = EquipmentAgentConfig(summary_min_display_seconds=2.0)
    agent_ = EquipmentAgent(gemini_client=gemini, config=config, event_bus=event_bus)

    await agent_.resolve_reservation(
        ANALYSIS_ID,
        equipment_id="EQ-001",
        scene_id="SC-050",
        requested_start="2026-09-03T09:00",
        requested_end="2026-09-03T12:00",
    )

    assert slept
    assert slept[-1] == pytest.approx(2.0, abs=0.05)
