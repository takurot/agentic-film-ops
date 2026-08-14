"""Unit tests for the Location MCP tool functions, plus one end-to-end test
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
from app.mcp_servers import location
from app.mcp_servers.location import (
    check_availability,
    confirm_location,
    contact_location_manager,
    find_alternative_locations,
    get_location,
    hold_location,
)
from app.seed import SCENE_42_BLOCK, seed_scene_42


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42 (LOC-003 rooftop) plus
    Studio B (LOC-STUDIO-B), the seeded indoor alternative. `app.db.engine`
    is monkeypatched since location.py's tool functions call `get_session()`
    with no explicit bind, which resolves `engine` from app.db's module
    globals at call time.
    """
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(engine)
    with get_session(engine) as db:
        seed_scene_42(db)
    yield engine
    engine.dispose()


async def test_get_location_returns_spec_shape_plus_status(seeded_db):
    result = await get_location(location_id="LOC-003")

    assert result == {
        "id": "LOC-003",
        "name": "Rooftop, Shibuya Tower",
        "type": "outdoor",
        "manager": "LOCMGR-001",
        "availability": [SCENE_42_BLOCK],
        "daily_cost": 3000,
        "weather_dependent": True,
        "status": "available",
    }


async def test_get_location_raises_for_unknown_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown location_id"):
        await get_location(location_id="LOC-DOES-NOT-EXIST")


async def test_check_availability_conflicts_with_overlapping_window(seeded_db):
    result = await check_availability(
        location_id="LOC-003", start="2026-09-02T15:00", end="2026-09-02T17:00"
    )

    assert result["available"] is False
    assert result["conflicts"] == [SCENE_42_BLOCK]


async def test_check_availability_free_for_non_overlapping_window(seeded_db):
    result = await check_availability(
        location_id="LOC-003", start="2026-09-03T09:00", end="2026-09-03T11:00"
    )

    assert result == {
        "location_id": "LOC-003",
        "start": "2026-09-03T09:00",
        "end": "2026-09-03T11:00",
        "available": True,
        "conflicts": [],
    }


async def test_check_availability_touching_boundary_is_available(seeded_db):
    # Scene 42's block ends at 18:00; a window starting exactly then doesn't
    # overlap under open-interval semantics.
    result = await check_availability(
        location_id="LOC-003", start="2026-09-02T18:00", end="2026-09-02T20:00"
    )

    assert result["available"] is True


async def test_check_availability_window_fully_containing_block_conflicts(seeded_db):
    result = await check_availability(
        location_id="LOC-003", start="2026-09-02T10:00", end="2026-09-02T22:00"
    )

    assert result["available"] is False
    assert result["conflicts"] == [SCENE_42_BLOCK]


async def test_check_availability_rejects_malformed_datetime(seeded_db):
    with pytest.raises(ValueError, match="Invalid ISO datetime"):
        await check_availability(location_id="LOC-003", start="not-a-date", end="2026-09-02T18:00")


async def test_check_availability_rejects_inverted_range(seeded_db):
    with pytest.raises(ValueError, match="start must be before end"):
        await check_availability(
            location_id="LOC-003", start="2026-09-02T18:00", end="2026-09-02T14:00"
        )


async def test_contact_location_manager_returns_scripted_response_for_scene_42(seeded_db):
    result = await contact_location_manager(location_id="LOC-003", message="Can we extend to 8pm?")

    assert result == {
        "location_id": "LOC-003",
        "manager_id": "LOCMGR-001",
        "message": "Can we extend to 8pm?",
        "response": location._MOCK_MANAGER_RESPONSES["LOC-003"],
        "contact_status": "responded",
    }


async def test_contact_location_manager_defaults_for_location_without_scripted_reply(seeded_db):
    result = await contact_location_manager(location_id="LOC-STUDIO-B", message="Are you free?")

    assert result["response"] == location._DEFAULT_MANAGER_RESPONSE
    assert result["contact_status"] == "responded"
    assert result["manager_id"] == "LOCMGR-002"


def test_contact_location_manager_has_a_longer_configured_latency_than_default():
    override = location.server.latency_config.seconds_for("contact_location_manager")
    default = location.server.latency_config.default_seconds
    assert override > default


async def test_find_alternative_locations_includes_studio_b_for_rooftop(seeded_db):
    result = await find_alternative_locations(location_id="LOC-003")

    assert result == {
        "location_id": "LOC-003",
        "alternatives": [
            {
                "id": "LOC-STUDIO-B",
                "name": "Studio B",
                "type": "indoor",
                "daily_cost": 2200,
                "weather_dependent": False,
            }
        ],
    }


async def test_find_alternative_locations_excludes_itself_and_other_weather_dependent(seeded_db):
    result = await find_alternative_locations(location_id="LOC-STUDIO-B")

    assert result == {"location_id": "LOC-STUDIO-B", "alternatives": []}


