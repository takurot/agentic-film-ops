"""Weather MCP (mock) per SPEC §5.4.

Tool signatures and response shapes are frozen as production-ready per SPEC
§5's "本物のAPIに置き換え可能なInterface" requirement — `_forecast_for()` is
the single seam to swap for a real weather provider (SPEC §11: Weather data
is "Mock / Real（切替可）").
"""

from typing import Any

from mcp_common.server import MCPCommonServer

server = MCPCommonServer("weather")

# Mock forecasts keyed by location_id. LOC-003 (Rooftop, Shibuya Tower) is
# Scene 42's demo location (SPEC §4.8) — a rain forecast that drives the
# whole demo scenario. Any other location_id falls back to _DEFAULT_FORECAST
# (clear weather) rather than erroring, since not every Production Resource
# Graph location is weather-relevant (e.g. indoor stages) and callers should
# be able to query any valid location_id.
_MOCK_FORECASTS: dict[str, dict[str, Any]] = {
    "LOC-003": {"conditions": "rain", "rain_probability": 0.92, "temperature_celsius": 19.0},
}
_DEFAULT_FORECAST: dict[str, Any] = {
    "conditions": "clear",
    "rain_probability": 0.05,
    "temperature_celsius": 22.0,
}

# Aligned with SPEC §6.4's Weather Agent incident trigger ("降水確率80%以上")
# so the MCP's risk grading and the Agent's incident threshold agree.
HIGH_RISK_THRESHOLD = 0.8
MEDIUM_RISK_THRESHOLD = 0.5


def _forecast_for(location_id: str, at: str | None = None) -> dict[str, Any]:
    """Look up (or synthesize) a forecast. Single seam to swap for a real provider."""
    base = _MOCK_FORECASTS.get(location_id, _DEFAULT_FORECAST)
    return {"location_id": location_id, "forecast_time": at, **base}


def _risk_for(rain_probability: float) -> tuple[str, str]:
    if rain_probability >= HIGH_RISK_THRESHOLD:
        return "high", "Heavy rain forecast exceeds outdoor shoot threshold."
    if rain_probability >= MEDIUM_RISK_THRESHOLD:
        return "medium", "Moderate rain chance — monitor conditions before call time."
    return "low", "Rain chance is minimal; no weather-related risk to the shoot."


@server.tool(resource_arg="location_id")
async def get_forecast(location_id: str, at: str | None = None) -> dict[str, Any]:
    """Forecast for a location, optionally at a specific ISO timestamp."""
    return _forecast_for(location_id, at)


@server.tool(resource_arg="location_id")
async def get_weather_risk(location_id: str, at: str | None = None) -> dict[str, Any]:
    """Risk assessment derived from the forecast's rain probability."""
    forecast = _forecast_for(location_id, at)
    risk_level, reason = _risk_for(forecast["rain_probability"])
    return {"location_id": location_id, "risk_level": risk_level, "reason": reason}


@server.tool(resource_arg="location_id")
async def subscribe_weather_alert(location_id: str) -> dict[str, Any]:
    """Mock subscription acknowledgement for weather alerts on a location.

    Scoped per location_id (not scene_id) — the Weather Agent (SPEC §6.4)
    maps a scene to its location before subscribing.
    """
    return {
        "location_id": location_id,
        "subscribed": True,
        "subscription_id": f"WXSUB-{location_id}",
    }


if __name__ == "__main__":
    server.run()
