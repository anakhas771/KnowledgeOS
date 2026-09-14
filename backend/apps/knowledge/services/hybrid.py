from __future__ import annotations

from collections import defaultdict

from apps.knowledge.services.lexical import search_lexical_chunks
from apps.knowledge.services.retrieval import search_similar_chunks

DEFAULT_SEMANTIC_WEIGHT = 0.7
DEFAULT_LEXICAL_WEIGHT = 0.3


def _min_max_normalize(scores: list[float]) -> list[float]:
    """
    Normalize scores to the [0, 1] range.

    When every candidate has the same score, return 1.0 for each
    candidate so the signal still contributes deterministically.
    """
    if not scores:
        return []

    minimum = min(scores)
    maximum = max(scores)

    if maximum == minimum:
        return [1.0] * len(scores)

    return [
        (score - minimum) / (maximum - minimum)
        for score in scores
    ]


def _merge_candidates(
    semantic_results: list[dict],
    lexical_results: list[dict],
    semantic_weight: float,
    lexical_weight: float,
) -> list[dict]:
    """
    Fuse semantic and lexical chunk candidates using normalized scores.
    """
    candidates: dict[int, dict] = {}

    semantic_normalized = _min_max_normalize(
        [float(result["score"]) for result in semantic_results]
    )
    lexical_normalized = _min_max_normalize(
        [float(result["score"]) for result in lexical_results]
    )

    for index, result in enumerate(semantic_results):
        chunk_id = result["chunk_id"]

        candidates[chunk_id] = {
            **result,
            "semantic_score": float(result["score"]),
            "lexical_score": 0.0,
            "hybrid_score": (
                semantic_weight * semantic_normalized[index]
            ),
        }

    for index, result in enumerate(lexical_results):
        chunk_id = result["chunk_id"]
        lexical_score = float(result["score"])

        if chunk_id not in candidates:
            candidates[chunk_id] = {
                **result,
                "semantic_score": 0.0,
                "lexical_score": lexical_score,
                "hybrid_score": (
                    lexical_weight * lexical_normalized[index]
                ),
            }
        else:
            candidates[chunk_id]["lexical_score"] = lexical_score
            candidates[chunk_id]["hybrid_score"] += (
                lexical_weight * lexical_normalized[index]
            )

    return sorted(
        candidates.values(),
        key=lambda result: (
            -result["hybrid_score"],
            -result["semantic_score"],
            -result["lexical_score"],
            result["chunk_id"],
        ),
    )


def search_hybrid_chunks(
    organization_id: int,
    query: str,
    query_embedding: list[float],
    limit: int = 5,
    semantic_limit: int = 10,
    lexical_limit: int = 10,
    semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT,
    lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
) -> list[dict]:
    """
    Retrieve and rank chunks using semantic + lexical signals.

    The two retrieval systems remain independent. This function only
    fuses their candidate sets after retrieval.
    """
    if semantic_weight < 0 or lexical_weight < 0:
        raise ValueError("Retrieval weights must not be negative.")

    if semantic_weight == 0 and lexical_weight == 0:
        raise ValueError(
            "At least one retrieval weight must be greater than zero."
        )

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

    ranked = _merge_candidates(
        semantic_results=semantic_results,
        lexical_results=lexical_results,
        semantic_weight=semantic_weight,
        lexical_weight=lexical_weight,
    )

    return ranked[:limit]

def debug_hybrid_candidates(
    organization_id: int,
    query: str,
    query_embedding: list[float],
    semantic_limit: int = 10,
    lexical_limit: int = 10,
    semantic_weight: float = 0.7,
    lexical_weight: float = 0.3,
) -> list[dict]:
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

    return _merge_candidates(
        semantic_results=semantic_results,
        lexical_results=lexical_results,
        semantic_weight=semantic_weight,
        lexical_weight=lexical_weight,
    )