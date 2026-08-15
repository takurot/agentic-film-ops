"""Unit tests for the Budget Agent (SPEC §6.3, Issue #13).

Uses the same `seeded_db` pattern as `test_budget_mcp_server.py` (duplicated
locally per this project's "many small files" convention, matching
`test_script_agent.py` / `test_actor_agent.py`), and `test_script_agent.py`'s
`_drain` / `_FailingMCP`-style helpers for the closest sibling Agent (no
external contact, no Gemini).
"""

from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine

import app.db as db_module
from app.agents.budget import BudgetMCPPort, CandidateOption, evaluate_cost_impact
from app.db import get_session, init_db
from app.events import AnalysisEventBus
from app.mcp_servers import budget as budget_mcp
from app.models import Scene
from app.seed import seed_scene_42


@pytest.fixture
def seeded_db(monkeypatch):
    """Isolated in-memory DB seeded with Scene 42, plus a bare SC-099 scene
    with no location/equipment/crew, same pattern as
    `test_script_agent.py`'s fixture of the same name."""
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


@pytest.fixture(autouse=True)
def zero_mcp_latency(monkeypatch):
    """Budget MCP's own artificial per-tool latency (0.5s default,
    `estimate_change_cost` overridden to 1.0s) would otherwise make every
    test here slow, especially the multi-candidate ones; zero it out the
    same way `test_actor_agent.py` / `test_weather_agent.py` do."""
    monkeypatch.setattr(budget_mcp.server.latency_config, "default_seconds", 0.0)
    monkeypatch.setattr(budget_mcp.server.latency_config, "overrides", {})


class _FailingMCP:
    """A `BudgetMCPPort` fake that fails on a chosen step, to prove the
    agent's FAILED handling isn't narrowed to `ValueError` (the only
    exception type the real Budget MCP tools can raise)."""

    def __init__(self, fail_on: str, exc: Exception):
        self.fail_on = fail_on
        self.exc = exc

    async def get_current_budget(self) -> dict:
        if self.fail_on == "get_current_budget":
            raise self.exc
        return {
            "total_budget": 12_400_000.0,
            "spent_to_date": 6_200_000.0,
            "remaining": 6_200_000.0,
            "currency": "USD",
        }

    async def estimate_change_cost(
        self,
        scene_id: str,
        new_location_id: str | None,
        new_start: str | None,
        new_end: str | None,
    ) -> dict:
        if self.fail_on == "estimate_change_cost":
            raise self.exc
        return {
            "scene_id": scene_id,
            "new_location_id": new_location_id,
            "new_start": new_start,
            "new_end": new_end,
            "location_cost": 0,
            "vendor_cost": 0,
            "overtime_cost": 0,
            "total_cost_impact": 0,
        }


class _RecordingMCP:
    """A `BudgetMCPPort` fake that records every call's arguments, to prove
    `CandidateOption` fields are forwarded to `estimate_change_cost`
    verbatim (including the all-`None` no-op case)."""

    def __init__(self):
        self.calls: list[dict] = []

    async def get_current_budget(self) -> dict:
        return {
            "total_budget": 12_400_000.0,
            "spent_to_date": 6_200_000.0,
            "remaining": 6_200_000.0,
            "currency": "USD",
        }

    async def estimate_change_cost(
        self,
        scene_id: str,
        new_location_id: str | None,
        new_start: str | None,
        new_end: str | None,
    ) -> dict:
        self.calls.append(
            {
                "scene_id": scene_id,
                "new_location_id": new_location_id,
                "new_start": new_start,
                "new_end": new_end,
            }
        )
        return {
            "scene_id": scene_id,
            "new_location_id": new_location_id,
            "new_start": new_start,
            "new_end": new_end,
            "location_cost": 0,
            "vendor_cost": 0,
            "overtime_cost": 0,
            "total_cost_impact": 0,
        }


def _drain(bus: AnalysisEventBus, analysis_id: str) -> list:
    queue = bus._queues[analysis_id][0]
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    return events


# --- CandidateOption validation (P2-2: fail fast, before any MCP call) -----


def test_candidate_option_requires_start_and_end_together_start_only():
    with pytest.raises(ValidationError, match="new_start and new_end must be provided together"):
        CandidateOption(candidate_id="C1", new_start="2026-09-03T14:00")


def test_candidate_option_requires_start_and_end_together_end_only():
    with pytest.raises(ValidationError, match="new_start and new_end must be provided together"):
        CandidateOption(candidate_id="C1", new_end="2026-09-03T20:00")


def test_candidate_option_allows_all_none_no_op_candidate():
    candidate = CandidateOption(candidate_id="C1")
    assert candidate.new_location_id is None
    assert candidate.new_start is None
    assert candidate.new_end is None


# --- evaluate_cost_impact: happy path ---------------------------------------


