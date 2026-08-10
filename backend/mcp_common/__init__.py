"""Shared boilerplate for the 6 mock MCP servers (SPEC §5 "Transport &
Invocation"): server bootstrap, mock-latency injection, and event-stream
logging, so each MCP server issue (Weather/Script/Actor/Equipment/
Location/Budget) only has to define its tools.
"""

from mcp_common.events import EventSink, MCPCallEvent, default_event_sink
from mcp_common.latency import LatencyConfig, simulate_latency
from mcp_common.server import MCPCommonServer

__all__ = [
    "EventSink",
    "LatencyConfig",
    "MCPCallEvent",
    "MCPCommonServer",
    "default_event_sink",
    "simulate_latency",
]
