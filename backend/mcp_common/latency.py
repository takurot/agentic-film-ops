"""Mock-latency injection (SPEC §7).

MCP tool responses are mocked, so they'd otherwise return instantly — which
reads as a flat API call list rather than an agentic system investigating
something. Each tool call sleeps for a configurable duration to simulate
that work taking real time.

Clean Architecture constraint: this module is part of mcp_common (shared library)
and must not import from app.*. Global scaling can be configured directly or
via the FILMOPS_LATENCY_SCALE environment variable.
"""

import asyncio
import os
from dataclasses import dataclass, field


def _get_env_scale() -> float:
    try:
        val = os.getenv("FILMOPS_LATENCY_SCALE")
        if val is not None:
            return float(val)
    except (ValueError, TypeError):
        pass
    return 1.0


@dataclass
class LatencyConfig:
    """Per-tool artificial delay in seconds, configurable for demo tuning."""

    default_seconds: float = 0.5
    overrides: dict[str, float] = field(default_factory=dict)
    scale: float = field(default_factory=_get_env_scale)

    def seconds_for(self, tool_name: str) -> float:
        base = self.overrides.get(tool_name, self.default_seconds)
        scale = _get_env_scale() if os.getenv("FILMOPS_LATENCY_SCALE") is not None else self.scale
        delay = base * scale
        return max(0.0, delay)

    def set_override(self, tool_name: str, seconds: float) -> None:
        self.overrides[tool_name] = max(0.0, seconds)


async def simulate_latency(config: LatencyConfig, tool_name: str) -> None:
    delay = config.seconds_for(tool_name)
    if delay > 0:
        await asyncio.sleep(delay)
