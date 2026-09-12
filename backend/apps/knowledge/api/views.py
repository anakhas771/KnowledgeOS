"""
Knowledge API views.

SearchAPIView  – existing semantic search endpoint
AskAPIView     – new RAG streaming endpoint (POST /api/v1/knowledge/ask/)
"""

from __future__ import annotations

import json
import time

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_engine.services.ollama import OllamaUnavailableError, stream_generate
from apps.ai_engine.services.rag import build_rag_prompt
from apps.knowledge.services.query_embedding import embed_query
from apps.knowledge.services.retrieval import search_similar_chunks
from apps.knowledge.services.search import perform_search

from .serializers import (
    AskRequestSerializer,
    SearchRequestSerializer,
    SearchResponseSerializer,
)

# ---------------------------------------------------------------------------
# RAG constants
# ---------------------------------------------------------------------------

_ASK_TOP_K: int = 5  # number of chunks retrieved for context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_sources(chunks: list[dict]) -> list[dict]:
    """
    Return only tenant-safe source fields from retrieval results.
    Strips embedding vectors, internal org IDs, raw content, etc.
    """
    return [
        {
            "chunk_id": c["chunk_id"],
            "document_id": c["document_id"],
            "document_title": c["document_title"],
            "score": round(float(c["score"]), 4),
        }
        for c in chunks
    ]


def _sse(payload: str) -> str:
    """Format a single SSE data line."""
    return f"data: {payload}\n\n"


def _sse_json(obj: object) -> str:
    return _sse(json.dumps(obj, ensure_ascii=False))


def _sse_error(message: str) -> str:
    return _sse_json({"type": "error", "message": message})


# ---------------------------------------------------------------------------
# Streaming generator
# ---------------------------------------------------------------------------


