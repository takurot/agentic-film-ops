"""Unit tests for the Budget MCP tool functions, plus one end-to-end test
that spawns the server as a real stdio subprocess against the real (seeded)
dev DB — mirrors test_equipment_mcp_server.py's structure.
"""

import json
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sqlalchemy import create_engine

import app.db as db_module
from app.db import get_session, init_db
from app.mcp_servers.budget import (
    calculate_overtime,
    calculate_vendor_cost,
    estimate_change_cost,
    get_current_budget,
)
from app.seed import seed_scene_42

SC_042_START = "2026-09-02T14:00"
SC_042_END = "2026-09-02T18:00"


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42, same pattern as
    test_equipment_mcp_server.py's fixture of the same name."""
    engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr(db_module, "engine", engine)
    init_db(engine)
    with get_session(engine) as db:
        seed_scene_42(db)
    yield engine
    engine.dispose()


# ---------------------------------------------------------------------------
# get_current_budget
# ---------------------------------------------------------------------------


async def test_get_current_budget_returns_totals_and_remaining(seeded_db):
    result = await get_current_budget()

    assert result["total_budget"] == 12_400_000.0
    assert result["spent_to_date"] == 6_200_000.0
    assert result["remaining"] == 6_200_000.0
    assert result["currency"] == "USD"


# ---------------------------------------------------------------------------
# calculate_overtime
# ---------------------------------------------------------------------------


async def test_calculate_overtime_no_overtime_when_actual_within_standard(seeded_db):
    result = await calculate_overtime(crew_id="CREW-001", standard_hours=8, actual_hours=6)

    assert result == {
        "crew_id": "CREW-001",
        "standard_hours": 8,
        "actual_hours": 6,
        "overtime_hours": 0,
        "overtime_rate_per_hour": 150.0,
        "overtime_cost": 0,
    }


async def test_calculate_overtime_computes_cost_for_hours_worked_beyond_standard(seeded_db):
    result = await calculate_overtime(crew_id="CREW-001", standard_hours=8, actual_hours=10)

    assert result["overtime_hours"] == 2
    assert result["overtime_cost"] == 300.0  # 2h * $150/h


async def test_calculate_overtime_handles_fractional_hours(seeded_db):
    result = await calculate_overtime(crew_id="CREW-001", standard_hours=8, actual_hours=8.5)

    assert result["overtime_hours"] == 0.5
    assert result["overtime_cost"] == 75.0  # 0.5h * $150/h


async def test_calculate_overtime_zero_standard_hours_counts_all_actual_hours(seeded_db):
    result = await calculate_overtime(crew_id="CREW-001", standard_hours=0, actual_hours=4)

    assert result["overtime_hours"] == 4
    assert result["overtime_cost"] == 600.0


async def test_calculate_overtime_unknown_crew_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown crew_id"):
        await calculate_overtime(crew_id="CREW-DOES-NOT-EXIST", standard_hours=8, actual_hours=10)


async def test_calculate_overtime_rejects_negative_standard_hours(seeded_db):
    with pytest.raises(ValueError, match="must be non-negative"):
        await calculate_overtime(crew_id="CREW-001", standard_hours=-1, actual_hours=10)


async def test_calculate_overtime_rejects_negative_actual_hours(seeded_db):
    with pytest.raises(ValueError, match="must be non-negative"):
        await calculate_overtime(crew_id="CREW-001", standard_hours=8, actual_hours=-1)


async def test_calculate_overtime_rejects_non_finite_hours(seeded_db):
    with pytest.raises(ValueError, match="finite"):
        await calculate_overtime(crew_id="CREW-001", standard_hours=8, actual_hours=float("inf"))


# ---------------------------------------------------------------------------
# calculate_vendor_cost
# ---------------------------------------------------------------------------


async def test_calculate_vendor_cost_bills_one_day_for_same_day_window(seeded_db):
    result = await calculate_vendor_cost(equipment_id="EQ-001", start=SC_042_START, end=SC_042_END)

    assert result == {
        "equipment_id": "EQ-001",
        "start": SC_042_START,
        "end": SC_042_END,
        "days": 1,
        "daily_cost": 1200,
        "total_cost": 1200.0,
    }


async def test_calculate_vendor_cost_bills_exactly_24h_as_one_day(seeded_db):
    result = await calculate_vendor_cost(
        equipment_id="EQ-001", start="2026-09-02T09:00", end="2026-09-03T09:00"
    )

    assert result["days"] == 1
    assert result["total_cost"] == 1200.0


async def test_calculate_vendor_cost_bills_24h_plus_one_minute_as_two_days(seeded_db):
    result = await calculate_vendor_cost(
        equipment_id="EQ-001", start="2026-09-02T09:00", end="2026-09-03T09:01"
    )

    assert result["days"] == 2
    assert result["total_cost"] == 2400.0


async def test_calculate_vendor_cost_unknown_equipment_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown equipment_id"):
        await calculate_vendor_cost(
            equipment_id="EQ-DOES-NOT-EXIST", start=SC_042_START, end=SC_042_END
        )


