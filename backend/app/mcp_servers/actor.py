"""Actor MCP (mock) per SPEC §5.1.

Reads/writes Actor rows from the Production Resource Graph (SPEC §4.2, the
same SQLite DB seeded by `app.seed`), same pattern as `script.py`. In
addition to the plain resource lookups (`get_actor`, `get_actor_availability`,
`get_actor_constraints`), this module models the manager contact workflow
(SPEC §7.1's "Contacting manager... WAITING FOR MANAGER... Manager
replied" sequence, with statuses drawn verbatim from SPEC §8.2) as three
separate polling tools rather than one blocking call:
`contact_manager()` starts the workflow, `get_contact_status()` polls it,
and `get_manager_response()` reads the (eventually) received reply. Contact
sessions are mock-only in-process state (`_contact_sessions`, keyed by
actor_id) — there's no real manager to call, so nothing needs to be
persisted to the DB; a fresh `contact_manager()` call simply starts a new
session, superseding any prior one for that actor.

`get_manager_response()` returns the manager's reply as raw, unparsed text
(SPEC §3.3: "Agent = Reasoning, MCP = Access") — turning that text into a
structured decision (e.g. "available after 4 PM") is the Actor Agent's job,
not this MCP's.
"""

import time
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Actor
from mcp_common.latency import LatencyConfig
from mcp_common.server import MCPCommonServer

# SPEC §7.1's Actor Agent pattern times "Checking calendar" (1.2s) and
# "Checking contract" (0.8s) explicitly; other tools use the 1.0s default.
server = MCPCommonServer(
    "actor",
    latency_config=LatencyConfig(
        default_seconds=1.0,
        overrides={"get_actor_availability": 1.2, "get_actor_constraints": 0.8},
    ),
)

ContactStatus = Literal["WAITING_EXTERNAL", "RESPONSE_RECEIVED"]

# SPEC §7.1: "WAITING FOR MANAGER ↓ 4 sec". Module-level so the demo can
# tune it (§7's "遅延値は設定可能"); tests monkeypatch it to 0 (or a large
# value, to freeze the WAITING_EXTERNAL state) for deterministic assertions.
_MANAGER_RESPONSE_DELAY_SECONDS = 4.0


@dataclass
class _ContactSession:
    """State for one contact_manager() workflow, keyed by actor_id in
    `_contact_sessions`. `responds_at` is a `time.monotonic()` deadline, so
    `get_contact_status()`/`get_manager_response()` derive the current
    status from elapsed time rather than mutating state on every read.
    """

    manager_id: str | None
    responds_at: float
    request_message: str | None = None


# Process-global by design: there's one mock "world" per running MCP server
# process (no per-analysis/per-request scoping needed for a hackathon demo
# with a single in-flight production). A second contact_manager() call for
# an actor already being contacted simply replaces the session — see
# test_contact_manager_called_twice_resets_the_session.
_contact_sessions: dict[str, _ContactSession] = {}

# Mock contract terms (SPEC §5.1 get_actor_constraints), not modeled in the
# Production Resource Graph (Actor has no contract-terms columns) — same
# "small in-memory lookup table" approach as script.py's continuity data.
_ACTOR_CONSTRAINTS: dict[str, dict[str, Any]] = {
    "ACT-001": {
        "max_daily_hours": 10,
        "meal_break_after_hours": 6,
        "notes": "Contract requires a 12-hour turnaround between calls.",
    },
}
_DEFAULT_ACTOR_CONSTRAINTS: dict[str, Any] = {
    "max_daily_hours": 12,
    "meal_break_after_hours": 6,
    "notes": "",
}

# Mock manager replies (SPEC §7.1's demo line, verbatim in AC #1: "available
# after 4 PM, hard stop 8 PM"), keyed by actor_id. Raw text only — parsing
# it into a decision is the Actor Agent's job, not this MCP's (see module
# docstring).
_MANAGER_RESPONSES: dict[str, str] = {
    "ACT-001": "Emma can make it after 4 PM, hard stop at 8 PM.",
}
_DEFAULT_MANAGER_RESPONSE = "Manager confirmed availability with no restrictions."


def _require_actor(db: Session, actor_id: str) -> Actor:
    actor = db.get(Actor, actor_id)
    if actor is None:
        raise ValueError(f"Unknown actor_id: {actor_id}")
    return actor


def _require_session(actor_id: str) -> _ContactSession:
    session = _contact_sessions.get(actor_id)
    if session is None:
        raise ValueError(f"No contact request in progress for actor_id: {actor_id}")
    return session


