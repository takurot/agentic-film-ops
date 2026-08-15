"""Centralized latency configuration and simulation system (SPEC §7).

SPEC §7 ("Latency Simulation") requirements:
1. Configurable per agent/step so the coordination reads as agentic.
2. Timing patterns per SPEC §7.1 (Actor Agent) and §7.2 (Equipment Agent) as presets.
3. Live tuning support via environment variables (`FILMOPS_LATENCY_SCALE`, `FILMOPS_LATENCY_OVERRIDES`)
   or config files without code changes.
4. "表示時間 = max(疑似遅延の目標値, 実際のGemini応答時間)" minimum display time floor against real Gemini calls.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from mcp_common.latency import LatencyConfig


def _get_env_scale() -> float:
    try:
        val = os.getenv("FILMOPS_LATENCY_SCALE")
        if val is not None:
            return max(0.0, float(val))
    except (ValueError, TypeError):
        pass
    return 1.0


@dataclass
class AgentStepLatencyConfig:
    """Config for steps within an agent (e.g. lookups, waits, analysis)."""

    default_seconds: float = 0.5
    overrides: dict[str, float] = field(default_factory=dict)
    scale: float = field(default_factory=_get_env_scale)

    def get_delay(self, step_name: str) -> float:
        base = self.overrides.get(step_name, self.default_seconds)
        delay = base * self.scale
        return max(0.0, delay)

    def set_override(self, step_name: str, seconds: float) -> None:
        self.overrides[step_name] = max(0.0, seconds)

    def __getattr__(self, name: str) -> float:
        if name in self.overrides:
            return self.get_delay(name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")


@dataclass
class ProductionLatencyConfig:
    """Central configuration for all Agents and MCP servers."""

    scale: float = field(default_factory=_get_env_scale)

    # Agent steps & presets
    actor: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "get_actor_availability": 1.2,  # SPEC §7.1 "Checking calendar... 1.2s"
                "get_actor_constraints": 0.8,  # SPEC §7.1 "Checking contract... 0.8s"
                "manager_wait": 4.0,  # SPEC §7.1 "WAITING FOR MANAGER... 4s"
                "parse_min_display": 1.0,  # SPEC §7.1 "Parsing response... / floor"
            },
        )
    )

    equipment: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "check_availability": 1.0,  # SPEC §7.2 "Checking inventory... 1.0s"
                "request_extension": 1.0,  # SPEC §7.2 "Contacting rental company... 1.0s"
                "request_reservation": 1.0,  # SPEC §7.2 "Contacting rental company... 1.0s"
                "vendor_wait": 3.5,  # SPEC §7.2 "WAITING... 3.5s"
            },
        )
    )

    location: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "get_location": 0.5,
                "check_availability": 0.8,
                "contact_location_manager": 1.5,
                "find_alternatives": 1.0,
            },
        )
    )

    budget: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "get_current_budget": 0.5,
                "estimate_change_cost": 1.0,
            },
        )
    )

    script: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "get_scene": 0.5,
                "get_scene_requirements": 0.5,
                "get_scene_dependencies": 0.8,
                "get_continuity_constraints": 0.8,
            },
        )
    )

    weather: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "get_forecast": 0.5,
                "get_weather_risk": 0.8,
            },
        )
    )

    schedule: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "solver_evaluation": 1.5,
                "option_generation": 1.0,
            },
        )
    )

    orchestrator: AgentStepLatencyConfig = field(
        default_factory=lambda: AgentStepLatencyConfig(
            default_seconds=0.5,
            overrides={
                "event_detection": 0.5,
                "affected_resources": 0.8,
                "reasoning_min_display": 1.5,
            },
        )
    )

    def __post_init__(self) -> None:
        self._apply_scale()

    def _apply_scale(self) -> None:
        for attr in [
            "actor",
            "equipment",
            "location",
            "budget",
            "script",
            "weather",
            "schedule",
            "orchestrator",
        ]:
            cfg: AgentStepLatencyConfig = getattr(self, attr)
            cfg.scale = self.scale

    def to_mcp_latency_config(self, domain: str) -> LatencyConfig:
        """Export as mcp_common.LatencyConfig for the corresponding domain server."""
        if hasattr(self, domain):
            step_cfg: AgentStepLatencyConfig = getattr(self, domain)
            return LatencyConfig(
                default_seconds=step_cfg.default_seconds,
                overrides=dict(step_cfg.overrides),
                scale=self.scale,
            )
        return LatencyConfig(scale=self.scale)


_GLOBAL_LATENCY_CONFIG: ProductionLatencyConfig | None = None


def get_latency_config(reload: bool = False) -> ProductionLatencyConfig:
    """Retrieve the current ProductionLatencyConfig, parsing environment overrides."""
    global _GLOBAL_LATENCY_CONFIG
    if _GLOBAL_LATENCY_CONFIG is not None and not reload:
        return _GLOBAL_LATENCY_CONFIG

    scale = _get_env_scale()
    config = ProductionLatencyConfig(scale=scale)

    overrides_env = os.getenv("FILMOPS_LATENCY_OVERRIDES")
    if overrides_env:
        try:
            overrides = json.loads(overrides_env)
            if isinstance(overrides, dict):
                for domain, domain_overrides in overrides.items():
                    if hasattr(config, domain) and isinstance(domain_overrides, dict):
                        domain_cfg: AgentStepLatencyConfig = getattr(config, domain)
                        for k, v in domain_overrides.items():
                            domain_cfg.set_override(k, float(v))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    _GLOBAL_LATENCY_CONFIG = config
    return config


async def simulate_agent_step_latency(config: AgentStepLatencyConfig, step_name: str) -> None:
    """Sleep for the configured step duration."""
    delay = config.get_delay(step_name)
    if delay > 0:
        await asyncio.sleep(delay)


async def with_min_display_time(coro: Any, min_seconds: float, scale: float | None = None) -> Any:
    """表示時間 = max(疑似遅延の目標値, 実際のGemini応答時間) (SPEC §7).

    Runs `coro`; if it finishes faster than `effective_min`, waits out the
    remainder. Never waits in addition to an already-slow real call.
    """
    if scale is None:
        scale = get_latency_config().scale
    effective_min = max(0.0, min_seconds * scale)

    start = time.monotonic()
    result = await coro
    elapsed = time.monotonic() - start
    remaining = effective_min - elapsed
    if remaining > 0:
        await asyncio.sleep(remaining)
    return result
