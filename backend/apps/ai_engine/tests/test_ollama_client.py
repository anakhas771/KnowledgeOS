"""
Unit tests for apps.ai_engine.services.ollama

Ollama is always mocked — no live server required.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from apps.ai_engine.services.ollama import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OllamaUnavailableError,
    stream_generate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sse_line(response: str = "", done: bool = False, eval_count: int = 0) -> bytes:
    """Build a JSON line as Ollama would emit."""
    import json
    obj: dict = {"response": response, "done": done}
    if done:
        obj["eval_count"] = eval_count
        obj["eval_duration"] = 1_000_000_000
        obj["total_duration"] = 2_000_000_000
    return (json.dumps(obj) + "\n").encode()


def _make_stream_response(lines: list[bytes], status_code: int = 200):
    """
    Return a mock that behaves like httpx.Response inside a ``with`` block
    and yields the provided lines from ``iter_lines()``.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.iter_lines.return_value = iter(
        line.decode() for line in lines
    )
    return mock_resp


# ---------------------------------------------------------------------------
# Tests: request construction
# ---------------------------------------------------------------------------


class TestOllamaRequestConstruction:
    """Verify the client sends the right URL, model, and payload."""

    def test_posts_to_correct_url_and_model(self):
        """stream_generate must POST to /api/generate with stream=True."""
        lines = [
            _make_sse_line("Hello"),
            _make_sse_line(done=True, eval_count=1),
        ]
        mock_resp = _make_stream_response(lines)

        with patch("apps.ai_engine.services.ollama.httpx.stream", return_value=mock_resp) as mock_stream:
            list(stream_generate("test prompt"))

        mock_stream.assert_called_once()
        call_args = mock_stream.call_args

        assert call_args[0][0] == "POST"
        assert call_args[0][1] == f"{OLLAMA_BASE_URL}/api/generate"
        json_payload = call_args[1]["json"]
        assert json_payload["model"] == OLLAMA_MODEL
        assert json_payload["prompt"] == "test prompt"
        assert json_payload["stream"] is True


# ---------------------------------------------------------------------------
# Tests: streaming yields tokens
# ---------------------------------------------------------------------------


class TestStreamingYieldsTokens:
    """Verify the generator yields the right (token, stats) tuples."""

    def test_yields_token_strings_then_done_stats(self):
        lines = [
            _make_sse_line("Hello"),
            _make_sse_line(" world"),
            _make_sse_line(done=True, eval_count=2),
        ]
        mock_resp = _make_stream_response(lines)

        with patch("apps.ai_engine.services.ollama.httpx.stream", return_value=mock_resp):
            results = list(stream_generate("any prompt"))

        # First two items: (token, None)
        assert results[0] == ("Hello", None)
        assert results[1] == (" world", None)
        # Last item: done stats
        token, stats = results[2]
        assert token == ""
        assert stats is not None
        assert stats["eval_count"] == 2

    def test_empty_response_field_not_yielded(self):
        """Lines with empty ``response`` must not produce a token tuple."""
        lines = [
            _make_sse_line(""),          # empty, should be skipped
            _make_sse_line("Hi"),
            _make_sse_line(done=True, eval_count=1),
        ]
        mock_resp = _make_stream_response(lines)

        with patch("apps.ai_engine.services.ollama.httpx.stream", return_value=mock_resp):
            results = list(stream_generate("any"))

        token_results = [(t, s) for t, s in results if s is None]
        assert len(token_results) == 1
        assert token_results[0] == ("Hi", None)


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestOllamaErrorHandling:
    """Verify all error cases surface as OllamaUnavailableError."""

    def test_connect_error_raises_safe_exception(self):
        import httpx

        with patch(
            "apps.ai_engine.services.ollama.httpx.stream",
            side_effect=httpx.ConnectError("refused"),
        ):
            with pytest.raises(OllamaUnavailableError):
                list(stream_generate("prompt"))

    def test_timeout_raises_safe_exception(self):
        import httpx

        with patch(
            "apps.ai_engine.services.ollama.httpx.stream",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with pytest.raises(OllamaUnavailableError):
                list(stream_generate("prompt"))

    def test_non_200_status_raises_safe_exception(self):
        mock_resp = _make_stream_response([], status_code=503)
        mock_resp.read = MagicMock()

        with patch("apps.ai_engine.services.ollama.httpx.stream", return_value=mock_resp):
            with pytest.raises(OllamaUnavailableError):
                list(stream_generate("prompt"))

    def test_exception_message_does_not_expose_internals(self):
        """OllamaUnavailableError message must not include internal details."""
        import httpx

        with patch(
            "apps.ai_engine.services.ollama.httpx.stream",
            side_effect=httpx.ConnectError("Connection refused to 192.168.1.100:11434"),
        ):
            try:
                list(stream_generate("prompt"))
            except OllamaUnavailableError as exc:
                # The safe message must not echo raw httpx internals
                assert "192.168.1.100" not in str(exc)
                assert "Connection refused" not in str(exc)
