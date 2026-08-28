"""Explicit runtime profiles and lifespan-owned application dependencies."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel

from app.db import DEFAULT_DB_PATH
from app.gemini_client import DEFAULT_MODEL, GeminiClient, GeminiConfig
from app.mcp_client import InProcessMCPClient, MCPClient, MCPStdioClient


class RuntimeConfigurationError(RuntimeError):
    """Runtime configuration is missing or unsupported."""


class RuntimeMode(StrEnum):
    LIVE_GEMINI = "LIVE_GEMINI"
    RECORDED_REPLAY = "RECORDED_REPLAY"


class RuntimeMetadata(BaseModel):
    mode: RuntimeMode
    reasoning_provider: str
    model: str | None
    mcp_transport: str
    adk_enabled: bool = False


@dataclass(frozen=True)
class RuntimeSettings:
    mode: RuntimeMode
    gemini_api_key: str | None = None
    model: str = DEFAULT_MODEL
    db_path: Path = DEFAULT_DB_PATH

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "RuntimeSettings":
        source = os.environ if environ is None else environ
        raw_mode = source.get("FILMOPS_RUNTIME_MODE")
        try:
            mode = RuntimeMode(raw_mode) if raw_mode is not None else None
        except ValueError as exc:
            raise RuntimeConfigurationError(
                "FILMOPS_RUNTIME_MODE must be LIVE_GEMINI or RECORDED_REPLAY"
            ) from exc
        if mode is None:
            raise RuntimeConfigurationError(
                "FILMOPS_RUNTIME_MODE must be LIVE_GEMINI or RECORDED_REPLAY"
            )
        raw_model = source.get("GEMINI_MODEL")
        if raw_model is not None and not raw_model.strip():
            raise RuntimeConfigurationError("GEMINI_MODEL must not be empty")
        raw_db_path = source.get("FILMOPS_DB_PATH")
        if raw_db_path is not None and not raw_db_path.strip():
            raise RuntimeConfigurationError("FILMOPS_DB_PATH must not be empty")
        return cls(
            mode=mode,
            gemini_api_key=source.get("GEMINI_API_KEY"),
            model=raw_model or DEFAULT_MODEL,
            db_path=Path(raw_db_path or str(DEFAULT_DB_PATH)).resolve(),
        )


class ReplayReasoningClient:
    """Versioned deterministic reasoning used only by RECORDED_REPLAY."""

    async def generate_content(self, contents: str) -> SimpleNamespace:
        if "talent manager" in contents:
            text = (
                '{"status":"AVAILABLE","window_start":"16:00",'
                '"window_end":"20:00","constraints":["Hard stop 20:00"]}'
            )
        elif "equipment rental vendor" in contents:
            text = '{"summary":"The requested equipment window is available."}'
        elif "location manager" in contents:
            text = '{"status":"AVAILABLE","notes":["Replay fixture"]}'
        elif "one-sentence justification" in contents:
            text = "Studio B is the lowest-cost available indoor alternative."
        else:
            text = "Option A is recommended because it preserves schedule and minimizes cost."
        return SimpleNamespace(text=text)


@dataclass(frozen=True)
class RuntimeContainer:
    settings: RuntimeSettings
    metadata: RuntimeMetadata
    engine: Any
    mcp_client: MCPClient
    analysis_runner: Any

    async def start(self) -> None:
        await self.mcp_client.start()

    async def close(self) -> None:
        if self.analysis_runner:
            await self.analysis_runner.shutdown()
        await self.mcp_client.close()


def build_runtime_container(
    settings: RuntimeSettings,
    *,
    gemini_factory: Callable[..., Any] | None = None,
    stdio_factory: Callable[..., MCPClient] | None = None,
    analysis_runner_factory: Callable[..., Any] | None = None,
) -> RuntimeContainer:
    """Build one immutable runtime without any LIVE-to-Replay downgrade."""
    from app.analysis_runner import AnalysisRunner
    from app.db import create_db_engine
    from app.orchestrator import ProductionOrchestrator

    if settings.mode is RuntimeMode.LIVE_GEMINI:
        make_gemini = gemini_factory or GeminiClient
        make_stdio = stdio_factory or MCPStdioClient
        reasoning = make_gemini(GeminiConfig(model=settings.model, api_key=settings.gemini_api_key))
        mcp_client = make_stdio(db_path=settings.db_path)
        metadata = RuntimeMetadata(
            mode=settings.mode,
            reasoning_provider="google-genai",
            model=settings.model,
            mcp_transport="stdio",
            adk_enabled=False,
        )
    else:
        reasoning = ReplayReasoningClient()
        mcp_client = InProcessMCPClient()
        metadata = RuntimeMetadata(
            mode=settings.mode,
            reasoning_provider="recorded-fixture",
            model=None,
            mcp_transport="in-process",
            adk_enabled=False,
        )

    engine = ProductionOrchestrator(
        gemini_client=reasoning,
        mcp_client=mcp_client,
        runtime_mode=settings.mode.value,
    )
    db_engine = create_db_engine(settings.db_path)
    analysis_runner = (
        analysis_runner_factory(db_engine)
        if analysis_runner_factory
        else AnalysisRunner(bind=db_engine)
    )
    return RuntimeContainer(
        settings=settings,
        metadata=metadata,
        engine=engine,
        mcp_client=mcp_client,
        analysis_runner=analysis_runner,
    )
