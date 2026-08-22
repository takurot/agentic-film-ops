"""Script Agent (SPEC §6.5, Issue #32).

A **read-only** Agent providing scene/script structural information to the
Orchestrator (#9) and other Agents (notably the Schedule Agent, #14, which
needs continuity data for its Constraint Solver — SPEC §6.6/§4.7). No writes,
no external contact (SPEC §6.5's flow has no manager/vendor contact step,
unlike Actor/Equipment Agent — SPEC §6.2/§6.3).

Flow (SPEC §6.5, verbatim):
    1. Script MCP -> get_scene() / get_scene_requirements() for scene requirements
    2. get_scene_dependencies() to identify affected resources (Actor/Equipment/Location)
    3. get_continuity_constraints() (SPEC §4.7) for continuity data
    4. Return the dependency list to the Orchestrator

Deliberately no Gemini call: unlike Actor Agent (parses free-text manager
replies) or Weather Agent (evaluates a risk threshold), SPEC §6.5's flow is
pure mechanical MCP-data aggregation with no natural-language interpretation
or judgment call to make. The "Agent reasoning is Real" boundary (SPEC §11)
is satisfied one level up: the Orchestrator's "Determine affected resources"
step (SPEC §6.1), which *consumes* this Agent's output, is the Real-Gemini
reasoning step. If continuity data ever needs interpretive explanation (e.g.
Explainability text, SPEC §9.8), that's new scope beyond #32's Acceptance
Criteria and belongs in a follow-up issue.

Transport note (SPEC §5 "Transport & Invocation"): production adapts the
lifespan-owned stdio `MCPClient` to `ScriptMCPPort`. Explicit replay and unit
tests may use the in-process port, preserving the same consumer-owned
interface and validated result models.
"""

from typing import Any, Protocol

from pydantic import BaseModel

from app.events import AgentEvent, AnalysisEventBus, default_event_bus
from app.mcp_client import MCPClient
from app.mcp_servers.script import (
    get_continuity_constraints as _get_continuity_constraints,
)
from app.mcp_servers.script import (
    get_scene as _get_scene,
)
from app.mcp_servers.script import (
    get_scene_dependencies as _get_scene_dependencies,
)
from app.mcp_servers.script import (
    get_scene_requirements as _get_scene_requirements,
)

AGENT_NAME = "ScriptAgent"


class SceneInfo(BaseModel):
    """Scene metadata, shaped from Script MCP's `get_scene()` (SPEC §4.1).
    Resource links (`actors`/`equipment`/`location`) live in `SceneDependencies`
    instead — this model only carries metadata, to avoid two fields disagreeing
    about the same links."""

    scene_id: str
    name: str
    type: str
    duration_hours: float
    scheduled: str


class SceneRequirements(BaseModel):
    """What's required to shoot the scene, from `get_scene_requirements()`."""

    scene_id: str
    duration_hours: float
    location_type: str | None
    weather_dependent: bool
    required_equipment: list[str]
    required_crew: list[str]


class SceneDependencies(BaseModel):
    """Resources this scene depends on (SPEC §5.5 AC: actor/equipment/location),
    from `get_scene_dependencies()` — the canonical source for resource links
    in `ScriptAgentResult`."""

    scene_id: str
    actors: list[str]
    equipment: list[str]
    location: str | None


class ContinuityConstraints(BaseModel):
    """Continuity constraints, shaped per SPEC §4.7."""

    scene_id: str
    must_precede: list[str]
    must_follow: list[str]
    same_day_as: list[str]
    notes: str


class ScriptAgentResult(BaseModel):
    """What the Script Agent returns to the Orchestrator (SPEC §6.5 step 4)
    and other Agents (e.g. Schedule Agent, #14)."""

    scene_id: str
    scene: SceneInfo
    requirements: SceneRequirements
    dependencies: SceneDependencies
    continuity: ContinuityConstraints


class ScriptMCPPort(Protocol):
    """The four Script MCP tools this Agent depends on (SPEC §5.5)."""

    async def get_scene(self, scene_id: str) -> dict[str, Any]: ...

    async def get_scene_requirements(self, scene_id: str) -> dict[str, Any]: ...

    async def get_scene_dependencies(self, scene_id: str) -> dict[str, Any]: ...

    async def get_continuity_constraints(self, scene_id: str) -> dict[str, Any]: ...


