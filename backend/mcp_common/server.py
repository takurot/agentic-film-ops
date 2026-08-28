"""MCP server bootstrap (SPEC §5 "Transport & Invocation").

Wraps `mcp.server.fastmcp.FastMCP` (stdio transport) so each of the 6 mock
MCP servers only has to define its tool functions; latency injection,
event logging, and FAILED-status error propagation are handled here once.
"""

import functools
import uuid
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from mcp.server.fastmcp import FastMCP

from mcp_common.events import EventSink, MCPCallEvent, default_event_sink
from mcp_common.latency import LatencyConfig, simulate_latency

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class MCPCommonServer:
    """A named MCP server with SPEC §5's common policy applied to every tool."""

    def __init__(
        self,
        name: str,
        *,
        latency_config: LatencyConfig | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.name = name
        self.mcp = FastMCP(name)
        self.latency_config = latency_config or LatencyConfig()
        self.event_sink = event_sink or default_event_sink

    def tool(self, resource_arg: str | None = None) -> Callable[[F], F]:
        """Register a mock MCP tool.

        Every call: publishes a QUERYING_MCP event, sleeps for the tool's
        configured latency, runs the tool, then publishes RESPONSE_RECEIVED
        (or FAILED, re-raising the exception so it propagates to the
        calling Agent per SPEC §5's error handling policy).

        `resource_arg`: name of the tool's kwarg to surface as the event's
        `resource` field (e.g. "actor_id"), if the tool takes one.
        """

        def decorator(func: F) -> F:
            tool_name = func.__name__

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                call_id = f"mcp-{uuid.uuid4().hex[:12]}"
                resource = kwargs.get(resource_arg) if resource_arg else None
                self.event_sink.publish(
                    MCPCallEvent.create(
                        call_id=call_id,
                        server=self.name,
                        tool=tool_name,
                        status="QUERYING_MCP",
                        message=f"Calling {tool_name}",
                        resource=resource,
                    )
                )
                try:
                    await simulate_latency(self.latency_config, tool_name)
                    result = await func(*args, **kwargs)
                except Exception as exc:
                    self.event_sink.publish(
                        MCPCallEvent.create(
                            call_id=call_id,
                            server=self.name,
                            tool=tool_name,
                            status="FAILED",
                            message=str(exc),
                            resource=resource,
                        )
                    )
                    raise

                self.event_sink.publish(
                    MCPCallEvent.create(
                        call_id=call_id,
                        server=self.name,
                        tool=tool_name,
                        status="RESPONSE_RECEIVED",
                        message=f"{tool_name} completed",
                        resource=resource,
                    )
                )
                return result

            return self.mcp.tool()(wrapper)

        return decorator

    def run(self) -> None:
        """Start serving over stdio (SPEC §5: MCP standard stdio transport)."""
        self.mcp.run(transport="stdio")
