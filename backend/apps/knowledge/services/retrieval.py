from django.db.models import F
from pgvector.django import CosineDistance
from apps.documents.models import DocumentChunk


def search_similar_chunks(
    organization_id: int,
    query_embedding: list[float],
    limit: int = 5,
    min_similarity: float = None,
) -> list[dict]:
    """
    Retrieve chunks similar to the given embedding for a specific organization.
    """
    # Create the distance expression
    distance_expr = CosineDistance('embedding', query_embedding)

    # Base queryset: tenant isolation + annotate distance
    qs = DocumentChunk.objects.filter(
        document__organization_id=organization_id,
        embedding__isnull=False
    ).alias(
        distance=distance_expr
    ).annotate(
        # Cosine similarity is 1 - Cosine Distance for normalized embeddings
        similarity=1.0 - distance_expr
    )

    if min_similarity is not None:
        qs = qs.filter(similarity__gte=min_similarity)

    qs = qs.order_by('-similarity')[:limit].select_related("document")

    results = []
    for chunk in qs:
        results.append({
            "chunk_id": chunk.id,
            "document_id": chunk.document.id,
            "document_title": chunk.document.title,
            "content": chunk.content,
            "score": chunk.similarity,
        })

    return results
