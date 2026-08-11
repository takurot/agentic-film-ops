"""Unit tests for the Weather MCP tool functions, plus one end-to-end test
that spawns the server as a real stdio subprocess — proof that mcp_common's
bootstrap actually works over the MCP transport, not just at the Python
function level.
"""

import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.mcp_servers import weather
from app.mcp_servers.weather import get_forecast, get_weather_risk, subscribe_weather_alert


async def test_get_forecast_returns_rain_risk_for_scene_42s_location():
    result = await get_forecast(location_id="LOC-003")

    assert result["location_id"] == "LOC-003"
    assert result["rain_probability"] == 0.92
    assert result["conditions"] == "rain"
    assert result["temperature_celsius"] == 19.0


async def test_get_forecast_defaults_to_clear_weather_for_unknown_location():
    result = await get_forecast(location_id="LOC-999")

    assert result == {
        "location_id": "LOC-999",
        "forecast_time": None,
        "conditions": "clear",
        "rain_probability": 0.05,
        "temperature_celsius": 22.0,
    }


async def test_get_forecast_echoes_requested_time():
    result = await get_forecast(location_id="LOC-003", at="2026-09-02T14:00")

    assert result["forecast_time"] == "2026-09-02T14:00"


async def test_get_weather_risk_flags_high_risk_for_scene_42s_location():
    result = await get_weather_risk(location_id="LOC-003")

    assert result["risk_level"] == "high"
    assert result["reason"]


async def test_get_weather_risk_flags_low_risk_for_unknown_location():
    result = await get_weather_risk(location_id="LOC-999")

    assert result["risk_level"] == "low"
    assert result["reason"]


async def test_subscribe_weather_alert_acknowledges_with_subscription_id():
    result = await subscribe_weather_alert(location_id="LOC-003")

    assert result == {
        "location_id": "LOC-003",
        "subscribed": True,
        "subscription_id": "WXSUB-LOC-003",
    }


def test_risk_thresholds_are_pinned_at_each_boundary():
    assert weather._risk_for(0.8)[0] == "high"
    assert weather._risk_for(0.79)[0] == "medium"
    assert weather._risk_for(0.5)[0] == "medium"
    assert weather._risk_for(0.49)[0] == "low"


def test_risk_reason_text_differs_per_level():
    reasons = {weather._risk_for(p)[1] for p in (0.9, 0.6, 0.1)}
    assert len(reasons) == 3


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
