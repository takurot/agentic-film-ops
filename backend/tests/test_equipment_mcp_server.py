"""Unit tests for the Equipment MCP tool functions, plus one end-to-end test
that spawns the server as a real stdio subprocess against the real (seeded)
dev DB — proof that mcp_common's bootstrap and the DB-backed tools actually
work over the MCP transport, not just at the Python function level.
"""

import json
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sqlalchemy import create_engine

import app.db as db_module
from app.db import get_session, init_db
from app.mcp_servers import equipment
from app.mcp_servers.equipment import (
    check_availability,
    get_equipment,
    get_vendor_response,
    request_extension,
    request_reservation,
    reserve_equipment,
)
from app.seed import seed_scene_42

SC_042_START = "2026-09-02T14:00"
SC_042_END = "2026-09-02T18:00"


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42 (EQ-001, EQ-004 both booked
    for SC-042). `app.db.engine` is monkeypatched since equipment.py's tool
    functions call `get_session()` with no explicit bind, which resolves
    `engine` from app.db's module globals at call time.
    """
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(engine)
    with get_session(engine) as db:
        seed_scene_42(db)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clear_vendor_requests():
    """`_VENDOR_REQUESTS` is process-global mutable state (unlike the
    read-only mock tables in weather.py/script.py) — reset it between tests
    so outcomes/request_ids from one test can't leak into another.
    """
    equipment._VENDOR_REQUESTS.clear()
    yield
    equipment._VENDOR_REQUESTS.clear()


async def test_get_equipment_returns_spec_shape_for_eq_001(seeded_db):
    result = await get_equipment(equipment_id="EQ-001")

    assert result == {
        "equipment_id": "EQ-001",
        "name": "ARRI Alexa 35",
        "vendor": "Cinema Rental Tokyo",
        "daily_cost": 1200,
        "availability": [{"scene_id": "SC-042", "start": SC_042_START, "end": SC_042_END}],
    }


async def test_get_equipment_unknown_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown equipment_id"):
        await get_equipment(equipment_id="EQ-DOES-NOT-EXIST")


async def test_check_availability_flags_conflict_within_existing_booking(seeded_db):
    result = await check_availability(
        equipment_id="EQ-001", start="2026-09-02T15:00", end="2026-09-02T16:00"
    )

    assert result["available"] is False
    assert result["conflicts"] == [{"scene_id": "SC-042", "start": SC_042_START, "end": SC_042_END}]


async def test_check_availability_free_for_non_overlapping_window(seeded_db):
    result = await check_availability(
        equipment_id="EQ-001", start="2026-09-03T09:00", end="2026-09-03T12:00"
    )

    assert result == {
        "equipment_id": "EQ-001",
        "start": "2026-09-03T09:00",
        "end": "2026-09-03T12:00",
        "available": True,
        "conflicts": [],
    }


async def test_check_availability_boundary_touch_is_not_a_conflict(seeded_db):
    """A window that starts exactly when the existing booking ends does not overlap it."""
    result = await check_availability(
        equipment_id="EQ-001", start=SC_042_END, end="2026-09-02T20:00"
    )

    assert result["available"] is True


async def test_check_availability_rejects_start_not_before_end(seeded_db):
    with pytest.raises(ValueError, match="start must be before end"):
        await check_availability(
            equipment_id="EQ-001", start="2026-09-03T12:00", end="2026-09-03T09:00"
        )


async def test_check_availability_unknown_equipment_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown equipment_id"):
        await check_availability(
            equipment_id="EQ-DOES-NOT-EXIST", start="2026-09-03T09:00", end="2026-09-03T12:00"
        )


async def test_check_availability_rejects_malformed_timestamp(seeded_db):
    with pytest.raises(ValueError, match="Invalid ISO-8601 timestamp"):
        await check_availability(
            equipment_id="EQ-001", start="not-a-timestamp", end="2026-09-03T12:00"
        )


async def test_request_reservation_confirms_free_window(seeded_db):
    ack = await request_reservation(
        equipment_id="EQ-001", scene_id="SC-050", start="2026-09-03T09:00", end="2026-09-03T12:00"
    )

    assert ack["equipment_id"] == "EQ-001"
    assert ack["status"] == "contacted_vendor"
    assert ack["request_id"]

    response = await get_vendor_response(request_id=ack["request_id"])
    assert response == {
        "request_id": ack["request_id"],
        "equipment_id": "EQ-001",
        "outcome": "confirmed",
        "reason": "Requested window is free; vendor confirmed the booking.",
    }


async def test_request_reservation_denies_conflicting_window(seeded_db):
    ack = await request_reservation(
        equipment_id="EQ-001", scene_id="SC-050", start="2026-09-02T15:00", end="2026-09-02T16:00"
    )

    response = await get_vendor_response(request_id=ack["request_id"])
    assert response["outcome"] == "denied"
    assert "SC-042" in response["reason"]


async def test_request_reservation_rejects_start_not_before_end(seeded_db):
    with pytest.raises(ValueError, match="start must be before end"):
        await request_reservation(
            equipment_id="EQ-001",
            scene_id="SC-050",
            start="2026-09-03T12:00",
            end="2026-09-03T09:00",
        )


async def test_request_reservation_unknown_equipment_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown equipment_id"):
        await request_reservation(
            equipment_id="EQ-DOES-NOT-EXIST",
            scene_id="SC-050",
            start="2026-09-03T09:00",
            end="2026-09-03T12:00",
        )


async def test_request_extension_confirms_when_new_window_is_clear(seeded_db):
    ack = await request_extension(
        equipment_id="EQ-004", scene_id="SC-042", new_end="2026-09-02T19:00"
    )

    response = await get_vendor_response(request_id=ack["request_id"])
    assert response["outcome"] == "confirmed"


async def test_request_extension_excludes_the_scenes_own_original_block(seeded_db):
    """Extending SC-042's own booking must not conflict with SC-042's own
    pre-extension block (proves exclude_scene_id actually excludes it)."""
    ack = await request_extension(
        equipment_id="EQ-001", scene_id="SC-042", new_end="2026-09-02T18:30"
    )

    response = await get_vendor_response(request_id=ack["request_id"])
    assert response["outcome"] == "confirmed"


async def test_request_extension_denies_when_new_window_hits_another_booking(seeded_db):
    # Reserve a block for another scene right after SC-042 on EQ-001, then try
    # to extend SC-042 into it.
    await reserve_equipment(
        equipment_id="EQ-001", scene_id="SC-051", start=SC_042_END, end="2026-09-02T20:00"
    )

    ack = await request_extension(
        equipment_id="EQ-001", scene_id="SC-042", new_end="2026-09-02T19:00"
    )

    response = await get_vendor_response(request_id=ack["request_id"])
    assert response["outcome"] == "denied"
    assert "SC-051" in response["reason"]


async def test_request_extension_unknown_scene_booking_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="No existing booking"):
        await request_extension(
            equipment_id="EQ-001", scene_id="SC-999", new_end="2026-09-02T19:00"
        )


async def test_get_vendor_response_unknown_request_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown request_id"):
        await get_vendor_response(request_id="VREQ-doesnotexist")


async def test_reserve_equipment_mutates_availability_and_persists(seeded_db):
    result = await reserve_equipment(
        equipment_id="EQ-001", scene_id="SC-050", start="2026-09-03T09:00", end="2026-09-03T12:00"
    )

    assert result["availability"] == [
        {"scene_id": "SC-042", "start": SC_042_START, "end": SC_042_END},
        {"scene_id": "SC-050", "start": "2026-09-03T09:00", "end": "2026-09-03T12:00"},
    ]

    # Re-query from a fresh session to confirm the mutation was actually
    # committed, not just returned from an in-memory object.
    with get_session(seeded_db) as db:
        eq = db.get(equipment.Equipment, "EQ-001")
        assert eq.availability == result["availability"]


async def test_reserve_equipment_upserts_by_scene_id_for_a_confirmed_extension(seeded_db):
    """Applying a confirmed extension re-reserves the same scene_id's slot
    rather than appending a duplicate block."""
    result = await reserve_equipment(
        equipment_id="EQ-001", scene_id="SC-042", start=SC_042_START, end="2026-09-02T18:30"
    )

    assert result["availability"] == [
        {"scene_id": "SC-042", "start": SC_042_START, "end": "2026-09-02T18:30"}
    ]


async def test_reserve_equipment_conflict_raises_and_does_not_mutate(seeded_db):
    with pytest.raises(ValueError, match="Cannot reserve"):
        await reserve_equipment(
            equipment_id="EQ-001",
            scene_id="SC-050",
            start="2026-09-02T15:00",
            end="2026-09-02T16:00",
        )

    with get_session(seeded_db) as db:
        eq = db.get(equipment.Equipment, "EQ-001")
        assert eq.availability == [{"scene_id": "SC-042", "start": SC_042_START, "end": SC_042_END}]


async def test_reserve_equipment_rejects_start_not_before_end(seeded_db):
    with pytest.raises(ValueError, match="start must be before end"):
        await reserve_equipment(
            equipment_id="EQ-001",
            scene_id="SC-050",
            start="2026-09-03T12:00",
            end="2026-09-03T09:00",
        )


async def test_reserve_equipment_unknown_equipment_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown equipment_id"):
        await reserve_equipment(
            equipment_id="EQ-DOES-NOT-EXIST",
            scene_id="SC-050",
            start="2026-09-03T09:00",
            end="2026-09-03T12:00",
        )


async def test_equipment_mcp_server_serves_tools_over_real_stdio_transport():
    # Seed the real dev DB (file-backed, so the subprocess sees it once it
    # opens the same file) rather than the monkeypatched in-memory engine
    # above, which only exists in this test process.
    init_db()
    with get_session() as db:
        seed_scene_42(db)

    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_servers.equipment"])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert {
            "get_equipment",
            "check_availability",
            "request_extension",
            "request_reservation",
            "get_vendor_response",
            "reserve_equipment",
        } <= tool_names

        result = await session.call_tool("get_equipment", {"equipment_id": "EQ-001"})
        payload = json.loads(result.content[0].text)
        assert payload["equipment_id"] == "EQ-001"
        assert payload["vendor"] == "Cinema Rental Tokyo"
