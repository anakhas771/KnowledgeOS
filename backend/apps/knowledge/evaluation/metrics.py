from __future__ import annotations

from collections.abc import Iterable, Sequence


def recall_at_k(
    retrieved_ids: Sequence[int],
    relevant_ids: Iterable[int],
    k: int,
) -> float:
    """
    Fraction of relevant documents retrieved within the top-k results.
    """
    if k <= 0:
        raise ValueError("k must be greater than 0")

    relevant = set(relevant_ids)

    if not relevant:
        return 0.0

    retrieved = set(retrieved_ids[:k])
    return len(retrieved & relevant) / len(relevant)


def precision_at_k(
    retrieved_ids: Sequence[int],
    relevant_ids: Iterable[int],
    k: int,
) -> float:
    """
    Fraction of top-k retrieved documents that are relevant.
    """
    if k <= 0:
        raise ValueError("k must be greater than 0")

    retrieved = list(retrieved_ids[:k])

    if not retrieved:
        return 0.0

    relevant = set(relevant_ids)

    return sum(
        document_id in relevant
        for document_id in retrieved
    ) / len(retrieved)


def reciprocal_rank(
    retrieved_ids: Sequence[int],
    relevant_ids: Iterable[int],
) -> float:
    """
    Reciprocal rank of the first relevant result.
    """
    relevant = set(relevant_ids)

    if not relevant:
        return 0.0

    for rank, document_id in enumerate(retrieved_ids, start=1):
        if document_id in relevant:
            return 1.0 / rank

    return 0.0


def mean_reciprocal_rank(
    rankings: Iterable[Sequence[int]],
    relevant_sets: Iterable[Iterable[int]],
) -> float:
    """
    Mean reciprocal rank across multiple queries.
    """
    scores = [
        reciprocal_rank(retrieved, relevant)
        for retrieved, relevant in zip(rankings, relevant_sets)
    ]

    if not scores:
        return 0.0

    return sum(scores) / len(scores)