async def test_evaluate_cost_impact_single_candidate_location_change(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    candidates = [CandidateOption(candidate_id="C1", new_location_id="LOC-STUDIO-B")]

    result = await evaluate_cost_impact("SC-042", candidates, analysis_id="AN-1", event_bus=bus)

    assert result.scene_id == "SC-042"
    assert result.budget.total_budget == 12_400_000.0
    assert result.budget.remaining == 6_200_000.0
    assert len(result.options) == 1
    option = result.options[0]
    assert option.candidate_id == "C1"
    assert option.location_cost == 2200.0  # Studio B daily_cost * 1 day
    assert option.vendor_cost == 0.0
    assert option.overtime_cost == 0.0
    assert option.total_cost_impact == 2200.0

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "QUERYING_MCP", "ANALYZING", "COMPLETED"]
    assert all(e.agent == "BudgetAgent" for e in events)
    assert all(e.resource == "SC-042" for e in events)
    assert all(e.message for e in events)


async def test_evaluate_cost_impact_multiple_candidates_preserves_order(seeded_db):
    candidates = [
        CandidateOption(candidate_id="C1", new_location_id="LOC-STUDIO-B"),
        CandidateOption(
            candidate_id="C2", new_start="2026-09-03T14:00", new_end="2026-09-03T20:00"
        ),
        CandidateOption(candidate_id="C3"),  # no-op candidate
    ]

    result = await evaluate_cost_impact("SC-042", candidates, analysis_id="AN-1")

    assert [o.candidate_id for o in result.options] == ["C1", "C2", "C3"]
    assert result.options[0].total_cost_impact == 2200.0
    assert result.options[1].total_cost_impact == 1900.0
    # No-op candidate: MCP layer's int 0 fields coerce cleanly to float 0.0.
    assert result.options[2].total_cost_impact == 0.0
    assert isinstance(result.options[2].total_cost_impact, float)


async def test_evaluate_cost_impact_options_are_directly_rankable_by_cost(seeded_db):
    """AC #2: 'Produces cost-impact figures consumed by the Schedule
    Agent's option evaluation' (SPEC §6.6 step 4, 'Cost impact（低いほ
    ど良い）') — the returned options must be directly sortable/rankable
    without further derivation."""
    candidates = [
        CandidateOption(candidate_id="EXPENSIVE", new_location_id="LOC-STUDIO-B"),
        CandidateOption(candidate_id="CHEAP"),  # no-op, 0 cost
    ]

    result = await evaluate_cost_impact("SC-042", candidates, analysis_id="AN-1")

    cheapest = min(result.options, key=lambda o: o.total_cost_impact)
    assert cheapest.candidate_id == "CHEAP"


async def test_evaluate_cost_impact_empty_candidates_returns_budget_only(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")

    result = await evaluate_cost_impact("SC-042", [], analysis_id="AN-1", event_bus=bus)

    assert result.options == []
    assert result.budget.remaining == 6_200_000.0

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "ANALYZING", "COMPLETED"]


# --- MCP-exclusivity (AC #1) -------------------------------------------------


def test_budget_agent_module_never_imports_the_db_layer_directly():
    """AC: 'Uses Budget MCP tools exclusively for access/action.' Statically
    verifies the Agent module has no import of app.db/app.models — all
    budget data must flow through app.mcp_servers.budget's tool functions.
    """
    import ast
    from pathlib import Path

    source_path = Path(__file__).parent.parent / "app" / "agents" / "budget.py"
    tree = ast.parse(source_path.read_text())
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert "app.db" not in imported_modules
    assert "app.models" not in imported_modules


# --- argument forwarding (Protocol seam) ------------------------------------


async def test_evaluate_cost_impact_forwards_candidate_fields_verbatim(seeded_db):
    mcp: BudgetMCPPort = _RecordingMCP()
    candidates = [
        CandidateOption(candidate_id="C1"),
        CandidateOption(
            candidate_id="C2",
            new_location_id="LOC-STUDIO-B",
            new_start="2026-09-03T14:00",
            new_end="2026-09-03T20:00",
        ),
    ]

    await evaluate_cost_impact("SC-042", candidates, analysis_id="AN-1", mcp=mcp)

    assert mcp.calls == [
        {
            "scene_id": "SC-042",
            "new_location_id": None,
            "new_start": None,
            "new_end": None,
        },
        {
            "scene_id": "SC-042",
            "new_location_id": "LOC-STUDIO-B",
            "new_start": "2026-09-03T14:00",
            "new_end": "2026-09-03T20:00",
        },
    ]


# --- event-stream isolation / concurrency -----------------------------------


async def test_evaluate_cost_impact_publishes_only_to_its_own_analysis_id(seeded_db):
    bus = AnalysisEventBus()
    queue_a = bus.subscribe("AN-A")
    bus.subscribe("AN-B")

    await evaluate_cost_impact("SC-042", [], analysis_id="AN-A", event_bus=bus)

    assert not bus._queues["AN-B"][0].qsize()
    assert queue_a.qsize() > 0


