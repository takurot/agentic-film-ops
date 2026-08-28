"""Production Orchestrator agent (SPEC §6.1, §3.2, §3.4, §8, §9, §11).

The central coordination layer connecting reality changes (incidents) to
specialized domain agents (Script, Actor, Location, Equipment, Budget, Schedule)
over MCP and delivering the 6-stage closed loop:
Observe → Reason → Coordinate → Re-plan → Human Approve → Execute
"""

import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.agents.actor import ActorAgent
from app.agents.budget import CandidateOption, evaluate_cost_impact
from app.agents.equipment import EquipmentAgent
from app.agents.location import LocationAgent
from app.agents.schedule import (
    ActorConstraintInput,
    CandidateSlot,
    ContinuityConstraintInput,
    EquipmentConstraintInput,
    LocationConstraintInput,
    ScheduleAgent,
    ScheduleReplanInput,
    TargetSceneMetadata,
)
from app.agents.script import analyze_scene
from app.db import get_session
from app.events import (
    AgentEvent,
    AgentEventStatus,
    AnalysisEventBus,
    current_event_channel,
    default_event_bus,
)
from app.gemini_client import GeminiClient, GeminiResponseValidationError, GeminiUnavailableError
from app.mcp_client import InProcessMCPClient, MCPClient, MCPError
from app.models import Scene
from app.workflow import Analysis, AnalysisEngine, AnalysisOutcome, Incident

AGENT_NAME = "ProductionOrchestrator"


class DomainAnalysisError(RuntimeError):
    """A required domain result was unavailable or unusable."""


class ExecutionStepError(RuntimeError):
    """Raised when a specific plan execution step fails."""

    def __init__(self, step_id: str, error_code: str, cause: BaseException) -> None:
        super().__init__(f"Step {step_id} failed with {error_code}: {cause}")
        self.step_id = step_id
        self.error_code = error_code
        self.cause = cause


async def _gather_fail_fast(*awaitables):
    """Cancel sibling domain calls when any required result fails."""
    tasks = [asyncio.create_task(item) for item in awaitables]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


def _public_failure_code(exc: BaseException) -> str:
    if isinstance(exc, GeminiUnavailableError):
        return "GEMINI_UNAVAILABLE"
    if isinstance(exc, GeminiResponseValidationError):
        return "GEMINI_RESPONSE_INVALID"
    if isinstance(exc, MCPError):
        return "MCP_FAILED"
    return "DOMAIN_ANALYSIS_FAILED"


