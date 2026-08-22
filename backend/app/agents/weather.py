"""Weather Agent (SPEC §6.4).

Monitors a tracked scene for adverse weather and originates an Incident when
a configurable risk threshold is exceeded. Unlike the other domain agents
(SPEC §6.2/6.3), the Weather Agent contacts no external human — it only
reads from Weather MCP (forecast/risk) and Script MCP (scene -> location) —
so its detection logic is deterministic Python rather than a Gemini call
(SPEC §11: this is "Real" application logic, not an LLM reasoning step;
`app/gemini_client.py` is not used here).

`check_scene()` is invoked directly (e.g. `python -m app.agents.weather
SC-042`, or a future poller/scheduler — Weather MCP's `subscribe_weather_alert`
is a mock acknowledgement that never pushes a callback, so polling is the
only realizable shape today). SPEC §3.2's "Dashboard must go through the
Orchestrator" constraint governs UI access, not this Agent's own invocation;
no HTTP route is added here.

"Notify Orchestrator" (SPEC §6.4 step 4 / "Event detection", SPEC §6.1) is
realized as an unresolved `Incident` row: Issue #9's Orchestrator (not yet
implemented) discovers it via `GET /api/incidents/active` and drives
`POST /api/incidents/{id}/analyze` from there — the seam `app/workflow.py`'s
`AnalysisEngine` already documents. `check_scene()`'s return value mirrors
that same Incident (as `IncidentSchema`, not the ORM row, to stay usable
after the DB session closes) for callers that already have one in hand.
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.db import get_session
from app.events import (
    AgentEvent,
    AgentEventStatus,
    AnalysisEventBus,
    default_event_bus,
    scene_channel,
)
from app.mcp_client import InProcessMCPClient, MCPClient
from app.workflow import Incident, IncidentSchema, incident_to_schema

AGENT_NAME = "WeatherAgent"
INCIDENT_TYPE = "WEATHER"
EVENT_TYPE_MONITOR = "WEATHER_MONITOR"
EVENT_TYPE_INCIDENT = "INCIDENT_DETECTED"

# SPEC §6.4's example ("降水確率80%以上") — matches Weather MCP's own
# HIGH_RISK_THRESHOLD (app/mcp_servers/weather.py) but kept independently
# configurable per Issue #31 AC3, not hardcoded to the Scene 42 demo.
DEFAULT_RAIN_PROBABILITY_THRESHOLD = 0.8


@dataclass(frozen=True)
class WeatherIncidentDetection:
    """Result of a single `check_scene()` call."""

    incident: IncidentSchema | None
    risk_level: str
    rain_probability: float


class WeatherAgent:
    """Checks one scene's forecast against a configurable rain-probability
    threshold and raises an Incident if it's met or exceeded."""

    def __init__(
        self,
        *,
        rain_probability_threshold: float = DEFAULT_RAIN_PROBABILITY_THRESHOLD,
        event_bus: AnalysisEventBus = default_event_bus,
        mcp_client: MCPClient | None = None,
    ) -> None:
        self.rain_probability_threshold = rain_probability_threshold
        self._event_bus = event_bus
        self._mcp = mcp_client or InProcessMCPClient()

    async def check_scene(self, scene_id: str) -> WeatherIncidentDetection:
        """Resolve `scene_id`'s location, check its forecast, and raise an
        Incident if the rain probability meets or exceeds the threshold.

        Publishes AgentEvent status transitions (SPEC §8.2) to
        `scene_channel(scene_id)` throughout; on any failure, publishes a
        FAILED event with the error message and re-raises.
        """
        channel = scene_channel(scene_id)
        self._publish(channel, scene_id, "QUEUED", f"Monitoring {scene_id} for weather risk")
        try:
            return await self._check_scene(channel, scene_id)
        except Exception as exc:
            self._publish(channel, scene_id, "FAILED", str(exc))
            raise

    async def _check_scene(self, channel: str, scene_id: str) -> WeatherIncidentDetection:
        self._publish(channel, scene_id, "THINKING", f"Resolving {scene_id}'s location")
        scene = await self._call("script", "get_scene", {"scene_id": scene_id})
        location_id = scene["location"]

        if location_id is None:
            self._publish(channel, scene_id, "COMPLETED", f"{scene_id} has no location to monitor")
            return WeatherIncidentDetection(incident=None, risk_level="low", rain_probability=0.0)

        self._publish(channel, scene_id, "QUERYING_MCP", f"Checking forecast for {location_id}")
        await self._call("weather", "subscribe_weather_alert", {"location_id": location_id})
        forecast = await self._call("weather", "get_forecast", {"location_id": location_id})
        risk = await self._call("weather", "get_weather_risk", {"location_id": location_id})
        self._publish(
            channel, scene_id, "RESPONSE_RECEIVED", f"Forecast received for {location_id}"
        )

        rain_probability = forecast["rain_probability"]
        self._publish(
            channel, scene_id, "ANALYZING", f"{risk['risk_level']} risk: {risk['reason']}"
        )

        if rain_probability < self.rain_probability_threshold:
            self._publish(
                channel,
                scene_id,
                "COMPLETED",
                f"No incident: rain probability {rain_probability:.0%} is below threshold",
            )
            return WeatherIncidentDetection(
                incident=None, risk_level=risk["risk_level"], rain_probability=rain_probability
            )

        incident = self._raise_incident(scene, forecast, risk)
        self._publish(
            channel,
            scene_id,
            "COMPLETED",
            f"Incident {incident.incident_id} raised: {incident.headline}",
            event_type=EVENT_TYPE_INCIDENT,
        )
        return WeatherIncidentDetection(
            incident=incident, risk_level=risk["risk_level"], rain_probability=rain_probability
        )

    async def _call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self._mcp.call(server, tool, arguments)

    def _raise_incident(
        self, scene: dict[str, Any], forecast: dict[str, Any], risk: dict[str, Any]
    ) -> IncidentSchema:
        """Create (or reuse) the unresolved Incident for this scene.

        Idempotent per unresolved incident: a scene already flagged doesn't
        accumulate duplicate rows on repeated `check_scene()` calls (e.g. a
        future poller re-checking the same scene before it's resolved).
        """
        with get_session() as db:
            existing = db.execute(
                select(Incident).where(
                    Incident.scene_id == scene["scene_id"],
                    Incident.type == INCIDENT_TYPE,
                    Incident.resolved.is_(False),
                )
            ).scalar_one_or_none()
            if existing is not None:
                return incident_to_schema(existing)

            incident = Incident(
                incident_id=f"INC-{uuid.uuid4().hex[:8]}",
                type=INCIDENT_TYPE,
                scene_id=scene["scene_id"],
                headline=f"Weather risk — {scene['name']}",
                detail=(
                    f"{risk['reason']} Rain probability "
                    f"{forecast['rain_probability']:.0%} at {scene['location']}."
                ),
                detected_at=datetime.now(),
                resolved=False,
            )
            db.add(incident)
            db.commit()
            return incident_to_schema(incident)

    def _publish(
        self,
        channel: str,
        scene_id: str,
        status: AgentEventStatus,
        message: str,
        *,
        event_type: str = EVENT_TYPE_MONITOR,
    ) -> None:
        self._event_bus.publish(
            channel,
            AgentEvent.create(
                agent=AGENT_NAME,
                type=event_type,
                status=status,
                message=message,
                resource=scene_id,
            ),
        )


async def _main(scene_id: str) -> None:
    """QA/demo entrypoint: `python -m app.agents.weather [SCENE_ID]`."""
    detection = await WeatherAgent().check_scene(scene_id)
    if detection.incident is not None:
        print(f"Incident raised: {detection.incident.incident_id} — {detection.incident.headline}")
    else:
        print(
            f"No incident ({detection.risk_level} risk, "
            f"{detection.rain_probability:.0%} rain probability)."
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main(sys.argv[1] if len(sys.argv) > 1 else "SC-042"))
