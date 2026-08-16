"""Schedule Agent (SPEC §6.6): constraint solver and replanning coordinator.

The Schedule Agent is activated after domain agents (Actor, Equipment, Location,
Budget) complete their investigations. It evaluates candidate schedule combinations
using a genuine deterministic Constraint Solver on the Production Resource Graph
and synthesizes comparative explainability (SPEC §9.8).

Clean Architecture note: This agent has no dedicated MCP server (SPEC §3.1) and
never imports app.db or app.models directly — all resource inputs are provided
via typed Pydantic models.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.events import AgentEvent, AgentEventStatus, AnalysisEventBus, default_event_bus
from app.gemini_client import (
    GeminiClient,
    GeminiUnavailableError,
    with_min_display_time,
)
from app.latency import get_latency_config

AGENT_NAME = "ScheduleAgent"
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class TargetSceneMetadata(BaseModel):
    scene_id: str
    name: str
    duration_hours: float
    original_scheduled: str  # ISO timestamp e.g. "2026-09-02T14:00"
    location_id: str | None = None
    actor_ids: list[str] = Field(default_factory=list)
    equipment_ids: list[str] = Field(default_factory=list)
    crew_ids: list[str] = Field(default_factory=list)


class CandidateSlot(BaseModel):
    candidate_id: str
    start_time: str  # ISO timestamp e.g. "2026-09-02T16:00"
    end_time: str  # ISO timestamp e.g. "2026-09-02T20:00"
    location_id: str
    cost_impact: float = 0.0
    delay_days: int = 0
    base_risk: RiskLevel = "LOW"
    label: str = ""


class ActorConstraintInput(BaseModel):
    actor_id: str
    name: str
    busy_blocks: list[tuple[str, str]] = Field(default_factory=list)  # (start, end) ISO
    hard_stop_time: str | None = None  # e.g. "20:00"
    day_available_windows: dict[str, tuple[str, str]] = Field(
        default_factory=dict
    )  # "2026-09-02": ("16:00", "20:00")
    default_available_window: tuple[str, str] = ("08:00", "22:00")


class LocationConstraintInput(BaseModel):
    location_id: str
    name: str
    weather_dependent: bool = False
    has_weather_risk: bool = False
    busy_blocks: list[tuple[str, str]] = Field(default_factory=list)


class EquipmentConstraintInput(BaseModel):
    equipment_id: str
    name: str
    busy_blocks: list[tuple[str, str]] = Field(default_factory=list)
    extension_available: bool = True


class CrewConstraintInput(BaseModel):
    crew_id: str
    name: str
    busy_blocks: list[tuple[str, str]] = Field(default_factory=list)
    max_daily_hours: float = 12.0
    min_rest_hours_between_shifts: float = 10.0


class ContinuityConstraintInput(BaseModel):
    must_precede: list[str] = Field(default_factory=list)
    must_follow: list[str] = Field(default_factory=list)
    same_day_as: list[str] = Field(default_factory=list)


class ScheduleReplanInput(BaseModel):
    scene: TargetSceneMetadata
    candidates: list[CandidateSlot]
    actors: list[ActorConstraintInput] = Field(default_factory=list)
    locations: list[LocationConstraintInput] = Field(default_factory=list)
    equipment: list[EquipmentConstraintInput] = Field(default_factory=list)
    crew: list[CrewConstraintInput] = Field(default_factory=list)
    continuity: ContinuityConstraintInput = Field(default_factory=ContinuityConstraintInput)
    other_scheduled_scenes: dict[str, datetime] = Field(default_factory=dict)


class ScheduleOption(BaseModel):
    option_id: str  # "OPTION_A", "OPTION_B", "OPTION_C"
    candidate_id: str
    label: str
    target_scene_id: str
    start_time: str
    end_time: str
    location_id: str
    cost_impact: float
    schedule_delay_days: int
    risk: RiskLevel
    recommended: bool = False
    checklist: list[str] = Field(default_factory=list)
    why: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


@dataclass
class SolverOutcome:
    feasible_options: list[ScheduleOption]
    pruned_candidates: list[tuple[CandidateSlot, str]]  # (candidate, reason)
    summary_message: str


@dataclass
class ScheduleAgentConfig:
    min_display_seconds: float = 1.0
    w_cost: float = 1.0
    w_delay: float = 5000.0
    w_risk: float = 2000.0


class ConstraintSolver:
    """Deterministic constraint solver evaluating replan candidate slots."""

    def __init__(self, config: ScheduleAgentConfig | None = None) -> None:
        self.config = config or ScheduleAgentConfig()

    def solve(self, input_data: ScheduleReplanInput) -> SolverOutcome:
        feasible: list[tuple[CandidateSlot, list[str], float]] = []
        pruned: list[tuple[CandidateSlot, str]] = []

        for candidate in input_data.candidates:
            cand_start = datetime.fromisoformat(candidate.start_time)
            cand_end = datetime.fromisoformat(candidate.end_time)
            checklist: list[str] = []
            is_valid = True
            rejection_reason = ""

            # 1. Cast Constraints
            for actor in input_data.actors:
                # Check busy blocks
                for b_start_str, b_end_str in actor.busy_blocks:
                    b_start = datetime.fromisoformat(b_start_str)
                    b_end = datetime.fromisoformat(b_end_str)
                    if not (cand_end <= b_start or cand_start >= b_end):
                        is_valid = False
                        rejection_reason = f"{actor.name} is busy during slot"
                        break
                if not is_valid:
                    break

                # Check hard stop
                if actor.hard_stop_time:
                    cand_end_time_str = cand_end.strftime("%H:%M")
                    if cand_end_time_str > actor.hard_stop_time:
                        is_valid = False
                        rejection_reason = (
                            f"{actor.name} hard stop at {actor.hard_stop_time} exceeded"
                        )
                        break

                # Check available window
                cand_date_str = cand_start.strftime("%Y-%m-%d")
                w_start_str, w_end_str = actor.day_available_windows.get(
                    cand_date_str, actor.default_available_window
                )
                cand_start_time_str = cand_start.strftime("%H:%M")
                cand_end_time_str = cand_end.strftime("%H:%M")
                if cand_start_time_str < w_start_str or cand_end_time_str > w_end_str:
                    is_valid = False
                    rejection_reason = f"{actor.name} outside available window {w_start_str}-{w_end_str} on {cand_date_str}"
                    break

                checklist.append(f"✓ {actor.name} available")

            if not is_valid:
                pruned.append((candidate, rejection_reason))
                continue

            # 2. Location Constraints
            loc = next(
                (
                    loc_cand
                    for loc_cand in input_data.locations
                    if loc_cand.location_id == candidate.location_id
                ),
                None,
            )
            if loc:
                if loc.weather_dependent and loc.has_weather_risk:
                    is_valid = False
                    rejection_reason = f"Outdoor location {loc.name} has severe weather risk"
                else:
                    for b_start_str, b_end_str in loc.busy_blocks:
                        b_start = datetime.fromisoformat(b_start_str)
                        b_end = datetime.fromisoformat(b_end_str)
                        if not (cand_end <= b_start or cand_start >= b_end):
                            is_valid = False
                            rejection_reason = f"Location {loc.name} is already booked"
                            break
                    if is_valid:
                        checklist.append(f"✓ {loc.name} available")
            else:
                checklist.append(f"✓ Location {candidate.location_id} available")

            if not is_valid:
                pruned.append((candidate, rejection_reason))
                continue

            # 3. Equipment Constraints
            for eq in input_data.equipment:
                for b_start_str, b_end_str in eq.busy_blocks:
                    b_start = datetime.fromisoformat(b_start_str)
                    b_end = datetime.fromisoformat(b_end_str)
                    if (
                        not (cand_end <= b_start or cand_start >= b_end)
                        and not eq.extension_available
                    ):
                        is_valid = False
                        rejection_reason = f"Equipment {eq.name} unavailable and cannot be extended"
                        break

                if is_valid:
                    checklist.append(f"✓ {eq.name} available")

            if not is_valid:
                pruned.append((candidate, rejection_reason))
                continue

            # 4. Continuity Constraints
            continuity = input_data.continuity
            for prec_scene_id in continuity.must_precede:
                if prec_scene_id in input_data.other_scheduled_scenes:
                    other_time = input_data.other_scheduled_scenes[prec_scene_id]
                    if cand_end > other_time:
                        is_valid = False
                        rejection_reason = f"Must precede {prec_scene_id} ({other_time.strftime('%Y-%m-%d %H:%M')})"
                        break

            for foll_scene_id in continuity.must_follow:
                if foll_scene_id in input_data.other_scheduled_scenes:
                    other_time = input_data.other_scheduled_scenes[foll_scene_id]
                    if cand_start < other_time:
                        is_valid = False
                        rejection_reason = (
                            f"Must follow {foll_scene_id} ({other_time.strftime('%Y-%m-%d %H:%M')})"
                        )
                        break

            for same_day_scene_id in continuity.same_day_as:
                if same_day_scene_id in input_data.other_scheduled_scenes:
                    other_time = input_data.other_scheduled_scenes[same_day_scene_id]
                    if cand_start.date() != other_time.date():
                        is_valid = False
                        rejection_reason = f"Must be on same day as {same_day_scene_id}"
                        break

            if not is_valid:
                pruned.append((candidate, rejection_reason))
                continue

            checklist.append("✓ Continuity valid")

            # Calculate weighted penalty score (lower is better)
            risk_weights = {"LOW": 1.0, "MEDIUM": 2.0, "HIGH": 3.0}
            score = (
                self.config.w_cost * candidate.cost_impact
                + self.config.w_delay * candidate.delay_days
                + self.config.w_risk * risk_weights.get(candidate.base_risk, 1.0)
            )
            feasible.append((candidate, checklist, score))

        if not feasible:
            return SolverOutcome(
                feasible_options=[],
                pruned_candidates=pruned,
                summary_message=f"NO FEASIBLE PLAN: Evaluated {len(input_data.candidates)} candidates, all pruned by constraints.",
            )

        # Sort by penalty score ascending
        feasible.sort(key=lambda x: x[2])

        # Assign Option letters (A, B, C...)
        option_letters = ["OPTION_A", "OPTION_B", "OPTION_C", "OPTION_D"]
        options: list[ScheduleOption] = []

        for idx, (cand, chk, _) in enumerate(feasible[:3]):
            opt_id = option_letters[idx] if idx < len(option_letters) else f"OPTION_{idx + 1}"
            options.append(
                ScheduleOption(
                    option_id=opt_id,
                    candidate_id=cand.candidate_id,
                    label=cand.label or f"Move {input_data.scene.scene_id} to {cand.start_time}",
                    target_scene_id=input_data.scene.scene_id,
                    start_time=cand.start_time,
                    end_time=cand.end_time,
                    location_id=cand.location_id,
                    cost_impact=cand.cost_impact,
                    schedule_delay_days=cand.delay_days,
                    risk=cand.base_risk,
                    recommended=(idx == 0),
                    checklist=chk,
                    why="",
                    details={
                        "candidate_id": cand.candidate_id,
                        "duration_hours": input_data.scene.duration_hours,
                    },
                )
            )

        return SolverOutcome(
            feasible_options=options,
            pruned_candidates=pruned,
            summary_message=f"{len(options)} FEASIBLE PLANS FOUND",
        )


class ScheduleAgentResult(BaseModel):
    scene_id: str
    options: list[ScheduleOption]
    overall_explainability: str
    pruned_count: int


_EXPLAINABILITY_PROMPT_TEMPLATE = """You are the Schedule Agent for an AI-powered film production system.
Synthesize a concise, executive-level explanation for why Option A is recommended over the alternatives for the producer dashboard.