async def test_calculate_vendor_cost_rejects_start_not_before_end(seeded_db):
    with pytest.raises(ValueError, match="start must be before end"):
        await calculate_vendor_cost(equipment_id="EQ-001", start=SC_042_END, end=SC_042_START)


async def test_calculate_vendor_cost_rejects_malformed_timestamp(seeded_db):
    with pytest.raises(ValueError, match="Invalid ISO-8601 timestamp"):
        await calculate_vendor_cost(equipment_id="EQ-001", start="not-a-timestamp", end=SC_042_END)


# ---------------------------------------------------------------------------
# estimate_change_cost
# ---------------------------------------------------------------------------


async def test_estimate_change_cost_no_change_args_is_all_zero(seeded_db):
    result = await estimate_change_cost(scene_id="SC-042")

    assert result == {
        "scene_id": "SC-042",
        "new_location_id": None,
        "new_start": None,
        "new_end": None,
        "location_cost": 0,
        "vendor_cost": 0,
        "overtime_cost": 0,
        "total_cost_impact": 0,
    }


async def test_estimate_change_cost_location_only_change_same_window(seeded_db):
    """Moving to Studio B without changing the time window: only the new
    location's day-rate is added (incremental cost model — the original
    rooftop booking is treated as already committed/sunk, not netted out;
    see budget.py's module docstring)."""
    result = await estimate_change_cost(scene_id="SC-042", new_location_id="LOC-STUDIO-B")

    assert result["location_cost"] == 2200.0  # Studio B daily_cost * 1 day
    assert result["vendor_cost"] == 0
    assert result["overtime_cost"] == 0
    assert result["total_cost_impact"] == 2200.0


async def test_estimate_change_cost_window_change_reprices_equipment_and_overtime(seeded_db):
    """Same location, but a longer window: equipment gets re-billed for the
    new window and any extra hours become crew overtime."""
    result = await estimate_change_cost(
        scene_id="SC-042", new_start="2026-09-03T14:00", new_end="2026-09-03T20:00"
    )

    assert result["location_cost"] == 0  # location unchanged
    assert result["vendor_cost"] == 1600.0  # (1200 + 400) * 1 day
    assert result["overtime_cost"] == 300.0  # 2h beyond the 4h standard * $150/h
    assert result["total_cost_impact"] == 1900.0


async def test_estimate_change_cost_combined_location_and_window_change(seeded_db):
    """Both a location swap and a window move in one call."""
    result = await estimate_change_cost(
        scene_id="SC-042",
        new_location_id="LOC-STUDIO-B",
        new_start="2026-09-03T16:00",
        new_end="2026-09-03T20:00",
    )

    assert result["location_cost"] == 2200.0  # Studio B * 1 day
    assert result["vendor_cost"] == 1600.0  # (1200 + 400) * 1 day
    assert result["overtime_cost"] == 0  # still 4h, matches scene's standard duration
    assert result["total_cost_impact"] == 3800.0


async def test_estimate_change_cost_same_location_id_as_current_is_not_a_change(seeded_db):
    result = await estimate_change_cost(scene_id="SC-042", new_location_id="LOC-003")

    assert result["location_cost"] == 0


async def test_estimate_change_cost_requires_start_and_end_together_start_only(seeded_db):
    with pytest.raises(ValueError, match="new_start and new_end must be provided together"):
        await estimate_change_cost(scene_id="SC-042", new_start="2026-09-03T14:00")


async def test_estimate_change_cost_requires_start_and_end_together_end_only(seeded_db):
    with pytest.raises(ValueError, match="new_start and new_end must be provided together"):
        await estimate_change_cost(scene_id="SC-042", new_end="2026-09-03T20:00")


async def test_estimate_change_cost_rejects_start_not_before_end(seeded_db):
    with pytest.raises(ValueError, match="start must be before end"):
        await estimate_change_cost(
            scene_id="SC-042", new_start="2026-09-03T20:00", new_end="2026-09-03T14:00"
        )


async def test_estimate_change_cost_unknown_scene_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown scene_id"):
        await estimate_change_cost(scene_id="SC-999")


async def test_estimate_change_cost_unknown_new_location_id_raises_value_error(seeded_db):
    with pytest.raises(ValueError, match="Unknown location_id"):
        await estimate_change_cost(scene_id="SC-042", new_location_id="LOC-DOES-NOT-EXIST")


# ---------------------------------------------------------------------------
# E2E: real stdio transport
# ---------------------------------------------------------------------------


async def test_budget_mcp_server_serves_tools_over_real_stdio_transport():
    init_db()
    with get_session() as db:
        seed_scene_42(db)

    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_servers.budget"])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert {
            "get_current_budget",
            "estimate_change_cost",
            "calculate_overtime",
            "calculate_vendor_cost",
        } <= tool_names

        result = await session.call_tool("get_current_budget", {})
        payload = json.loads(result.content[0].text)
        assert payload["total_budget"] == 12_400_000.0

        result = await session.call_tool(
            "calculate_vendor_cost",
            {"equipment_id": "EQ-001", "start": SC_042_START, "end": SC_042_END},
        )
        payload = json.loads(result.content[0].text)
        assert payload["total_cost"] == 1200.0