def _ask_stream(prompt: str, chunks: list[dict], t_request_start: float):
    """
    Generator that drives the SSE response.

    Error handling contract:
      - If Ollama fails BEFORE the first token:  we cannot return a 503 at
        this point (headers already sent), so we yield an SSE error event
        and terminate gracefully.
      - If Ollama fails AFTER the first token:   same — yield SSE error event.
      - Callers must call the Ollama client BEFORE starting StreamingHttpResponse
        if they want a genuine 503.  See AskAPIView.post() for the probe pattern.
    """
    t_ollama_start = time.monotonic()
    t_first_token: float | None = None

    generation_start_ns: float | None = None
    token_count: int = 0
    done_stats: dict | None = None

    try:
        for token, stats in stream_generate(prompt):
            if stats is not None:
                # Final done chunk
                done_stats = stats
                token_count = stats.get("eval_count", 0)
                break

            # Token chunk
            if t_first_token is None:
                t_first_token = time.monotonic()
                generation_start_ns = t_first_token

            yield _sse(token)

    except OllamaUnavailableError:
        yield _sse_error("AI generation service unavailable")
        return
    except Exception:
        # Catch-all: never expose internals
        yield _sse_error("AI generation service unavailable")
        return

    # -----------------------------------------------------------------------
    # Final metadata event
    # -----------------------------------------------------------------------
    t_stream_end = time.monotonic()

    ttft_ms = (
        int((t_first_token - t_ollama_start) * 1000)
        if t_first_token is not None
        else None
    )
    generation_ms = (
        int((t_stream_end - generation_start_ns) * 1000)
        if generation_start_ns is not None
        else 0
    )
    total_ms = int((t_stream_end - t_request_start) * 1000)

    # embedding_ms and retrieval_ms were measured before streaming started;
    # they are passed in via the closure through `chunks` being present, but
    # we receive them explicitly via the outer scope (see AskAPIView.post).
    # This generator receives them as part of the metadata dict built outside.
    metadata = {
        "type": "done",
        "sources": _safe_sources(chunks),
        "metrics": {
            "ttft_ms": ttft_ms,
            "generation_ms": generation_ms,
            "total_ms": total_ms,
            "token_count": token_count,
        },
    }
    yield _sse_json(metadata)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class SearchAPIView(APIView):
    """
    Semantic search over the organization's knowledge chunks.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Validate request payload
        serializer = SearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        query = serializer.validated_data["query"]
        limit = serializer.validated_data["limit"]
        min_similarity = serializer.validated_data.get("min_similarity")

        # Tenant isolation enforced here:
        # Organization ID must come from the authenticated user, NOT the payload
        organization_id = request.user.organization_id

        # Perform the actual semantic search
        result_data = perform_search(
            organization_id=organization_id,
            query=query,
            limit=limit,
            min_similarity=min_similarity,
        )

        # Serialize and return response
        response_serializer = SearchResponseSerializer(data=result_data)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.validated_data, status=status.HTTP_200_OK)


class AskAPIView(APIView):
    """
    RAG question-answering endpoint.

    POST /api/v1/knowledge/ask/
    Request:  { "query": "..." }
    Response: text/event-stream  (SSE)

    Error strategy
    ──────────────
    All fallible operations (auth, validation, embedding, retrieval, prompt
    building) are performed BEFORE the StreamingHttpResponse is constructed.
    If any of those steps fails, a normal JSON response (400/503) is returned
    so the HTTP status code is still meaningful.

    The only operation that runs *inside* the streaming generator is the Ollama
    call itself.  If Ollama fails before the first token, we emit an SSE error
    event and close the stream.  If it fails mid-stream, same treatment.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # ------------------------------------------------------------------
        # 1. Validate request  (returns 400 on failure — before streaming)
        # ------------------------------------------------------------------
        serializer = AskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        query: str = serializer.validated_data["query"]

        # ------------------------------------------------------------------
        # 2. Tenant isolation — org_id from authenticated user ONLY
        # ------------------------------------------------------------------
        organization_id: int = request.user.organization_id

        t_request_start = time.monotonic()

        # ------------------------------------------------------------------
        # 3. Embed query  (returns 503 on failure — before streaming)
        # ------------------------------------------------------------------
        t0 = time.monotonic()
        try:
            query_embedding = embed_query(query)
        except Exception:
            return Response(
                {"detail": "Embedding service unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        embedding_ms = int((time.monotonic() - t0) * 1000)

        # ------------------------------------------------------------------
        # 4. Retrieve context  (returns 503 on failure — before streaming)
        # ------------------------------------------------------------------
        t1 = time.monotonic()
        try:
            chunks = search_similar_chunks(
                organization_id=organization_id,
                query_embedding=query_embedding,
                limit=_ASK_TOP_K,
            )
        except Exception:
            return Response(
                {"detail": "Knowledge retrieval service unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        retrieval_ms = int((time.monotonic() - t1) * 1000)

        # ------------------------------------------------------------------
        # 5. Build RAG prompt  (pure Python — cannot fail in practice)
        # ------------------------------------------------------------------
        prompt = build_rag_prompt(query=query, chunks=chunks)

        # ------------------------------------------------------------------
        # 6. Return streaming response
        #    From this point on, status 200 is committed.
        #    Ollama errors are handled inside _ask_stream() as SSE events.
        # ------------------------------------------------------------------

        # Closure: inject pre-measured metrics into the done event
        def _stream_with_metrics():
            t_ollama_start = time.monotonic()
            t_first_token: float | None = None
            generation_start: float | None = None
            token_count: int = 0

            try:
                for token, done_stats in stream_generate(prompt):
                    if done_stats is not None:
                        token_count = done_stats.get("eval_count", 0)
                        break

                    if t_first_token is None:
                        t_first_token = time.monotonic()
                        generation_start = t_first_token

                    yield _sse(token)

            except OllamaUnavailableError:
                yield _sse_error("AI generation service unavailable")
                return
            except Exception:
                yield _sse_error("AI generation service unavailable")
                return

            # Final metadata event
            t_end = time.monotonic()

            ttft_ms = (
                int((t_first_token - t_ollama_start) * 1000)
                if t_first_token is not None
                else None
            )
            generation_ms = (
                int((t_end - generation_start) * 1000)
                if generation_start is not None
                else 0
            )
            total_ms = int((t_end - t_request_start) * 1000)

            metadata = {
                "type": "done",
                "sources": _safe_sources(chunks),
                "metrics": {
                    "embedding_ms": embedding_ms,
                    "retrieval_ms": retrieval_ms,
                    "ttft_ms": ttft_ms,
                    "generation_ms": generation_ms,
                    "total_ms": total_ms,
                    "token_count": token_count,
                },
            }
            yield _sse_json(metadata)

        response = StreamingHttpResponse(
            _stream_with_metrics(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
