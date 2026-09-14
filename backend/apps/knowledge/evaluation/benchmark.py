from __future__ import annotations

import statistics
import time
from collections.abc import Callable

from apps.documents.models import Document
from apps.knowledge.evaluation.dataset import EVALUATION_CASES
from apps.knowledge.evaluation.metrics import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from apps.knowledge.services.hybrid import search_hybrid_chunks
from apps.knowledge.services.lexical import search_lexical_chunks
from apps.knowledge.services.query_embedding import embed_query
from apps.knowledge.services.retrieval import search_similar_chunks
from apps.knowledge.services.rrf import search_rrf_chunks

def unique_preserving_order(values: list[int]) -> list[int]:
    """
    Convert chunk-level document IDs into a document-level ranking
    while preserving the first occurrence of each document.
    """
    seen: set[int] = set()
    unique_values: list[int] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)

    return unique_values


def _get_title_to_id(
    organization_id: int,
) -> dict[str, int]:
    relevant_titles = {
        title
        for case in EVALUATION_CASES
        for title in case.relevant_document_titles
    }

    title_to_id = dict(
        Document.objects.filter(
            organization_id=organization_id,
            title__in=relevant_titles,
        ).values_list("title", "id")
    )

    missing_titles = relevant_titles - title_to_id.keys()

    if missing_titles:
        raise ValueError(
            "Evaluation corpus is incomplete. Missing documents: "
            + ", ".join(sorted(missing_titles))
        )

    return title_to_id


def _build_case_result(
    case,
    title_to_id: dict[str, int],
    results: list[dict],
    latency_ms: float,
) -> dict:
    relevant_ids = tuple(
        title_to_id[title]
        for title in case.relevant_document_titles
    )

    retrieved_chunk_document_ids = [
        result["document_id"]
        for result in results
    ]

    retrieved_document_ids = unique_preserving_order(
        retrieved_chunk_document_ids
    )

    return {
        "category": case.category,
        "query": case.query,
        "retrieved_document_ids": retrieved_document_ids,
        "relevant_document_ids": list(relevant_ids),
        "recall_at_1": recall_at_k(
            retrieved_document_ids,
            relevant_ids,
            1,
        ),
        "recall_at_3": recall_at_k(
            retrieved_document_ids,
            relevant_ids,
            3,
        ),
        "recall_at_5": recall_at_k(
            retrieved_document_ids,
            relevant_ids,
            5,
        ),
        "precision_at_5": precision_at_k(
            retrieved_document_ids,
            relevant_ids,
            5,
        ),
        "reciprocal_rank": reciprocal_rank(
            retrieved_document_ids,
            relevant_ids,
        ),
        "latency_ms": round(latency_ms, 2),
    }


def _summarize(rows: list[dict]) -> dict:
    return {
        "recall_at_1": statistics.mean(
            row["recall_at_1"]
            for row in rows
        ),
        "recall_at_3": statistics.mean(
            row["recall_at_3"]
            for row in rows
        ),
        "recall_at_5": statistics.mean(
            row["recall_at_5"]
            for row in rows
        ),
        "precision_at_5": statistics.mean(
            row["precision_at_5"]
            for row in rows
        ),
        "mrr": mean_reciprocal_rank(
            [
                row["retrieved_document_ids"]
                for row in rows
            ],
            [
                row["relevant_document_ids"]
                for row in rows
            ],
        ),
        "median_latency_ms": statistics.median(
            [
                row["latency_ms"]
                for row in rows
            ]
        ),
    }


def _summarize_by_category(rows: list[dict]) -> dict[str, dict]:
    categories: dict[str, list[dict]] = {}

    for row in rows:
        categories.setdefault(
            row["category"],
            [],
        ).append(row)

    return {
        category: _summarize(category_rows)
        for category, category_rows in sorted(categories.items())
    }