async def test_hold_location_sets_status_and_persists(seeded_db):
    result = await hold_location(
        location_id="LOC-STUDIO-B",
        scene_id="SC-042",
        start="2026-09-02T14:00",
        end="2026-09-02T18:00",
    )

    assert result == {"location_id": "LOC-STUDIO-B", "scene_id": "SC-042", "status": "held"}

    refreshed = await get_location(location_id="LOC-STUDIO-B")
    assert refreshed["status"] == "held"
    assert {"scene_id": "SC-042", "start": "2026-09-02T14:00", "end": "2026-09-02T18:00"} in (
        refreshed["availability"]
    )


async def test_confirm_location_sets_status_and_persists(seeded_db):
    result = await confirm_location(
        location_id="LOC-STUDIO-B",
        scene_id="SC-042",
        start="2026-09-02T14:00",
        end="2026-09-02T18:00",
    )

    assert result == {"location_id": "LOC-STUDIO-B", "scene_id": "SC-042", "status": "confirmed"}

    refreshed = await get_location(location_id="LOC-STUDIO-B")
    assert refreshed["status"] == "confirmed"


async def test_hold_then_confirm_location_ends_in_confirmed_status(seeded_db):
    await hold_location(
        location_id="LOC-STUDIO-B",
        scene_id="SC-042",
        start="2026-09-02T14:00",
        end="2026-09-02T18:00",
    )
    held = await get_location(location_id="LOC-STUDIO-B")
    assert held["status"] == "held"

    await confirm_location(
        location_id="LOC-STUDIO-B",
        scene_id="SC-042",
        start="2026-09-02T14:00",
        end="2026-09-02T18:00",
    )
    confirmed = await get_location(location_id="LOC-STUDIO-B")
    assert confirmed["status"] == "confirmed"
    # Confirming shouldn't duplicate the busy block hold already added.
    assert (
        confirmed["availability"].count(
            {"scene_id": "SC-042", "start": "2026-09-02T14:00", "end": "2026-09-02T18:00"}
        )
        == 1
    )


async def test_hold_location_after_confirm_makes_it_unavailable(seeded_db):
    await hold_location(
        location_id="LOC-STUDIO-B",
        scene_id="SC-042",
        start="2026-09-02T14:00",
        end="2026-09-02T18:00",
    )

    availability = await check_availability(
        location_id="LOC-STUDIO-B", start="2026-09-02T15:00", end="2026-09-02T16:00"
    )
    assert availability["available"] is False


@pytest.mark.parametrize("tool", [get_location, hold_location, confirm_location])
async def test_mutation_and_lookup_tools_raise_for_unknown_location_id(seeded_db, tool):
    kwargs = {"location_id": "LOC-DOES-NOT-EXIST"}
    if tool in (hold_location, confirm_location):
        kwargs.update(scene_id="SC-042", start="2026-09-02T14:00", end="2026-09-02T18:00")
    with pytest.raises(ValueError, match="Unknown location_id"):
        await tool(**kwargs)


async def test_check_availability_raises_for_unknown_location_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown location_id"):
        await check_availability(
            location_id="LOC-DOES-NOT-EXIST", start="2026-09-02T14:00", end="2026-09-02T18:00"
        )


async def test_contact_location_manager_raises_for_unknown_location_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown location_id"):
        await contact_location_manager(location_id="LOC-DOES-NOT-EXIST", message="hi")


async def test_find_alternative_locations_raises_for_unknown_location_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown location_id"):
        await find_alternative_locations(location_id="LOC-DOES-NOT-EXIST")


async def test_location_mcp_server_serves_tools_over_real_stdio_transport():
    # Seed the real dev DB (file-backed, so the subprocess sees it once it
    # opens the same file) rather than the monkeypatched in-memory engine
    # above, which only exists in this test process.
    init_db()
    with get_session() as db:
        seed_scene_42(db)

    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_servers.location"])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert {
            "get_location",
            "check_availability",
            "contact_location_manager",
            "find_alternative_locations",
            "hold_location",
            "confirm_location",
        } <= tool_names

        # Stable fields only — LOC-003's status/availability can be mutated
        # by other test runs / manual demo sessions against this shared file.
        result = await session.call_tool("get_location", {"location_id": "LOC-003"})
        payload = json.loads(result.content[0].text)
        assert payload["id"] == "LOC-003"
        assert payload["name"] == "Rooftop, Shibuya Tower"
        assert payload["weather_dependent"] is True
        assert "status" in payload

        # Fresh mutation within this test — safe to assert on directly.
        hold_result = await session.call_tool(
            "hold_location",
            {
                "location_id": "LOC-STUDIO-B",
                "scene_id": "SC-042",
                "start": "2026-09-02T14:00",
                "end": "2026-09-02T18:00",
            },
        )
        hold_payload = json.loads(hold_result.content[0].text)
        assert hold_payload["status"] == "held"
