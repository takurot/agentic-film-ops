"""The Agent Event Stream (SPEC §8), delivered over `WS
/api/analyses/{analysis_id}/events` (SPEC §3.4).

Agent events (this module's `AgentEvent`) and MCP call events
(`mcp_common.events.MCPCallEvent`) are multiplexed onto the same
per-analysis stream, distinguished by `type == "MCP_CALL"` for the latter.
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


class AnalysisEventBus:
    """Per-analysis in-process pub/sub feeding the WS event stream.

    Each WebSocket connection subscribes its own `asyncio.Queue`; anything
    server-side (Agents, MCP servers via mcp_common, or tests) can publish
    to it without knowing who — if anyone — is currently connected.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[AnalysisEvent]]] = {}

    def publish(self, analysis_id: str, event: AnalysisEvent) -> None:
        for queue in self._queues.get(analysis_id, []):
            queue.put_nowait(event)

    def subscribe(self, analysis_id: str) -> "asyncio.Queue[AnalysisEvent]":
        queue: asyncio.Queue[AnalysisEvent] = asyncio.Queue()
        self._queues.setdefault(analysis_id, []).append(queue)
        return queue

    def unsubscribe(self, analysis_id: str, queue: "asyncio.Queue[AnalysisEvent]") -> None:
        listeners = self._queues.get(analysis_id, [])
        if queue in listeners:
            listeners.remove(queue)


default_event_bus = AnalysisEventBus()
