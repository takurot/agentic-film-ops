"""Tests for Security Hardening, CORS, Rate Limiting, Request Size, and Secret Redaction (Issue #88)."""

from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.analysis_runner import AnalysisRunner
from app.db import Base, get_db_session
from app.main import create_app
from app.models import Scene
from app.runtime import (
    RuntimeContainer,
    RuntimeMode,
    RuntimeSettings,
    build_runtime_container,
)
from app.security import (
    SecurityConfig,
    mutation_rate_limiter,
    redact_secrets,
    reset_rate_limiter,
)
from app.workflow import (
    AnalysisEngine,
    AnalysisOutcome,
    Incident,
    get_analysis_engine,
)


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    mutation_rate_limiter.reset()
    reset_rate_limiter.reset()
    yield
    mutation_rate_limiter.reset()
    reset_rate_limiter.reset()


@pytest.fixture
def test_db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    from app.db import get_session

    with get_session(engine) as session:
        scene = Scene(
            scene_id="42",
            name="Rooftop Scene",
            type="EXT",
            duration_hours=4.0,
            scheduled=datetime.now(),
        )
        incident = Incident(
            incident_id="INC-TEST-001",
            scene_id="42",
            type="WEATHER",
            headline="Rain Alert",
            detail="Heavy rain forecast",
            detected_at=datetime.now(),
            resolved=False,
        )
        session.add_all([scene, incident])
        session.commit()

    return engine


def make_test_runtime_container(engine, runner=None):
    base = build_runtime_container(RuntimeSettings(mode=RuntimeMode.RECORDED_REPLAY))
    return RuntimeContainer(
        settings=base.settings,
        metadata=base.metadata,
        engine=engine,
        mcp_client=base.mcp_client,
        analysis_runner=runner or AnalysisRunner(bind=engine),
    )


class MockAnalysisEngine(AnalysisEngine):
    async def run_analysis(self, incident: Incident, analysis_id: str) -> AnalysisOutcome:
        return AnalysisOutcome(
            status="COMPLETED",
            options=[
                {
                    "option_id": "OPT-A",
                    "title": "Swap to Studio B",
                    "description": "Move indoors",
                    "cost_impact": 4200.0,
                    "schedule_delay_days": 0,
                    "risk_level": "LOW",
                    "recommended": True,
                    "tradeoffs": ["Zero delay"],
                }
            ],
            explainability="Deterministic resolution",
        )

    async def execute_plan(
        self,
        analysis_id: str,
        option: dict,
        incident_id: str,
        db: Any,
    ) -> list[str]:
        return ["CONFIRM_LOCATION", "RESOLVE_INCIDENT"]


@pytest.fixture
def secured_app(test_db_engine):
    config = SecurityConfig(
        allowed_origins=["http://localhost:3000", "https://takurot0708.web.app"],
        allow_credentials=True,
        require_auth=False,
        max_request_body_bytes=64 * 1024,
        rate_limit_mutations_per_min=5,
        rate_limit_reset_per_min=3,
        max_concurrent_analyses=2,
    )
    app = create_app(security_config=config)
    app.state.runtime = make_test_runtime_container(test_db_engine)

    from app.db import get_session

    def override_get_db():
        with get_session(test_db_engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_analysis_engine] = lambda: MockAnalysisEngine()
    return app


def test_cors_allowed_origin(secured_app):
    """Allowed origins receive Access-Control-Allow-Origin header."""
    client = TestClient(secured_app)
    res = client.get(
        "/api/production/health",
        headers={"Origin": "https://takurot0708.web.app"},
    )
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "https://takurot0708.web.app"
    assert res.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin(secured_app):
    """Disallowed origin does NOT receive Access-Control-Allow-Origin header."""
    client = TestClient(secured_app)
    res = client.get(
        "/api/production/health",
        headers={"Origin": "https://malicious-attacker.com"},
    )
    assert res.status_code == 200
    assert "access-control-allow-origin" not in res.headers


