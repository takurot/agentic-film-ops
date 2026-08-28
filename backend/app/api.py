"""Dashboard <-> Orchestrator API contract (SPEC §3.4).

This is the *only* path the Dashboard may use to read or change Orchestrator
state (SPEC §3.2) — no route here does so outside of `.../decision`.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis_runner import AnalysisRunner, get_analysis_runner
from app.db import get_db_session
from app.events import AnalysisEvent, default_event_bus
from app.models import Scene
from app.scenario_loader import load_demo_scenario
from app.schemas import (
    ProductionHealthSchema,
    TodaySceneProgressSchema,
    TodaySceneStatus,
)
from app.security import (
    SecurityConfig,
    enforce_mutation_rate_limit,
    enforce_reset_rate_limit,
    verify_demo_auth,
)
from app.seed import reset_demo_state
from app.workflow import (
    Analysis,
    AnalysisEngine,
    DecisionRequest,
    ExecutionSchema,
    Incident,
    analysis_to_schema,
    get_analysis_engine,
    incident_to_schema,
)

router = APIRouter()


@router.get("/api/runtime")
def get_runtime_metadata(request: Request, response: Response) -> dict:
    """Public, secret-free evidence of the backend runtime in use."""
    container = getattr(request.app.state, "runtime", None)
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Runtime container not initialized",
        )
    response.headers["Cache-Control"] = "no-store"
    return container.metadata.model_dump(mode="json")


@router.get("/api/production/health")
def get_production_health(db: Session = Depends(get_db_session)) -> dict:
    """Production Health summary endpoint (SPEC §3.4, §9.1)."""
    active_incidents = (
        db.execute(select(Incident).where(Incident.resolved.is_(False))).scalars().all()
    )
    total_scenes = db.execute(select(Scene)).scalars().all()
    scenario = load_demo_scenario()
    prod = scenario.production

    today_scenes = [
        TodaySceneProgressSchema(
            scene_id=s.scene_id,
            name=s.name,
            status=TodaySceneStatus(s.status),
            progress_percent=int(s.progress_percent),
        )
        for s in scenario.today_scenes
    ]

    return ProductionHealthSchema(
        production_day_current=prod.production_day_current,
        production_day_total=prod.production_day_total,
        schedule_adherence_percent=prod.schedule_adherence_percent,
        budget_spent_usd=prod.budget_spent_usd,
        budget_total_usd=prod.budget_total_usd,
        scenes_completed=prod.scenes_completed,
        scenes_total=prod.scenes_total,
        overall_risk=prod.overall_risk if len(active_incidents) > 0 else "LOW",
        total_scenes=max(len(total_scenes), prod.scenes_total),
        active_incidents=len(active_incidents),
        today_scenes=today_scenes,
    ).model_dump(mode="json")


@router.post(
    "/api/demo/reset",
    dependencies=[Depends(verify_demo_auth), Depends(enforce_reset_rate_limit)],
)
async def reset_demo(
    db: Session = Depends(get_db_session),
    runner: AnalysisRunner = Depends(get_analysis_runner),
) -> dict:
    """Reset the demo scenario to pre-demo baseline (Issue #34, SPEC §2.2)."""
    runner.cancel_all()
    return reset_demo_state(bind=db.get_bind())


@router.get("/api/incidents/active")
def list_active_incidents(db: Session = Depends(get_db_session)) -> list[dict]:
    incidents = db.execute(select(Incident).where(Incident.resolved.is_(False))).scalars().all()
    return [incident_to_schema(i).model_dump(mode="json") for i in incidents]


@router.post(
    "/api/incidents/{incident_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_demo_auth), Depends(enforce_mutation_rate_limit)],
)
async def analyze_incident(
    incident_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    engine: AnalysisEngine = Depends(get_analysis_engine),
    runner: AnalysisRunner = Depends(get_analysis_runner),
) -> dict:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    security_config: SecurityConfig = getattr(
        request.app.state, "security_config", SecurityConfig.from_env()
    )

    # Check concurrency limit
    if runner.active_count >= security_config.max_concurrent_analyses:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"CONCURRENCY_LIMIT_EXCEEDED — Max {security_config.max_concurrent_analyses} active analyses allowed simultaneously",
            headers={"Retry-After": "5"},
        )

    # Guard against duplicate active analysis for the same incident
    active_analysis = (
        db.execute(
            select(Analysis).where(
                Analysis.incident_id == incident_id,
                Analysis.status.in_(["QUEUED", "ANALYZING"]),
            )
        )
        .scalars()
        .first()
    )
    if active_analysis is not None:
        return analysis_to_schema(active_analysis).model_dump(mode="json")

    analysis_id = f"AN-{uuid.uuid4().hex[:8]}"
    analysis = Analysis(
        analysis_id=analysis_id,
        incident_id=incident_id,
        status="QUEUED",
        options=[],
    )
    db.add(analysis)
    db.commit()

    runner.start_analysis(incident_id, analysis_id, engine, bind=db.get_bind())

    return analysis_to_schema(analysis).model_dump(mode="json")


@router.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db_session)) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_to_schema(analysis).model_dump(mode="json")


