"""MCP call event logging (SPEC §8).

Each MCP tool invocation is published as an event so the Dashboard's Agent
Event Stream can show it, multiplexed as `type: "MCP_CALL"` alongside Agent
events (Issue #29's API contract). `EventSink` is an in-process pub/sub
seam: #29 subscribes a WebSocket broadcaster to it; until then, anything
(including tests) can subscribe directly.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

MCPCallStatus = Literal["QUERYING_MCP", "RESPONSE_RECEIVED", "FAILED"]


class MCPCallEvent(BaseModel):
    """An MCP tool call, shaped like the SPEC §8.1 event schema."""

    timestamp: str
    type: Literal["MCP_CALL"] = "MCP_CALL"
    server: str
    tool: str
    status: MCPCallStatus
    message: str
    resource: str | None = None

    @classmethod
    def create(
        cls,
        *,
        server: str,
        tool: str,
        status: MCPCallStatus,
        message: str,
        resource: str | None = None,
    ) -> "MCPCallEvent":
        return cls(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            server=server,
            tool=tool,
            status=status,
            message=message,
            resource=resource,
        )


EventListener = Callable[[MCPCallEvent], None]


class EventSink:
    """In-process pub/sub for MCP call events."""

    def __init__(self) -> None:
        self._listeners: list[EventListener] = []

    def subscribe(self, listener: EventListener) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        self._listeners.remove(listener)

    def publish(self, event: MCPCallEvent) -> None:
        for listener in self._listeners:
            listener(event)


default_event_sink = EventSink()
