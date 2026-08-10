"""Weather MCP (mock) — reference implementation proving out mcp_common.

Only `get_forecast`, `get_weather_risk`, and `subscribe_weather_alert`
(SPEC §5.4) are implemented, with intentionally simple mock data. The full
Weather MCP (Scene 42's 92% rain-probability scenario, richer forecast
data, etc.) is Issue #3's scope — this exists to prove mcp_common works
end to end, for the other 5 MCP server issues to build against.
"""

from mcp_common.server import MCPCommonServer

server = MCPCommonServer("weather")


@server.tool(resource_arg="location_id")
async def get_forecast(location_id: str) -> dict:
    """24h mock forecast for a location."""
    return {
        "location_id": location_id,
        "conditions": "rain",
        "rain_probability": 0.92,
        "temperature_celsius": 19,
    }


@server.tool(resource_arg="location_id")
async def get_weather_risk(location_id: str) -> dict:
    """Mock risk assessment derived from the forecast."""
    return {
        "location_id": location_id,
        "risk_level": "high",
        "reason": "Heavy rain forecast exceeds outdoor shoot threshold.",
    }


@server.tool(resource_arg="location_id")
async def subscribe_weather_alert(location_id: str) -> dict:
    """Mock subscription acknowledgement for future weather alerts."""
    return {"location_id": location_id, "subscribed": True}


if __name__ == "__main__":
    server.run()
