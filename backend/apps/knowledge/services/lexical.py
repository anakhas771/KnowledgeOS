from __future__ import annotations

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)

from apps.documents.models import DocumentChunk


def search_lexical_chunks(
    organization_id: int,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """
    Retrieve chunks using PostgreSQL full-text search.

    Results are tenant-isolated, must match the full-text query,
    and are ranked by PostgreSQL search relevance.
    """
    search_vector = SearchVector(
        "content",
        config="english",
    )

    search_query = SearchQuery(
        query,
        config="english",
        search_type="plain",
    )

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