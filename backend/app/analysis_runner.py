"""Background Analysis Runner executing Orchestrator pipelines asynchronously (Issue #82, SPEC §3.4, §6.1)."""

import asyncio
import logging
from typing import Any

from sqlalchemy import Engine, update
from sqlalchemy.orm import Session

from app.db import get_session
from app.events import AgentEvent, current_event_channel, default_event_bus
from app.workflow import Analysis, AnalysisEngine, AnalysisOutcome, Incident

logger = logging.getLogger(__name__)


def recover_stale_analyses(bind: Engine) -> int:
    """Recover leftover QUEUED or ANALYZING records from previous process crashes."""
    with get_session(bind) as session:
        stmt = (
            update(Analysis)
            .where(Analysis.status.in_(["QUEUED", "ANALYZING"]))
            .values(
                status="FAILED",
                explainability="Analysis interrupted by process restart",
            )
        )
        res = session.execute(stmt)
        session.commit()
        return res.rowcount


class AnalysisRunner:
    """Manages background async execution of impact analyses outside HTTP request lifecycles."""

    def __init__(self, bind: Engine) -> None:
        self.bind = bind
        self._tasks: set[asyncio.Task[Any]] = set()

    def start_analysis(
        self,
        incident_id: str,
        analysis_id: str,
        engine: AnalysisEngine,
        bind: Engine | None = None,
    ) -> asyncio.Task[None]:
        """Spawn a background task to execute the analysis pipeline."""
        target_bind = bind or self.bind
        task = asyncio.create_task(
            self._execute_analysis(incident_id, analysis_id, engine, target_bind),
            name=f"analysis-{analysis_id}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _execute_analysis(
        self,
        incident_id: str,
        analysis_id: str,
        engine: AnalysisEngine,
        bind: Engine,
    ) -> None:
        token = current_event_channel.set(analysis_id)
        try:
            # 1. Start Phase: Set status to ANALYZING in a short transaction
            with Session(bind=bind, expire_on_commit=False) as db:
                analysis = db.get(Analysis, analysis_id)
                incident = db.get(Incident, incident_id)
                if not analysis or not incident:
                    logger.error(f"Cannot run analysis {analysis_id}: record or incident missing")
                    return
                analysis.status = "ANALYZING"
                db.commit()

            default_event_bus.publish(
                analysis_id,
                AgentEvent.create(
                    agent="Orchestrator",
                    type="AGENT_START",
                    status="ANALYZING",
                    message="Analysis started",
                ),
            )

            # 2. Execution Phase: Run Orchestrator without holding open DB transaction
            try:
                outcome = await engine.run_analysis(incident, analysis_id)
            except asyncio.CancelledError:
                with get_session(bind) as db:
                    analysis = db.get(Analysis, analysis_id)
                    if analysis and analysis.status in ("QUEUED", "ANALYZING"):
                        analysis.status = "FAILED"
                        analysis.explainability = "Analysis was cancelled"
                        db.commit()
                raise

            except BaseException as exc:
                logger.exception("Unhandled error during analysis %s", analysis_id)
                outcome = AnalysisOutcome(
                    status="FAILED",
                    explainability=f"Analysis failed: {exc}",
                )

            # 3. Commit-Before-Publish: Update DB status and options first
            with get_session(bind) as db:
                analysis = db.get(Analysis, analysis_id)
                if analysis:
                    analysis.status = outcome.status
                    analysis.options = outcome.options
                    analysis.explainability = outcome.explainability
                    db.commit()

            # 4. Publish Terminal Event after DB commit
            if outcome.status == "COMPLETED":
                default_event_bus.publish(
                    analysis_id,
                    AgentEvent.create(
                        agent="Orchestrator",
                        type="ANALYSIS_COMPLETED",
                        status="COMPLETED",
                        message="Analysis completed",
                    ),
                )
            else:
                default_event_bus.publish(
                    analysis_id,
                    AgentEvent.create(
                        agent="Orchestrator",
                        type="ANALYSIS_FAILED",
                        status="FAILED",
                        message=outcome.explainability or "Analysis failed",
                    ),
                )

        finally:
            current_event_channel.reset(token)

    def cancel_all(self) -> None:
        """Cancel all running analysis tasks (e.g. on demo reset)."""
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        self._tasks.clear()

    async def shutdown(self) -> None:
        """Gracefully cancel and drain all background tasks on server shutdown."""
        self.cancel_all()
        await asyncio.sleep(0)


def get_analysis_runner(request: Any = None) -> AnalysisRunner:
    if request is not None:
        runtime = getattr(getattr(request, "app", None), "state", None)
        if runtime is not None:
            container = getattr(runtime, "runtime", None)
            if container is not None and getattr(container, "analysis_runner", None) is not None:
                return container.analysis_runner
    from app.db import engine

    return AnalysisRunner(bind=engine)
