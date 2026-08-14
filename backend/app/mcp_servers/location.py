"""Location MCP (mock) per SPEC §5.3.

Reads Location structure from the Production Resource Graph (SPEC §4, the
same SQLite DB seeded by `app.seed`) rather than an independent mock table,
mirroring `app.mcp_servers.script`'s rationale: the Resource Graph is the
single source of truth other components read from, so `get_location()`,
`check_availability()`, and `find_alternative_locations()` are shaped
directly from it. `contact_location_manager()` is the exception — a
manager's reply text has no graph representation, so it's backed by a small
in-memory lookup table instead (same pattern as weather.py's
`_MOCK_FORECASTS`).

`Location.status` (`available` / `held` / `confirmed`) is an extension
beyond SPEC §4.4's example JSON, added because `hold_location()` /
`confirm_location()` need somewhere to record booking state — see
`app.models.Location`'s docstring comment.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Location
from mcp_common.latency import LatencyConfig
from mcp_common.server import MCPCommonServer

# contact_location_manager simulates the longest wait of this server's tools
# (SPEC §7.1's Actor Agent pattern shows "Contacting manager... WAITING FOR
# MANAGER" as its slowest leg), so it gets a longer configured delay than
# the default lookup/mutation tools.
server = MCPCommonServer(
    "location",
    latency_config=LatencyConfig(overrides={"contact_location_manager": 1.5}),
)


def _require_location(db: Session, location_id: str) -> Location:
    location = db.get(Location, location_id)
    if location is None:
        raise ValueError(f"Unknown location_id: {location_id}")
    return location


def _parse_window(start: str, end: str) -> tuple[datetime, datetime]:
    """Parse an ISO 8601 start/end pair, validating it at the boundary."""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO datetime for start/end: {exc}") from exc
    if start_dt >= end_dt:
        raise ValueError(f"start must be before end: {start!r} >= {end!r}")
    return start_dt, end_dt


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    """Open-interval overlap: touching boundaries (a_end == b_start) don't conflict."""
    return a_start < b_end and b_start < a_end


def _upsert_block(location: Location, scene_id: str, start: str, end: str) -> None:
    """Add (or replace) this scene's busy block in `availability` (SPEC §4.6).

    Reassigns the list rather than mutating in place, since SQLAlchemy's
    plain `JSON` column type doesn't track in-place mutation of its Python
    value — only attribute reassignment marks it dirty for commit.
    """
    blocks = [b for b in location.availability if b.get("scene_id") != scene_id]
    blocks.append({"scene_id": scene_id, "start": start, "end": end})
    location.availability = blocks


@server.tool(resource_arg="location_id")
async def get_location(location_id: str) -> dict[str, Any]:
    """Location metadata, shaped per SPEC §4.4 (plus `status`)."""
    with get_session() as db:
        location = _require_location(db, location_id)
        return {
            "id": location.id,
            "name": location.name,
            "type": location.type,
            "manager": location.manager_id,
            "availability": location.availability,
            "daily_cost": location.daily_cost,
            "weather_dependent": location.weather_dependent,
            "status": location.status,
        }


@server.tool(resource_arg="location_id")
async def check_availability(location_id: str, start: str, end: str) -> dict[str, Any]:
    """Whether `location_id` is free for `[start, end)`, per SPEC §4.6's
    busy-block exclusion rule: free means no overlap with any block in
    `availability`."""
    start_dt, end_dt = _parse_window(start, end)
    with get_session() as db:
        location = _require_location(db, location_id)
        conflicts = [
            block
            for block in location.availability
            if _overlaps(
                start_dt,
                end_dt,
                datetime.fromisoformat(block["start"]),
                datetime.fromisoformat(block["end"]),
            )
        ]
    return {
        "location_id": location_id,
        "start": start,
        "end": end,
        "available": not conflicts,
        "conflicts": conflicts,
    }


# Mock manager replies (no Production Resource Graph representation, same
# pattern as weather.py's _MOCK_FORECASTS/_DEFAULT_FORECAST). LOC-003 is
# Scene 42's demo location (SPEC §4.8).
_MOCK_MANAGER_RESPONSES: dict[str, str] = {
    "LOC-003": (
        "Understood — the rooftop slot is confirmed as scheduled. "
        "Let us know if the shoot needs to move."
    ),
}
_DEFAULT_MANAGER_RESPONSE = "Received your request; we'll confirm availability shortly."


@server.tool(resource_arg="location_id")
async def contact_location_manager(location_id: str, message: str) -> dict[str, Any]:
    """Simulate contacting the location's manager and getting a reply.

    The "async" part of SPEC §5.3's AC is the latency this tool is
    configured with above (`server.tool()`'s wrapper sleeps before this
    body runs) — the returned `response` is a synthesized reply, not an
    echo of `message`.
    """
    with get_session() as db:
        location = _require_location(db, location_id)
        manager_id = location.manager_id
    return {
        "location_id": location_id,
        "manager_id": manager_id,
        "message": message,
        "response": _MOCK_MANAGER_RESPONSES.get(location_id, _DEFAULT_MANAGER_RESPONSE),
        "contact_status": "responded",
    }


@server.tool(resource_arg="location_id")
async def find_alternative_locations(location_id: str) -> dict[str, Any]:
    """Other locations not weather-dependent, e.g. Studio B as an indoor
    substitute for Scene 42's rooftop (SPEC §9.6/§9.7/§9.10's demo
    transcript). Derived from the graph (not a mock table) since
    substitutability is itself graph data (`type`/`weather_dependent`),
    unlike a manager's reply text."""
    with get_session() as db:
        _require_location(db, location_id)  # validates existence
        stmt = select(Location).where(
            Location.id != location_id, Location.weather_dependent.is_(False)
        )
        candidates = db.scalars(stmt).all()
        alternatives = [
            {
                "id": loc.id,
                "name": loc.name,
                "type": loc.type,
                "daily_cost": loc.daily_cost,
                "weather_dependent": loc.weather_dependent,
            }
            for loc in candidates
        ]
    return {"location_id": location_id, "alternatives": alternatives}


@server.tool(resource_arg="location_id")
async def hold_location(location_id: str, scene_id: str, start: str, end: str) -> dict[str, Any]:
    """Tentatively book `location_id` for `scene_id`'s window."""
    with get_session() as db:
        location = _require_location(db, location_id)
        _upsert_block(location, scene_id, start, end)
        location.status = "held"
        db.commit()
        return {"location_id": location_id, "scene_id": scene_id, "status": location.status}


@server.tool(resource_arg="location_id")
async def confirm_location(location_id: str, scene_id: str, start: str, end: str) -> dict[str, Any]:
    """Finalize `location_id`'s booking for `scene_id`'s window."""
    with get_session() as db:
        location = _require_location(db, location_id)
        _upsert_block(location, scene_id, start, end)
        location.status = "confirmed"
        db.commit()
        return {"location_id": location_id, "scene_id": scene_id, "status": location.status}


if __name__ == "__main__":
    server.run()
