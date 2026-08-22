"""Unit and integration tests for Schedule Agent and Constraint Solver (SPEC §6.6, §9.6, §9.7, §9.8, §11)."""

import ast
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.agents.schedule import (
    ActorConstraintInput,
    CandidateSlot,
    ConstraintSolver,
    ContinuityConstraintInput,
    CrewConstraintInput,
    EquipmentConstraintInput,
    LocationConstraintInput,
    ScheduleAgent,
    ScheduleAgentResult,
    ScheduleReplanInput,
    TargetSceneMetadata,
)
from app.events import AnalysisEventBus
from app.gemini_client import GeminiUnavailableError

ANALYSIS_ID = "AN-SCHED-001"


def make_gemini_stub(response_text: str | None = None, side_effect=None) -> AsyncMock:
    stub = AsyncMock()
    if side_effect is not None:
        stub.generate_content = AsyncMock(side_effect=side_effect)
    else:
        fake_response = AsyncMock()
        fake_response.text = response_text or (
            "This option was selected because both principal actors are available, "
            "camera package can be extended, and Studio B is available indoors."
        )
        stub.generate_content = AsyncMock(return_value=fake_response)
    return stub


@pytest.fixture
def event_bus():
    return AnalysisEventBus()


def sample_replan_input() -> ScheduleReplanInput:
    """Create a standard replan input modeling the Scene 42 rain alert scenario."""
    return ScheduleReplanInput(
        scene=TargetSceneMetadata(
            scene_id="SC-042",
            name="Dialogue scene (Scene 42)",
            duration_hours=4.0,
            original_scheduled="2026-09-02T14:00",
            location_id="LOC-001",
            actor_ids=["ACT-001", "ACT-002"],
            equipment_ids=["EQ-001"],
            crew_ids=["CRW-001", "CRW-002"],
        ),
        candidates=[
            # Candidate 1: Same day afternoon at indoor Studio B (Wed 16:00-20:00)
            CandidateSlot(
                candidate_id="C1",
                start_time="2026-09-02T16:00",
                end_time="2026-09-02T20:00",
                location_id="LOC-003",  # Studio B (indoor)
                cost_impact=8400.0,
                delay_days=0,
                base_risk="LOW",
                label="Move Scene 42 to Wed 16:00-20:00 (Studio B)",
            ),
            # Candidate 2: Next day morning (Thu 09:00-13:00) at Studio B
            CandidateSlot(
                candidate_id="C2",
                start_time="2026-09-03T09:00",
                end_time="2026-09-03T13:00",
                location_id="LOC-003",
                cost_impact=29800.0,
                delay_days=1,
                base_risk="LOW",
                label="Move Scene 42 to Thu 09:00-13:00 (Studio B)",
            ),
            # Candidate 3: Friday morning (Fri 09:00-13:00)
            CandidateSlot(
                candidate_id="C3",
                start_time="2026-09-04T09:00",
                end_time="2026-09-04T13:00",
                location_id="LOC-003",
                cost_impact=35000.0,
                delay_days=2,
                base_risk="MEDIUM",
                label="Move Scene 42 to Fri 09:00-13:00 (Studio B)",
            ),
        ],
        actors=[
            ActorConstraintInput(
                actor_id="ACT-001",
                name="Emma Carter",
                busy_blocks=[
                    ("2026-09-02T14:00", "2026-09-02T16:00"),  # busy until 16:00 on Wed
                ],
                hard_stop_time="20:00",  # hard stop at 20:00 on Wed
                day_available_windows={"2026-09-02": ("16:00", "20:00")},
            ),
            ActorConstraintInput(
                actor_id="ACT-002",
                name="Daniel Craig",
                busy_blocks=[],
            ),
        ],
        locations=[
            LocationConstraintInput(
                location_id="LOC-003",
                name="Studio B",
                weather_dependent=False,
                busy_blocks=[],
            ),
            LocationConstraintInput(
                location_id="LOC-001",
                name="Rooftop (Outdoor)",
                weather_dependent=True,
                has_weather_risk=True,
                busy_blocks=[],
            ),
        ],
        equipment=[
            EquipmentConstraintInput(
                equipment_id="EQ-001",
                name="ARRI Alexa 35",
                busy_blocks=[],
                extension_available=True,
            )
        ],
        crew=[
            CrewConstraintInput(
                crew_id="CRW-001",
                name="Camera Operator",
                busy_blocks=[],
                max_daily_hours=12.0,
                min_rest_hours_between_shifts=10.0,
            )
        ],
        continuity=ContinuityConstraintInput(
            must_precede=["SC-050"],  # Scene 42 must precede Scene 50
            must_follow=["SC-039"],  # Scene 42 must follow Scene 39
            same_day_as=[],
        ),
        other_scheduled_scenes={
            "SC-039": datetime(2026, 9, 1, 10, 0),  # Scheduled Sept 1
            "SC-050": datetime(2026, 9, 5, 14, 0),  # Scheduled Sept 5
        },
    )


