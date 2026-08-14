"""Budget MCP (mock) per SPEC §5.6.

SPEC §4 (Production Resource Graph) has no Budget/Project entity — the only
cost fields that exist anywhere in the graph are `Equipment.daily_cost`,
`Location.daily_cost`, and `Crew.overtime_rate_per_hour`. This server keeps
the production's overall budget totals (`_PRODUCTION_BUDGET`) as a small
read-only in-memory constant instead of a new DB table, same "not modeled in
the graph → small in-memory lookup" treatment as script.py's continuity
constraints / actor.py's contract terms. `get_current_budget()`'s
`total_budget` is SPEC §9.1's own dashboard figure ("Budget $12.4M")
verbatim; `spent_to_date` is set to a plausible ~50% burn consistent with
that same mockup's "PRODUCTION DAY 27 / 54" — SPEC doesn't specify a burn
rate, so this is a documented assumption, not a derived value. Unlike every
other MCP server here, none of this module's tools mutate the DB (SPEC
§5.6 defines no hold/confirm-style tool) — `_PRODUCTION_BUDGET` is never
written to.

`calculate_overtime()` and `calculate_vendor_cost()` are real computations
against real Equipment/Location/Crew rate fields (SPEC §11: the world's
resource data is mock, but the system computing over it is real).
`estimate_change_cost()` composes those same two calculations plus a
location-cost term into a single cost-impact estimate for replanning a
scene (SPEC §6.6 step 3's "Budget MCP から見積もったコスト増分" /
§9.7's Cost impact card) — see its own docstring for the cost model.
"""

import math
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Crew, Equipment, Location, Scene
from mcp_common.latency import LatencyConfig
from mcp_common.server import MCPCommonServer

server = MCPCommonServer(
    "budget",
    # estimate_change_cost aggregates multiple lookups into one decision,
    # so it gets a bump over the pure getters/calculators below it (mirrors
    # equipment.py's pattern of a longer delay for "doing work" tools).
    latency_config=LatencyConfig(overrides={"estimate_change_cost": 1.0}),
)

# Not modeled in SPEC §4 (see module docstring) — total_budget mirrors SPEC
# §9.1's dashboard figure verbatim ("Budget $12.4M"); spent_to_date is a
# documented ~50% burn assumption. Read-only: no tool in this module writes
# to it.
_PRODUCTION_BUDGET: dict[str, float | str] = {
    "total_budget": 12_400_000.0,
    "spent_to_date": 6_200_000.0,
    "currency": "USD",
}


def _require_crew(db: Session, crew_id: str) -> Crew:
    crew = db.get(Crew, crew_id)
    if crew is None:
        raise ValueError(f"Unknown crew_id: {crew_id}")
    return crew


def _require_equipment(db: Session, equipment_id: str) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise ValueError(f"Unknown equipment_id: {equipment_id}")
    return equipment


def _require_location(db: Session, location_id: str) -> Location:
    location = db.get(Location, location_id)
    if location is None:
        raise ValueError(f"Unknown location_id: {location_id}")
    return location


def _require_scene(db: Session, scene_id: str) -> Scene:
    scene = db.get(Scene, scene_id)
    if scene is None:
        raise ValueError(f"Unknown scene_id: {scene_id}")
    return scene


def _parse(timestamp: str) -> datetime:
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp: {timestamp!r}") from exc


def _require_start_before_end(start: str, end: str) -> None:
    if _parse(start) >= _parse(end):
        raise ValueError(f"start must be before end (got start={start!r}, end={end!r})")


