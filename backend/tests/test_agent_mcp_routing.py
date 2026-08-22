from typing import Any

from app.agents.actor import ActorAgent, ActorAgentConfig
from app.agents.budget import evaluate_cost_impact
from app.agents.equipment import EquipmentAgent, EquipmentAgentConfig
from app.agents.location import LocationAgent, LocationAgentConfig
from app.agents.script import analyze_scene
from app.agents.weather import WeatherAgent


class NoopGeminiClient:
    async def generate_content(
        self, prompt: str
    ):  # pragma: no cover - routing tests do not call it
        raise AssertionError(f"Unexpected Gemini call: {prompt}")


class RecordingMCPClient:
    def __init__(self, responses: dict[tuple[str, str], dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def call(self, server: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((server, tool, arguments))
        return self.responses[(server, tool)]


async def test_actor_equipment_and_location_agents_route_through_injected_client() -> None:
    mcp = RecordingMCPClient(
        {
            ("actor", "get_actor_availability"): {
                "actor_id": "ACT-001",
                "availability": [],
            },
            ("actor", "get_actor_constraints"): {
                "actor_id": "ACT-001",
                "max_hours_per_day": 8,
            },
            ("equipment", "check_availability"): {
                "equipment_id": "EQ-001",
                "available": True,
                "conflicts": [],
            },
            ("location", "get_location"): {
                "id": "LOC-003",
                "name": "Rooftop",
            },
            ("location", "check_availability"): {
                "location_id": "LOC-003",
                "available": True,
                "conflicts": [],
            },
        }
    )
    gemini = NoopGeminiClient()
    actor = ActorAgent(gemini, ActorAgentConfig(parse_min_display_seconds=0), mcp_client=mcp)
    equipment = EquipmentAgent(
        gemini, EquipmentAgentConfig(summary_min_display_seconds=0), mcp_client=mcp
    )
    location = LocationAgent(
        gemini, LocationAgentConfig(parse_min_display_seconds=0), mcp_client=mcp
    )

    await actor._check_calendar_and_contract("AN-1", "ACT-001")
    await equipment._check_inventory("AN-1", "EQ-001", "2026-09-02T16:00", "2026-09-02T20:00")
    await location._get_location("AN-1", "LOC-003")
    await location._check_availability("AN-1", "LOC-003", "2026-09-02T16:00", "2026-09-02T20:00")

    assert mcp.calls == [
        ("actor", "get_actor_availability", {"actor_id": "ACT-001"}),
        ("actor", "get_actor_constraints", {"actor_id": "ACT-001"}),
        (
            "equipment",
            "check_availability",
            {
                "equipment_id": "EQ-001",
                "start": "2026-09-02T16:00",
                "end": "2026-09-02T20:00",
            },
        ),
        ("location", "get_location", {"location_id": "LOC-003"}),
        (
            "location",
            "check_availability",
            {
                "location_id": "LOC-003",
                "start": "2026-09-02T16:00",
                "end": "2026-09-02T20:00",
            },
        ),
    ]


async def test_script_budget_and_weather_route_through_injected_client() -> None:
    mcp = RecordingMCPClient(
        {
            ("script", "get_scene"): {
                "scene_id": "SC-042",
                "name": "Rooftop",
                "type": "outdoor",
                "duration_hours": 4,
                "scheduled": "2026-09-02T14:00",
                "location": "LOC-003",
            },
            ("script", "get_scene_requirements"): {
                "scene_id": "SC-042",
                "duration_hours": 4,
                "location_type": "outdoor",
                "weather_dependent": True,
                "required_equipment": [],
                "required_crew": [],
            },
            ("script", "get_scene_dependencies"): {
                "scene_id": "SC-042",
                "actors": [],
                "equipment": [],
                "location": "LOC-003",
            },
            ("script", "get_continuity_constraints"): {
                "scene_id": "SC-042",
                "must_precede": [],
                "must_follow": [],
                "same_day_as": [],
                "notes": "",
            },
            ("budget", "get_current_budget"): {
                "total_budget": 100,
                "spent_to_date": 20,
                "remaining": 80,
                "currency": "USD",
            },
            ("weather", "subscribe_weather_alert"): {
                "location_id": "LOC-003",
                "subscribed": True,
            },
            ("weather", "get_forecast"): {
                "location_id": "LOC-003",
                "rain_probability": 0.1,
            },
            ("weather", "get_weather_risk"): {
                "location_id": "LOC-003",
                "risk_level": "low",
                "reason": "Clear",
            },
        }
    )

    await analyze_scene("SC-042", analysis_id="AN-2", mcp_client=mcp)
    await evaluate_cost_impact("SC-042", [], analysis_id="AN-2", mcp_client=mcp)
    detection = await WeatherAgent(mcp_client=mcp).check_scene("SC-042")

    assert detection.incident is None
    assert mcp.calls == [
        ("script", "get_scene", {"scene_id": "SC-042"}),
        ("script", "get_scene_requirements", {"scene_id": "SC-042"}),
        ("script", "get_scene_dependencies", {"scene_id": "SC-042"}),
        ("script", "get_continuity_constraints", {"scene_id": "SC-042"}),
        ("budget", "get_current_budget", {}),
        ("script", "get_scene", {"scene_id": "SC-042"}),
        ("weather", "subscribe_weather_alert", {"location_id": "LOC-003"}),
        ("weather", "get_forecast", {"location_id": "LOC-003"}),
        ("weather", "get_weather_risk", {"location_id": "LOC-003"}),
    ]
