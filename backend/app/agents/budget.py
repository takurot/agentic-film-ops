"""Budget Agent (SPEC §6.3): reasoning layer over the Budget MCP (SPEC §5.6).

Agent = Reasoning, MCP = Access (SPEC §3.3): this module calls only
`app.mcp_servers.budget`'s tool functions for all budget data — it never
imports `app.db`/`app.models` directly (statically verified by
`tests/test_budget_agent.py`'s import check, covering the Issue #13
Acceptance Criterion "Uses Budget MCP exclusively for access/action").

**Pattern choice — Script Agent, not Actor Agent.** SPEC §6.3 says Budget
Agent's "詳細フローは Actor Agent に準ずる" (flow follows Actor Agent), but
that can't be taken literally: Budget MCP (SPEC §5.6) has no analogue of
Actor MCP's `contact_manager()`/manager-reply tools, so there is no
external-human-contact leg, no `WAITING_EXTERNAL`/`RESPONSE_RECEIVED` pair,
and nothing for a Gemini call to parse. The applicable precedent is instead
Script Agent (`app/agents/script.py`, SPEC §6.5): a read-only, no-external-
contact Agent that fetches from its MCP and shapes the result into Pydantic
models, with a `QUEUED -> QUERYING_MCP(*) -> ANALYZING -> COMPLETED` event
flow.

**SPEC §11 ("Agent reasoning is Real") for this Agent specifically**
(§11 names Budget Agent, unlike Script Agent, so this needs its own
argument rather than borrowing Script Agent's): `estimate_change_cost()`
(Budget MCP) is itself the real computation, run over this seed data's real
Equipment/Location/Crew rate fields — see that function's own docstring.
This Agent's job is to call it once per candidate and assemble the results;
no natural-language interpretation or judgment call happens here. The
downstream consumer that performs "Real" reasoning over the assembled
figures is the Orchestrator at its "Evaluate
alternatives" step (SPEC §6.1) — this Agent's `BudgetAgentResult` is that
step's input, not a place where interpretation already happened. Any
future interpretive cost narrative (e.g. Explainability text, SPEC §9.8)
is new scope for a follow-up issue.

Transport note (SPEC §5 "Transport & Invocation"): production adapts the
lifespan-owned stdio `MCPClient` to `BudgetMCPPort`. Explicit replay and unit
tests may use the in-process port, preserving the same consumer-owned
interface and validated result models.
"""

from collections.abc import Callable
from typing import Any, Protocol

from pydantic import BaseModel, model_validator

from app.events import AgentEvent, AnalysisEventBus, default_event_bus
from app.mcp_client import MCPClient
from app.mcp_servers.budget import estimate_change_cost as _estimate_change_cost
from app.mcp_servers.budget import get_current_budget as _get_current_budget

AGENT_NAME = "BudgetAgent"


class BudgetSnapshot(BaseModel):
    """`get_current_budget()` shaped 1:1 (SPEC §5.6, §9.1's dashboard figure)."""

    total_budget: float
    spent_to_date: float
    remaining: float
    currency: str


class CandidateOption(BaseModel):
    """One candidate re-plan slot for a scene (SPEC §6.6 step 2's "候補と
    なるスロット"), as the caller (the future Schedule Agent, #14) would
    propose it. `candidate_id` is an opaque caller-supplied label used only
    to correlate the returned `CostImpactOption` back to its candidate —
    this Agent doesn't interpret it, and duplicate `candidate_id` values
    across a call are not deduplicated or validated (the caller's
    responsibility, same "opaque, caller-owned" treatment as `scene_id`/
    `actor_id` elsewhere in this codebase's Agents).

    `new_start`/`new_end` must be provided together (or not at all) — the
    same rule `estimate_change_cost()` (Budget MCP) enforces, validated here
    too so a malformed candidate fails at construction time, before any MCP
    call or event is published, rather than surfacing as an
    indistinguishable-looking MCP FAILED event.
    """

    candidate_id: str
    new_location_id: str | None = None
    new_start: str | None = None
    new_end: str | None = None

    @model_validator(mode="after")
    def _require_start_and_end_together(self) -> "CandidateOption":
        if (self.new_start is None) != (self.new_end is None):
            raise ValueError("new_start and new_end must be provided together")
        return self


class CostImpactOption(BaseModel):
    """Cost impact of one candidate (SPEC §6.6 step 3's "Budget MCP から見
    積もったコスト増分" / §9.7's Cost impact card), shaped from
    `estimate_change_cost()`'s cost fields plus `candidate_id` correlation.
    Doesn't echo back `new_location_id`/`new_start`/`new_end` — those
    already live on the input `CandidateOption` (correlated via
    `candidate_id`), and repeating them here would risk the two disagreeing
    (mirrors `script.py`'s `SceneInfo` docstring's same rationale for not
    duplicating resource links across two fields).
    """

    candidate_id: str
    location_cost: float
    vendor_cost: float
    overtime_cost: float
    total_cost_impact: float


class BudgetAgentResult(BaseModel):
    """Handed back to the Orchestrator/Schedule Agent (SPEC §6.6 step 3-4)."""

    scene_id: str
    budget: BudgetSnapshot
    options: list[CostImpactOption]  # same order as the input candidates list


class BudgetMCPPort(Protocol):
    """The two Budget MCP tools this Agent depends on (SPEC §5.6)."""

    async def get_current_budget(self) -> dict[str, Any]: ...

    async def estimate_change_cost(
        self,
        scene_id: str,
        new_location_id: str | None,
        new_start: str | None,
        new_end: str | None,
    ) -> dict[str, Any]: ...


