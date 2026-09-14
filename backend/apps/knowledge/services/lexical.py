from __future__ import annotations

import re

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)

from apps.documents.models import DocumentChunk


def _build_lexical_query(query: str) -> SearchQuery:
    """
    Build an OR-based PostgreSQL full-text query from the user's terms.

    OR semantics make lexical retrieval useful for natural-language
    questions where only a subset of the query terms may occur in the
    target chunk.
    """
    terms = re.findall(r"[A-Za-z0-9']+", query)

    if not terms:
        raise ValueError("Lexical query must contain searchable terms.")

    search_query = SearchQuery(
        terms[0],
        config="english",
        search_type="plain",
    )

    for term in terms[1:]:
        search_query |= SearchQuery(
            term,
            config="english",
            search_type="plain",
        )

    return search_query


def search_lexical_chunks(
    organization_id: int,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve chunks using PostgreSQL full-text search.

    Results are tenant-isolated, match at least one searchable query
    term, and are ranked by PostgreSQL full-text relevance.
    """
    search_vector = SearchVector(
        "content",
        config="english",
    )

    search_query = _build_lexical_query(query)

    qs = (
        DocumentChunk.objects
        .filter(
            document__organization_id=organization_id,
            content__isnull=False,
        )
        .annotate(
            search_vector=search_vector,
            lexical_score=SearchRank(
                search_vector,
                search_query,
            ),
        )
        .filter(
            search_vector=search_query,
        )
        .order_by("-lexical_score", "id")[:limit]
        .select_related("document")
    )

    return [
        {
            "chunk_id": chunk.id,
            "document_id": chunk.document.id,
            "document_title": chunk.document.title,
            "content": chunk.content,
            "score": chunk.lexical_score,
        }
        for chunk in qs
    ]