def test_cors_preflight_options(secured_app):
    """Preflight OPTIONS request handles allowed and disallowed origins."""
    client = TestClient(secured_app)

    # Allowed preflight
    res_ok = client.options(
        "/api/incidents/INC-TEST-001/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert res_ok.status_code == 200
    assert res_ok.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # Disallowed preflight
    res_bad = client.options(
        "/api/incidents/INC-TEST-001/analyze",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res_bad.status_code == 400 or "access-control-allow-origin" not in res_bad.headers


def test_security_headers_present(secured_app):
    """Security headers are injected into HTTP responses."""
    client = TestClient(secured_app)
    res = client.get("/api/production/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "default-src 'none'" in res.headers.get("content-security-policy", "")


def test_request_body_size_limit(test_db_engine):
    """Payloads exceeding maximum body size are rejected with 413 Payload Too Large."""
    config = SecurityConfig(
        max_request_body_bytes=1024,  # 1 KB limit for testing
    )
    app = create_app(security_config=config)
    app.state.runtime = make_test_runtime_container(test_db_engine)

    from app.db import get_session

    app.dependency_overrides[get_db_session] = lambda: get_session(test_db_engine)

    client = TestClient(app)

    # Small body under limit
    res_ok = client.post(
        "/api/analyses/AN-TEST/decision",
        json={"decision": "REJECT", "idempotency_key": "k1"},
    )
    # Returns 404 because AN-TEST not in DB, but not 413
    assert res_ok.status_code == 404

    # Large body over 1KB
    huge_data = {"decision": "REJECT", "payload": "A" * 2000}
    res_large = client.post(
        "/api/analyses/AN-TEST/decision",
        json=huge_data,
    )
    assert res_large.status_code == 413
    assert "PAYLOAD_TOO_LARGE" in res_large.text


def test_mutation_rate_limiting(secured_app):
    """Excessive mutation requests trigger 429 Too Many Requests with Retry-After header."""
    client = TestClient(secured_app)

    # Threshold is 5 per minute
    for _ in range(5):
        res = client.post("/api/incidents/INC-TEST-001/analyze")
        assert res.status_code == 202

    # 6th request must be rate limited
    res_blocked = client.post("/api/incidents/INC-TEST-001/analyze")
    assert res_blocked.status_code == 429
    assert "RATE_LIMIT_EXCEEDED" in res_blocked.text
    assert "retry-after" in res_blocked.headers


def test_reset_rate_limiting(secured_app):
    """Excessive demo reset requests trigger 429 Too Many Requests."""
    client = TestClient(secured_app)

    # Threshold is 3 per minute
    for _ in range(3):
        res = client.post("/api/demo/reset")
        assert res.status_code == 200

    # 4th request must be rate limited
    res_blocked = client.post("/api/demo/reset")
    assert res_blocked.status_code == 429
    assert "RATE_LIMIT_EXCEEDED" in res_blocked.text


def test_concurrency_limiting(test_db_engine):
    """Analysis concurrency limit blocks new jobs when max concurrent capacity is reached."""
    config = SecurityConfig(
        max_concurrent_analyses=1,  # Max 1 concurrent job
    )
    app = create_app(security_config=config)

    # Mock active_count = 1
    class BusyRunner(AnalysisRunner):
        @property
        def active_count(self) -> int:
            return 1

    app.state.runtime = make_test_runtime_container(
        test_db_engine, runner=BusyRunner(bind=test_db_engine)
    )

    from app.db import get_session

    app.dependency_overrides[get_db_session] = lambda: get_session(test_db_engine)
    app.dependency_overrides[get_analysis_engine] = lambda: MockAnalysisEngine()

    client = TestClient(app)
    res = client.post("/api/incidents/INC-TEST-001/analyze")
    assert res.status_code == 429
    assert "CONCURRENCY_LIMIT_EXCEEDED" in res.text


def test_session_auth_gate_enabled(test_db_engine):
    """When FILMOPS_REQUIRE_AUTH is enabled, unauthenticated mutations return 401."""
    config = SecurityConfig(
        require_auth=True,
        auth_token="secret-demo-token-12345",
    )
    app = create_app(security_config=config)
    app.state.runtime = make_test_runtime_container(test_db_engine)

    from app.db import get_session

    app.dependency_overrides[get_db_session] = lambda: get_session(test_db_engine)

    client = TestClient(app)

    # 1. No token -> 401
    res_no_token = client.post("/api/demo/reset")
    assert res_no_token.status_code == 401
    assert "UNAUTHORIZED" in res_no_token.text

    # 2. Invalid token -> 401
    res_bad_token = client.post(
        "/api/demo/reset",
        headers={"X-FilmOps-Session-Token": "wrong-token"},
    )
    assert res_bad_token.status_code == 401

    # 3. Valid X-FilmOps-Session-Token -> 200
    res_ok_header = client.post(
        "/api/demo/reset",
        headers={"X-FilmOps-Session-Token": "secret-demo-token-12345"},
    )
    assert res_ok_header.status_code == 200

    # 4. Valid Authorization: Bearer token -> 200
    res_ok_bearer = client.post(
        "/api/demo/reset",
        headers={"Authorization": "Bearer secret-demo-token-12345"},
    )
    assert res_ok_bearer.status_code == 200


def test_secret_redaction_helper():
    """redact_secrets replaces Gemini API keys."""
    raw = "Failed with key AIzaSyA1234567890123456789012345678901 and path /Users/admin/app.py"
    sanitized = redact_secrets(raw)
    assert "AIzaSyA1234567890123456789012345678901" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_runtime_endpoint_does_not_leak_secrets(secured_app):
    """GET /api/runtime does not expose API keys or auth tokens."""
    client = TestClient(secured_app)
    res = client.get("/api/runtime")
    assert res.status_code == 200
    body = res.text
    assert "AIza" not in body
    assert "secret" not in body.lower()
    assert "key" not in body.lower() or "mode" in body.lower()
