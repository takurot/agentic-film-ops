"""Tests for the Gemini reliability layer (SPEC §7 / §11, Issue #33)."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from google.genai import errors

from app.gemini_client import (
    DEFAULT_MODEL,
    GeminiClient,
    GeminiConfig,
    GeminiUnavailableError,
    with_min_display_time,
)


def make_api_error(code: int) -> errors.APIError:
    return errors.APIError(code, {"error": {"message": "boom"}})


def test_config_pins_a_concrete_model_by_default(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    config = GeminiConfig(api_key="test-key")

    assert config.model == DEFAULT_MODEL
    assert "latest" not in config.model


def test_config_model_is_overridable_via_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")

    config = GeminiConfig(api_key="test-key")

    assert config.model == "gemini-2.5-pro"


def test_client_construction_without_api_key_fails_fast(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiClient(GeminiConfig(api_key=None))


async def test_generate_content_returns_result_on_first_success():
    fake_response = object()
    fake_sdk_client = AsyncMock()
    fake_sdk_client.aio.models.generate_content = AsyncMock(return_value=fake_response)
    client = GeminiClient(GeminiConfig(api_key="test-key"), client=fake_sdk_client)

    result = await client.generate_content("hello")

    assert result is fake_response
    assert fake_sdk_client.aio.models.generate_content.await_count == 1


async def test_generate_content_retries_once_on_rate_limit_then_succeeds(monkeypatch):
    fake_response = object()
    fake_sdk_client = AsyncMock()
    fake_sdk_client.aio.models.generate_content = AsyncMock(
        side_effect=[make_api_error(429), fake_response]
    )
    slept = []
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=lambda s: slept.append(s)))
    client = GeminiClient(
        GeminiConfig(api_key="test-key", max_retries=1, retry_backoff_seconds=2.0),
        client=fake_sdk_client,
    )

    result = await client.generate_content("hello")

    assert result is fake_response
    assert fake_sdk_client.aio.models.generate_content.await_count == 2
    assert slept == [2.0]


async def test_generate_content_fails_cleanly_after_exhausting_retries(monkeypatch):
    fake_sdk_client = AsyncMock()
    fake_sdk_client.aio.models.generate_content = AsyncMock(
        side_effect=[make_api_error(503), make_api_error(503)]
    )
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    client = GeminiClient(GeminiConfig(api_key="test-key", max_retries=1), client=fake_sdk_client)

    with pytest.raises(GeminiUnavailableError):
        await client.generate_content("hello")

    assert fake_sdk_client.aio.models.generate_content.await_count == 2


async def test_generate_content_does_not_retry_non_retryable_errors():
    fake_sdk_client = AsyncMock()
    fake_sdk_client.aio.models.generate_content = AsyncMock(side_effect=make_api_error(400))
    client = GeminiClient(GeminiConfig(api_key="test-key", max_retries=1), client=fake_sdk_client)

    with pytest.raises(GeminiUnavailableError):
        await client.generate_content("hello")

    assert fake_sdk_client.aio.models.generate_content.await_count == 1


async def test_generate_content_treats_timeout_as_retryable_then_fails_cleanly(monkeypatch):
    async def hang(*args, **kwargs):
        # Never completes on its own — asyncio.sleep is patched below, so a
        # sleep-based hang wouldn't actually block; an unset Event does.
        await asyncio.Event().wait()

    fake_sdk_client = AsyncMock()
    fake_sdk_client.aio.models.generate_content = hang
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    client = GeminiClient(
        GeminiConfig(api_key="test-key", max_retries=1, timeout_seconds=0.01),
        client=fake_sdk_client,
    )

    with pytest.raises(GeminiUnavailableError):
        await client.generate_content("hello")


async def test_with_min_display_time_waits_out_the_remainder(monkeypatch):
    slept = []
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=lambda s: slept.append(s)))

    async def fast_call():
        return "done"

    result = await with_min_display_time(fast_call(), min_seconds=2.0)

    assert result == "done"
    assert len(slept) == 1
    assert slept[0] == pytest.approx(2.0, abs=0.05)


async def test_with_min_display_time_does_not_add_wait_when_call_already_slow(monkeypatch):
    slept = []
    monkeypatch.setattr(asyncio, "sleep", AsyncMock(side_effect=lambda s: slept.append(s)))

    async def slow_call():
        return "done"

    # min_seconds of 0 means "no floor" — the real call time already satisfies it.
    result = await with_min_display_time(slow_call(), min_seconds=0)

    assert result == "done"
    assert slept == []