def _require_non_negative_finite(value: float, label: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number (got {value!r})")
    if value < 0:
        raise ValueError(f"{label} must be non-negative (got {value!r})")


def _days_for(start: str, end: str) -> int:
    """Rental billing in day-blocks, minimum 1 day: exactly 24h bills as one
    day, any excess beyond a whole day rolls into a new billed day."""
    hours = (_parse(end) - _parse(start)).total_seconds() / 3600
    return max(1, math.ceil(hours / 24))


def _overtime_cost(rate_per_hour: float, standard_hours: float, actual_hours: float) -> float:
    overtime_hours = max(0.0, actual_hours - standard_hours)
    return round(overtime_hours * rate_per_hour, 2)


@server.tool()
async def get_current_budget() -> dict[str, Any]:
    """Current production-wide budget totals (SPEC §5.6, §9.1's dashboard
    figure). Single production — no project_id, mirrors the rest of this
    codebase's single-production scope (nothing else here is multi-project
    either)."""
    total_budget = float(_PRODUCTION_BUDGET["total_budget"])
    spent_to_date = float(_PRODUCTION_BUDGET["spent_to_date"])
    return {
        "total_budget": total_budget,
        "spent_to_date": spent_to_date,
        "remaining": round(total_budget - spent_to_date, 2),
        "currency": _PRODUCTION_BUDGET["currency"],
    }


@server.tool(resource_arg="crew_id")
async def calculate_overtime(
    crew_id: str, standard_hours: float, actual_hours: float
) -> dict[str, Any]:
    """Overtime cost for a crew member, real-computed from
    `Crew.overtime_rate_per_hour` (SPEC §4.5)."""
    _require_non_negative_finite(standard_hours, "standard_hours")
    _require_non_negative_finite(actual_hours, "actual_hours")
    with get_session() as db:
        crew = _require_crew(db, crew_id)
        rate = crew.overtime_rate_per_hour
    overtime_hours = max(0.0, actual_hours - standard_hours)
    return {
        "crew_id": crew_id,
        "standard_hours": standard_hours,
        "actual_hours": actual_hours,
        "overtime_hours": overtime_hours,
        "overtime_rate_per_hour": rate,
        "overtime_cost": _overtime_cost(rate, standard_hours, actual_hours),
    }


@server.tool(resource_arg="equipment_id")
async def calculate_vendor_cost(equipment_id: str, start: str, end: str) -> dict[str, Any]:
    """Rental cost for booking `equipment_id` over `[start, end)`, real-computed
    from `Equipment.daily_cost` (SPEC §4.3) billed in day-blocks."""
    _require_start_before_end(start, end)
    with get_session() as db:
        equipment = _require_equipment(db, equipment_id)
        daily_cost = equipment.daily_cost
    days = _days_for(start, end)
    return {
        "equipment_id": equipment_id,
        "start": start,
        "end": end,
        "days": days,
        "daily_cost": daily_cost,
        "total_cost": round(days * daily_cost, 2),
    }


@server.tool(resource_arg="scene_id")
async def estimate_change_cost(
    scene_id: str,
    new_location_id: str | None = None,
    new_start: str | None = None,
    new_end: str | None = None,
) -> dict[str, Any]:
    """Cost impact of moving `scene_id` to a new location and/or time window
    (SPEC §6.6 step 3 / §9.7's "Cost impact" card).

    **Cost model — incremental, not netted.** This estimates what the
    change *adds*, not the net difference against the current plan: the
    scene's current location/equipment booking is treated as already
    committed (mirrors real production practice, where a last-minute
    location swap doesn't refund a deposit already paid on the original
    booking). Concretely:
    - `location_cost`: the new location's day-rate for the requested window,
      only if `new_location_id` differs from the scene's current location.
      0 if `new_location_id` is omitted (no location change proposed).
    - `vendor_cost`: the scene's existing equipment re-billed for the new
      window (via the same day-block rule as `calculate_vendor_cost`). 0 if
      no new window is given — the equipment's existing booking is
      unaffected by a location-only change.
    - `overtime_cost`: the scene's crew's overtime beyond the scene's
      current `duration_hours`, for the new window's duration (via the same
      formula as `calculate_overtime`). 0 if no new window is given.
    - `total_cost_impact` is the sum of the three. This is deliberately a
      smaller, real number derived from this seed data's actual rates (not
      a reproduction of SPEC §9.7's illustrative "+$8,400" demo figure) —
      a downstream Schedule/Budget Agent (later phase) composes these
      primitives, together with other resources' cost inputs, into the
      final cost-impact figure shown in the UI.

    The scene's "current window" is derived as `Scene.scheduled` through
    `scheduled + duration_hours` (SPEC §4.1) — Scene has no separate
    start/end fields.

    `new_start`/`new_end` must be provided together (or not at all);
    providing only one raises `ValueError`.
    """
    if (new_start is None) != (new_end is None):
        raise ValueError("new_start and new_end must be provided together")
    if new_start is not None and new_end is not None:
        _require_start_before_end(new_start, new_end)

    with get_session() as db:
        scene = _require_scene(db, scene_id)
        current_location_id = scene.location_id
        current_start = scene.scheduled.isoformat(timespec="minutes")
        current_end = (scene.scheduled + timedelta(hours=scene.duration_hours)).isoformat(
            timespec="minutes"
        )
        standard_hours = scene.duration_hours
        equipment_daily_costs = [e.daily_cost for e in scene.equipment]
        crew_rates = [c.overtime_rate_per_hour for c in scene.crew]

        new_location_daily_cost: float | None = None
        if new_location_id is not None:
            new_location_daily_cost = _require_location(db, new_location_id).daily_cost

    target_start = new_start or current_start
    target_end = new_end or current_end
    target_days = _days_for(target_start, target_end)

    location_cost = 0.0
    if new_location_id is not None and new_location_id != current_location_id:
        location_cost = round(new_location_daily_cost * target_days, 2)

    vendor_cost = 0.0
    overtime_cost = 0.0
    if new_start is not None:
        vendor_cost = round(sum(dc * target_days for dc in equipment_daily_costs), 2)
        actual_hours = (_parse(target_end) - _parse(target_start)).total_seconds() / 3600
        overtime_cost = round(
            sum(_overtime_cost(rate, standard_hours, actual_hours) for rate in crew_rates), 2
        )

    return {
        "scene_id": scene_id,
        "new_location_id": new_location_id,
        "new_start": new_start,
        "new_end": new_end,
        "location_cost": location_cost,
        "vendor_cost": vendor_cost,
        "overtime_cost": overtime_cost,
        "total_cost_impact": round(location_cost + vendor_cost + overtime_cost, 2),
    }


if __name__ == "__main__":
    server.run()
