"""Validated MCP client boundary for stdio and recorded replay runtimes.

The live client owns one initialized ``ClientSession`` per fixed MCP server.
Commands and tool names come only from the registry below; model or request
data can never influence process launch configuration.
"""

import asyncio
import importlib
import json
import os
import subprocess
import sys
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent

from app.events import AnalysisEventBus, current_event_channel, default_event_bus
from mcp_common.events import MCPCallEvent

MAX_MCP_RESPONSE_BYTES = 1_000_000


class MCPError(RuntimeError):
    """Base class for stable, sanitized MCP client failures."""


class MCPTransportError(MCPError):
    """The stdio transport could not be started or used."""


class MCPProtocolError(MCPError):
    """The server or protocol response violated the fixed MCP contract."""


class MCPToolError(MCPError):
    """A registered MCP tool returned an error result."""


@dataclass(frozen=True)
class MCPServerSpec:
    module: str
    tools: frozenset[str]


SERVER_REGISTRY: dict[str, MCPServerSpec] = {
    "actor": MCPServerSpec(
        "app.mcp_servers.actor",
        frozenset(
            {
                "get_actor",
                "get_actor_availability",
                "get_actor_constraints",
                "contact_manager",
                "get_contact_status",
                "get_manager_response",
                "hold_actor",
                "confirm_actor",
            }
        ),
    ),
    "equipment": MCPServerSpec(
        "app.mcp_servers.equipment",
        frozenset(
            {
                "get_equipment",
                "check_availability",
                "request_extension",
                "request_reservation",
                "get_vendor_response",
                "reserve_equipment",
            }
        ),
    ),
    "location": MCPServerSpec(
        "app.mcp_servers.location",
        frozenset(
            {
                "get_location",
                "check_availability",
                "contact_location_manager",
                "find_alternative_locations",
                "hold_location",
                "confirm_location",
            }
        ),
    ),
    "script": MCPServerSpec(
        "app.mcp_servers.script",
        frozenset(
            {
                "get_scene",
                "get_scene_requirements",
                "get_scene_dependencies",
                "get_continuity_constraints",
            }
        ),
    ),
    "weather": MCPServerSpec(
        "app.mcp_servers.weather",
        frozenset({"get_forecast", "get_weather_risk", "subscribe_weather_alert"}),
    ),
    "budget": MCPServerSpec(
        "app.mcp_servers.budget",
        frozenset(
            {
                "get_current_budget",
                "estimate_change_cost",
                "calculate_overtime",
                "calculate_vendor_cost",
            }
        ),
    ),
}


class MCPClient(Protocol):
    async def start(self) -> None: ...

    async def close(self) -> None: ...

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


def _validate_server_tool(server: str, tool: str) -> MCPServerSpec:
    spec = SERVER_REGISTRY.get(server)
    if spec is None:
        raise MCPProtocolError("MCP_SERVER_NOT_ALLOWED")
    if tool not in spec.tools:
        raise MCPProtocolError("MCP_TOOL_NOT_ALLOWED")
    return spec