@router.post(
    "/api/analyses/{analysis_id}/decision",
    dependencies=[Depends(verify_demo_auth), Depends(enforce_mutation_rate_limit)],
)
async def decide_analysis(
    analysis_id: str,
    request: DecisionRequest,
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db_session),
    engine: AnalysisEngine = Depends(get_analysis_engine),
) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    idempotency_key = request.idempotency_key or idempotency_header

    # 1. Existing decision handling: check for duplicate/replay, retry, or conflict
    if analysis.decision is not None:
        is_same_decision = analysis.decision == request.decision and (
            request.decision == "REJECT" or analysis.decided_option_id == request.option_id
        )
        if not is_same_decision:
            raise HTTPException(
                status_code=409,
                detail="Analysis already decided with a different decision or option",
            )

        # Retry handling for FAILED execution
        if request.decision == "APPROVE" and analysis.execution_status == "FAILED":
            option_dict = {option["option_id"]: option for option in (analysis.options or [])}
            selected_option = option_dict.get(request.option_id) or {}
            if idempotency_key is not None:
                analysis.idempotency_key = idempotency_key
            analysis.execution_status = "IN_PROGRESS"
            db.commit()

            try:
                steps = await engine.execute_plan(
                    analysis_id=analysis_id,
                    option=selected_option,
                    incident_id=analysis.incident_id,
                    db=db,
                )
                if not analysis.execution_steps or (
                    analysis.execution_steps and isinstance(analysis.execution_steps[0], str)
                ):
                    analysis.execution_steps = steps
                analysis.execution_status = "COMPLETED"
                db.commit()
                return analysis_to_schema(analysis).model_dump(mode="json")
            except BaseException as exc:
                analysis.execution_status = "FAILED"
                db.commit()
                raise HTTPException(
                    status_code=500, detail=f"Execution retry failed: {exc}"
                ) from exc

        # Idempotent replay if idempotency key is supplied and matches
        if idempotency_key is not None and analysis.idempotency_key == idempotency_key:
            return analysis_to_schema(analysis).model_dump(mode="json")

        # Without an idempotency key matching, repeat decision returns 409
        raise HTTPException(status_code=409, detail="Analysis already decided")

    # 2. Initial decision
    if request.decision == "APPROVE":
        option_dict = {option["option_id"]: option for option in (analysis.options or [])}
        if analysis.status != "COMPLETED" or request.option_id not in option_dict:
            raise HTTPException(status_code=409, detail="No feasible option to approve")
        analysis.decision = "APPROVE"
        analysis.decided_option_id = request.option_id
        analysis.idempotency_key = idempotency_key
        analysis.execution_status = "IN_PROGRESS"
        db.commit()

        try:
            steps = await engine.execute_plan(
                analysis_id=analysis_id,
                option=option_dict[request.option_id],
                incident_id=analysis.incident_id,
                db=db,
            )
            if not analysis.execution_steps or (
                analysis.execution_steps and isinstance(analysis.execution_steps[0], str)
            ):
                analysis.execution_steps = steps
            analysis.execution_status = "COMPLETED"
            db.commit()
        except BaseException as exc:
            analysis.execution_status = "FAILED"
            db.commit()
            raise HTTPException(status_code=500, detail=f"Execution failed: {exc}") from exc

    else:
        analysis.decision = "REJECT"
        analysis.decided_option_id = None
        analysis.idempotency_key = idempotency_key
        analysis.execution_status = "NOT_STARTED"
        db.commit()

    return analysis_to_schema(analysis).model_dump(mode="json")


@router.get("/api/analyses/{analysis_id}/execution")
def get_execution(analysis_id: str, db: Session = Depends(get_db_session)) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    raw_steps = list(analysis.execution_steps or [])
    steps: list[str] = []
    step_records: list[dict] = []
    for item in raw_steps:
        if isinstance(item, dict):
            step_records.append(item)
            steps.append(item.get("details") or item.get("label") or item.get("step_id", ""))
        elif isinstance(item, str):
            steps.append(item)

    return ExecutionSchema(
        analysis_id=analysis.analysis_id,
        status=analysis.execution_status,
        steps=steps,
        step_records=step_records if step_records else None,
    ).model_dump(mode="json")


@router.websocket("/api/analyses/{analysis_id}/events")
async def analysis_events_ws(websocket: WebSocket, analysis_id: str) -> None:
    """WebSocket stream of Agent and MCP events for an analysis (SPEC §3.4, §8)."""
    await websocket.accept()
    queue = default_event_bus.subscribe(analysis_id, replay_history=True)
    try:
        while True:
            try:
                event: AnalysisEvent = await asyncio.wait_for(queue.get(), timeout=1.0)
                await websocket.send_json(event.model_dump(mode="json"))
            except TimeoutError:
                if (
                    getattr(websocket.client_state, "name", None) == "DISCONNECTED"
                    or getattr(websocket.application_state, "name", None) == "DISCONNECTED"
                ):
                    break
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        default_event_bus.unsubscribe(analysis_id, queue)


@router.get("/api/analyses/{analysis_id}/events/stream")
async def analysis_events_sse(
    analysis_id: str,
    db: Session = Depends(get_db_session),
) -> StreamingResponse:
    """Server-Sent Events (SSE) stream of Agent and MCP events (SPEC §3.4, §8)."""
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = default_event_bus.subscribe(analysis_id, replay_history=True)
        try:
            while True:
                try:
                    event: AnalysisEvent = await asyncio.wait_for(queue.get(), timeout=15.0)
                    payload = event.model_dump_json()
                    yield f"data: {payload}\n\n"
                except TimeoutError:
                    # Keepalive comment (SPEC §8)
                    yield ": keepalive\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            default_event_bus.unsubscribe(analysis_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