def _contact_status(session: _ContactSession) -> ContactStatus:
    return "RESPONSE_RECEIVED" if time.monotonic() >= session.responds_at else "WAITING_EXTERNAL"


@server.tool(resource_arg="actor_id")
async def get_actor(actor_id: str) -> dict[str, Any]:
    """Actor info shaped per SPEC §4.2 (`id`/`manager` keys match the spec's
    own example verbatim, unlike this module's other, envelope-shaped
    tools)."""
    with get_session() as db:
        actor = _require_actor(db, actor_id)
        return {
            "id": actor.id,
            "name": actor.name,
            "manager": actor.manager_id,
            "availability": actor.availability,
            "status": actor.status,
        }


@server.tool(resource_arg="actor_id")
async def get_actor_availability(actor_id: str) -> dict[str, Any]:
    """Busy blocks for the actor (SPEC §4.6 format)."""
    with get_session() as db:
        actor = _require_actor(db, actor_id)
        return {"actor_id": actor_id, "availability": actor.availability}


@server.tool(resource_arg="actor_id")
async def get_actor_constraints(actor_id: str) -> dict[str, Any]:
    """Contract constraints for the actor (mock, SPEC §5.1)."""
    with get_session() as db:
        _require_actor(db, actor_id)  # only validates existence
    constraints = _ACTOR_CONSTRAINTS.get(actor_id, _DEFAULT_ACTOR_CONSTRAINTS)
    return {"actor_id": actor_id, **constraints}


@server.tool(resource_arg="actor_id")
async def hold_actor(actor_id: str) -> dict[str, Any]:
    """Tentatively hold the actor (SPEC §4.2 status mutation, AC #3)."""
    with get_session() as db:
        actor = _require_actor(db, actor_id)
        previous_status = actor.status
        actor.status = "held"
        db.commit()
        return {"actor_id": actor_id, "status": actor.status, "previous_status": previous_status}


@server.tool(resource_arg="actor_id")
async def confirm_actor(actor_id: str) -> dict[str, Any]:
    """Confirm the actor (SPEC §4.2 status mutation, AC #3)."""
    with get_session() as db:
        actor = _require_actor(db, actor_id)
        previous_status = actor.status
        actor.status = "confirmed"
        db.commit()
        return {"actor_id": actor_id, "status": actor.status, "previous_status": previous_status}


@server.tool(resource_arg="actor_id")
async def contact_manager(actor_id: str, message: str | None = None) -> dict[str, Any]:
    """Start a mock async manager contact (SPEC §7.1/§8.2, AC #1/#2).

    Starts (or restarts) a `_ContactSession` for `actor_id` that becomes
    "due" after `_MANAGER_RESPONSE_DELAY_SECONDS`. `message` is the outgoing
    request text (optional; echoed back for callers that want it, e.g. a
    future External Communication Mock UI panel).
    """
    with get_session() as db:
        actor = _require_actor(db, actor_id)
        manager_id = actor.manager_id
    _contact_sessions[actor_id] = _ContactSession(
        manager_id=manager_id,
        responds_at=time.monotonic() + _MANAGER_RESPONSE_DELAY_SECONDS,
        request_message=message,
    )
    return {
        "actor_id": actor_id,
        "contact_status": "WAITING_EXTERNAL",
        "manager_id": manager_id,
        "request_message": message,
    }


@server.tool(resource_arg="actor_id")
async def get_contact_status(actor_id: str) -> dict[str, Any]:
    """Poll the in-progress contact workflow's status (SPEC §8.2). Read-only
    — status is derived from elapsed time, not mutated here."""
    with get_session() as db:
        _require_actor(db, actor_id)
    session = _require_session(actor_id)
    return {"actor_id": actor_id, "contact_status": _contact_status(session)}


@server.tool(resource_arg="actor_id")
async def get_manager_response(actor_id: str) -> dict[str, Any]:
    """The manager's raw reply, once received (AC #1). While still pending,
    returns the WAITING_EXTERNAL status with a null message rather than
    raising — a pending external response is a normal state, not a tool
    failure (SPEC §5's error-handling policy reserves FAILED for genuine
    errors, e.g. an unknown actor_id, which still raises `ValueError`)."""
    with get_session() as db:
        _require_actor(db, actor_id)
    session = _require_session(actor_id)
    status = _contact_status(session)
    if status == "WAITING_EXTERNAL":
        return {"actor_id": actor_id, "contact_status": status, "message": None}
    message = _MANAGER_RESPONSES.get(actor_id, _DEFAULT_MANAGER_RESPONSE)
    return {"actor_id": actor_id, "contact_status": status, "message": message}


if __name__ == "__main__":
    server.run()
