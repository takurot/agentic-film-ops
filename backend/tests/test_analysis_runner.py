import asyncio
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.orm import sessionmaker

from app.analysis_runner import AnalysisRunner, recover_stale_analyses
from app.db import create_db_engine, init_db
from app.workflow import (
    Analysis,
    AnalysisEngine,
    AnalysisOutcome,
    Incident,
)


class MockEngine(AnalysisEngine):
    def __init__(self, delay: float = 0.01, should_fail: bool = False):
        self.delay = delay
        self.should_fail = should_fail
        self.call_count = 0

    async def run_analysis(self, incident: Incident, analysis_id: str) -> AnalysisOutcome:
        self.call_count += 1
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.should_fail:
            raise RuntimeError("Engine encountered simulated failure")
        return AnalysisOutcome(
            status="COMPLETED",
            options=[{"option_id": "OPT-A", "cost_impact": 4200}],
            explainability="Simulated explanation",
        )

    async def execute_plan(
        self, analysis_id: str, option: dict, incident_id: str, db: Any = None
    ) -> list[str]:
        return []


@pytest.fixture
def test_db():
    engine = create_db_engine(
        create_db_engine.__defaults__[0] if create_db_engine.__defaults__ else None
    )
    # in-memory sqlite
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    init_db(engine)

    Session = sessionmaker(bind=engine)
    with Session() as db:
        inc = Incident(
            incident_id="INC-001",
            type="WEATHER_RISK",
            scene_id="SC-042",
            headline="Rain alert",
            detail="Storm forecast",
            detected_at=datetime.now(),
            resolved=False,
        )
        db.add(inc)
        db.commit()

    return engine


@pytest.mark.asyncio
async def test_runner_executes_analysis_to_completion(test_db):
    runner = AnalysisRunner(bind=test_db)
    engine = MockEngine(delay=0.01)

    Session = sessionmaker(bind=test_db)
    with Session() as db:
        an = Analysis(analysis_id="AN-100", incident_id="INC-001", status="QUEUED")
        db.add(an)
        db.commit()

    task = runner.start_analysis("INC-001", "AN-100", engine)
    await task

    with Session() as db:
        an = db.get(Analysis, "AN-100")
        assert an is not None
        assert an.status == "COMPLETED"
        assert len(an.options) == 1
        assert an.explainability == "Simulated explanation"


@pytest.mark.asyncio
async def test_runner_handles_engine_exceptions_cleanly(test_db):
    runner = AnalysisRunner(bind=test_db)
    engine = MockEngine(delay=0.01, should_fail=True)

    Session = sessionmaker(bind=test_db)
    with Session() as db:
        an = Analysis(analysis_id="AN-ERR", incident_id="INC-001", status="QUEUED")
        db.add(an)
        db.commit()

    task = runner.start_analysis("INC-001", "AN-ERR", engine)
    await task

    with Session() as db:
        an = db.get(Analysis, "AN-ERR")
        assert an is not None
        assert an.status == "FAILED"
        assert "Simulated failure" in an.explainability or "failed" in an.explainability


@pytest.mark.asyncio
async def test_stale_analysis_recovery(test_db):
    Session = sessionmaker(bind=test_db)
    with Session() as db:
        an1 = Analysis(analysis_id="AN-STALE-1", incident_id="INC-001", status="QUEUED")
        an2 = Analysis(analysis_id="AN-STALE-2", incident_id="INC-001", status="ANALYZING")
        an3 = Analysis(analysis_id="AN-DONE", incident_id="INC-001", status="COMPLETED")
        db.add_all([an1, an2, an3])
        db.commit()

    count = recover_stale_analyses(test_db)
    assert count == 2

    with Session() as db:
        assert db.get(Analysis, "AN-STALE-1").status == "FAILED"
        assert db.get(Analysis, "AN-STALE-2").status == "FAILED"
        assert db.get(Analysis, "AN-DONE").status == "COMPLETED"


@pytest.mark.asyncio
async def test_runner_cancel_all(test_db):
    runner = AnalysisRunner(bind=test_db)
    engine = MockEngine(delay=1.0)  # long running

    Session = sessionmaker(bind=test_db)
    with Session() as db:
        an = Analysis(analysis_id="AN-CANCEL", incident_id="INC-001", status="QUEUED")
        db.add(an)
        db.commit()

    runner.start_analysis("INC-001", "AN-CANCEL", engine)
    await asyncio.sleep(0.02)
    runner.cancel_all()
    await asyncio.sleep(0.02)

    assert len(runner._tasks) == 0
