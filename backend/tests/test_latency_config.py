import asyncio
import pytest

from app.latency import (
    AgentStepLatencyConfig,
    ProductionLatencyConfig,
    get_latency_config,
    simulate_agent_step_latency,
    with_min_display_time,
)


def test_default_presets_match_spec_7():
    """Verify SPEC §7.1 and §7.2 timing presets."""
    config = ProductionLatencyConfig()

    # SPEC §7.1 Actor pattern: calendar 1.2s, contract 0.8s, manager wait 4.0s, parse floor 1.0s
    assert config.actor.get_actor_availability == 1.2
    assert config.actor.get_actor_constraints == 0.8
    assert config.actor.manager_wait == 4.0
    assert config.actor.parse_min_display == 1.0

    # SPEC §7.2 Equipment pattern: inventory 1.0s, contact rental 1.0s, vendor wait 3.5s
    assert config.equipment.check_availability == 1.0
    assert config.equipment.request_extension == 1.0
    assert config.equipment.request_reservation == 1.0
    assert config.equipment.vendor_wait == 3.5

    # Location pattern: contact 1.5s
    assert config.location.contact_location_manager == 1.5


def test_scale_factor_multiplies_all_delays():
    """Scale factor scales all configured delays proportionally."""
    config = ProductionLatencyConfig(scale=0.5)

    assert config.actor.get_delay("get_actor_availability") == 0.6
    assert config.actor.get_delay("get_actor_constraints") == 0.4
    assert config.actor.get_delay("manager_wait") == 2.0
    assert config.actor.get_delay("parse_min_display") == 0.5
    assert config.equipment.get_delay("vendor_wait") == 1.75


def test_zero_scale_results_in_zero_delay():
    """Scale 0.0 results in 0.0 delay for fast automated testing."""
    config = ProductionLatencyConfig(scale=0.0)

    assert config.actor.get_delay("get_actor_availability") == 0.0
    assert config.actor.get_delay("manager_wait") == 0.0
    assert config.equipment.get_delay("vendor_wait") == 0.0


def test_environment_variable_scale(monkeypatch):
    """FILMOPS_LATENCY_SCALE sets the global scale factor."""
    monkeypatch.setenv("FILMOPS_LATENCY_SCALE", "2.0")
    config = get_latency_config(reload=True)

    assert config.scale == 2.0
    assert config.actor.get_delay("get_actor_availability") == 2.4


def test_environment_variable_json_override(monkeypatch):
    """FILMOPS_LATENCY_OVERRIDES allows granular JSON tuning without code changes."""
    monkeypatch.delenv("FILMOPS_LATENCY_SCALE", raising=False)
    monkeypatch.setenv(
        "FILMOPS_LATENCY_OVERRIDES",
        '{"actor": {"manager_wait": 1.5}, "equipment": {"vendor_wait": 2.0}}',
    )
    config = get_latency_config(reload=True)

    assert config.actor.manager_wait == 1.5
    assert config.equipment.vendor_wait == 2.0
    # Other values remain default
    assert config.actor.get_actor_availability == 1.2


def test_to_mcp_latency_config():
    """Conversion to mcp_common.LatencyConfig retains values and scale."""
    config = ProductionLatencyConfig(scale=0.5)
    mcp_actor = config.to_mcp_latency_config("actor")

    assert mcp_actor.seconds_for("get_actor_availability") == 0.6
    assert mcp_actor.seconds_for("get_actor_constraints") == 0.4
    assert mcp_actor.seconds_for("other_tool") == 0.5 * 0.5  # default 0.5 * scale 0.5


@pytest.mark.asyncio
async def test_simulate_agent_step_latency(monkeypatch):
    """simulate_agent_step_latency sleeps for the scaled duration."""
    slept = []

    async def fake_sleep(sec):
        slept.append(sec)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    step_config = AgentStepLatencyConfig(
        default_seconds=1.0,
        overrides={"custom_step": 2.5},
        scale=1.0,
    )
    await simulate_agent_step_latency(step_config, "custom_step")
    assert slept == [2.5]


@pytest.mark.asyncio
async def test_with_min_display_time_enforces_floor(monkeypatch):
    """Floor logic: max(configured_target, actual_duration) per SPEC §7."""
    slept = []

    async def fake_sleep(sec):
        slept.append(sec)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    async def fast_coro():
        return "done"

    res = await with_min_display_time(fast_coro(), min_seconds=1.0, scale=1.0)
    assert res == "done"
    assert len(slept) == 1
    assert 0.9 <= slept[0] <= 1.0
