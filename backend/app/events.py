"""The Agent Event Stream (SPEC §8), delivered over `WS
/api/analyses/{analysis_id}/events` (SPEC §3.4).

Agent events (this module's `AgentEvent`) and MCP call events
(`mcp_common.events.MCPCallEvent`) are multiplexed onto the same
per-analysis stream, distinguished by `type == "MCP_CALL"` for the latter.

`AnalysisEventBus` itself is keyed by a generic `channel` string, not only
`analysis_id` — an `Analysis` row (and its id) only exists once a human has
triggered impact analysis for an already-detected Incident (SPEC §9.1's
"START AI IMPACT ANALYSIS"). Agents that *originate* incidents (e.g.
WeatherAgent, SPEC §6.4) run before that id exists, so they publish on a
different channel (see `scene_channel`); `/api/analyses/{id}/events`
(app/api.py) simply subscribes with `analysis_id` as the channel, unchanged.
"""

import asyncio
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from mcp_common.events import MCPCallEvent

AgentEventStatus = Literal[
    "QUEUED",
    "THINKING",
    "QUERYING_MCP",
    "WAITING_EXTERNAL",
    "RESPONSE_RECEIVED",
    "ANALYZING",
    "COMPLETED",
    "FAILED",
]


class AgentEvent(BaseModel):
    """An Agent's progress update, shaped like SPEC §8.1's example."""

    timestamp: str
    agent: str
    type: str
    status: AgentEventStatus
    message: str
    resource: str | None = None

    @classmethod
    def create(
        cls,
        *,
        agent: str,
        type: str,  # matches SPEC §8.1's field name
        status: AgentEventStatus,
        message: str,
        resource: str | None = None,
    ) -> "AgentEvent":
        """Build an event with `timestamp` filled in, mirroring
        `MCPCallEvent.create` (mcp_common/events.py) so Agents don't each
        format `datetime.now()` themselves."""
        return cls(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent=agent,
            type=type,
            status=status,
            message=message,
            resource=resource,
        )


AnalysisEvent = AgentEvent | MCPCallEvent


def scene_channel(scene_id: str) -> str:
    """Event bus channel for an Agent monitoring a scene ahead of any Incident
    or Analysis existing (e.g. WeatherAgent, SPEC §6.4)."""
    return f"scene:{scene_id}"


class AnalysisEventBus:
    """Per-channel in-process pub/sub feeding the WS event stream.

    Each WebSocket connection subscribes its own `asyncio.Queue`; anything
    server-side (Agents, MCP servers via mcp_common, or tests) can publish
    to it without knowing who — if anyone — is currently connected.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[AnalysisEvent]]] = {}

    def publish(self, channel: str, event: AnalysisEvent) -> None:
        for queue in self._queues.get(channel, []):
            queue.put_nowait(event)

    def subscribe(self, channel: str) -> "asyncio.Queue[AnalysisEvent]":
        queue: asyncio.Queue[AnalysisEvent] = asyncio.Queue()
        self._queues.setdefault(channel, []).append(queue)
        return queue

    def unsubscribe(self, channel: str, queue: "asyncio.Queue[AnalysisEvent]") -> None:
        listeners = self._queues.get(channel, [])
        if queue in listeners:
            listeners.remove(queue)


default_event_bus = AnalysisEventBus()
