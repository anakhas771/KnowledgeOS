"""
Ollama HTTP streaming client.

Reads configuration from environment:
  OLLAMA_BASE_URL  – default: http://host.docker.internal:11434
  OLLAMA_MODEL     – default: qwen3:4b-instruct-2507-q4_K_M

Uses httpx for streaming; the Django process never loads or runs an LLM.
"""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration (module-level, read once at import time)
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = os.getenv(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434",
).rstrip("/")

OLLAMA_MODEL: str = os.getenv(
    "OLLAMA_MODEL",
    "qwen3:4b-instruct-2507-q4_K_M",
)

# How long to wait for the first byte from Ollama (seconds).
# Kept generous because the model may still be loading on first request.
_CONNECT_TIMEOUT: float = 10.0
_READ_TIMEOUT: float = 120.0


# ---------------------------------------------------------------------------
# Typed exception
# ---------------------------------------------------------------------------


class OllamaUnavailableError(Exception):
    """
    Raised when the Ollama service cannot be reached or returns a non-2xx
    response.  Never wraps raw httpx internals — safe to surface via API.
    """


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------


def stream_generate(prompt: str) -> Generator[tuple[str, dict[str, Any] | None], None, None]:
    """
    Stream tokens from Ollama's ``POST /api/generate`` endpoint.

    Yields ``(token: str, done_stats: dict | None)`` tuples:

    * While the model is generating, ``token`` is a non-empty string and
      ``done_stats`` is ``None``.
    * On the final Ollama chunk (``"done": true``), ``token`` is ``""``
      and ``done_stats`` contains Ollama's timing/count fields.

    Raises:
        OllamaUnavailableError: If the connection fails or Ollama returns
            a non-2xx HTTP status before any data is read.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
    }

    timeout = httpx.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=10.0, pool=5.0)

    try:
        with httpx.stream("POST", url, json=payload, timeout=timeout) as response:
            if response.status_code != 200:
                # Read the body so we can log a hint, but do NOT leak it
                response.read()
                raise OllamaUnavailableError(
                    f"Ollama returned HTTP {response.status_code}"
                )

            for raw_line in response.iter_lines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue

                try:
                    chunk = json.loads(raw_line)
                except json.JSONDecodeError:
                    # Ignore malformed lines; they shouldn't appear in normal operation
                    continue

                if chunk.get("done"):
                    # Final stats chunk — no token text
                    done_stats: dict[str, Any] = {
                        "eval_count": chunk.get("eval_count", 0),
                        "eval_duration": chunk.get("eval_duration", 0),
                        "prompt_eval_count": chunk.get("prompt_eval_count", 0),
                        "total_duration": chunk.get("total_duration", 0),
                    }
                    yield ("", done_stats)
                    return
                else:
                    token: str = chunk.get("response", "")
                    if token:
                        yield (token, None)

    except httpx.ConnectError as exc:
        raise OllamaUnavailableError(
            "Cannot connect to Ollama service."
        ) from exc
    except httpx.TimeoutException as exc:
        raise OllamaUnavailableError(
            "Ollama service timed out."
        ) from exc
    except httpx.HTTPError as exc:
        raise OllamaUnavailableError(
            "Ollama HTTP error."
        ) from exc