# --- ConstraintSolver Unit Tests ---------------------------------------------


def test_solver_finds_and_ranks_feasible_candidates():
    input_data = sample_replan_input()
    solver = ConstraintSolver()
    result = solver.solve(input_data)

    assert len(result.feasible_options) >= 2
    # First option should be Option A, recommended
    option_a = result.feasible_options[0]
    assert option_a.option_id == "OPTION_A"
    assert option_a.recommended is True
    assert option_a.cost_impact == 8400.0
    assert option_a.schedule_delay_days == 0
    assert option_a.risk == "LOW"

    # Check checklist items
    checklist_str = " ".join(option_a.checklist)
    assert "Emma Carter available" in checklist_str or "Emma available" in checklist_str
    assert "Studio B" in checklist_str
    assert "Continuity" in checklist_str


def test_solver_prunes_candidate_on_actor_hard_stop():
    input_data = sample_replan_input()
    # Add a candidate that ends at 21:00 (violating Emma's 20:00 hard stop)
    input_data.candidates.append(
        CandidateSlot(
            candidate_id="C_LATE",
            start_time="2026-09-02T17:00",
            end_time="2026-09-02T21:00",  # Ends after 20:00
            location_id="LOC-003",
            cost_impact=5000.0,
            delay_days=0,
            base_risk="LOW",
            label="Late evening slot",
        )
    )
    solver = ConstraintSolver()
    result = solver.solve(input_data)

    cand_ids = [opt.candidate_id for opt in result.feasible_options]
    assert "C_LATE" not in cand_ids


def test_solver_prunes_candidate_on_weather_risk_for_outdoor_location():
    input_data = sample_replan_input()
    # Add a candidate using the outdoor rooftop location which has weather risk
    input_data.candidates.append(
        CandidateSlot(
            candidate_id="C_OUTDOOR",
            start_time="2026-09-02T16:00",
            end_time="2026-09-02T20:00",
            location_id="LOC-001",  # Outdoor rooftop with weather risk
            cost_impact=2000.0,
            delay_days=0,
            base_risk="HIGH",
            label="Rooftop outdoor slot",
        )
    )
    solver = ConstraintSolver()
    result = solver.solve(input_data)

    cand_ids = [opt.candidate_id for opt in result.feasible_options]
    assert "C_OUTDOOR" not in cand_ids


def test_solver_prunes_candidate_on_continuity_must_follow_violation():
    input_data = sample_replan_input()
    # Scene 39 is on Sept 1. If we move Scene 42 to Aug 30, it violates must_follow=["SC-039"]
    input_data.candidates.append(
        CandidateSlot(
            candidate_id="C_EARLY",
            start_time="2026-08-30T10:00",
            end_time="2026-08-30T14:00",
            location_id="LOC-003",
            cost_impact=1000.0,
            delay_days=-3,
            base_risk="LOW",
            label="Way too early slot",
        )
    )
    solver = ConstraintSolver()
    result = solver.solve(input_data)

    cand_ids = [opt.candidate_id for opt in result.feasible_options]
    assert "C_EARLY" not in cand_ids


