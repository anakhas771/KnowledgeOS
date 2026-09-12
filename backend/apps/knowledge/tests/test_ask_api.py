"""
Integration tests for POST /api/v1/knowledge/ask/

Ollama is always mocked.  No live LLM or embedding service required;
embed_query and search_similar_chunks are also patched where needed.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.documents.models import Document, DocumentChunk
from apps.organizations.models import Organization

# ---------------------------------------------------------------------------
# Shared test doubles / fixtures
# ---------------------------------------------------------------------------

_ASK_URL = "/api/v1/knowledge/ask/"

_MOCK_EMBEDDING = list(
    (np.array([0.1] * 384) / np.linalg.norm([0.1] * 384)).tolist()
)

_MOCK_CHUNKS = [
    {
        "chunk_id": 1,
        "document_id": 10,
        "document_title": "KnowledgeOS Overview",
        "content": "KnowledgeOS is an enterprise knowledge platform.",
        "score": 0.92,
    }
]

_DONE_STATS = {
    "eval_count": 18,
    "eval_duration": 2_000_000_000,
    "total_duration": 3_000_000_000,
    "prompt_eval_count": 42,
}


def _make_mock_stream(tokens: list[str] = None):
    """
    Return a generator that yields (token, None) for each token, then
    ("", done_stats) at the end — matching stream_generate()'s contract.
    """
    if tokens is None:
        tokens = ["KnowledgeOS", " is", " an", " enterprise", " platform."]

    def _gen(_prompt):
        for tok in tokens:
            yield (tok, None)
        yield ("", _DONE_STATS)

    return _gen


def _make_error_stream():
    """Generator that immediately raises OllamaUnavailableError."""
    from apps.ai_engine.services.ollama import OllamaUnavailableError

    def _gen(_prompt):
        raise OllamaUnavailableError("Cannot connect to Ollama service.")
        yield  # make it a generator

    return _gen


def _parse_sse(content: bytes) -> list[dict | str]:
    """
    Parse SSE content bytes into a list.
    JSON-parseable data lines → dict; raw text lines → str.
    """
    results = []
    for line in content.decode().splitlines():
        if not line.startswith("data: "):
            continue
        payload = line[len("data: "):]
        try:
            results.append(json.loads(payload))
        except json.JSONDecodeError:
            results.append(payload)
    return results


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------


class AskAPITestCase(APITestCase):
    """Tests for POST /api/v1/knowledge/ask/"""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme Corp", slug="acme-corp"
        )
        self.org_b = Organization.objects.create(
            name="Other Corp", slug="other-corp"
        )

        self.user = User.objects.create_user(
            username="alice",
            email="alice@acme.local",
            password="TestPassword123!",
            organization=self.org,
            role=User.Role.DEVELOPER,
        )
        self.user_b = User.objects.create_user(
            username="bob",
            email="bob@other.local",
            password="TestPassword123!",
            organization=self.org_b,
            role=User.Role.DEVELOPER,
        )

        self.doc = Document.objects.create(
            organization=self.org,
            title="KnowledgeOS Overview",
            uploaded_by=self.user,
        )

        self.chunk = DocumentChunk.objects.create(
            document=self.doc,
            chunk_index=1,
            content="KnowledgeOS is an enterprise knowledge platform.",
            embedding=_MOCK_EMBEDDING,
        )

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def test_unauthenticated_ask_returns_401(self):
        response = self.client.post(
            _ASK_URL, {"query": "What is KnowledgeOS?"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Input validation (all before streaming starts)
    # ------------------------------------------------------------------

    def test_empty_query_rejected_with_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "   "}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_query_rejected_with_400(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(_ASK_URL, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Happy path — authenticated ask succeeds
    # ------------------------------------------------------------------

    @patch("apps.knowledge.api.views.stream_generate", side_effect=_make_mock_stream())
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch(
        "apps.knowledge.api.views.search_similar_chunks",
        return_value=_MOCK_CHUNKS,
    )
    def test_authenticated_ask_returns_sse_stream(
        self, mock_retrieve, mock_embed, mock_stream
    ):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL,
            {"query": "What is KnowledgeOS?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("text/event-stream", response.get("Content-Type", ""))

        # Collect streamed content
        content = b"".join(response.streaming_content)
        events = _parse_sse(content)

        # Should have token events + one done event
        done_events = [e for e in events if isinstance(e, dict) and e.get("type") == "done"]
        self.assertEqual(len(done_events), 1)

        done = done_events[0]

        # Sources should be present and safe (no embeddings, no org IDs)
        self.assertIn("sources", done)
        self.assertIn("metrics", done)

        source = done["sources"][0]
        self.assertIn("chunk_id", source)
        self.assertIn("document_id", source)
        self.assertIn("document_title", source)
        self.assertIn("score", source)
        self.assertNotIn("embedding", source)
        self.assertNotIn("organization_id", source)
        self.assertNotIn("content", source)

        # Metrics should be present
        metrics = done["metrics"]
        self.assertIn("embedding_ms", metrics)
        self.assertIn("retrieval_ms", metrics)
        self.assertIn("ttft_ms", metrics)
        self.assertIn("generation_ms", metrics)
        self.assertIn("total_ms", metrics)
        self.assertIn("token_count", metrics)
        self.assertEqual(metrics["token_count"], 18)

    # ------------------------------------------------------------------
    # Tenant isolation
    # ------------------------------------------------------------------

    @patch("apps.knowledge.api.views.stream_generate", side_effect=_make_mock_stream())
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch("apps.knowledge.api.views.search_similar_chunks", return_value=[])
    def test_organization_id_comes_from_user_not_payload(
        self, mock_retrieve, mock_embed, mock_stream
    ):
        """
        Even if a client passes extra fields, org_id must always come from
        request.user.organization_id.
        """
        self.client.force_authenticate(user=self.user)
        # Attempt to pass a fake org_id in the payload (should be ignored)
        self.client.post(
            _ASK_URL,
            {"query": "test", "organization_id": self.org_b.id},
            format="json",
        )

        mock_retrieve.assert_called_once()
        call_kwargs = mock_retrieve.call_args[1]
        self.assertEqual(call_kwargs["organization_id"], self.org.id)

    @patch("apps.knowledge.api.views.stream_generate", side_effect=_make_mock_stream())
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch("apps.knowledge.api.views.search_similar_chunks", return_value=[])
    def test_user_b_cannot_access_org_a_chunks(
        self, mock_retrieve, mock_embed, mock_stream
    ):
        """user_b belongs to org_b — retrieval must be scoped to org_b."""
        self.client.force_authenticate(user=self.user_b)
        self.client.post(
            _ASK_URL, {"query": "What is KnowledgeOS?"}, format="json"
        )

        mock_retrieve.assert_called_once()
        call_kwargs = mock_retrieve.call_args[1]
        self.assertEqual(call_kwargs["organization_id"], self.org_b.id)
        # Must NOT be org_a's ID
        self.assertNotEqual(call_kwargs["organization_id"], self.org.id)

    # ------------------------------------------------------------------
    # RAG context forwarding
    # ------------------------------------------------------------------

    @patch("apps.knowledge.api.views.stream_generate", side_effect=_make_mock_stream())
    @patch("apps.knowledge.api.views.build_rag_prompt", return_value="MOCK PROMPT")
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch(
        "apps.knowledge.api.views.search_similar_chunks",
        return_value=_MOCK_CHUNKS,
    )
    def test_retrieval_chunks_are_passed_to_rag_builder(
        self, mock_retrieve, mock_embed, mock_build, mock_stream
    ):
        """Chunks from search_similar_chunks must be forwarded to build_rag_prompt."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "enterprise platform"}, format="json"
        )
        # Consume the stream
        b"".join(response.streaming_content)

        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args[1]
        self.assertEqual(call_kwargs["query"], "enterprise platform")
        self.assertEqual(call_kwargs["chunks"], _MOCK_CHUNKS)

    @patch("apps.knowledge.api.views.stream_generate", side_effect=_make_mock_stream())
    @patch("apps.knowledge.api.views.build_rag_prompt", return_value="MOCK PROMPT")
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch(
        "apps.knowledge.api.views.search_similar_chunks",
        return_value=_MOCK_CHUNKS,
    )
    def test_ollama_receives_built_prompt(
        self, mock_retrieve, mock_embed, mock_build, mock_stream
    ):
        """stream_generate must be called with the prompt returned by build_rag_prompt."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "enterprise platform"}, format="json"
        )
        b"".join(response.streaming_content)

        mock_stream.assert_called_once_with("MOCK PROMPT")

    # ------------------------------------------------------------------
    # Ollama failure: before first token → SSE error event
    # ------------------------------------------------------------------

    @patch(
        "apps.knowledge.api.views.stream_generate",
        side_effect=_make_error_stream(),
    )
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch(
        "apps.knowledge.api.views.search_similar_chunks",
        return_value=_MOCK_CHUNKS,
    )
    def test_ollama_failure_emits_sse_error_event(
        self, mock_retrieve, mock_embed, mock_stream
    ):
        """
        If Ollama is unreachable, the stream must emit an error SSE event —
        never expose raw exception details.
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "What is KnowledgeOS?"}, format="json"
        )

        # HTTP status is 200 because headers were already committed
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = b"".join(response.streaming_content)
        events = _parse_sse(content)

        error_events = [
            e for e in events
            if isinstance(e, dict) and e.get("type") == "error"
        ]
        self.assertEqual(len(error_events), 1)

        error = error_events[0]
        # Must have a generic user-facing message
        self.assertIn("message", error)
        # Must NOT expose internal details
        self.assertNotIn("OllamaUnavailableError", error["message"])
        self.assertNotIn("Traceback", error["message"])
        self.assertNotIn("Cannot connect", error["message"])

    # ------------------------------------------------------------------
    # Embedding service failure → 503 before streaming
    # ------------------------------------------------------------------

    @patch(
        "apps.knowledge.api.views.embed_query",
        side_effect=Exception("embedding service down"),
    )
    def test_embedding_failure_returns_503_before_streaming(self, mock_embed):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "test"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        # Must be a normal JSON response, not a stream
        self.assertFalse(getattr(response, "streaming", False))
        data = response.json()
        self.assertIn("detail", data)
        # No internal exception text
        self.assertNotIn("embedding service down", data["detail"])

    # ------------------------------------------------------------------
    # Retrieval failure → 503 before streaming
    # ------------------------------------------------------------------

    @patch(
        "apps.knowledge.api.views.search_similar_chunks",
        side_effect=Exception("db connection lost"),
    )
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    def test_retrieval_failure_returns_503_before_streaming(
        self, mock_embed, mock_retrieve
    ):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "test"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(getattr(response, "streaming", False))
        data = response.json()
        self.assertNotIn("db connection lost", data.get("detail", ""))

    # ------------------------------------------------------------------
    # Token count from Ollama
    # ------------------------------------------------------------------

    @patch("apps.knowledge.api.views.stream_generate", side_effect=_make_mock_stream())
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch(
        "apps.knowledge.api.views.search_similar_chunks",
        return_value=_MOCK_CHUNKS,
    )
    def test_token_count_reflects_ollama_eval_count(
        self, mock_retrieve, mock_embed, mock_stream
    ):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "What is KnowledgeOS?"}, format="json"
        )
        content = b"".join(response.streaming_content)
        events = _parse_sse(content)

        done = next(e for e in events if isinstance(e, dict) and e.get("type") == "done")
        self.assertEqual(done["metrics"]["token_count"], _DONE_STATS["eval_count"])

    # ------------------------------------------------------------------
    # Single LLM call per request
    # ------------------------------------------------------------------

    @patch("apps.knowledge.api.views.stream_generate", side_effect=_make_mock_stream())
    @patch("apps.knowledge.api.views.embed_query", return_value=_MOCK_EMBEDDING)
    @patch(
        "apps.knowledge.api.views.search_similar_chunks",
        return_value=_MOCK_CHUNKS,
    )
    def test_only_one_ollama_call_per_request(
        self, mock_retrieve, mock_embed, mock_stream
    ):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            _ASK_URL, {"query": "enterprise"}, format="json"
        )
        b"".join(response.streaming_content)

        # stream_generate must have been called exactly once
        mock_stream.assert_called_once()
