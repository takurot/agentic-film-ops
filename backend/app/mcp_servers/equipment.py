"""Equipment MCP (mock) per SPEC §5.2.

Reads/writes `Equipment` from the Production Resource Graph (SPEC §4, the
same SQLite DB seeded by `app.seed`) for the "real" parts of this server —
inventory lookup and reservation state — since the Resource Graph is the
single source of truth other components (Constraint Solver, Schedule Agent)
also read from. `_decide_vendor_outcome()` is the single seam to swap for a
real rental-company API (SPEC §11: "Rental company" is Mock).

The vendor contact/response workflow (`request_extension`/`request_reservation`
+ `get_vendor_response`) realizes SPEC §7.2's latency pattern ("Contacting
rental company → WAITING → Vendor confirmed") as two separate tool calls: the
`request_*` tools return an acknowledgement immediately, and the mock outcome
is retrieved later via `get_vendor_response`. That two-call gap plus each
tool's own configured latency is what reads as a "wait" (SPEC §7). Pending
requests live in `_VENDOR_REQUESTS`, a process-local in-memory dict — not a
Production Resource Graph table, since vendor-contact state isn't part of
that schema (mirrors `script.py`'s `_CONTINUITY_CONSTRAINTS` precedent for
graph-external mock data). Mutating a plain module-level dict without a lock
is safe here because FastMCP tool coroutines run cooperatively on a single
asyncio event loop — no other coroutine can interleave except at an `await`
point, same assumption `mcp_common.server`'s wrapper itself relies on. This
also means `_VENDOR_REQUESTS` only lives for one server subprocess's
lifetime: an Equipment Agent (SPEC §6) must keep one long-lived stdio
connection per demo session, not reconnect per call, or `get_vendor_response`
will raise for requests made against a since-restarted process.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Equipment
from mcp_common.latency import LatencyConfig
from mcp_common.server import MCPCommonServer

# SPEC §7.2's pattern ("Checking inventory → Contacting rental company →
# WAITING → Vendor confirmed") needs per-tool latency, not mcp_common's flat
# 0.5s default, or the vendor "wait" reads as just another instant API call.
_LATENCY = LatencyConfig(
    default_seconds=0.5,
    overrides={
        "check_availability": 1.0,  # "Checking inventory"
        "request_extension": 1.0,  # "Contacting rental company"
        "request_reservation": 1.0,  # "Contacting rental company"
        "get_vendor_response": 3.5,  # "WAITING"
    },
)

server = MCPCommonServer("equipment", latency_config=_LATENCY)


def _require_equipment(db: Session, equipment_id: str) -> Equipment:
    equipment = db.get(Equipment, equipment_id)
    if equipment is None:
        raise ValueError(f"Unknown equipment_id: {equipment_id}")
    return equipment


def _parse(timestamp: str) -> datetime:
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 timestamp: {timestamp!r}") from exc


def _require_start_before_end(start: str, end: str) -> None:
    if _parse(start) >= _parse(end):
        raise ValueError(f"start must be before end (got start={start!r}, end={end!r})")


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    return _parse(a_start) < _parse(b_end) and _parse(b_start) < _parse(a_end)


def _conflicts(
    blocks: list[dict[str, Any]],
    start: str,
    end: str,
    exclude_scene_id: str | None = None,
) -> list[dict[str, Any]]:
    """Booked blocks overlapping `[start, end)`, optionally excluding one
    scene_id's own block (used when re-evaluating that scene's own slot)."""
    return [
        block
        for block in blocks
        if block.get("scene_id") != exclude_scene_id
        and _overlaps(start, end, block["start"], block["end"])
    ]


_VENDOR_REQUESTS: dict[str, dict[str, Any]] = {}


def _new_request_id() -> str:
    return f"VREQ-{uuid.uuid4().hex[:8]}"


def _decide_vendor_outcome(
    blocks: list[dict[str, Any]],
    start: str,
    end: str,
    exclude_scene_id: str | None = None,
) -> tuple[str, str]:
    """Mock vendor decision, derived from the equipment's real booked blocks
    rather than randomized — single seam to swap for a real rental-company API."""
    conflicts = _conflicts(blocks, start, end, exclude_scene_id)
    if not conflicts:
        return "confirmed", "Requested window is free; vendor confirmed the booking."
    conflicting_scenes = ", ".join(sorted({block["scene_id"] for block in conflicts}))
    return "denied", f"Equipment is already booked for {conflicting_scenes} in that window."


@server.tool(resource_arg="equipment_id")
async def get_equipment(equipment_id: str) -> dict[str, Any]:
    """Equipment metadata, shaped per SPEC §4."""
    with get_session() as db:
        equipment = _require_equipment(db, equipment_id)
        return {
            "equipment_id": equipment.id,
            "name": equipment.name,
            "vendor": equipment.vendor,
            "daily_cost": equipment.daily_cost,
            "availability": list(equipment.availability),
        }


@server.tool(resource_arg="equipment_id")
async def check_availability(equipment_id: str, start: str, end: str) -> dict[str, Any]:
    """Whether `equipment_id` is free for `[start, end)`."""
    _require_start_before_end(start, end)
    with get_session() as db:
        blocks = list(_require_equipment(db, equipment_id).availability)
    conflicts = _conflicts(blocks, start, end)
    return {
        "equipment_id": equipment_id,
        "start": start,
        "end": end,
        "available": not conflicts,
        "conflicts": conflicts,
    }


@server.tool(resource_arg="equipment_id")
async def request_reservation(
    equipment_id: str, scene_id: str, start: str, end: str
) -> dict[str, Any]:
    """Contact the rental company about a new reservation (SPEC §7.2
    "Contacting rental company"). Returns an acknowledgement only — call
    `get_vendor_response()` with the returned `request_id` for the outcome."""
    _require_start_before_end(start, end)
    with get_session() as db:
        blocks = list(_require_equipment(db, equipment_id).availability)
    outcome, reason = _decide_vendor_outcome(blocks, start, end)
    request_id = _new_request_id()
    _VENDOR_REQUESTS[request_id] = {
        "equipment_id": equipment_id,
        "kind": "reservation",
        "scene_id": scene_id,
        "start": start,
        "end": end,
        "outcome": outcome,
        "reason": reason,
    }
    return {"request_id": request_id, "equipment_id": equipment_id, "status": "contacted_vendor"}


@server.tool(resource_arg="equipment_id")
async def request_extension(equipment_id: str, scene_id: str, new_end: str) -> dict[str, Any]:
    """Contact the rental company about extending `scene_id`'s existing
    booking on `equipment_id` through `new_end`."""
    with get_session() as db:
        blocks = list(_require_equipment(db, equipment_id).availability)
    current = next((b for b in blocks if b.get("scene_id") == scene_id), None)
    if current is None:
        raise ValueError(
            f"No existing booking for scene_id {scene_id!r} on equipment {equipment_id!r}"
        )
    _require_start_before_end(current["start"], new_end)
    outcome, reason = _decide_vendor_outcome(
        blocks, current["start"], new_end, exclude_scene_id=scene_id
    )
    request_id = _new_request_id()
    _VENDOR_REQUESTS[request_id] = {
        "equipment_id": equipment_id,
        "kind": "extension",
        "scene_id": scene_id,
        "start": current["start"],
        "end": new_end,
        "outcome": outcome,
        "reason": reason,
    }
    return {"request_id": request_id, "equipment_id": equipment_id, "status": "contacted_vendor"}


@server.tool()
async def get_vendor_response(request_id: str) -> dict[str, Any]:
    """Retrieve the mock vendor's confirmed/denied outcome for a prior
    `request_reservation()`/`request_extension()` call (SPEC §7.2 "Vendor
    confirmed")."""
    request = _VENDOR_REQUESTS.get(request_id)
    if request is None:
        raise ValueError(f"Unknown request_id: {request_id}")
    return {
        "request_id": request_id,
        "equipment_id": request["equipment_id"],
        "outcome": request["outcome"],
        "reason": request["reason"],
    }


@server.tool(resource_arg="equipment_id")
async def reserve_equipment(
    equipment_id: str, scene_id: str, start: str, end: str
) -> dict[str, Any]:
    """Confirm a reservation, mutating `equipment_id`'s availability. Upserts
    by `scene_id`: replaces any existing block for `scene_id` rather than
    appending, so applying a confirmed extension (or re-reserving the scene's
    own slot) doesn't collide with the block it's replacing."""
    _require_start_before_end(start, end)
    with get_session() as db:
        equipment = _require_equipment(db, equipment_id)
        blocks = list(equipment.availability)
        conflicts = _conflicts(blocks, start, end, exclude_scene_id=scene_id)
        if conflicts:
            conflicting_scenes = ", ".join(sorted({b["scene_id"] for b in conflicts}))
            raise ValueError(f"Cannot reserve: conflicts with {conflicting_scenes}")
        updated = [b for b in blocks if b.get("scene_id") != scene_id]
        updated.append({"scene_id": scene_id, "start": start, "end": end})
        # Reassign (rather than mutate in place) since Equipment.availability
        # is a plain JSON column with no MutableList tracking — an in-place
        # .append()/.remove() would not be flagged dirty and wouldn't persist.
        equipment.availability = updated
        db.commit()
        return {
            "equipment_id": equipment_id,
            "scene_id": scene_id,
            "start": start,
            "end": end,
            "availability": updated,
        }


if __name__ == "__main__":
    server.run()
