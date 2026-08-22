from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.runtime import (
    RuntimeConfigurationError,
    RuntimeMode,
    RuntimeSettings,
    build_runtime_container,
)


def test_runtime_mode_is_required() -> None:
    with pytest.raises(RuntimeConfigurationError, match="FILMOPS_RUNTIME_MODE"):
        RuntimeSettings.from_env({})


@pytest.mark.parametrize("value", ["", "live_gemini", " LIVE_GEMINI ", "UNKNOWN"])
def test_runtime_mode_rejects_unknown_or_normalized_values(value: str) -> None:
    with pytest.raises(RuntimeConfigurationError, match="FILMOPS_RUNTIME_MODE"):
        RuntimeSettings.from_env({"FILMOPS_RUNTIME_MODE": value})


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("LIVE_GEMINI", RuntimeMode.LIVE_GEMINI),
        ("RECORDED_REPLAY", RuntimeMode.RECORDED_REPLAY),
    ],
)
def test_runtime_mode_accepts_only_documented_values(value: str, expected: RuntimeMode) -> None:
    settings = RuntimeSettings.from_env({"FILMOPS_RUNTIME_MODE": value})

    assert settings.mode is expected


@pytest.mark.parametrize(
    ("name", "value"),
    [("GEMINI_MODEL", ""), ("GEMINI_MODEL", "   "), ("FILMOPS_DB_PATH", "")],
)
def test_runtime_rejects_empty_explicit_configuration(name: str, value: str) -> None:
    with pytest.raises(RuntimeConfigurationError, match=name):
        RuntimeSettings.from_env(
            {
                "FILMOPS_RUNTIME_MODE": "LIVE_GEMINI",
                "GEMINI_API_KEY": "test-key",
                name: value,
            }
        )


def test_replay_runtime_does_not_construct_gemini_or_stdio() -> None:
    gemini_factory = Mock(side_effect=AssertionError("Gemini must not be constructed"))
    stdio_factory = Mock(side_effect=AssertionError("stdio must not be constructed"))

    container = build_runtime_container(
        RuntimeSettings(mode=RuntimeMode.RECORDED_REPLAY),
        gemini_factory=gemini_factory,
        stdio_factory=stdio_factory,
    )

    assert container.metadata.mode is RuntimeMode.RECORDED_REPLAY
    assert container.metadata.reasoning_provider == "recorded-fixture"
    assert container.metadata.mcp_transport == "in-process"
    assert container.metadata.adk_enabled is False
    gemini_factory.assert_not_called()
    stdio_factory.assert_not_called()


def test_live_runtime_uses_gemini_and_stdio_factories(tmp_path) -> None:
    gemini = AsyncMock()
    gemini.generate_content.return_value.text = (
        '{"status":"AVAILABLE","window_start":"16:00","window_end":"20:00","constraints":[]}'
    )
    stdio = AsyncMock()
    gemini_factory = Mock(return_value=gemini)
    stdio_factory = Mock(return_value=stdio)

    container = build_runtime_container(
        RuntimeSettings(
            mode=RuntimeMode.LIVE_GEMINI,
            gemini_api_key="test-key",
            db_path=tmp_path / "live.db",
        ),
        gemini_factory=gemini_factory,
        stdio_factory=stdio_factory,
    )

    assert container.metadata.mode is RuntimeMode.LIVE_GEMINI
    assert container.metadata.reasoning_provider == "google-genai"
    assert container.metadata.mcp_transport == "stdio"
    gemini_factory.assert_called_once()
    stdio_factory.assert_called_once()


async def test_live_runtime_routes_reasoning_through_the_injected_gemini_spy(tmp_path) -> None:
    gemini = AsyncMock()
    gemini.generate_content.return_value.text = (
        '{"status":"AVAILABLE","window_start":"16:00","window_end":"20:00","constraints":[]}'
    )
    container = build_runtime_container(
        RuntimeSettings(
            mode=RuntimeMode.LIVE_GEMINI,
            gemini_api_key="test-key",
            db_path=tmp_path / "live.db",
        ),
        gemini_factory=Mock(return_value=gemini),
        stdio_factory=Mock(return_value=AsyncMock()),
    )

    parsed = await container.engine._actor_agent._parse_manager_reply("Available after 4 PM")

    assert parsed.status == "AVAILABLE"
    gemini.generate_content.assert_awaited_once()


def test_runtime_metadata_endpoint_exposes_no_secret(monkeypatch) -> None:
    monkeypatch.setenv("FILMOPS_RUNTIME_MODE", "RECORDED_REPLAY")
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-key")

    with TestClient(app) as client:
        response = client.get("/api/runtime")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload == {
        "mode": "RECORDED_REPLAY",
        "reasoning_provider": "recorded-fixture",
        "model": None,
        "mcp_transport": "in-process",
        "adk_enabled": False,
    }
    assert "secret" not in response.text


def test_public_materials_do_not_claim_an_unimplemented_adk_runtime() -> None:
    repository = Path(__file__).resolve().parents[2]
    public_sources = [
        repository / "README.md",
        *sorted((repository / "docs").glob("*.md")),
        repository / "frontend/public/youtube_metadata.txt",
        *sorted((repository / "frontend/src").rglob("*.ts")),
        *sorted((repository / "frontend/src").rglob("*.tsx")),
        *sorted((repository / "remotion/src").rglob("*.ts")),
        *sorted((repository / "remotion/src").rglob("*.tsx")),
    ]

    for source in public_sources:
        text = source.read_text()
        assert "Google ADK" not in text, source
        assert "Agent Development Kit" not in text, source
