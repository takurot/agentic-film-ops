import pytest

from mcp_common.events import EventSink
from mcp_common.latency import LatencyConfig
from mcp_common.server import MCPCommonServer


def make_server():
    return MCPCommonServer(
        "weather",
        latency_config=LatencyConfig(default_seconds=0),
        event_sink=EventSink(),
    )


async def test_tool_call_emits_querying_then_response_received_events():
    server = make_server()
    events = []
    server.event_sink.subscribe(events.append)

    @server.tool()
    async def get_forecast(location_id: str) -> dict:
        return {"location_id": location_id, "rain_probability": 0.92}

    result = await get_forecast(location_id="LOC-003")

    assert result == {"location_id": "LOC-003", "rain_probability": 0.92}
    statuses = [e.status for e in events]
    assert statuses == ["QUERYING_MCP", "RESPONSE_RECEIVED"]
    assert all(e.tool == "get_forecast" and e.server == "weather" for e in events)
    assert events[0].call_id is not None
    assert events[0].call_id == events[1].call_id
    assert events[0].call_id.startswith("mcp-")


async def test_tool_call_emits_failed_event_and_reraises_on_error():
    server = make_server()
    events = []
    server.event_sink.subscribe(events.append)

    @server.tool()
    async def broken_tool() -> dict:
        raise ValueError("upstream vendor unavailable")

    with pytest.raises(ValueError, match="upstream vendor unavailable"):
        await broken_tool()

    statuses = [e.status for e in events]
    assert statuses == ["QUERYING_MCP", "FAILED"]
    assert events[0].call_id is not None
    assert events[0].call_id == events[1].call_id


async def test_tool_call_surfaces_resource_arg_on_events():
    server = make_server()
    events = []
    server.event_sink.subscribe(events.append)

    @server.tool(resource_arg="location_id")
    async def get_forecast(location_id: str) -> dict:
        return {"location_id": location_id}

    await get_forecast(location_id="LOC-003")

    assert all(e.resource == "LOC-003" for e in events)


async def test_tool_call_applies_configured_latency(monkeypatch):
    server = make_server()
    server.latency_config.set_override("get_forecast", 0.25)

    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    import asyncio

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    @server.tool()
    async def get_forecast() -> dict:
        return {}

    await get_forecast()

    assert slept == [0.25]


async def test_registered_tool_is_visible_on_the_underlying_fastmcp_server():
    server = make_server()

    @server.tool()
    async def get_forecast() -> dict:
        return {}

    tool_names = {t.name for t in await server.mcp.list_tools()}
    assert "get_forecast" in tool_names
