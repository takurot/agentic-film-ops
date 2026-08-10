"""Dashboard <-> Orchestrator API contract (SPEC §3.4).

This is the *only* path the Dashboard may use to read or change Orchestrator
state (SPEC §3.2) — no route here does so outside of `.../decision`.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db_session
from app.events import AgentEvent, default_event_bus
from app.models import Scene
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


@router.get("/api/production/health")
def get_production_health(db: Session = Depends(get_db_session)) -> dict:
    """Production Health summary (SPEC §9.1).

    Schedule/Budget/Risk aggregation depends on the Schedule Agent (#14)
    and Budget Agent (#13), which don't exist yet — reporting only what
    the current data layer actually supports rather than fabricating those
    numbers.
    """
    total_scenes = db.execute(select(Scene)).scalars().all()
    active_incidents = (
        db.execute(select(Incident).where(Incident.resolved.is_(False))).scalars().all()
    )
    return {
        "total_scenes": len(total_scenes),
        "active_incidents": len(active_incidents),
    }


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

    outcome = await engine.run_analysis(incident)

    analysis = Analysis(
        analysis_id=f"AN-{uuid.uuid4().hex[:8]}",
        incident_id=incident_id,
        status=outcome.status,
        options=outcome.options,
        explainability=outcome.explainability,
    )
    db.add(analysis)
    db.commit()

    return {"analysis_id": analysis.analysis_id}


@router.get("/api/analyses/{analysis_id}")
def get_analysis(analysis_id: str, db: Session = Depends(get_db_session)) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_to_schema(analysis).model_dump(mode="json")


@router.post("/api/analyses/{analysis_id}/decision")
def decide_analysis(
    analysis_id: str, request: DecisionRequest, db: Session = Depends(get_db_session)
) -> dict:
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.decision is not None:
        raise HTTPException(status_code=409, detail="Analysis already decided")

    if request.decision == "APPROVE":
        option_ids = {option["option_id"] for option in analysis.options}
        if analysis.status != "COMPLETED" or request.option_id not in option_ids:
            raise HTTPException(status_code=409, detail="No feasible option to approve")
        analysis.decision = "APPROVE"
        analysis.decided_option_id = request.option_id
        analysis.execution_status = "IN_PROGRESS"
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
async def analysis_events(websocket: WebSocket, analysis_id: str) -> None:
    await websocket.accept()
    queue = default_event_bus.subscribe(analysis_id)
    try:
        while True:
            event: AgentEvent = await queue.get()
            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    finally:
        default_event_bus.unsubscribe(analysis_id, queue)
