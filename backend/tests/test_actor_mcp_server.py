"""Unit tests for the Actor MCP tool functions, plus one end-to-end test
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
from app.mcp_servers import actor
from app.mcp_servers.actor import (
    confirm_actor,
    contact_manager,
    get_actor,
    get_actor_availability,
    get_actor_constraints,
    get_contact_status,
    get_manager_response,
    hold_actor,
)
from app.models import Actor
from app.seed import seed_scene_42


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42 (ACT-001 Emma Carter,
    ACT-002 Daniel), plus a bare ACT-099 actor with no manager to exercise
    the "no manager on file" branch. `app.db.engine` is monkeypatched since
    actor.py's tool functions call `get_session()` with no explicit bind,
    which resolves `engine` from app.db's module globals at call time.
    """
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(engine)
    with get_session(engine) as db:
        seed_scene_42(db)
        db.add(
            Actor(
                id="ACT-099",
                name="Unmanaged Extra",
                manager=None,
                availability=[],
                status="unconfirmed",
            )
        )
        db.commit()
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clear_contact_sessions():
    """`_contact_sessions` is module-global state shared across every test
    in this file (and, in principle, every caller of actor.py within this
    process) — clear it before each test so no test's contact_manager()
    workflow leaks into another's assertions, regardless of execution order.
    """
    actor._contact_sessions.clear()
    yield
    actor._contact_sessions.clear()


@pytest.fixture(autouse=True)
def zero_manager_response_delay(monkeypatch):
    """Tests must not depend on real wall-clock time to observe the
    WAITING_EXTERNAL -> RESPONSE_RECEIVED transition. Setting the delay to
    0 means a session is immediately "due" once created; tests instead
    control the WAITING state explicitly (see
    test_get_contact_status_progresses_from_waiting_to_response_received).
    """
    monkeypatch.setattr(actor, "_MANAGER_RESPONSE_DELAY_SECONDS", 0.0)


# --- get_actor ---------------------------------------------------------


async def test_get_actor_returns_spec_shape_for_emma_carter(seeded_db):
    result = await get_actor(actor_id="ACT-001")

    assert result == {
        "id": "ACT-001",
        "name": "Emma Carter",
        "manager": "MGR-001",
        "availability": [
            {"scene_id": "SC-038", "start": "2026-09-01T09:00", "end": "2026-09-01T13:00"},
            {"scene_id": "SC-042", "start": "2026-09-02T14:00", "end": "2026-09-02T18:00"},
        ],
        "status": "confirmed",
    }


async def test_get_actor_handles_actor_with_no_manager(seeded_db):
    result = await get_actor(actor_id="ACT-099")

    assert result["manager"] is None


async def test_get_actor_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await get_actor(actor_id="ACT-DOES-NOT-EXIST")


# --- get_actor_availability ---------------------------------------------


async def test_get_actor_availability_returns_busy_blocks_for_emma_carter(seeded_db):
    result = await get_actor_availability(actor_id="ACT-001")

    assert result["actor_id"] == "ACT-001"
    assert result["availability"] == [
        {"scene_id": "SC-038", "start": "2026-09-01T09:00", "end": "2026-09-01T13:00"},
        {"scene_id": "SC-042", "start": "2026-09-02T14:00", "end": "2026-09-02T18:00"},
    ]


async def test_get_actor_availability_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await get_actor_availability(actor_id="ACT-DOES-NOT-EXIST")


# --- get_actor_constraints -----------------------------------------------


async def test_get_actor_constraints_returns_scripted_entry_for_emma_carter(seeded_db):
    result = await get_actor_constraints(actor_id="ACT-001")

    assert result["actor_id"] == "ACT-001"
    assert result["max_daily_hours"] == 10
    assert result["notes"]


async def test_get_actor_constraints_defaults_for_actor_without_scripted_terms(seeded_db):
    result = await get_actor_constraints(actor_id="ACT-002")

    assert result == {
        "actor_id": "ACT-002",
        "max_daily_hours": 12,
        "meal_break_after_hours": 6,
        "notes": "",
    }


async def test_get_actor_constraints_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await get_actor_constraints(actor_id="ACT-DOES-NOT-EXIST")


# --- hold_actor / confirm_actor -------------------------------------------


async def test_hold_actor_sets_status_to_held_and_returns_previous_status(seeded_db):
    result = await hold_actor(actor_id="ACT-001")

    assert result == {"actor_id": "ACT-001", "status": "held", "previous_status": "confirmed"}
    refreshed = await get_actor(actor_id="ACT-001")
    assert refreshed["status"] == "held"


async def test_confirm_actor_sets_status_to_confirmed(seeded_db):
    await hold_actor(actor_id="ACT-002")

    result = await confirm_actor(actor_id="ACT-002")

    assert result == {"actor_id": "ACT-002", "status": "confirmed", "previous_status": "held"}
    refreshed = await get_actor(actor_id="ACT-002")
    assert refreshed["status"] == "confirmed"


async def test_hold_actor_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await hold_actor(actor_id="ACT-DOES-NOT-EXIST")


async def test_confirm_actor_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await confirm_actor(actor_id="ACT-DOES-NOT-EXIST")


# --- contact_manager / get_contact_status / get_manager_response ---------


async def test_contact_manager_returns_waiting_status_and_manager_id(seeded_db):
    result = await contact_manager(actor_id="ACT-001")

    assert result["actor_id"] == "ACT-001"
    assert result["contact_status"] == "WAITING_EXTERNAL"
    assert result["manager_id"] == "MGR-001"


