from __future__ import annotations

import statistics
import time
from apps.knowledge.services.lexical import search_lexical_chunks
from apps.documents.models import Document
from apps.knowledge.evaluation.dataset import EVALUATION_CASES
from apps.knowledge.evaluation.metrics import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from apps.knowledge.services.query_embedding import embed_query
from apps.knowledge.services.retrieval import search_similar_chunks


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

def run_lexical_benchmark(
    organization_id: int,
    limit: int = 5,
) -> dict:
    """
    Run the retrieval benchmark against PostgreSQL full-text search.
    """
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

    rows = []
    latencies = []

    for case in EVALUATION_CASES:
        relevant_ids = tuple(
            title_to_id[title]
            for title in case.relevant_document_titles
        )

        started = time.perf_counter()

        results = search_lexical_chunks(
            organization_id=organization_id,
            query=case.query,
            limit=limit,
        )

        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)

        retrieved_chunk_document_ids = [
            result["document_id"]
            for result in results
        ]

        retrieved_document_ids = unique_preserving_order(
            retrieved_chunk_document_ids
        )

        rows.append(
            {
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
        )

    return {
        "cases": rows,
        "summary": {
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
                latencies
            ),
        },
    }
    
def run_benchmark(
    organization_id: int,
    limit: int = 5,
) -> dict:
    """
    Run the retrieval benchmark against the production semantic
    retrieval implementation.
    """
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

    rows = []
    latencies = []

    for case in EVALUATION_CASES:
        relevant_ids = tuple(
            title_to_id[title]
            for title in case.relevant_document_titles
        )

        started = time.perf_counter()

        embedding = embed_query(case.query)

        results = search_similar_chunks(
            organization_id=organization_id,
            query_embedding=embedding,
            limit=limit,
        )

        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)

        retrieved_chunk_document_ids = [
            result["document_id"]
            for result in results
        ]

        retrieved_document_ids = unique_preserving_order(
            retrieved_chunk_document_ids
        )

        rows.append(
            {
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
        )

    return {
        "cases": rows,
        "summary": {
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
                latencies
            ),
        },
    }