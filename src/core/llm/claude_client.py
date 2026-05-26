import logging
import os
import time
from typing import Any

import anthropic
from anthropic import APIConnectionError, APIStatusError, APITimeoutError
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.7
STRUCTURED_OUTPUT_TEMPERATURE = 0.0  # deterministic for schema-bound calls

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds; exponential backoff multiplier
REQUEST_TIMEOUT = 60.0  # seconds


# ── Request / Response models ─────────────────────────────────────────────────

class ClaudeRequest(BaseModel):
    messages: list[dict[str, str]]
    system: str = ""
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE


class ClaudeResponse(BaseModel):
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    latency_ms: float = Field(description="Wall-clock time for the API call in milliseconds")


# ── Client ────────────────────────────────────────────────────────────────────

class ClaudeClient:
    """Thin wrapper around the Anthropic SDK with retry and timeout handling."""

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or pass it explicitly."
            )
        self._client = anthropic.Anthropic(
            api_key=resolved_key,
            timeout=REQUEST_TIMEOUT,
        )
        logger.info("ClaudeClient initialised (model default: %s)", DEFAULT_MODEL)

    def complete(self, request: ClaudeRequest) -> ClaudeResponse:
        """Send a chat completion request with automatic retry on transient errors."""
        attempt = 0
        last_error: Exception | None = None

        while attempt < MAX_RETRIES:
            try:
                return self._call(request)
            except APITimeoutError as exc:
                last_error = exc
                logger.warning(
                    "Request timed out (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, exc,
                )
            except APIConnectionError as exc:
                last_error = exc
                logger.warning(
                    "Connection error (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, exc,
                )
            except APIStatusError as exc:
                # 429 rate-limit and 5xx server errors are retryable; others are not.
                if exc.status_code in {429, 500, 502, 503, 529}:
                    last_error = exc
                    logger.warning(
                        "Retryable API error %d (attempt %d/%d): %s",
                        exc.status_code, attempt + 1, MAX_RETRIES, exc.message,
                    )
                else:
                    logger.error(
                        "Non-retryable API error %d: %s",
                        exc.status_code, exc.message,
                    )
                    raise

            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.info("Retrying in %.1fs …", delay)
            time.sleep(delay)
            attempt += 1

        raise RuntimeError(
            f"Claude API call failed after {MAX_RETRIES} attempts."
        ) from last_error

    def _call(self, request: ClaudeRequest) -> ClaudeResponse:
        """Single attempt — no retry logic here."""
        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": request.messages,
        }
        if request.system:
            kwargs["system"] = request.system

        logger.debug(
            "Calling %s | max_tokens=%d | temperature=%.2f | messages=%d",
            request.model, request.max_tokens, request.temperature, len(request.messages),
        )

        t0 = time.perf_counter()
        raw = self._client.messages.create(**kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000

        content = raw.content[0].text if raw.content else ""

        response = ClaudeResponse(
            content=content,
            model=raw.model,
            input_tokens=raw.usage.input_tokens,
            output_tokens=raw.usage.output_tokens,
            stop_reason=raw.stop_reason or "unknown",
            latency_ms=round(latency_ms, 2),
        )

        logger.info(
            "Response received | stop=%s | tokens=(%d in / %d out) | latency=%.0fms",
            response.stop_reason,
            response.input_tokens,
            response.output_tokens,
            response.latency_ms,
        )
        return response
