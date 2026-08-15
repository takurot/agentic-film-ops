"""Gemini reliability layer (Issue #33; SPEC §7 "実 Gemini レイテンシとの
関係", §11 Mock/Real boundary — Agent reasoning is Real).

Wraps the `google-genai` SDK with:
- a pinned model version, read from config (not a floating "-latest" alias)
- one retry-with-backoff on transient/rate-limit errors, then a clean,
  typed failure — never a hang or an unhandled crash
- `with_min_display_time`, applying §7's latency-simulation floor to a real
  Gemini call: the artificial delay is a *minimum* display time, not
  additive to the real response time.
"""

import asyncio
import os
from dataclasses import dataclass, field

from google import genai
from google.genai import errors
from google.genai.types import GenerateContentResponse

from app.latency import with_min_display_time

# A concrete, versioned model — not a "-latest" alias that could silently
# change behavior mid-demo. Override via GEMINI_MODEL if this needs bumping.
DEFAULT_MODEL = "gemini-2.5-flash"

# 429 (rate limit) and 5xx (transient server errors) are worth retrying;
# other APIError codes (e.g. 400 bad request, 403 auth) are not.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class GeminiUnavailableError(Exception):
    """Raised when Gemini is unavailable after the configured retries.

    Callers (Agents, once implemented — #9/#10-#14) should catch this and
    report a `FAILED` Agent Event Stream status (SPEC §8.2) rather than let
    it propagate as an unhandled crash.
    """


@dataclass
class GeminiConfig:
    model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL", DEFAULT_MODEL))
    api_key: str | None = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY"))
    max_retries: int = 1
    retry_backoff_seconds: float = 1.0
    timeout_seconds: float = 30.0


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, errors.APIError) and exc.code in _RETRYABLE_STATUS_CODES


class GeminiClient:
    """Async wrapper around `google.genai.Client` applying the policy above."""

    def __init__(self, config: GeminiConfig | None = None, client: genai.Client | None = None):
        self.config = config or GeminiConfig()
        if client is not None:
            self._client = client
        elif self.config.api_key:
            self._client = genai.Client(api_key=self.config.api_key)
        else:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. See README 'Gemini setup' for how to configure it."
            )

    async def generate_content(self, contents: str) -> GenerateContentResponse:
        last_exc: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=self.config.model, contents=contents
                    ),
                    timeout=self.config.timeout_seconds,
                )
            except TimeoutError as exc:
                last_exc = exc
            except errors.APIError as exc:
                last_exc = exc
                if not _is_retryable(exc):
                    break

            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_backoff_seconds)

        raise GeminiUnavailableError(
            f"Gemini call failed after {self.config.max_retries + 1} attempt(s): {last_exc}"
        ) from last_exc


__all__ = [
    "DEFAULT_MODEL",
    "GeminiClient",
    "GeminiConfig",
    "GeminiUnavailableError",
    "with_min_display_time",
]
