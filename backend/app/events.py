"""The Agent Event Stream (SPEC §8), delivered over WebSocket or SSE (SPEC §3.4).

Agent events (`AgentEvent`) and MCP call events (`MCPCallEvent`) are
multiplexed onto the same per-analysis stream, distinguished by `type == "MCP_CALL"`
for the latter.

`AnalysisEventBus` manages in-process pub/sub per channel (e.g. `analysis_id` or `scene_channel`),
maintaining a bounded event history buffer (`deque(maxlen=...)`) so reconnecting or newly
joining clients can catch up on previously emitted events.

`current_event_channel` is a `contextvars.ContextVar` that allows asynchronous agent tasks
to tag their execution context with the active channel (e.g. `analysis_id`). The MCP event sink
bridge listens to `mcp_common.events.default_event_sink` and forwards MCP events to the
context's active channel automatically.
"""

import asyncio
import contextvars
from collections import deque
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from mcp_common.events import MCPCallEvent, default_event_sink

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


# Task-local active channel context for automatic MCPCallEvent routing
current_event_channel: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_event_channel", default=None
)


class AnalysisEventBus:
    """Per-channel in-process pub/sub feeding the WS/SSE event streams.

    Each connection subscribes its own `asyncio.Queue`; anything server-side
    (Agents, Orchestrator, MCP servers via mcp_common, or tests) can publish
    to it. A bounded in-memory event history buffer is retained per channel for catchup.
    """

    def __init__(self, max_history_per_channel: int = 500) -> None:
        self._queues: dict[str, list[asyncio.Queue[AnalysisEvent]]] = {}
        self._history: dict[str, deque[AnalysisEvent]] = {}
        self._max_history = max_history_per_channel

    def publish(self, channel: str, event: AnalysisEvent) -> None:
        # Buffer event in bounded history
        history = self._history.setdefault(channel, deque(maxlen=self._max_history))
        history.append(event)

        # Distribute to active subscribers
        for queue in self._queues.get(channel, []):
            queue.put_nowait(event)

    def get_history(self, channel: str) -> list[AnalysisEvent]:
        """Return a copy of the event history for the given channel."""
        return list(self._history.get(channel, []))

    def subscribe(
        self, channel: str, replay_history: bool = False
    ) -> "asyncio.Queue[AnalysisEvent]":
        """Subscribe to a channel, pre-populating with historical events atomically if requested."""
        queue: asyncio.Queue[AnalysisEvent] = asyncio.Queue()
        if replay_history:
            for past_event in self._history.get(channel, []):
                queue.put_nowait(past_event)
        self._queues.setdefault(channel, []).append(queue)
        return queue

    def unsubscribe(self, channel: str, queue: "asyncio.Queue[AnalysisEvent]") -> None:
        listeners = self._queues.get(channel, [])
        if queue in listeners:
            listeners.remove(queue)
            if not listeners:
                self._queues.pop(channel, None)

    def subscriber_count(self, channel: str) -> int:
        return len(self._queues.get(channel, []))

    def reset(self) -> None:
        """Clear all active subscriptions and historical event buffers."""
        self._queues.clear()
        self._history.clear()


default_event_bus = AnalysisEventBus()


def _on_mcp_call_event(event: MCPCallEvent) -> None:
    """Forward MCP events to the active context channel if one is set."""
    channel = current_event_channel.get()
    if channel is not None:
        default_event_bus.publish(channel, event)


default_event_sink.subscribe(_on_mcp_call_event)