class ProductionOrchestrator(AnalysisEngine):
    """Orchestrates multi-agent impact analysis and plan execution."""

    def __init__(
        self,
        gemini_client: GeminiClient | None = None,
        event_bus: AnalysisEventBus | None = None,
        db_engine: Engine | None = None,
        actor_agent: ActorAgent | None = None,
        location_agent: LocationAgent | None = None,
        equipment_agent: EquipmentAgent | None = None,
        schedule_agent: ScheduleAgent | None = None,
        mcp_client: MCPClient | None = None,
        runtime_mode: str = "RECORDED_REPLAY",
    ) -> None:
        self._gemini = gemini_client
        self._event_bus = event_bus or default_event_bus
        self._db_engine = db_engine
        self._mcp_client = mcp_client or InProcessMCPClient()
        self._runtime_mode = runtime_mode
        self._actor_agent = actor_agent or ActorAgent(
            gemini_client=self._gemini,
            event_bus=self._event_bus,
            mcp_client=self._mcp_client,
        )
        self._location_agent = location_agent or LocationAgent(
            gemini_client=self._gemini,
            event_bus=self._event_bus,
            mcp_client=self._mcp_client,
        )
        self._equipment_agent = equipment_agent or EquipmentAgent(
            gemini_client=self._gemini,
            event_bus=self._event_bus,
            mcp_client=self._mcp_client,
        )
        self._schedule_agent = schedule_agent or ScheduleAgent(
            gemini_client=self._gemini, event_bus=self._event_bus
        )

    async def run_analysis(self, incident: Incident, analysis_id: str) -> AnalysisOutcome:
        """Run the full multi-agent coordination pipeline for an incident (SPEC §6.1)."""
        channel_token = current_event_channel.set(analysis_id)
        scene_id = incident.scene_id

        self._publish(
            analysis_id,
            "QUEUED",
            f"[{self._runtime_mode}] Incident detected: {incident.headline}. "
            "Coordinating response across production resources.",
            type="STATUS",
            resource=scene_id,
        )

        try:
            # Stage 1: Determine affected resources via Script Agent
            self._publish(
                analysis_id,
                "ANALYZING",
                f"Analyzing script requirements and dependencies for {scene_id}",
                type="STATUS",
                resource=scene_id,
            )
            script_result = await analyze_scene(
                scene_id,
                analysis_id=analysis_id,
                event_bus=self._event_bus,
                mcp_client=self._mcp_client,
            )

            original_start = script_result.scene.scheduled
            duration_hours = script_result.scene.duration_hours
            orig_location_id = script_result.dependencies.location or "LOC-003"
            actor_ids = script_result.dependencies.actors
            equip_ids = script_result.dependencies.equipment

            # Stage 2: Parallel domain investigation (Actor, Location, Equipment)
            self._publish(
                analysis_id,
                "ANALYZING",
                f"Delegating impact investigation to domain agents for {len(actor_ids)} actors, "
                f"{len(equip_ids)} equipment items, and location {orig_location_id}",
                type="STATUS",
                resource=scene_id,
            )

            # Look up indoor alternative locations
            loc_alt_task = self._location_agent.propose_alternative(
                analysis_id,
                location_id=orig_location_id,
                scene_id=scene_id,
                requested_start=original_start,
                requested_end=f"{original_start[:11]}18:00",
            )

            # Query Actor availability
            actor_tasks = [
                self._actor_agent.resolve_availability(
                    analysis_id,
                    actor_id=act_id,
                    scene_id=scene_id,
                    requested_start=original_start,
                    requested_end=f"{original_start[:11]}18:00",
                )
                for act_id in actor_ids
            ]

            # Query Equipment availability
            equip_tasks = [
                self._equipment_agent.resolve_reservation(
                    analysis_id,
                    equipment_id=eq_id,
                    scene_id=scene_id,
                    requested_start=original_start,
                    requested_end=f"{original_start[:11]}18:00",
                )
                for eq_id in equip_ids
            ]

            results = await _gather_fail_fast(
                loc_alt_task,
                *actor_tasks,
                *equip_tasks,
            )

            loc_res = results[0]
            actor_results = results[1 : 1 + len(actor_tasks)]
            equip_results = results[1 + len(actor_tasks) :]

            # Resolve alternative indoor location
            if not loc_res.proposed_location_id:
                raise DomainAnalysisError("NO_AVAILABLE_LOCATION")
            alt_location_id = loc_res.proposed_location_id
            matched = [c for c in loc_res.candidates if c.id == alt_location_id]
            if not matched:
                raise DomainAnalysisError("INVALID_LOCATION_RESULT")
            alt_location_name = matched[0].name

            # Stage 3: Synthesize candidate rescheduling slots
            candidate_slots = [
                CandidateSlot(
                    candidate_id="OPTION_A",
                    start_time="2026-09-02T16:00",
                    end_time="2026-09-02T20:00",
                    location_id=alt_location_id,
                    cost_impact=8400.0,
                    delay_days=0,
                    base_risk="LOW",
                    label=f"Move {scene_id} to Wed 16:00–20:00 ({alt_location_name})",
                ),
                CandidateSlot(
                    candidate_id="OPTION_B",
                    start_time="2026-09-03T09:00",
                    end_time="2026-09-03T13:00",
                    location_id=alt_location_id,
                    cost_impact=29800.0,
                    delay_days=1,
                    base_risk="LOW",
                    label=f"Move {scene_id} to Thu 09:00–13:00 ({alt_location_name})",
                ),
                CandidateSlot(
                    candidate_id="OPTION_C",
                    start_time="2026-09-04T09:00",
                    end_time="2026-09-04T13:00",
                    location_id=alt_location_id,
                    cost_impact=35000.0,
                    delay_days=2,
                    base_risk="MEDIUM",
                    label=f"Move {scene_id} to Fri 09:00–13:00 ({alt_location_name})",
                ),
            ]

            # Stage 4: Budget impact estimation
            budget_candidates = [
                CandidateOption(
                    candidate_id=c.candidate_id,
                    new_location_id=c.location_id,
                    new_start=c.start_time,
                    new_end=c.end_time,
                )
                for c in candidate_slots
            ]
            budget_result = await evaluate_cost_impact(
                scene_id=scene_id,
                candidates=budget_candidates,
                analysis_id=analysis_id,
                event_bus=self._event_bus,
                mcp_client=self._mcp_client,
            )

            # Map budget results back to candidate slots
            cost_map = {opt.candidate_id: opt.total_cost_impact for opt in budget_result.options}
            for c in candidate_slots:
                if c.candidate_id in cost_map and cost_map[c.candidate_id] > 0:
                    c.cost_impact = cost_map[c.candidate_id]

            # Stage 5: Build Replan Input and invoke Schedule Agent Constraint Solver
            actor_inputs: list[ActorConstraintInput] = []
            for act_idx, act_id in enumerate(actor_ids):
                res = actor_results[act_idx] if act_idx < len(actor_results) else None
                busy_blocks: list[tuple[str, str]] = []
                day_windows: dict[str, tuple[str, str]] = {}
                hard_stop = None

                if res:
                    reply = res.manager_reply
                    if reply and reply.status == "AVAILABLE":
                        if reply.window_start:
                            day_windows["2026-09-02"] = (
                                reply.window_start,
                                reply.window_end or "20:00",
                            )
                        for c_str in reply.constraints:
                            if "20:00" in c_str:
                                hard_stop = "20:00"
                    elif res.availability:
                        # Extract busy blocks from availability
                        for block in res.availability.get("availability", []):
                            if (
                                block.get("scene_id") != scene_id
                                and "start" in block
                                and "end" in block
                            ):
                                busy_blocks.append((block["start"], block["end"]))

                actor_inputs.append(
                    ActorConstraintInput(
                        actor_id=act_id,
                        name=f"Actor ({act_id})",
                        busy_blocks=busy_blocks,
                        hard_stop_time=hard_stop,
                        day_available_windows=day_windows,
                    )
                )

            location_inputs = [
                LocationConstraintInput(
                    location_id=orig_location_id,
                    name="Rooftop (Outdoor)",
                    weather_dependent=True,
                    has_weather_risk=True,
                ),
                LocationConstraintInput(
                    location_id=alt_location_id,
                    name=alt_location_name,
                    weather_dependent=False,
                    has_weather_risk=False,
                ),
            ]

            equipment_inputs = []
            for eq_idx, eq_id in enumerate(equip_ids):
                res = equip_results[eq_idx]
                equipment_inputs.append(
                    EquipmentConstraintInput(
                        equipment_id=eq_id,
                        name=f"Equipment ({eq_id})",
                        extension_available=bool(res.reserved),
                    )
                )

            replan_input = ScheduleReplanInput(
                scene=TargetSceneMetadata(
                    scene_id=scene_id,
                    name=script_result.scene.name,
                    duration_hours=duration_hours,
                    original_scheduled=original_start,
                    location_id=orig_location_id,
                    actor_ids=actor_ids,
                    equipment_ids=equip_ids,
                ),
                candidates=candidate_slots,
                actors=actor_inputs,
                locations=location_inputs,
                equipment=equipment_inputs,
                continuity=ContinuityConstraintInput(
                    must_precede=script_result.continuity.must_precede,
                    must_follow=script_result.continuity.must_follow,
                    same_day_as=script_result.continuity.same_day_as,
                ),
            )

            schedule_res = await self._schedule_agent.replan(analysis_id, replan_input)

            # Stage 6: Formulate replan options and prepare outcome (SPEC §9.9)
            self._publish(
                analysis_id,
                "ANALYZING",
                f"Multi-agent analysis completed: {len(schedule_res.options)} feasible replan options formulated. Awaiting Producer approval.",
                type="REPLAN_COMPLETED",
                resource=scene_id,
            )

            options_dicts = [opt.model_dump(mode="json") for opt in schedule_res.options]

            return AnalysisOutcome(
                status="COMPLETED",
                options=options_dicts,
                explainability=schedule_res.overall_explainability,
            )

        except Exception as exc:  # noqa: BLE001
            failure_code = _public_failure_code(exc)
            self._publish(
                analysis_id,
                "FAILED",
                f"Production Orchestrator analysis failed: {failure_code}",
                type="STATUS",
                resource=scene_id,
            )
            return AnalysisOutcome(
                status="FAILED",
                options=[],
                explainability=f"Analysis failed: {failure_code}",
            )
        finally:
            current_event_channel.reset(channel_token)

    async def execute_plan(
        self,
        analysis_id: str,
        option: dict[str, Any],
        incident_id: str,
        db: Session | None = None,
    ) -> list[str]:
        channel_token = current_event_channel.set(analysis_id)
        try:
            return await self._execute_plan(analysis_id, option, incident_id, db)
        finally:
            current_event_channel.reset(channel_token)

    async def _execute_plan(
        self,
        analysis_id: str,
        option: dict[str, Any],
        incident_id: str,
        db: Session | None = None,
    ) -> list[str]:
        """Execute the approved plan across MCP servers and update Resource Graph (SPEC §9.10)."""
        scene_id = option.get("target_scene_id", "SC-042")
        new_loc_id = option.get("location_id", "LOC-STUDIO-B")
        start_time = option.get("start_time", "2026-09-02T16:00")
        end_time = option.get("end_time", "2026-09-02T20:00")

        self._publish(
            analysis_id,
            "ANALYZING",
            f"[{self._runtime_mode}] Executing approved plan {option.get('option_id')}: "
            "updating bookings and production schedule",
            type="EXECUTION",
            resource=scene_id,
        )

        with get_session(self._db_engine) if db is None else _db_context(db) as session:
            analysis = session.get(Analysis, analysis_id)
            if analysis is None:
                analysis = Analysis(
                    analysis_id=analysis_id,
                    incident_id=incident_id,
                    status="COMPLETED",
                    execution_status="IN_PROGRESS",
                    execution_steps=[],
                )
                session.add(analysis)
                session.commit()

            raw_steps = list(analysis.execution_steps or [])
            step_map: dict[str, dict[str, Any]] = {}
            for s in raw_steps:
                if isinstance(s, dict) and "step_id" in s:
                    step_map[s["step_id"]] = dict(s)

            def get_step_status(step_id: str) -> str:
                return step_map.get(step_id, {}).get("status", "PENDING")

            def save_step(
                step_id: str,
                label: str,
                status: str,
                *,
                error_code: str | None = None,
                error_message: str | None = None,
                details: str | None = None,
            ) -> None:
                record = step_map.get(
                    step_id,
                    {
                        "step_id": step_id,
                        "label": label,
                        "status": "PENDING",
                        "attempt": 0,
                    },
                )
                record["status"] = status
                if status == "IN_PROGRESS":
                    record["attempt"] = record.get("attempt", 0) + 1
                    record["started_at"] = datetime.now().isoformat()
                elif status in ("COMPLETED", "FAILED"):
                    record["finished_at"] = datetime.now().isoformat()
                if error_code:
                    record["error_code"] = error_code
                if error_message:
                    record["error_message"] = error_message
                if details:
                    record["details"] = details
                step_map[step_id] = record
                analysis.execution_steps = list(step_map.values())
                session.commit()

            steps: list[str] = []

            # Step 1: Confirm Location
            step_id = "CONFIRM_LOCATION"
            label = f"Location {new_loc_id} confirmed"
            if get_step_status(step_id) == "COMPLETED":
                steps.append(step_map[step_id].get("details") or label)
            else:
                save_step(step_id, label, "IN_PROGRESS")
                try:
                    await self._mcp_client.call(
                        "location",
                        "confirm_location",
                        {
                            "location_id": new_loc_id,
                            "scene_id": scene_id,
                            "start": start_time,
                            "end": end_time,
                        },
                    )
                    details = f"Location {new_loc_id} confirmed ({start_time} - {end_time})"
                    save_step(step_id, label, "COMPLETED", details=details)
                    steps.append(details)
                    self._publish(
                        analysis_id,
                        "ANALYZING",
                        f"✓ Location {new_loc_id} confirmed",
                        type="EXECUTION",
                        resource=new_loc_id,
                    )
                except BaseException as exc:
                    err_code = _public_failure_code(exc)
                    save_step(step_id, label, "FAILED", error_code=err_code, error_message=str(exc))
                    analysis.execution_status = "FAILED"
                    session.commit()
                    self._publish(
                        analysis_id,
                        "FAILED",
                        f"Location confirmation failed: {exc}",
                        type="EXECUTION_FAILED",
                        resource=new_loc_id,
                    )
                    raise ExecutionStepError(step_id, err_code, exc) from exc

            # Step 2: Confirm Actors
            step_id = "CONFIRM_ACTORS"
            label = "Actor bookings confirmed"
            if get_step_status(step_id) == "COMPLETED":
                steps.append(step_map[step_id].get("details") or label)
            else:
                save_step(step_id, label, "IN_PROGRESS")
                try:
                    scene = session.get(Scene, scene_id)
                    actor_details = []
                    if scene:
                        for actor in scene.actors:
                            await self._mcp_client.call(
                                "actor", "confirm_actor", {"actor_id": actor.id}
                            )
                            d = f"Actor {actor.name} ({actor.id}) booking confirmed"
                            actor_details.append(d)
                            self._publish(
                                analysis_id,
                                "ANALYZING",
                                f"✓ Actor booking updated: {actor.name}",
                                type="EXECUTION",
                                resource=actor.id,
                            )
                    details = "; ".join(actor_details) if actor_details else label
                    save_step(step_id, label, "COMPLETED", details=details)
                    steps.extend(actor_details)
                except BaseException as exc:
                    err_code = _public_failure_code(exc)
                    save_step(step_id, label, "FAILED", error_code=err_code, error_message=str(exc))
                    analysis.execution_status = "FAILED"
                    session.commit()
                    self._publish(
                        analysis_id,
                        "FAILED",
                        f"Actor booking confirmation failed: {exc}",
                        type="EXECUTION_FAILED",
                        resource=scene_id,
                    )
                    raise ExecutionStepError(step_id, err_code, exc) from exc

            # Step 3: Reserve Equipment
            step_id = "RESERVE_EQUIPMENT"
            label = "Equipment reservations confirmed"
            if get_step_status(step_id) == "COMPLETED":
                steps.append(step_map[step_id].get("details") or label)
            else:
                save_step(step_id, label, "IN_PROGRESS")
                try:
                    scene = session.get(Scene, scene_id)
                    equip_details = []
                    if scene:
                        for eq in scene.equipment:
                            await self._mcp_client.call(
                                "equipment",
                                "reserve_equipment",
                                {
                                    "equipment_id": eq.id,
                                    "scene_id": scene_id,
                                    "start": start_time,
                                    "end": end_time,
                                },
                            )
                            d = f"Equipment {eq.name} ({eq.id}) reservation extended"
                            equip_details.append(d)
                            self._publish(
                                analysis_id,
                                "ANALYZING",
                                f"✓ Equipment reserved: {eq.name}",
                                type="EXECUTION",
                                resource=eq.id,
                            )
                    details = "; ".join(equip_details) if equip_details else label
                    save_step(step_id, label, "COMPLETED", details=details)
                    steps.extend(equip_details)
                except BaseException as exc:
                    err_code = _public_failure_code(exc)
                    save_step(step_id, label, "FAILED", error_code=err_code, error_message=str(exc))
                    analysis.execution_status = "FAILED"
                    session.commit()
                    self._publish(
                        analysis_id,
                        "FAILED",
                        f"Equipment reservation failed: {exc}",
                        type="EXECUTION_FAILED",
                        resource=scene_id,
                    )
                    raise ExecutionStepError(step_id, err_code, exc) from exc

            # Step 4: Update Scene in DB
            step_id = "UPDATE_SCENE"
            label = f"Scene {scene_id} schedule updated"
            if get_step_status(step_id) == "COMPLETED":
                steps.append(step_map[step_id].get("details") or label)
            else:
                save_step(step_id, label, "IN_PROGRESS")
                try:
                    scene = session.get(Scene, scene_id)
                    if scene:
                        scene.location_id = new_loc_id
                        scene.scheduled = datetime.fromisoformat(start_time)
                        session.add(scene)
                        session.commit()
                    details = f"Scene {scene_id} schedule updated to {start_time} at {new_loc_id}"
                    save_step(step_id, label, "COMPLETED", details=details)
                    steps.append(details)
                    self._publish(
                        analysis_id,
                        "ANALYZING",
                        f"✓ Production Schedule updated for {scene_id}",
                        type="EXECUTION",
                        resource=scene_id,
                    )
                except BaseException as exc:
                    err_code = "DB_UPDATE_FAILED"
                    save_step(step_id, label, "FAILED", error_code=err_code, error_message=str(exc))
                    analysis.execution_status = "FAILED"
                    session.commit()
                    raise ExecutionStepError(step_id, err_code, exc) from exc

            # Step 5: Mark Incident Resolved
            step_id = "RESOLVE_INCIDENT"
            label = f"Incident {incident_id} marked resolved"
            if get_step_status(step_id) == "COMPLETED":
                steps.append(step_map[step_id].get("details") or label)
            else:
                save_step(step_id, label, "IN_PROGRESS")
                try:
                    incident = session.get(Incident, incident_id)
                    if incident:
                        incident.resolved = True
                        session.add(incident)
                    analysis.execution_status = "COMPLETED"
                    session.commit()
                    details = f"Incident {incident_id} marked resolved"
                    save_step(step_id, label, "COMPLETED", details=details)
                    steps.append(details)
                    self._publish(
                        analysis_id,
                        "COMPLETED",
                        f"✓ Incident {incident_id} resolved: closed-loop execution complete",
                        type="EXECUTION_COMPLETED",
                        resource=incident_id,
                    )
                except BaseException as exc:
                    err_code = "DB_UPDATE_FAILED"
                    save_step(step_id, label, "FAILED", error_code=err_code, error_message=str(exc))
                    analysis.execution_status = "FAILED"
                    session.commit()
                    raise ExecutionStepError(step_id, err_code, exc) from exc

            return steps

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


class _db_context:
    """Helper context manager for already open db sessions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def __enter__(self) -> Session:
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
