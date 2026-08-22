import time
from typing import Any

from django.conf import settings
from .query_embedding import embed_query
from .retrieval import search_similar_chunks


def perform_search(
    organization_id: int,
    query: str,
    limit: int = 5,
    min_similarity: float = None,
) -> dict[str, Any]:
    """
    Perform semantic search and record internal latency metrics.
    """
    t0 = time.time()
    
    # 1. Embed query
    query_embedding = embed_query(query)
    t1 = time.time()
    
    # 2. Retrieve chunks
    results = search_similar_chunks(
        organization_id=organization_id,
        query_embedding=query_embedding,
        limit=limit,
        min_similarity=min_similarity,
    )
    t2 = time.time()

    embedding_ms = int((t1 - t0) * 1000)
    retrieval_ms = int((t2 - t1) * 1000)
    total_ms = int((t2 - t0) * 1000)
    
    return {
        "query": query,
        "results": results,
        "meta": {
            "embedding_ms": embedding_ms,
            "retrieval_ms": retrieval_ms,
            "total_ms": total_ms,
        }
    }
