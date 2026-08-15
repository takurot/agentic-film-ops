"""Unit tests for the Script Agent (SPEC §6.5, Issue #32).

Uses the same `seeded_db` pattern as `test_script_mcp_server.py` (duplicated
locally per this project's "many small files" convention rather than
imported, matching `test_actor_mcp_server.py` / `test_equipment_mcp_server.py`).

Note: `app.mcp_servers.script`'s tool functions also publish `MCPCallEvent`s
to `mcp_common.events.default_event_sink` on every call (a separate pub/sub
from the `AnalysisEventBus` this file asserts against) — that stream isn't
bridged into the per-analysis bus yet, so it never interferes with the
assertions below.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine

import app.db as db_module
from app.agents.script import ContinuityConstraints, ScriptMCPPort, analyze_scene
from app.db import get_session, init_db
from app.events import AnalysisEventBus
from app.models import Scene
from app.seed import seed_scene_42


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42, plus a bare SC-099 scene
    with no continuity data and no linked actors/equipment/location."""
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


class _FailingMCP:
    """A `ScriptMCPPort` fake that fails on a chosen step, to prove the
    agent's FAILED handling isn't accidentally narrowed to `ValueError`
    (the only exception type the real Script MCP tools can raise)."""

    def __init__(self, fail_on: str, exc: Exception):
        self.fail_on = fail_on
        self.exc = exc

    async def get_scene(self, scene_id: str) -> dict:
        if self.fail_on == "get_scene":
            raise self.exc
        return {"scene_id": scene_id, "name": "x", "type": "outdoor", "duration_hours": 1}

    async def get_scene_requirements(self, scene_id: str) -> dict:
        if self.fail_on == "get_scene_requirements":
            raise self.exc
        return {
            "scene_id": scene_id,
            "duration_hours": 1,
            "location_type": "outdoor",
            "weather_dependent": True,
            "required_equipment": [],
            "required_crew": [],
        }

    async def get_scene_dependencies(self, scene_id: str) -> dict:
        if self.fail_on == "get_scene_dependencies":
            raise self.exc
        return {"scene_id": scene_id, "actors": [], "equipment": [], "location": None}

    async def get_continuity_constraints(self, scene_id: str) -> dict:
        if self.fail_on == "get_continuity_constraints":
            raise self.exc
        return {
            "scene_id": scene_id,
            "must_precede": [],
            "must_follow": [],
            "same_day_as": [],
            "notes": "",
        }


def _drain(bus: AnalysisEventBus, analysis_id: str) -> list:
    queue = bus._queues[analysis_id][0]
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    return events


async def test_analyze_scene_returns_correct_dependency_list_for_scene_42(seeded_db):
    result = await analyze_scene("SC-042", analysis_id="AN-1")

    assert result.dependencies.scene_id == "SC-042"
    assert result.dependencies.actors == ["ACT-001", "ACT-002"]
    assert result.dependencies.equipment == ["EQ-001", "EQ-004"]
    assert result.dependencies.location == "LOC-003"


async def test_analyze_scene_returns_empty_dependency_list_for_scene_without_resources(seeded_db):
    result = await analyze_scene("SC-099", analysis_id="AN-1")

    assert result.dependencies.actors == []
    assert result.dependencies.equipment == []
    assert result.dependencies.location is None


async def test_analyze_scene_returns_continuity_constraints_matching_spec_schema(seeded_db):
    result = await analyze_scene("SC-042", analysis_id="AN-1")

    assert result.continuity.scene_id == "SC-042"
    assert result.continuity.must_precede == ["SC-043"]
    assert result.continuity.must_follow == ["SC-041"]
    assert result.continuity.same_day_as == []
    assert "Wardrobe continuity" in result.continuity.notes


async def test_analyze_scene_defaults_continuity_for_scene_without_constraints(seeded_db):
    result = await analyze_scene("SC-099", analysis_id="AN-1")

    assert result.continuity == ContinuityConstraints(
        scene_id="SC-099", must_precede=[], must_follow=[], same_day_as=[], notes=""
    )


async def test_analyze_scene_includes_scene_metadata_and_typed_requirements(seeded_db):
    result = await analyze_scene("SC-042", analysis_id="AN-1")

    assert result.scene.scene_id == "SC-042"
    assert result.scene.name == "Rooftop confrontation"
    assert result.scene.duration_hours == 4
    assert result.scene.scheduled == "2026-09-02T14:00"

    assert result.requirements.location_type == "outdoor"
    assert result.requirements.weather_dependent is True
    assert set(result.requirements.required_equipment) == {"EQ-001", "EQ-004"}


async def test_analyze_scene_publishes_expected_event_sequence(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")

    await analyze_scene("SC-042", analysis_id="AN-1", event_bus=bus)

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == [
        "QUEUED",
        "QUERYING_MCP",
        "QUERYING_MCP",
        "QUERYING_MCP",
        "ANALYZING",
        "COMPLETED",
    ]
    assert all(e.agent == "ScriptAgent" for e in events)
    assert all(e.resource == "SC-042" for e in events)
    assert all(e.message for e in events)


async def test_analyze_scene_publishes_only_to_its_own_analysis_id(seeded_db):
    bus = AnalysisEventBus()
    queue_a = bus.subscribe("AN-A")
    bus.subscribe("AN-B")

    await analyze_scene("SC-042", analysis_id="AN-A", event_bus=bus)

    assert not bus._queues["AN-B"][0].qsize()
    assert queue_a.qsize() > 0


async def test_analyze_scene_publishes_failed_event_and_reraises_on_unknown_scene(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")

    with pytest.raises(ValueError, match="Unknown scene_id"):
        await analyze_scene("SC-DOES-NOT-EXIST", analysis_id="AN-1", event_bus=bus)

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "FAILED"]
    assert "Unknown scene_id" in events[-1].message


async def test_analyze_scene_publishes_failed_event_for_non_value_error(seeded_db):
    """Proves the FAILED handling isn't narrowed to `ValueError` specifically
    (the only exception type the real Script MCP tools happen to raise)."""
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    mcp: ScriptMCPPort = _FailingMCP("get_scene_dependencies", RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await analyze_scene("SC-042", analysis_id="AN-1", event_bus=bus, mcp=mcp)

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "QUERYING_MCP", "FAILED"]
    assert "boom" in events[-1].message


async def test_analyze_scene_does_not_short_circuit_when_only_last_call_fails(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    mcp: ScriptMCPPort = _FailingMCP("get_continuity_constraints", RuntimeError("late failure"))

    with pytest.raises(RuntimeError, match="late failure"):
        await analyze_scene("SC-042", analysis_id="AN-1", event_bus=bus, mcp=mcp)

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "QUERYING_MCP", "QUERYING_MCP", "FAILED"]


async def test_analyze_scene_runs_concurrently_for_different_analysis_ids_without_cross_talk(
    seeded_db,
):
    import asyncio

    bus = AnalysisEventBus()
    queue_42 = bus.subscribe("AN-42")
    queue_99 = bus.subscribe("AN-99")

    await asyncio.gather(
        analyze_scene("SC-042", analysis_id="AN-42", event_bus=bus),
        analyze_scene("SC-099", analysis_id="AN-99", event_bus=bus),
    )

    events_42 = []
    while not queue_42.empty():
        events_42.append(queue_42.get_nowait())
    events_99 = []
    while not queue_99.empty():
        events_99.append(queue_99.get_nowait())

    assert all(e.resource == "SC-042" for e in events_42)
    assert all(e.resource == "SC-099" for e in events_99)
