"""Script MCP (mock) per SPEC §5.5.

Reads Scene structure from the Production Resource Graph (SPEC §4, the same
SQLite DB seeded by `app.seed`) rather than an independent mock table, since
the Resource Graph is itself the single source of truth other components
(Schedule Agent, Constraint Solver — SPEC §6.6) read from. `get_scene()` and
`get_scene_dependencies()` are shaped directly from that graph.
`get_continuity_constraints()` returns data not modeled in the graph at all
(SPEC §4.7), so it's backed by a small in-memory lookup table instead.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Scene
from mcp_common.server import MCPCommonServer

server = MCPCommonServer("script")


def _require_scene(db: Session, scene_id: str) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError(f"Unknown scene_id: {scene_id}")
    return scene


@server.tool(resource_arg="scene_id")
async def get_scene(scene_id: str) -> dict[str, Any]:
    """Scene metadata, shaped per SPEC §4.1. `db` stays open while building the
    dict since `actors`/`equipment`/`crew` are lazily-loaded relationships that
    would raise DetachedInstanceError if touched after the session closes."""
    with get_session() as db:
        scene = _require_scene(db, scene_id)
        return {
            "scene_id": scene.scene_id,
            "name": scene.name,
            "type": scene.type,
            "duration_hours": scene.duration_hours,
            "actors": [a.id for a in scene.actors],
            "location": scene.location_id,
            "equipment": [e.id for e in scene.equipment],
            "crew": [c.id for c in scene.crew],
            "scheduled": scene.scheduled.isoformat(timespec="minutes"),
        }


@server.tool(resource_arg="scene_id")
async def get_scene_requirements(scene_id: str) -> dict[str, Any]:
    """What's required to shoot the scene, derived from its resource graph links."""
    with get_session() as db:
        scene = _require_scene(db, scene_id)
        return {
            "scene_id": scene.scene_id,
            "duration_hours": scene.duration_hours,
            "location_type": scene.location.type if scene.location else None,
            "weather_dependent": scene.location.weather_dependent if scene.location else False,
            "required_equipment": [e.id for e in scene.equipment],
            "required_crew": [c.id for c in scene.crew],
        }


@server.tool(resource_arg="scene_id")
async def get_scene_dependencies(scene_id: str) -> dict[str, Any]:
    """Resource links this scene depends on (SPEC §5.5 AC: actor/equipment/
    location). Crew is available via get_scene() but omitted here to match
    SPEC §6.5 step 2's Actor/Equipment/Location impact-analysis scope."""
    with get_session() as db:
        scene = _require_scene(db, scene_id)
        return {
            "scene_id": scene.scene_id,
            "actors": [a.id for a in scene.actors],
            "equipment": [e.id for e in scene.equipment],
            "location": scene.location_id,
        }


# Mock continuity data (SPEC §4.7) — not modeled in the Production Resource
# Graph (Scene has no must_precede/must_follow/same_day_as columns), so this
# is a separate lookup table keyed by scene_id. SC-042's values are SPEC
# §4.7's own example verbatim; SC-041/SC-043 are forward references to
# scenes not yet in the seed data (only Scene 42 is seeded so far).
_CONTINUITY_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "SC-042": {
        "must_precede": ["SC-043"],
        "must_follow": ["SC-041"],
        "same_day_as": [],
        "notes": "Wardrobe continuity requires SC-042 and SC-043 to be shot on the same day.",
    },
}
_DEFAULT_CONTINUITY: dict[str, Any] = {
    "must_precede": [],
    "must_follow": [],
    "same_day_as": [],
    "notes": "",
}


@server.tool(resource_arg="scene_id")
async def get_continuity_constraints(scene_id: str) -> dict[str, Any]:
    """Continuity constraints for a scene, shaped per SPEC §4.7."""
    with get_session() as db:
        _require_scene(db, scene_id)  # only validates existence; no relationship access needed
    constraints = _CONTINUITY_CONSTRAINTS.get(scene_id, _DEFAULT_CONTINUITY)
    return {"scene_id": scene_id, **constraints}


if __name__ == "__main__":
    server.run()
