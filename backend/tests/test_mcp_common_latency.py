import asyncio

import pytest

from mcp_common.latency import LatencyConfig, simulate_latency


def test_seconds_for_returns_default_when_no_override():
    config = LatencyConfig(default_seconds=0.5)

    assert config.seconds_for("get_forecast") == 0.5


def test_seconds_for_returns_override_when_set():
    config = LatencyConfig(default_seconds=0.5)
    config.set_override("get_forecast", 2.0)

    assert config.seconds_for("get_forecast") == 2.0
    assert config.seconds_for("get_weather_risk") == 0.5


@pytest.mark.asyncio
async def test_simulate_latency_sleeps_for_the_configured_duration(monkeypatch):
    config = LatencyConfig(default_seconds=1.5)
    slept_for = []

    async def fake_sleep(seconds):
        slept_for.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await simulate_latency(config, "get_forecast")

    assert slept_for == [1.5]


@pytest.mark.asyncio
async def test_simulate_latency_skips_sleep_when_zero(monkeypatch):
    config = LatencyConfig(default_seconds=0)
    called = []

    async def fake_sleep(seconds):
        called.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await simulate_latency(config, "get_forecast")

    assert called == []
