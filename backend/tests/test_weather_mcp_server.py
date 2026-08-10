"""Unit tests for the Weather MCP tool functions, plus one end-to-end test
that spawns the server as a real stdio subprocess — proof that mcp_common's
bootstrap actually works over the MCP transport, not just at the Python
function level.
"""

import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.mcp_servers.weather import get_forecast, get_weather_risk, subscribe_weather_alert


async def test_get_forecast_returns_rain_risk_for_scene_42s_location():
    result = await get_forecast(location_id="LOC-003")

    assert result["location_id"] == "LOC-003"
    assert result["rain_probability"] == 0.92


async def test_get_weather_risk_flags_high_risk():
    result = await get_weather_risk(location_id="LOC-003")

    assert result["risk_level"] == "high"


async def test_subscribe_weather_alert_acknowledges():
    result = await subscribe_weather_alert(location_id="LOC-003")

    assert result == {"location_id": "LOC-003", "subscribed": True}


async def test_weather_mcp_server_serves_tools_over_real_stdio_transport():
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_servers.weather"])

    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {t.name for t in tools.tools}
        assert {"get_forecast", "get_weather_risk", "subscribe_weather_alert"} <= tool_names

        result = await session.call_tool("get_forecast", {"location_id": "LOC-003"})
        payload = json.loads(result.content[0].text)
        assert payload["location_id"] == "LOC-003"
        assert payload["rain_probability"] == 0.92