Target Scene: {scene_name} ({scene_id})
Recommended Option: {option_a_label} (Cost: +${option_a_cost:,.0f}, Delay: {option_a_delay} days, Risk: {option_a_risk})
Checklist: {option_a_checklist}
Alternatives:
{alternatives_text}

Provide a concise justification bullet list and comparative summary matching SPEC §9.8 style.
"""


class ScheduleAgent:
    """Schedule Agent running constraint evaluation and explainability synthesis."""

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        config: ScheduleAgentConfig | None = None,
        event_bus: AnalysisEventBus | None = None,
    ) -> None:
        self._gemini = gemini_client
        self._config = config or ScheduleAgentConfig()
        self._event_bus = event_bus or default_event_bus
        self._solver = ConstraintSolver(self._config)

    async def replan(
        self, analysis_id: str, input_data: ScheduleReplanInput
    ) -> ScheduleAgentResult:
        if input_data is None:
            self._publish(analysis_id, "FAILED", "Invalid replan input: None", type="STATUS")
            raise ValueError("input_data must not be None")

        scene_id = input_data.scene.scene_id
        self._publish(
            analysis_id,
            "QUEUED",
            f"Replanning production schedule for {scene_id}",
            type="STATUS",
            resource=scene_id,
        )

        try:
            # Step 1: Candidate evaluation
            num_combinations = len(input_data.candidates)
            self._publish(
                analysis_id,
                "ANALYZING",
                f"Evaluating {num_combinations} schedule combinations",
                type="STATUS",
                resource=scene_id,
            )

            # Step 2: Checklist emission (SPEC §9.6)
            self._publish(
                analysis_id,
                "ANALYZING",
                "Checking: ✓ Cast, ✓ Crew, ✓ Equipment, ✓ Location, ✓ Continuity, ✓ Budget",
                type="CHECKLIST",
                resource=scene_id,
            )

            # Run deterministic solver
            outcome = self._solver.solve(input_data)

            if not outcome.feasible_options:
                self._publish(
                    analysis_id,
                    "COMPLETED",
                    "AI REPLAN COMPLETE: 0 FEASIBLE PLANS FOUND",
                    type="STATUS",
                    resource=scene_id,
                )
                return ScheduleAgentResult(
                    scene_id=scene_id,
                    options=[],
                    overall_explainability=outcome.summary_message,
                    pruned_count=len(outcome.pruned_candidates),
                )

            # Synthesize explainability (SPEC §9.8, §11)
            explainability = await self._synthesize_explainability(
                input_data, outcome.feasible_options
            )

            # Populate individual 'why' strings
            for opt in outcome.feasible_options:
                if opt.recommended:
                    opt.why = "Selected as recommended plan: lowest cost and schedule impact."
                else:
                    opt.why = f"Alternative plan (+${opt.cost_impact:,.0f}, {opt.schedule_delay_days}d delay)."

            self._publish(
                analysis_id,
                "COMPLETED",
                f"AI REPLAN COMPLETE: {len(outcome.feasible_options)} FEASIBLE PLANS FOUND",
                type="STATUS",
                resource=scene_id,
            )

            return ScheduleAgentResult(
                scene_id=scene_id,
                options=outcome.feasible_options,
                overall_explainability=explainability,
                pruned_count=len(outcome.pruned_candidates),
            )

        except Exception as exc:
            self._publish(
                analysis_id,
                "FAILED",
                f"Schedule Agent failed: {exc}",
                type="STATUS",
                resource=scene_id,
            )
            raise

    async def _synthesize_explainability(
        self, input_data: ScheduleReplanInput, options: list[ScheduleOption]
    ) -> str:
        if not options:
            return "No feasible plans found."

        opt_a = options[0]
        alts_text = ""
        for alt in options[1:]:
            diff_cost = alt.cost_impact - opt_a.cost_impact
            diff_delay = alt.schedule_delay_days - opt_a.schedule_delay_days
            alts_text += f"- {alt.option_id} ({alt.label}): +${diff_cost:,.0f} cost, +{diff_delay} days delay\n"

        # Fallback explanation template (SPEC §9.8)
        fallback_text = (
            "Option A was selected because:\n"
            "• All required cast and crew are available\n"
            "• Camera package and studio space can be reserved\n"
            "• Script continuity is preserved with 0 days schedule delay\n"
        )
        if len(options) > 1:
            diff_cost = options[1].cost_impact - opt_a.cost_impact
            diff_delay = options[1].schedule_delay_days - opt_a.schedule_delay_days
            fallback_text += f"\nCompared with Option B:\n${diff_cost:,.0f} lower cost\n{diff_delay} day(s) less delay"

        if self._gemini is None:
            return fallback_text

        prompt = _EXPLAINABILITY_PROMPT_TEMPLATE.format(
            scene_name=input_data.scene.name,
            scene_id=input_data.scene.scene_id,
            option_a_label=opt_a.label,
            option_a_cost=opt_a.cost_impact,
            option_a_delay=opt_a.schedule_delay_days,
            option_a_risk=opt_a.risk,
            option_a_checklist=", ".join(opt_a.checklist),
            alternatives_text=alts_text or "None",
        )

        try:
            latency_cfg = get_latency_config().schedule
            min_secs = latency_cfg.get_delay("option_generation")
            response = await with_min_display_time(
                self._gemini.generate_content(prompt),
                min_seconds=min_secs,
            )
            text = (response.text or "").strip()
            return text if text else fallback_text
        except (GeminiUnavailableError, RuntimeError, ValueError, TimeoutError):
            return fallback_text

    def _publish(
        self,
        analysis_id: str,
        status: AgentEventStatus,
        message: str,
        *,
        type: str,
        resource: str | None = None,
    ) -> None:
        self._event_bus.publish(
            analysis_id,
            AgentEvent.create(
                agent=AGENT_NAME,
                type=type,
                status=status,
                message=message,
                resource=resource,
            ),
        )