async def test_evaluate_cost_impact_runs_concurrently_without_cross_talk(seeded_db):
    import asyncio

    bus = AnalysisEventBus()
    queue_42 = bus.subscribe("AN-42")
    queue_99 = bus.subscribe("AN-99")

    await asyncio.gather(
        evaluate_cost_impact("SC-042", [], analysis_id="AN-42", event_bus=bus),
        evaluate_cost_impact("SC-099", [], analysis_id="AN-99", event_bus=bus),
    )

    events_42 = []
    while not queue_42.empty():
        events_42.append(queue_42.get_nowait())
    events_99 = []
    while not queue_99.empty():
        events_99.append(queue_99.get_nowait())

    assert all(e.resource == "SC-042" for e in events_42)
    assert all(e.resource == "SC-099" for e in events_99)


# --- MCP failure propagation (AC + SPEC §5) ---------------------------------


async def test_unknown_scene_id_publishes_failed_and_reraises(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    candidates = [CandidateOption(candidate_id="C1", new_location_id="LOC-STUDIO-B")]

    with pytest.raises(ValueError, match="Unknown scene_id"):
        await evaluate_cost_impact(
            "SC-DOES-NOT-EXIST", candidates, analysis_id="AN-1", event_bus=bus
        )

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "QUERYING_MCP", "FAILED"]
    assert "Unknown scene_id" in events[-1].message


async def test_unknown_location_id_publishes_failed_and_reraises(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    candidates = [CandidateOption(candidate_id="C1", new_location_id="LOC-DOES-NOT-EXIST")]

    with pytest.raises(ValueError, match="Unknown location_id"):
        await evaluate_cost_impact("SC-042", candidates, analysis_id="AN-1", event_bus=bus)

    events = _drain(bus, "AN-1")
    assert events[-1].status == "FAILED"


async def test_get_current_budget_failure_publishes_failed_and_reraises(seeded_db):
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    mcp: BudgetMCPPort = _FailingMCP("get_current_budget", RuntimeError("budget service down"))

    with pytest.raises(RuntimeError, match="budget service down"):
        await evaluate_cost_impact("SC-042", [], analysis_id="AN-1", event_bus=bus, mcp=mcp)

    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "FAILED"]
    assert "budget service down" in events[-1].message


async def test_non_value_error_from_estimate_change_cost_publishes_failed_and_reraises(seeded_db):
    """Proves FAILED handling isn't narrowed to `ValueError` (the only
    exception type the real Budget MCP tools happen to raise)."""
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    mcp: BudgetMCPPort = _FailingMCP("estimate_change_cost", RuntimeError("boom"))
    candidates = [CandidateOption(candidate_id="C1")]

    with pytest.raises(RuntimeError, match="boom"):
        await evaluate_cost_impact("SC-042", candidates, analysis_id="AN-1", event_bus=bus, mcp=mcp)

    events = _drain(bus, "AN-1")
    assert events[-1].status == "FAILED"
    assert "boom" in events[-1].message


async def test_failure_on_second_candidate_does_not_call_third(seeded_db):
    """A failure partway through the candidate loop must (a) have already
    published the QUERYING_MCP event for the first, already-processed
    candidate, and (b) short-circuit — the third candidate's
    `estimate_change_cost` must never be called."""
    bus = AnalysisEventBus()
    bus.subscribe("AN-1")
    calls: list[str] = []

    class _PartialFailureMCP:
        async def get_current_budget(self) -> dict:
            return {
                "total_budget": 12_400_000.0,
                "spent_to_date": 6_200_000.0,
                "remaining": 6_200_000.0,
                "currency": "USD",
            }

        async def estimate_change_cost(
            self,
            scene_id: str,
            new_location_id: str | None,
            new_start: str | None,
            new_end: str | None,
        ) -> dict:
            candidate_id = new_location_id or "unknown"
            calls.append(candidate_id)
            if candidate_id == "C2":
                raise RuntimeError("mid-loop failure")
            return {
                "scene_id": scene_id,
                "new_location_id": new_location_id,
                "new_start": new_start,
                "new_end": new_end,
                "location_cost": 0,
                "vendor_cost": 0,
                "overtime_cost": 0,
                "total_cost_impact": 0,
            }

    candidates = [
        CandidateOption(candidate_id="C1", new_location_id="C1"),
        CandidateOption(candidate_id="C2", new_location_id="C2"),
        CandidateOption(candidate_id="C3", new_location_id="C3"),
    ]

    with pytest.raises(RuntimeError, match="mid-loop failure"):
        await evaluate_cost_impact(
            "SC-042", candidates, analysis_id="AN-1", event_bus=bus, mcp=_PartialFailureMCP()
        )

    assert calls == ["C1", "C2"]  # C3 never called
    events = _drain(bus, "AN-1")
    statuses = [e.status for e in events]
    assert statuses == ["QUEUED", "QUERYING_MCP", "QUERYING_MCP", "QUERYING_MCP", "FAILED"]