class _InProcessBudgetMCP:
    """Explicit replay/test port calling Budget MCP functions in-process.

    Calls with keyword
    arguments throughout — `MCPCommonServer.tool()` reads its `resource_arg`
    via `kwargs.get(...)`, so a positional call would silently emit
    `MCPCallEvent`s with `resource=None`."""

    async def get_current_budget(self) -> dict[str, Any]:
        return await _get_current_budget()

    async def estimate_change_cost(
        self,
        scene_id: str,
        new_location_id: str | None,
        new_start: str | None,
        new_end: str | None,
    ) -> dict[str, Any]:
        return await _estimate_change_cost(
            scene_id=scene_id,
            new_location_id=new_location_id,
            new_start=new_start,
            new_end=new_end,
        )


_default_mcp = _InProcessBudgetMCP()


class _ClientBudgetMCP:
    def __init__(self, client: MCPClient) -> None:
        self._client = client

    async def get_current_budget(self) -> dict[str, Any]:
        return await self._client.call("budget", "get_current_budget", {})

    async def estimate_change_cost(
        self,
        scene_id: str,
        new_location_id: str | None,
        new_start: str | None,
        new_end: str | None,
    ) -> dict[str, Any]:
        return await self._client.call(
            "budget",
            "estimate_change_cost",
            {
                "scene_id": scene_id,
                "new_location_id": new_location_id,
                "new_start": new_start,
                "new_end": new_end,
            },
        )


async def evaluate_cost_impact(
    scene_id: str,
    candidates: list[CandidateOption],
    *,
    analysis_id: str,
    event_bus: AnalysisEventBus | None = None,
    mcp: BudgetMCPPort | None = None,
    mcp_client: MCPClient | None = None,
) -> BudgetAgentResult:
    """SPEC §6.3 flow (Budget Agent, adapted per this module's docstring):
    fetch the current production budget, then `estimate_change_cost()` once
    per candidate (in order), then assemble the result. Reports status
    transitions to the Event Stream (SPEC §8) under `analysis_id`.

    Raises whatever the underlying `BudgetMCPPort` raises (e.g. `ValueError`
    for an unknown `scene_id`/`new_location_id`, from the real Budget MCP)
    after publishing a FAILED event — mirrors `MCPCommonServer.tool()`'s
    propagate-after-report policy (SPEC §5). A failure partway through the
    candidate loop stops the loop immediately (no further candidates are
    evaluated) rather than continuing past it.

    An empty `candidates` list is a valid, non-error call — the budget
    snapshot alone is a legitimate result (`options` is simply empty).
    """
    bus = event_bus or default_event_bus
    if mcp is not None and mcp_client is not None:
        raise ValueError("Pass either mcp or mcp_client, not both")
    budget_mcp = mcp or (_ClientBudgetMCP(mcp_client) if mcp_client else _default_mcp)

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

    publish("QUEUED", f"Queued budget impact analysis for {scene_id}", type="STATUS")

    try:
        budget_raw, candidate_raws = await _fetch_cost_estimates(
            budget_mcp, scene_id, candidates, publish
        )
    except Exception as exc:
        publish("FAILED", str(exc), type="STATUS")
        raise

    publish(
        "ANALYZING",
        f"Assembling budget impact for {len(candidates)} candidate(s)",
        type="STATUS",
    )

    result = _build_result(scene_id, budget_raw, candidate_raws)

    publish(
        "COMPLETED",
        f"Estimated cost impact for {len(candidates)} candidate(s)",
        type="STATUS",
    )

    return result


async def _fetch_cost_estimates(
    mcp_client: BudgetMCPPort,
    scene_id: str,
    candidates: list[CandidateOption],
    publish: Callable[..., None],
) -> tuple[dict[str, Any], list[tuple[str, dict[str, Any]]]]:
    """SPEC §6.3 flow: current budget, then `estimate_change_cost()` once per
    candidate (in order, stopping immediately on the first failure)."""
    publish("QUERYING_MCP", "Checking current production budget", type="MCP_QUERY")
    budget_raw = await mcp_client.get_current_budget()

    candidate_raws: list[tuple[str, dict[str, Any]]] = []
    for candidate in candidates:
        publish(
            "QUERYING_MCP",
            f"Estimating cost impact of candidate {candidate.candidate_id}",
            type="MCP_QUERY",
        )
        raw = await mcp_client.estimate_change_cost(
            scene_id=scene_id,
            new_location_id=candidate.new_location_id,
            new_start=candidate.new_start,
            new_end=candidate.new_end,
        )
        candidate_raws.append((candidate.candidate_id, raw))
    return budget_raw, candidate_raws


def _build_result(
    scene_id: str,
    budget_raw: dict[str, Any],
    candidate_raws: list[tuple[str, dict[str, Any]]],
) -> BudgetAgentResult:
    return BudgetAgentResult(
        scene_id=scene_id,
        budget=BudgetSnapshot(**budget_raw),
        options=[
            CostImpactOption(
                candidate_id=candidate_id,
                location_cost=raw["location_cost"],
                vendor_cost=raw["vendor_cost"],
                overtime_cost=raw["overtime_cost"],
                total_cost_impact=raw["total_cost_impact"],
            )
            for candidate_id, raw in candidate_raws
        ],
    )