def _run_benchmark(
    organization_id: int,
    limit: int,
    search_fn: Callable[[str, list[float] | None], list[dict]],
    requires_embedding: bool,
) -> dict:
    title_to_id = _get_title_to_id(organization_id)

    rows = []

    for case in EVALUATION_CASES:
        started = time.perf_counter()

        query_embedding = (
            embed_query(case.query)
            if requires_embedding
            else None
        )

        results = search_fn(
            case.query,
            query_embedding,
        )

        latency_ms = (
            time.perf_counter() - started
        ) * 1000

        rows.append(
            _build_case_result(
                case=case,
                title_to_id=title_to_id,
                results=results[:limit],
                latency_ms=latency_ms,
            )
        )

    return {
        "cases": rows,
        "summary": _summarize(rows),
        "by_category": _summarize_by_category(rows),
    }


def run_benchmark(
    organization_id: int,
    limit: int = 5,
) -> dict:
    """
    Benchmark semantic retrieval.
    """

    def semantic_search(
        query: str,
        query_embedding: list[float] | None,
    ) -> list[dict]:
        if query_embedding is None:
            raise ValueError(
                "Semantic retrieval requires a query embedding."
            )

        return search_similar_chunks(
            organization_id=organization_id,
            query_embedding=query_embedding,
            limit=limit,
        )

    return _run_benchmark(
        organization_id=organization_id,
        limit=limit,
        search_fn=semantic_search,
        requires_embedding=True,
    )


def run_lexical_benchmark(
    organization_id: int,
    limit: int = 5,
) -> dict:
    """
    Benchmark lexical retrieval.
    """

    def lexical_search(
        query: str,
        query_embedding: list[float] | None,
    ) -> list[dict]:
        return search_lexical_chunks(
            organization_id=organization_id,
            query=query,
            limit=limit,
        )

    return _run_benchmark(
        organization_id=organization_id,
        limit=limit,
        search_fn=lexical_search,
        requires_embedding=False,
    )


def run_hybrid_benchmark(
    organization_id: int,
    limit: int = 5,
    semantic_weight: float = 0.7,
    lexical_weight: float = 0.3,
) -> dict:
    """
    Benchmark hybrid retrieval using the configured signal weights.
    """

    def hybrid_search(
        query: str,
        query_embedding: list[float] | None,
    ) -> list[dict]:
        if query_embedding is None:
            raise ValueError(
                "Hybrid retrieval requires a query embedding."
            )

        return search_hybrid_chunks(
            organization_id=organization_id,
            query=query,
            query_embedding=query_embedding,
            limit=limit,
            semantic_limit=max(limit * 2, 10),
            lexical_limit=max(limit * 2, 10),
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
        )

    return _run_benchmark(
        organization_id=organization_id,
        limit=limit,
        search_fn=hybrid_search,
        requires_embedding=True,
    )

def run_hybrid_weight_sweep(
    organization_id: int,
    limit: int = 5,
) -> dict[tuple[float, float], dict]:
    """
    Benchmark hybrid retrieval across multiple semantic/lexical
    weight configurations.
    """
    weight_pairs = (
        (0.9, 0.1),
        (0.8, 0.2),
        (0.7, 0.3),
        (0.6, 0.4),
        (0.5, 0.5),
    )

    return {
        (semantic_weight, lexical_weight): run_hybrid_benchmark(
            organization_id=organization_id,
            limit=limit,
            semantic_weight=semantic_weight,
            lexical_weight=lexical_weight,
        )
        for semantic_weight, lexical_weight in weight_pairs
    }

def run_rrf_benchmark(
    organization_id: int,
    limit: int = 5,
    k: int = 60,
) -> dict:
    """
    Benchmark Reciprocal Rank Fusion retrieval.
    """

    def rrf_search(
        query: str,
        query_embedding: list[float] | None,
    ) -> list[dict]:
        if query_embedding is None:
            raise ValueError(
                "RRF retrieval requires a query embedding."
            )

        return search_rrf_chunks(
            organization_id=organization_id,
            query=query,
            query_embedding=query_embedding,
            limit=limit,
            semantic_limit=max(limit * 2, 10),
            lexical_limit=max(limit * 2, 10),
            k=k,
        )

    return _run_benchmark(
        organization_id=organization_id,
        limit=limit,
        search_fn=rrf_search,
        requires_embedding=True,
    )