"""Unit tests for the Script MCP tool functions, plus one end-to-end test
that spawns the server as a real stdio subprocess against the real (seeded)
dev DB — proof that mcp_common's bootstrap and the DB-backed tools actually
work over the MCP transport, not just at the Python function level.
"""

import json
import sys
from datetime import datetime

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sqlalchemy import create_engine

import app.db as db_module
from app.db import get_session, init_db
from app.mcp_servers.script import (
    get_continuity_constraints,
    get_scene,
    get_scene_dependencies,
    get_scene_requirements,
)
from app.models import Scene
from app.seed import seed_scene_42


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42, plus a bare SC-099 scene
    (no continuity data) to exercise get_continuity_constraints' default
    branch. `app.db.engine` is monkeypatched since script.py's tool
    functions call `get_session()` with no explicit bind, which resolves
    `engine` from app.db's module globals at call time.
    """
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(engine)
    with get_session(engine) as db:
        seed_scene_42(db)
        db.add(
            Scene(
                scene_id="SC-099",
                name="Unrelated scene",
                type="indoor",
                duration_hours=1,
                scheduled=datetime(2026, 9, 3, 9, 0),
            )
        )
        db.commit()
    yield engine
    engine.dispose()


async def test_get_scene_returns_spec_shape_for_scene_42(seeded_db):
    result = await get_scene(scene_id="SC-042")

    assert result == {
        "scene_id": "SC-042",
        "name": "Rooftop confrontation",
        "type": "outdoor",
        "duration_hours": 4,
        "actors": ["ACT-001", "ACT-002"],
        "location": "LOC-003",
        "equipment": ["EQ-001", "EQ-004"],
        "crew": ["CREW-001"],
        "scheduled": "2026-09-02T14:00",
    }


async def test_get_scene_requirements_derived_from_scene_42(seeded_db):
    result = await get_scene_requirements(scene_id="SC-042")

    assert result["scene_id"] == "SC-042"
    assert result["duration_hours"] == 4
    assert result["location_type"] == "outdoor"
    assert result["weather_dependent"] is True
    assert set(result["required_equipment"]) == {"EQ-001", "EQ-004"}
    assert result["required_crew"] == ["CREW-001"]


async def test_get_scene_dependencies_returns_actor_equipment_location_links(seeded_db):
    result = await get_scene_dependencies(scene_id="SC-042")

    assert result == {
        "scene_id": "SC-042",
        "actors": ["ACT-001", "ACT-002"],
        "equipment": ["EQ-001", "EQ-004"],
        "location": "LOC-003",
    }


async def test_get_continuity_constraints_returns_scene_42_example(seeded_db):
    result = await get_continuity_constraints(scene_id="SC-042")

    assert result == {
        "scene_id": "SC-042",
        "must_precede": ["SC-043"],
        "must_follow": ["SC-041"],
        "same_day_as": [],
        "notes": "Wardrobe continuity requires SC-042 and SC-043 to be shot on the same day.",
    }


async def test_get_continuity_constraints_defaults_for_scene_without_constraints(seeded_db):
    result = await get_continuity_constraints(scene_id="SC-099")

    assert result == {
        "scene_id": "SC-099",
        "must_precede": [],
        "must_follow": [],
        "same_day_as": [],
        "notes": "",
    }


@pytest.mark.parametrize(
    "tool",
    [get_scene, get_scene_requirements, get_scene_dependencies, get_continuity_constraints],
)
async def test_unknown_scene_id_raises_value_error(seeded_db, tool):
    with pytest.raises(ValueError, match="Unknown scene_id"):
        await tool(scene_id="SC-DOES-NOT-EXIST")


async def test_script_mcp_server_serves_tools_over_real_stdio_transport():
    # Seed the real dev DB (file-backed, so the subprocess sees it once it
    # opens the same file) rather than the monkeypatched in-memory engine
    # above, which only exists in this test process.
    init_db()
    with get_session() as db:
        seed_scene_42(db)

    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_servers.script"])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert {
            "get_scene",
            "get_scene_requirements",
            "get_scene_dependencies",
            "get_continuity_constraints",
        } <= tool_names

        result = await session.call_tool("get_scene", {"scene_id": "SC-042"})
        payload = json.loads(result.content[0].text)
        assert payload["scene_id"] == "SC-042"
        assert payload["location"] == "LOC-003"