async def test_contact_manager_echoes_optional_request_message(seeded_db):
    result = await contact_manager(actor_id="ACT-001", message="Can Emma make Sept 2 call time?")

    assert result["request_message"] == "Can Emma make Sept 2 call time?"


async def test_contact_manager_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await contact_manager(actor_id="ACT-DOES-NOT-EXIST")


async def test_get_contact_status_without_prior_contact_manager_call_raises(seeded_db):
    with pytest.raises(ValueError, match="No contact request in progress"):
        await get_contact_status(actor_id="ACT-001")


async def test_get_contact_status_progresses_from_waiting_to_response_received(
    seeded_db, monkeypatch
):
    # Use a real (non-zero) delay for this test specifically so we can
    # observe the WAITING_EXTERNAL state before it becomes due.
    monkeypatch.setattr(actor, "_MANAGER_RESPONSE_DELAY_SECONDS", 100.0)
    await contact_manager(actor_id="ACT-001")

    waiting = await get_contact_status(actor_id="ACT-001")
    assert waiting["contact_status"] == "WAITING_EXTERNAL"

    # Fast-forward: make the session's deadline already passed.
    actor._contact_sessions["ACT-001"].responds_at = 0.0

    received = await get_contact_status(actor_id="ACT-001")
    assert received["contact_status"] == "RESPONSE_RECEIVED"

    # Status is derived (read-only), so polling again doesn't regress it.
    received_again = await get_contact_status(actor_id="ACT-001")
    assert received_again["contact_status"] == "RESPONSE_RECEIVED"


async def test_get_contact_status_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await get_contact_status(actor_id="ACT-DOES-NOT-EXIST")


async def test_get_manager_response_pending_returns_waiting_without_raising(seeded_db, monkeypatch):
    monkeypatch.setattr(actor, "_MANAGER_RESPONSE_DELAY_SECONDS", 100.0)
    await contact_manager(actor_id="ACT-001")

    result = await get_manager_response(actor_id="ACT-001")

    assert result == {"actor_id": "ACT-001", "contact_status": "WAITING_EXTERNAL", "message": None}


async def test_get_manager_response_returns_emma_carters_availability_window(seeded_db):
    await contact_manager(actor_id="ACT-001")  # delay is 0 in this test via autouse fixture

    result = await get_manager_response(actor_id="ACT-001")

    assert result["actor_id"] == "ACT-001"
    assert result["contact_status"] == "RESPONSE_RECEIVED"
    assert "4 PM" in result["message"]
    assert "8 PM" in result["message"]


async def test_get_manager_response_defaults_for_actor_without_scripted_reply(seeded_db):
    await contact_manager(actor_id="ACT-002")

    result = await get_manager_response(actor_id="ACT-002")

    assert result["contact_status"] == "RESPONSE_RECEIVED"
    assert result["message"] == "Manager confirmed availability with no restrictions."


async def test_get_manager_response_raises_for_unknown_actor_id(seeded_db):
    with pytest.raises(ValueError, match="Unknown actor_id"):
        await get_manager_response(actor_id="ACT-DOES-NOT-EXIST")


async def test_get_manager_response_raises_without_prior_contact_manager_call(seeded_db):
    with pytest.raises(ValueError, match="No contact request in progress"):
        await get_manager_response(actor_id="ACT-001")


async def test_contact_manager_called_twice_resets_the_session(seeded_db, monkeypatch):
    monkeypatch.setattr(actor, "_MANAGER_RESPONSE_DELAY_SECONDS", 100.0)
    await contact_manager(actor_id="ACT-001")
    actor._contact_sessions["ACT-001"].responds_at = 0.0
    assert (await get_contact_status(actor_id="ACT-001"))["contact_status"] == "RESPONSE_RECEIVED"

    await contact_manager(actor_id="ACT-001")

    status = await get_contact_status(actor_id="ACT-001")
    assert status["contact_status"] == "WAITING_EXTERNAL"


# --- stdio E2E -------------------------------------------------------------


async def test_actor_mcp_server_serves_tools_over_real_stdio_transport():
    # Seed the real dev DB (file-backed, so the subprocess sees it once it
    # opens the same file) rather than the monkeypatched in-memory engine
    # above, which only exists in this test process. Read-only assertions
    # only: hold_actor/confirm_actor would permanently flip ACT-001's status
    # in that shared dev DB and change the demo's starting state.
    init_db()
    with get_session() as db:
        seed_scene_42(db)

    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_servers.actor"])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert {
            "get_actor",
            "get_actor_availability",
            "get_actor_constraints",
            "contact_manager",
            "get_contact_status",
            "get_manager_response",
            "hold_actor",
            "confirm_actor",
        } <= tool_names

        result = await session.call_tool("get_actor", {"actor_id": "ACT-001"})
        payload = json.loads(result.content[0].text)
        assert payload["id"] == "ACT-001"
        assert payload["manager"] == "MGR-001"

        contacted = await session.call_tool("contact_manager", {"actor_id": "ACT-001"})
        contacted_payload = json.loads(contacted.content[0].text)
        assert contacted_payload["contact_status"] == "WAITING_EXTERNAL"

        status = await session.call_tool("get_contact_status", {"actor_id": "ACT-001"})
        status_payload = json.loads(status.content[0].text)
        assert status_payload["contact_status"] in {"WAITING_EXTERNAL", "RESPONSE_RECEIVED"}