def build_child_environment(
    parent: dict[str, str],
    *,
    backend_root: Path,
    db_path: Path,
    latency_scale: float,
) -> dict[str, str]:
    """Build the minimal environment inherited by mock MCP subprocesses."""
    if str(db_path) == ":memory:":
        raise ValueError("MCP subprocesses require a file-backed SQLite database")

    child: dict[str, str] = {}
    for key in ("PATH", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT"):
        value = parent.get(key)
        if value:
            child[key] = value
    child.update(
        {
            "PYTHONPATH": str(backend_root.resolve()),
            "PYTHONUNBUFFERED": "1",
            "FILMOPS_DB_PATH": str(db_path.resolve()),
            "FILMOPS_LATENCY_SCALE": str(latency_scale),
        }
    )
    return child


def decode_tool_result(
    result: CallToolResult, *, max_response_bytes: int = MAX_MCP_RESPONSE_BYTES
) -> dict[str, Any]:
    """Decode only successful JSON-object MCP results at the trust boundary."""
    if result.isError:
        raise MCPToolError("MCP_TOOL_FAILED")

    data: Any
    if result.structuredContent is not None:
        data = result.structuredContent
    else:
        if len(result.content) != 1 or not isinstance(result.content[0], TextContent):
            raise MCPProtocolError("MCP_INVALID_RESPONSE")
        raw = result.content[0].text
        if len(raw.encode("utf-8")) > max_response_bytes:
            raise MCPProtocolError("MCP_RESPONSE_TOO_LARGE")
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise MCPProtocolError("MCP_INVALID_RESPONSE") from exc

    if not isinstance(data, dict):
        raise MCPProtocolError("MCP_INVALID_RESPONSE")
    try:
        encoded = json.dumps(data, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MCPProtocolError("MCP_INVALID_RESPONSE") from exc
    if len(encoded) > max_response_bytes:
        raise MCPProtocolError("MCP_RESPONSE_TOO_LARGE")
    return data


class MCPStdioClient:
    """Long-lived, lifespan-owned stdio sessions for the six MCP servers."""

    def __init__(
        self,
        *,
        db_path: Path,
        backend_root: Path | None = None,
        event_bus: AnalysisEventBus | None = None,
        timeout_seconds: float = 15.0,
        latency_scale: float = 1.0,
    ) -> None:
        self.db_path = db_path
        self.backend_root = (backend_root or Path(__file__).resolve().parents[1]).resolve()
        self._event_bus = event_bus or default_event_bus
        self._timeout_seconds = timeout_seconds
        self._latency_scale = latency_scale
        self._stack: AsyncExitStack | None = None
        self._sessions: dict[str, ClientSession] = {}
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        stack = AsyncExitStack()
        await stack.__aenter__()
        sessions: dict[str, ClientSession] = {}
        try:
            child_env = build_child_environment(
                dict(os.environ),
                backend_root=self.backend_root,
                db_path=self.db_path,
                latency_scale=self._latency_scale,
            )
            for server_name, spec in SERVER_REGISTRY.items():
                params = StdioServerParameters(
                    command=sys.executable,
                    args=["-m", spec.module],
                    env=child_env,
                    cwd=self.backend_root,
                )
                read_stream, write_stream = await stack.enter_async_context(
                    # Child diagnostics may contain provider or database values.
                    # Suppress them here and expose only stable errors above.
                    stdio_client(params, errlog=subprocess.DEVNULL)  # type: ignore[arg-type]
                )
                session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
                await asyncio.wait_for(session.initialize(), timeout=self._timeout_seconds)
                listed = await asyncio.wait_for(session.list_tools(), timeout=self._timeout_seconds)
                actual_tools = {registered.name for registered in listed.tools}
                if actual_tools != set(spec.tools):
                    raise MCPProtocolError("MCP_TOOL_REGISTRY_MISMATCH")
                sessions[server_name] = session
        except BaseException as exc:
            await stack.aclose()
            if isinstance(exc, MCPError):
                raise
            raise MCPTransportError("MCP_STARTUP_FAILED") from exc

        self._stack = stack
        self._sessions = sessions
        self._started = True

    async def close(self) -> None:
        stack, self._stack = self._stack, None
        self._sessions = {}
        self._started = False
        if stack is not None:
            await stack.aclose()

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        _validate_server_tool(server, tool)
        if not self._started:
            raise MCPTransportError("MCP_CLIENT_NOT_STARTED")

        call_id = f"mcp-{uuid.uuid4().hex[:12]}"
        channel = current_event_channel.get()
        resource = next(
            (str(value) for key, value in arguments.items() if key.endswith("_id")), None
        )
        if channel is not None:
            self._event_bus.publish(
                channel,
                MCPCallEvent.create(
                    call_id=call_id,
                    server=server,
                    tool=tool,
                    status="QUERYING_MCP",
                    message=f"Calling {tool}",
                    resource=resource,
                ),
            )

        try:
            result = await asyncio.wait_for(
                self._sessions[server].call_tool(tool, arguments),
                timeout=self._timeout_seconds,
            )
            decoded = decode_tool_result(result)
        except TimeoutError as exc:
            self._publish_failure(channel, server, tool, resource, call_id=call_id)
            raise MCPTransportError("MCP_CALL_TIMEOUT") from exc
        except MCPError:
            self._publish_failure(channel, server, tool, resource, call_id=call_id)
            raise
        except Exception as exc:
            self._publish_failure(channel, server, tool, resource, call_id=call_id)
            raise MCPTransportError("MCP_CALL_FAILED") from exc

        if channel is not None:
            self._event_bus.publish(
                channel,
                MCPCallEvent.create(
                    call_id=call_id,
                    server=server,
                    tool=tool,
                    status="RESPONSE_RECEIVED",
                    message=f"{tool} completed",
                    resource=resource,
                ),
            )
        return decoded

    def _publish_failure(
        self,
        channel: str | None,
        server: str,
        tool: str,
        resource: str | None,
        call_id: str | None = None,
    ) -> None:
        if channel is not None:
            self._event_bus.publish(
                channel,
                MCPCallEvent.create(
                    call_id=call_id,
                    server=server,
                    tool=tool,
                    status="FAILED",
                    message="MCP call failed",
                    resource=resource,
                ),
            )


class InProcessMCPClient:
    """Explicit replay/test client using the registered tool functions."""

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        spec = _validate_server_tool(server, tool)
        module = importlib.import_module(spec.module)
        function = getattr(module, tool)
        result = await function(**arguments)
        if not isinstance(result, dict):
            raise MCPProtocolError("MCP_INVALID_RESPONSE")
        return result