class _InProcessScriptMCP:
    """Explicit replay/test port calling registered tool functions in-process."""

    async def get_scene(self, scene_id: str) -> dict[str, Any]:
        return await _get_scene(scene_id=scene_id)

    async def get_scene_requirements(self, scene_id: str) -> dict[str, Any]:
        return await _get_scene_requirements(scene_id=scene_id)

    async def get_scene_dependencies(self, scene_id: str) -> dict[str, Any]:
        return await _get_scene_dependencies(scene_id=scene_id)

    async def get_continuity_constraints(self, scene_id: str) -> dict[str, Any]:
        return await _get_continuity_constraints(scene_id=scene_id)


_default_mcp = _InProcessScriptMCP()


class _ClientScriptMCP:
    def __init__(self, client: MCPClient) -> None:
        self._client = client

    async def get_scene(self, scene_id: str) -> dict[str, Any]:
        return await self._client.call("script", "get_scene", {"scene_id": scene_id})

    async def get_scene_requirements(self, scene_id: str) -> dict[str, Any]:
        return await self._client.call("script", "get_scene_requirements", {"scene_id": scene_id})

    async def get_scene_dependencies(self, scene_id: str) -> dict[str, Any]:
        return await self._client.call("script", "get_scene_dependencies", {"scene_id": scene_id})

    async def get_continuity_constraints(self, scene_id: str) -> dict[str, Any]:
        return await self._client.call(
            "script", "get_continuity_constraints", {"scene_id": scene_id}
        )


async def analyze_scene(
    scene_id: str,
    *,
    analysis_id: str,
    event_bus: AnalysisEventBus | None = None,
    mcp: ScriptMCPPort | None = None,
    mcp_client: MCPClient | None = None,
) -> ScriptAgentResult:
    """Run the SPEC §6.5 flow for `scene_id`, reporting status transitions to
    the Event Stream (SPEC §8) under `analysis_id`.

    Raises whatever the underlying `ScriptMCPPort` raises (e.g. `ValueError`
    for an unknown `scene_id`, from the real Script MCP) after publishing a
    FAILED event — mirrors `MCPCommonServer.tool()`'s propagate-after-report
    policy (SPEC §5), so the Orchestrator sees the exception rather than a
    silently swallowed failure.
    """
    bus = event_bus or default_event_bus
    if mcp is not None and mcp_client is not None:
        raise ValueError("Pass either mcp or mcp_client, not both")
    script_mcp = mcp or (_ClientScriptMCP(mcp_client) if mcp_client else _default_mcp)

    def publish(status: str, message: str, *, type: str) -> None:
        bus.publish(
            analysis_id,
            AgentEvent.create(
                agent=AGENT_NAME,
                type=type,
                status=status,
                message=message,
                resource=scene_id,
            ),
        )

    publish("QUEUED", f"Queued script analysis for {scene_id}", type="STATUS")

    try:
        publish(
            "QUERYING_MCP",
            f"Fetching scene and requirements for {scene_id}",
            type="MCP_QUERY",
        )
        scene_raw = await script_mcp.get_scene(scene_id)
        requirements_raw = await script_mcp.get_scene_requirements(scene_id)

        publish(
            "QUERYING_MCP",
            f"Identifying affected resources for {scene_id}",
            type="MCP_QUERY",
        )
        dependencies_raw = await script_mcp.get_scene_dependencies(scene_id)

        publish(
            "QUERYING_MCP",
            f"Checking continuity constraints for {scene_id}",
            type="MCP_QUERY",
        )
        continuity_raw = await script_mcp.get_continuity_constraints(scene_id)
    except Exception as exc:
        publish("FAILED", str(exc), type="STATUS")
        raise

    publish("ANALYZING", f"Assembling scene impact for {scene_id}", type="STATUS")

    result = ScriptAgentResult(
        scene_id=scene_id,
        scene=SceneInfo(**scene_raw),
        requirements=SceneRequirements(**requirements_raw),
        dependencies=SceneDependencies(**dependencies_raw),
        continuity=ContinuityConstraints(**continuity_raw),
    )

    publish("COMPLETED", f"Scene impact analysis complete for {scene_id}", type="STATUS")

    return result
