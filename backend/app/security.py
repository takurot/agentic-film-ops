"""Security, CORS, Rate Limiting, Request Size, and Secret Redaction for Agentic FilmOps (Issue #88).

Provides pure ASGI middlewares, rate limiters, constant-time auth verification,
and secret boundary protection for local and public Cloud Run deployments.
"""

from __future__ import annotations

import collections
import os
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException, Request, status

GEMINI_KEY_REGEX = re.compile(r"AIza[0-9A-Za-z_\-]{30,50}")
BEARER_TOKEN_REGEX = re.compile(r"Bearer\s+([A-Za-z0-9_\-\.]+)", re.IGNORECASE)


@dataclass
class SecurityConfig:
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://takurot0708.web.app",
            "https://takurot0708.firebaseapp.com",
        ]
    )
    allow_credentials: bool = True
    require_auth: bool = False
    auth_token: str | None = None
    max_request_body_bytes: int = 64 * 1024  # 64 KB
    rate_limit_mutations_per_min: int = 30
    rate_limit_reset_per_min: int = 10
    max_concurrent_analyses: int = 2

    @classmethod
    def from_env(cls) -> SecurityConfig:
        raw_origins = os.getenv("FILMOPS_ALLOWED_ORIGINS")
        if raw_origins:
            origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        else:
            origins = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "https://takurot0708.web.app",
                "https://takurot0708.firebaseapp.com",
            ]

        # In standard CORS, wildcard with credentials is prohibited by browsers
        allow_cred = True
        if "*" in origins:
            allow_cred = False

        require_auth = os.getenv("FILMOPS_REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")
        auth_token = os.getenv("FILMOPS_AUTH_TOKEN")

        try:
            max_body = int(os.getenv("FILMOPS_MAX_REQUEST_BODY_BYTES", str(64 * 1024)))
        except ValueError:
            max_body = 64 * 1024

        try:
            rate_mutate = int(os.getenv("FILMOPS_RATE_LIMIT_MUTATE", "30"))
        except ValueError:
            rate_mutate = 30

        try:
            rate_reset = int(os.getenv("FILMOPS_RATE_LIMIT_RESET", "10"))
        except ValueError:
            rate_reset = 10

        try:
            max_concurrent = int(os.getenv("FILMOPS_MAX_CONCURRENT_ANALYSES", "2"))
        except ValueError:
            max_concurrent = 2

        return cls(
            allowed_origins=origins,
            allow_credentials=allow_cred,
            require_auth=require_auth,
            auth_token=auth_token,
            max_request_body_bytes=max_body,
            rate_limit_mutations_per_min=rate_mutate,
            rate_limit_reset_per_min=rate_reset,
            max_concurrent_analyses=max_concurrent,
        )


def redact_secrets(text: str) -> str:
    """Redact sensitive keys and tokens from strings, error messages, and logs."""
    if not text:
        return ""
    return GEMINI_KEY_REGEX.sub("[REDACTED_API_KEY]", str(text))


def get_client_ip_from_scope(scope: dict[str, Any]) -> str:
    """Extract client IP from ASGI scope, prioritizing X-Forwarded-For behind reverse proxies."""
    headers = dict(scope.get("headers", []))
    x_forwarded_for = headers.get(b"x-forwarded-for")
    if x_forwarded_for:
        try:
            # First IP in comma-separated chain is the client IP
            first_ip = x_forwarded_for.decode("latin1").split(",")[0].strip()
            if first_ip:
                return first_ip
        except (UnicodeDecodeError, IndexError, ValueError):
            pass

    client = scope.get("client")
    if client and len(client) > 0 and client[0]:
        return str(client[0])

    return "127.0.0.1"


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter with TTL eviction."""

    def __init__(self, window_seconds: float = 60.0, max_entries: int = 5000):
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._records: dict[str, collections.deque[float]] = {}
        self._last_prune = time.monotonic()

    def is_allowed(self, key: str, max_requests: int) -> tuple[bool, int]:
        """Check if request is allowed. Returns (allowed: bool, retry_after_seconds: int)."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            # Periodic pruning of expired keys
            if now - self._last_prune > 30.0 or len(self._records) > self.max_entries:
                self._prune(cutoff)
                self._last_prune = now

            deque = self._records.setdefault(key, collections.deque())

            # Remove timestamps older than window
            while deque and deque[0] < cutoff:
                deque.popleft()

            if len(deque) >= max_requests:
                earliest = deque[0]
                retry_after = max(1, int(self.window_seconds - (now - earliest)))
                return False, retry_after

            deque.append(now)
            return True, 0

    def _prune(self, cutoff: float) -> None:
        to_delete = []
        for k, deque in self._records.items():
            while deque and deque[0] < cutoff:
                deque.popleft()
            if not deque:
                to_delete.append(k)
        for k in to_delete:
            self._records.pop(k, None)

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


