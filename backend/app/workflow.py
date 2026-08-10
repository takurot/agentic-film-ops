"""Incident/Analysis workflow state backing the API contract (SPEC §3.4).

This is deliberately not the Production Orchestrator (Issue #9) — there is
no real Gemini-driven impact analysis here yet. `AnalysisEngine` is the
seam #9 plugs a real implementation into; until then, `get_analysis_engine`
returns a stub that reports the Orchestrator isn't implemented rather than
fabricating options or a fake success.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base

AnalysisStatus = Literal["QUEUED", "ANALYZING", "COMPLETED", "FAILED"]
Decision = Literal["APPROVE", "REJECT"]
ExecutionStatus = Literal["NOT_STARTED", "IN_PROGRESS", "COMPLETED"]


class Incident(Base):
    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String)
    scene_id: Mapped[str] = mapped_column(String)
    headline: Mapped[str] = mapped_column(String)
    detail: Mapped[str] = mapped_column(String)
    detected_at: Mapped[datetime] = mapped_column(DateTime)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class Analysis(Base):
    __tablename__ = "analyses"

    analysis_id: Mapped[str] = mapped_column(String, primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.incident_id"))
    status: Mapped[str] = mapped_column(String, default="QUEUED")
    options: Mapped[list] = mapped_column(JSON, default=list)
    explainability: Mapped[str | None] = mapped_column(String, default=None)
    decision: Mapped[str | None] = mapped_column(String, default=None)
    decided_option_id: Mapped[str | None] = mapped_column(String, default=None)
    execution_status: Mapped[str] = mapped_column(String, default="NOT_STARTED")
    execution_steps: Mapped[list] = mapped_column(JSON, default=list)


class IncidentSchema(BaseModel):
    incident_id: str
    type: str
    scene_id: str
    headline: str
    detail: str
    detected_at: datetime
    resolved: bool


class AnalysisSchema(BaseModel):
    analysis_id: str
    incident_id: str
    status: AnalysisStatus
    options: list[dict]
    explainability: str | None
    decision: Decision | None
    decided_option_id: str | None
    execution_status: ExecutionStatus


class ExecutionSchema(BaseModel):
    analysis_id: str
    status: ExecutionStatus
    steps: list[str]


class DecisionRequest(BaseModel):
    decision: Decision
    option_id: str | None = None


@dataclass
class AnalysisOutcome:
    status: Literal["COMPLETED", "FAILED"]
    options: list[dict] = field(default_factory=list)
    explainability: str | None = None


class AnalysisEngine(ABC):
    """Runs impact analysis for an incident. Issue #9 provides the real,
    Gemini-driven implementation; see `NotImplementedAnalysisEngine` below.
    """

    @abstractmethod
    async def run_analysis(self, incident: Incident) -> AnalysisOutcome: ...


class NotImplementedAnalysisEngine(AnalysisEngine):
    """Default engine until the Production Orchestrator (#9) is implemented."""

    async def run_analysis(self, incident: Incident) -> AnalysisOutcome:
        return AnalysisOutcome(
            status="FAILED",
            options=[],
            explainability="Production Orchestrator not yet implemented (Issue #9).",
        )


_default_engine = NotImplementedAnalysisEngine()


def get_analysis_engine() -> AnalysisEngine:
    return _default_engine


def analysis_to_schema(analysis: Analysis) -> AnalysisSchema:
    return AnalysisSchema(
        analysis_id=analysis.analysis_id,
        incident_id=analysis.incident_id,
        status=analysis.status,
        options=analysis.options,
        explainability=analysis.explainability,
        decision=analysis.decision,
        decided_option_id=analysis.decided_option_id,
        execution_status=analysis.execution_status,
    )


def incident_to_schema(incident: Incident) -> IncidentSchema:
    return IncidentSchema(
        incident_id=incident.incident_id,
        type=incident.type,
        scene_id=incident.scene_id,
        headline=incident.headline,
        detail=incident.detail,
        detected_at=incident.detected_at,
        resolved=incident.resolved,
    )
