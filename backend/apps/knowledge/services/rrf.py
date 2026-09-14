from __future__ import annotations

from apps.knowledge.services.lexical import search_lexical_chunks
from apps.knowledge.services.retrieval import search_similar_chunks


DEFAULT_RRF_K = 60


def _fuse_rankings(
    semantic_results: list[dict],
    lexical_results: list[dict],
    k: int = DEFAULT_RRF_K,
) -> list[dict]:
    """
    Fuse semantic and lexical rankings using Reciprocal Rank Fusion.

    RRF uses rank positions instead of combining incompatible score
    distributions.
    """
    if k <= 0:
        raise ValueError("RRF k must be greater than zero.")

    candidates: dict[int, dict] = {}

    for rank, result in enumerate(semantic_results, start=1):
        chunk_id = result["chunk_id"]

        candidates.setdefault(
            chunk_id,
            {
                **result,
                "semantic_score": float(result["score"]),
                "lexical_score": 0.0,
                "semantic_rank": None,
                "lexical_rank": None,
                "rrf_score": 0.0,
            },
        )

        candidates[chunk_id]["semantic_rank"] = rank
        candidates[chunk_id]["rrf_score"] += 1.0 / (k + rank)

    for rank, result in enumerate(lexical_results, start=1):
        chunk_id = result["chunk_id"]

        if chunk_id not in candidates:
            candidates[chunk_id] = {
                **result,
                "semantic_score": 0.0,
                "lexical_score": float(result["score"]),
                "semantic_rank": None,
                "lexical_rank": rank,
                "rrf_score": 1.0 / (k + rank),
            }
        else:
            candidates[chunk_id]["lexical_score"] = float(
                result["score"]
            )
            candidates[chunk_id]["lexical_rank"] = rank
            candidates[chunk_id]["rrf_score"] += (
                1.0 / (k + rank)
            )

    return sorted(
        candidates.values(),
        key=lambda result: (
            -result["rrf_score"],
            result["chunk_id"],
        ),
    )


def search_rrf_chunks(
    organization_id: int,
    query: str,
    query_embedding: list[float],
    limit: int = 5,
    semantic_limit: int = 10,
    lexical_limit: int = 10,
    k: int = DEFAULT_RRF_K,
) -> list[dict]:
    """
    Retrieve semantic and lexical candidates and fuse their rankings
    using Reciprocal Rank Fusion.
    """
    semantic_results = search_similar_chunks(
        organization_id=organization_id,
        query_embedding=query_embedding,
        limit=semantic_limit,
    )

    lexical_results = search_lexical_chunks(
        organization_id=organization_id,
        query=query,
        limit=lexical_limit,
    )

    ranked = _fuse_rankings(
        semantic_results=semantic_results,
        lexical_results=lexical_results,
        k=k,
    )

    return ranked[:limit]