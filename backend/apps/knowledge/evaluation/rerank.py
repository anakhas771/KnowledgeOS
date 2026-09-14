from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

# Generic English stopwords. Natural-language evaluation queries are dominated
# by function words ("how does the ... work"), which match nearly every chunk
# and therefore carry no ranking signal. PostgreSQL's "english" full-text
# configuration already discards these for lexical retrieval, so removing them
# here keeps the experimental reranker consistent with the existing lexical
# service rather than introducing a new notion of term importance.
STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "been", "before",
        "between", "but", "by", "can", "did", "do", "does", "for", "from",
        "had", "has", "have", "how", "i", "if", "in", "into", "is", "it",
        "its", "of", "on", "or", "s", "so", "than", "that", "the", "their",
        "them", "then", "there", "these", "they", "this", "to", "was",
        "what", "when", "where", "which", "while", "who", "why", "will",
        "with", "would", "you", "your",
    }
)

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RerankConfig:
    """
    Explicit, serializable configuration for the reranking experiment.

    Weights are applied to independent signals; no signal is counted twice.
    With ``lexical_weight`` and ``title_weight`` both zero the reranked
    ordering is identical to the semantic baseline ordering, which makes the
    experiment falsifiable.
    """

    enabled: bool = True
    candidate_pool_size: int = 10
    semantic_weight: float = 0.5
    lexical_weight: float = 0.3
    title_weight: float = 0.2
    ignore_stopwords: bool = True

    def __post_init__(self) -> None:
        if self.candidate_pool_size < 1:
            raise ValueError("candidate_pool_size must be at least 1.")

        weights = (
            self.semantic_weight,
            self.lexical_weight,
            self.title_weight,
        )

        if any(weight < 0 for weight in weights):
            raise ValueError("Rerank weights must not be negative.")

        if all(weight == 0 for weight in weights):
            raise ValueError(
                "At least one rerank weight must be greater than zero."
            )

    def as_dict(self) -> dict[str, Any]:
        """Serialize the configuration for benchmark artifacts."""
        return {
            "enabled": self.enabled,
            "candidate_pool_size": self.candidate_pool_size,
            "semantic_weight": self.semantic_weight,
            "lexical_weight": self.lexical_weight,
            "title_weight": self.title_weight,
            "ignore_stopwords": self.ignore_stopwords,
        }


def tokenize(text: str | None, ignore_stopwords: bool = True) -> set[str]:
    """
    Lowercase, punctuation-insensitive tokenization.

    When stopword removal would discard every token the unfiltered tokens are
    returned instead, so an all-stopword query still produces a usable signal
    rather than silently collapsing to pure semantic ranking.
    """
    if not text:
        return set()

    tokens = set(_TOKEN_PATTERN.findall(text.lower()))

    if not ignore_stopwords:
        return tokens

    meaningful = tokens - STOPWORDS

    return meaningful or tokens


def token_overlap(
    query: str,
    text: str | None,
    ignore_stopwords: bool = True,
) -> float:
    """
    Fraction of the query's tokens that also occur in ``text``.

    Normalizing by the query length (rather than by the text length) keeps the
    signal in [0, 1] and avoids penalizing longer chunks.
    """
    query_tokens = tokenize(query, ignore_stopwords=ignore_stopwords)

    if not query_tokens:
        return 0.0

    text_tokens = tokenize(text, ignore_stopwords=ignore_stopwords)

    return len(query_tokens & text_tokens) / len(query_tokens)


def _min_max_normalize(scores: list[float]) -> list[float]:
    """
    Normalize scores to [0, 1], mirroring the existing hybrid service.

    Cosine similarities occupy a narrow band, so without normalization the
    semantic weight would be effectively smaller than the overlap weights.
    Normalizing is monotonic, so it never reorders the semantic baseline.
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


def rerank_candidates(
    candidates: Sequence[dict],
    query: str,
    config: RerankConfig | None = None,
) -> list[dict]:
    """
    Deterministically rerank an already-retrieved candidate pool.

    Returns new dictionaries; the input sequence and its dictionaries are
    never mutated. Sorting is stable on the score alone, so candidates with
    equal scores retain their incoming (semantic) relative order.
    """
    config = config or RerankConfig()

    if not candidates:
        return []

    semantic_scores = [
        float(candidate.get("score") or 0.0)
        for candidate in candidates
    ]
    normalized_semantic = _min_max_normalize(semantic_scores)

    scored: list[dict] = []

    for candidate, semantic_score in zip(candidates, normalized_semantic):
        content_overlap = token_overlap(
            query,
            candidate.get("content"),
            ignore_stopwords=config.ignore_stopwords,
        )
        title_overlap = token_overlap(
            query,
            candidate.get("document_title"),
            ignore_stopwords=config.ignore_stopwords,
        )

        rerank_score = (
            config.semantic_weight * semantic_score
            + config.lexical_weight * content_overlap
            + config.title_weight * title_overlap
        )

        scored.append(
            {
                **candidate,
                "semantic_score_normalized": semantic_score,
                "content_overlap": content_overlap,
                "title_overlap": title_overlap,
                "rerank_score": rerank_score,
            }
        )

    scored.sort(key=lambda result: -result["rerank_score"])

    return scored


def rerank_pool(
    candidates: Sequence[dict],
    query: str,
    limit: int = 5,
    config: RerankConfig | None = None,
) -> list[dict]:
    """
    Trim a candidate pool to the configured size, rerank it, and return the
    final top-K chunks.

    Document-level deduplication is intentionally left to the benchmark's
    existing ``unique_preserving_order`` step so the experiment does not
    change evaluation semantics.
    """
    config = config or RerankConfig()

    if limit < 1:
        raise ValueError("limit must be at least 1.")

    pool = list(candidates)[: config.candidate_pool_size]

    if not config.enabled:
        return pool[:limit]

    return rerank_candidates(pool, query, config=config)[:limit]


def with_weights(
    config: RerankConfig,
    semantic_weight: float,
    lexical_weight: float,
    title_weight: float,
) -> RerankConfig:
    """Return a copy of ``config`` with substituted signal weights."""
    return replace(
        config,
        semantic_weight=semantic_weight,
        lexical_weight=lexical_weight,
        title_weight=title_weight,
    )
