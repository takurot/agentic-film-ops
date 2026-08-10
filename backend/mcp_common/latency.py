"""Mock-latency injection (SPEC §7).

MCP tool responses are mocked, so they'd otherwise return instantly — which
reads as a flat API call list rather than an agentic system investigating
something. Each tool call sleeps for a configurable duration to simulate
that work taking real time.

This does not implement §7's "minimum display time" floor against real
Gemini latency — that only applies to Agent/Orchestrator reasoning calls
(Issue #33), not these mock MCP tool calls.
"""

import asyncio
from dataclasses import dataclass, field


@dataclass
class LatencyConfig:
    """Per-tool artificial delay in seconds, configurable for demo tuning."""

    default_seconds: float = 0.5
    overrides: dict[str, float] = field(default_factory=dict)

    def seconds_for(self, tool_name: str) -> float:
        return self.overrides.get(tool_name, self.default_seconds)

    def set_override(self, tool_name: str, seconds: float) -> None:
        self.overrides[tool_name] = seconds


async def simulate_latency(config: LatencyConfig, tool_name: str) -> None:
    delay = config.seconds_for(tool_name)
    if delay > 0:
        await asyncio.sleep(delay)
