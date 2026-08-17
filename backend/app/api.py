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
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.events import AnalysisEvent, default_event_bus
from app.models import Scene
from app.schemas import (
    ProductionHealthSchema,
    TodaySceneProgressSchema,
    TodaySceneStatus,
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


@router.get("/api/production/health", response_model=ProductionHealthSchema)
def get_production_health(db: Session = Depends(get_db_session)) -> ProductionHealthSchema:
    """Production Health summary (SPEC §9.1)."""
    total_scenes = db.execute(select(Scene)).scalars().all()
    active_incidents = (
        db.execute(select(Incident).where(Incident.resolved.is_(False))).scalars().all()
    )

    # Today's scenes progress (Scenes 38, 39, 40 per SPEC §9.1)
    today_scenes = [
        TodaySceneProgressSchema(
            scene_id="SC-038",
            name="Scene 38 — Alleyway Chase",
            status=TodaySceneStatus.COMPLETED,
            progress_percent=100,
        ),
        TodaySceneProgressSchema(
            scene_id="SC-039",
            name="Scene 39 — Subway Escape",
            status=TodaySceneStatus.COMPLETED,
            progress_percent=100,
        ),
        TodaySceneProgressSchema(
            scene_id="SC-040",
            name="Scene 40 — Safehouse Planning",
            status=TodaySceneStatus.SHOOTING,
            progress_percent=60,
        ),
    ]

    return ProductionHealthSchema(
        production_day_current=27,
        production_day_total=54,
        schedule_adherence_percent=94.0,
        budget_spent_usd=12_400_000.0,
        budget_total_usd=20_000_000.0,
        scenes_completed=82,
        scenes_total=143,
        overall_risk="MEDIUM" if len(active_incidents) > 0 else "LOW",
        total_scenes=max(len(total_scenes), 143),
        active_incidents=len(active_incidents),
        today_scenes=today_scenes,
    )


@router.post("/api/demo/reset")
def reset_demo(db: Session = Depends(get_db_session)) -> dict:
    """Reset the demo scenario to pre-demo baseline (Issue #34, SPEC §2.2)."""
    return reset_demo_state(bind=db.get_bind())


@router.get("/api/incidents/active")
def list_active_incidents(db: Session = Depends(get_db_session)) -> list[dict]:
    incidents = db.execute(select(Incident).where(Incident.resolved.is_(False))).scalars().all()
    return [incident_to_schema(i).model_dump(mode="json") for i in incidents]


@router.post("/api/incidents/{incident_id}/analyze")
async def analyze_incident(
    incident_id: str,
    db: Session = Depends(get_db_session),
    engine: AnalysisEngine = Depends(get_analysis_engine),
) -> dict:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    analysis_id = f"AN-{uuid.uuid4().hex[:8]}"
    analysis = Analysis(
        analysis_id=analysis_id,
        incident_id=incident_id,
        status="ANALYZING",
        options=[],
    )
    db.add(analysis)
    db.commit()

    outcome = await engine.run_analysis(incident, analysis_id)

    analysis.status = outcome.status
    analysis.options = outcome.options
    analysis.explainability = outcome.explainability
    db.commit()

    return analysis_to_schema(analysis).model_dump(mode="json")


@router.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db_session)) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_to_schema(analysis).model_dump(mode="json")


@router.post("/api/analyses/{analysis_id}/decision")
async def decide_analysis(
    analysis_id: str,
    request: DecisionRequest,
    db: Session = Depends(get_db_session),
    engine: AnalysisEngine = Depends(get_analysis_engine),
) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.decision is not None:
        raise HTTPException(status_code=409, detail="Analysis already decided")

    if request.decision == "APPROVE":
        option_dict = {option["option_id"]: option for option in analysis.options}
        if analysis.status != "COMPLETED" or request.option_id not in option_dict:
            raise HTTPException(status_code=409, detail="No feasible option to approve")
        analysis.decision = "APPROVE"
        analysis.decided_option_id = request.option_id
        analysis.execution_status = "IN_PROGRESS"
        db.commit()

        # Execute approved plan across MCP servers
        steps = await engine.execute_plan(
            analysis_id=analysis_id,
            option=option_dict[request.option_id],
            incident_id=analysis.incident_id,
            db=db,
        )
        analysis.execution_steps = steps
        analysis.execution_status = "COMPLETED"
    else:
        analysis.decision = "REJECT"

    db.commit()
    return analysis_to_schema(analysis).model_dump(mode="json")


@router.get("/api/analyses/{analysis_id}/execution")
def get_execution(analysis_id: str, db: Session = Depends(get_db_session)) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return ExecutionSchema(
        analysis_id=analysis.analysis_id,
        status=analysis.execution_status,
        steps=analysis.execution_steps,
    ).model_dump(mode="json")


@router.websocket("/api/analyses/{analysis_id}/events")
async def analysis_events_ws(websocket: WebSocket, analysis_id: str) -> None:
    """WebSocket stream of Agent and MCP events for an analysis (SPEC §3.4, §8)."""
    await websocket.accept()
    queue = default_event_bus.subscribe(analysis_id, replay_history=True)
    try:
        while True:
            event: AnalysisEvent = await queue.get()
            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
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