# Global limiter instances
mutation_rate_limiter = SlidingWindowRateLimiter(window_seconds=60.0)
reset_rate_limiter = SlidingWindowRateLimiter(window_seconds=60.0)


class SecurityHeadersASGIMiddleware:
    """Pure ASGI middleware that attaches security headers to HTTP responses."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


class RequestBodySizeLimitASGIMiddleware:
    """Pure ASGI middleware enforcing maximum request body size (prevents memory DoS)."""

    def __init__(self, app: Any, max_body_bytes: int = 64 * 1024):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Check declared content-length if present
        headers = dict(scope.get("headers", []))
        content_length_raw = headers.get(b"content-length")
        if content_length_raw:
            try:
                content_length = int(content_length_raw.decode("latin1"))
                if content_length > self.max_body_bytes:
                    await self._send_payload_too_large(send)
                    return
            except ValueError:
                pass

        bytes_received = 0

        async def receive_with_limit() -> dict[str, Any]:
            nonlocal bytes_received
            message = await receive()
            if message["type"] == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > self.max_body_bytes:
                    raise PayloadTooLargeError()
            return message

        try:
            await self.app(scope, receive_with_limit, send)
        except PayloadTooLargeError:
            await self._send_payload_too_large(send)

    async def _send_payload_too_large(self, send: Callable) -> None:
        payload = b'{"detail":"PAYLOAD_TOO_LARGE","error_code":"REQUEST_BODY_EXCEEDS_LIMIT"}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(payload)).encode("latin1")),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": payload,
            }
        )


class PayloadTooLargeError(Exception):
    pass


def verify_demo_auth(request: Request) -> None:
    """FastAPI dependency to verify session/auth tokens when FILMOPS_REQUIRE_AUTH is enabled."""
    security_config: SecurityConfig = getattr(
        request.app.state, "security_config", SecurityConfig.from_env()
    )

    if not security_config.require_auth:
        return

    expected_token = security_config.auth_token
    if not expected_token:
        # Require auth is enabled but no server token configured
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_MISCONFIGURED — Server requires auth but FILMOPS_AUTH_TOKEN is unset",
        )

    # Check X-FilmOps-Session-Token or Authorization Bearer
    provided_token = request.headers.get("X-FilmOps-Session-Token")
    if not provided_token:
        auth_header = request.headers.get("Authorization", "")
        match = BEARER_TOKEN_REGEX.match(auth_header)
        if match:
            provided_token = match.group(1)

    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UNAUTHORIZED — Valid session token or bearer credential required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison
    if not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="UNAUTHORIZED — Invalid session token or bearer credential",
            headers={"WWW-Authenticate": "Bearer"},
        )


def enforce_mutation_rate_limit(request: Request) -> None:
    """FastAPI dependency to rate limit mutating endpoints per client IP."""
    security_config: SecurityConfig = getattr(
        request.app.state, "security_config", SecurityConfig.from_env()
    )
    client_ip = get_client_ip_from_scope(request.scope)
    key = f"mutate:{client_ip}"

    allowed, retry_after = mutation_rate_limiter.is_allowed(
        key, security_config.rate_limit_mutations_per_min
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"RATE_LIMIT_EXCEEDED — Max {security_config.rate_limit_mutations_per_min} mutation requests per minute",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_reset_rate_limit(request: Request) -> None:
    """FastAPI dependency to rate limit demo reset calls per client IP."""
    security_config: SecurityConfig = getattr(
        request.app.state, "security_config", SecurityConfig.from_env()
    )
    client_ip = get_client_ip_from_scope(request.scope)
    key = f"reset:{client_ip}"

    allowed, retry_after = reset_rate_limiter.is_allowed(
        key, security_config.rate_limit_reset_per_min
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"RATE_LIMIT_EXCEEDED — Max {security_config.rate_limit_reset_per_min} resets per minute",
            headers={"Retry-After": str(retry_after)},
        )