def test_solver_prunes_candidate_on_continuity_must_precede_violation():
    input_data = sample_replan_input()
    # Scene 50 is on Sept 5. If we move Scene 42 to Sept 6, it violates must_precede=["SC-050"]
    input_data.candidates.append(
        CandidateSlot(
            candidate_id="C_TOO_LATE",
            start_time="2026-09-06T10:00",
            end_time="2026-09-06T14:00",
            location_id="LOC-003",
            cost_impact=1000.0,
            delay_days=4,
            base_risk="LOW",
            label="Way too late slot",
        )
    )
    solver = ConstraintSolver()
    result = solver.solve(input_data)

    cand_ids = [opt.candidate_id for opt in result.feasible_options]
    assert "C_TOO_LATE" not in cand_ids


def test_solver_handles_zero_feasible_candidates():
    input_data = sample_replan_input()
    # Empty candidates list
    input_data.candidates = []
    solver = ConstraintSolver()
    result = solver.solve(input_data)

    assert result.feasible_options == []
    assert "NO FEASIBLE PLAN" in result.summary_message


# --- ScheduleAgent Integration Tests ------------------------------------------


@pytest.mark.asyncio
async def test_schedule_agent_replan_flow_and_events(event_bus):
    input_data = sample_replan_input()
    gemini_stub = make_gemini_stub()
    agent = ScheduleAgent(gemini_client=gemini_stub, event_bus=event_bus)

    queue = event_bus.subscribe(ANALYSIS_ID)

    result: ScheduleAgentResult = await agent.replan(ANALYSIS_ID, input_data)

    assert len(result.options) >= 2
    assert result.options[0].recommended is True
    assert result.options[0].option_id == "OPTION_A"
    assert result.overall_explainability is not None

    # Drain events and verify SPEC §9.6 event sequence
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    statuses = [e.status for e in events]
    assert "QUEUED" in statuses
    assert "ANALYZING" in statuses
    assert "COMPLETED" in statuses

    # Verify checklist event was emitted
    messages = [e.message for e in events]
    assert any("Evaluating" in m and "combinations" in m for m in messages)
    assert any("Cast" in m for m in messages)

    event_bus.unsubscribe(ANALYSIS_ID, queue)


@pytest.mark.asyncio
async def test_schedule_agent_fails_closed_when_gemini_unavailable(event_bus):
    input_data = sample_replan_input()
    failing_gemini = make_gemini_stub(side_effect=GeminiUnavailableError("Service unavailable"))
    agent = ScheduleAgent(gemini_client=failing_gemini, event_bus=event_bus)

    queue = event_bus.subscribe(ANALYSIS_ID)
    with pytest.raises(GeminiUnavailableError):
        await agent.replan(ANALYSIS_ID, input_data)
    events = []
    while not queue.empty():
        events.append(queue.get_nowait())
    assert events[-1].status == "FAILED"
    event_bus.unsubscribe(ANALYSIS_ID, queue)


@pytest.mark.asyncio
async def test_schedule_agent_publishes_failed_and_reraises_on_critical_error(event_bus):
    agent = ScheduleAgent(gemini_client=make_gemini_stub(), event_bus=event_bus)

    queue = event_bus.subscribe(ANALYSIS_ID)

    # Pass invalid input that triggers unhandled exception
    with pytest.raises(ValueError, match="input_data must not be None"):
        await agent.replan(ANALYSIS_ID, None)  # type: ignore

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    assert events[-1].status == "FAILED"
    event_bus.unsubscribe(ANALYSIS_ID, queue)


def test_schedule_agent_never_imports_app_db_or_models():
    """Static AST check ensuring Clean Architecture layer separation."""
    schedule_file = Path(__file__).resolve().parent.parent / "app" / "agents" / "schedule.py"
    with open(schedule_file, "r") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("app.db"), f"Forbidden import: {alias.name}"
                assert not alias.name.startswith("app.models"), f"Forbidden import: {alias.name}"
                assert not alias.name.startswith("sqlalchemy"), f"Forbidden import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert not mod.startswith("app.db"), f"Forbidden import from {mod}"
            assert not mod.startswith("app.models"), f"Forbidden import from {mod}"
            assert not mod.startswith("sqlalchemy"), f"Forbidden import from {mod}"
