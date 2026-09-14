"""
Evaluation-only chunk-size and overlap experiment.

Production chunking is untouched: ``chunk_text`` and its defaults
(``chunk_size=1000``, ``overlap=150``) are reused exactly as the ingestion task
calls them, and ``process_document``'s normalization is reused for text
preparation. Only the parameters passed in vary.

Isolation
---------
Each configuration is seeded into its own dedicated organization
(``chunking-eval-<name>``), separate from both the real user corpus and the
existing ``knowledgeos-retrieval-evaluation`` organization. Nothing in this
module reads or writes documents outside those organizations.

Attribution
-----------
Two independent factors affect retrieval quality: how documents were chunked,
and how candidates were ranked. ``run_chunking_experiment`` varies chunking with
the ranking strategy held fixed; ``run_attribution_matrix`` crosses chunking
configurations with ranking strategies so a measured change can be attributed to
one factor rather than assumed to belong to either.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from django.db import transaction

from apps.documents.models import Document, DocumentChunk
from apps.documents.services.chunker import TextChunk, chunk_text
from apps.documents.services.embeddings import embed_texts
from apps.documents.services.processor import normalize_text
from apps.knowledge.evaluation.benchmark import (
    run_benchmark,
    run_hybrid_benchmark,
    run_rrf_benchmark,
)
from apps.knowledge.evaluation.chunking_corpus import SOURCE_DOCUMENTS

CHUNKING_ORG_PREFIX = "chunking-eval"

CHUNKING_USER_PREFIX = "chunking_eval"


@dataclass(frozen=True)
class ChunkingConfig:
    """A single chunking configuration under evaluation."""

    name: str
    chunk_size: int
    overlap: int
    description: str = ""

    def __post_init__(self) -> None:
        # Mirror the production chunker's contract so an invalid configuration
        # fails here rather than midway through seeding a corpus.
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        if self.overlap < 0:
            raise ValueError("overlap cannot be negative.")

        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")

    @property
    def organization_slug(self) -> str:
        return f"{CHUNKING_ORG_PREFIX}-{self.name}"

    @property
    def overlap_ratio(self) -> float:
        return self.overlap / self.chunk_size

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "overlap_ratio": round(self.overlap_ratio, 4),
            "description": self.description,
        }


# Production default is (1000, 150). The comparison set holds overlap
# proportional to size at ~12-17% so that `small`/`medium`/`current` isolate
# chunk size, while `moderate_overlap` changes only overlap relative to
# `current` and therefore isolates the overlap effect.
CHUNKING_CONFIGS: tuple[ChunkingConfig, ...] = (
    ChunkingConfig(
        name="current",
        chunk_size=1000,
        overlap=150,
        description="Production default (chunk_text defaults)",
    ),
    ChunkingConfig(
        name="small",
        chunk_size=300,
        overlap=50,
        description="Smaller chunks, proportional overlap",
    ),
    ChunkingConfig(
        name="medium",
        chunk_size=600,
        overlap=75,
        description="Medium chunks, proportional overlap",
    ),
    ChunkingConfig(
        name="moderate_overlap",
        chunk_size=1000,
        overlap=300,
        description="Production size with moderate (30%) overlap",
    ),
)

CONFIGS_BY_NAME = {config.name: config for config in CHUNKING_CONFIGS}

RANKING_STRATEGIES = ("semantic", "hybrid", "rrf")


def get_config(name: str) -> ChunkingConfig:
    if name not in CONFIGS_BY_NAME:
        raise ValueError(
            f"Unknown chunking configuration '{name}'. "
            f"Available: {', '.join(sorted(CONFIGS_BY_NAME))}"
        )

    return CONFIGS_BY_NAME[name]


def build_chunks(
    title: str,
    config: ChunkingConfig,
) -> list[TextChunk]:
    """
    Chunk one source document under ``config``.

    Text preparation reuses ``normalize_text`` so the input matches what the
    ingestion pipeline would produce, and chunking reuses the production
    ``chunk_text``. The source literal is fixed, so this is deterministic.
    """
    normalized = normalize_text(SOURCE_DOCUMENTS[title])

    return chunk_text(
        normalized,
        chunk_size=config.chunk_size,
        overlap=config.overlap,
    )


def _locate_chunk_offsets(
    source: str,
    chunks: list[TextChunk],
) -> list[tuple[int, int]]:
    """
    Recover each chunk's ``[start, end)`` offsets in ``source``.

    ``chunk_text`` strips each slice before storing it, so offsets cannot be
    derived from chunk lengths alone. Searching forward from a moving cursor
    recovers the true boundaries, which is what boundary-integrity measurement
    needs. Returns ``(-1, -1)`` for any chunk that cannot be located rather
    than guessing.
    """
    offsets: list[tuple[int, int]] = []
    cursor = 0

    for chunk in chunks:
        start = source.find(chunk.content, cursor)

        if start == -1:
            offsets.append((-1, -1))
            continue

        end = start + len(chunk.content)
        offsets.append((start, end))

        # Chunks advance monotonically; overlap means the next chunk may begin
        # before this one ends, so the cursor advances by less than a full chunk.
        cursor = start + 1

    return offsets


def measure_boundary_integrity(
    title: str,
    config: ChunkingConfig,
) -> dict:
    """
    Measure how often chunk boundaries fall inside a word or a sentence.

    The production chunker is character-based, so it has no notion of word or
    sentence boundaries. This does not assume the boundaries are clean; it
    counts how often they are not, which is the property a chunking experiment
    needs to report honestly.
    """
    source = normalize_text(SOURCE_DOCUMENTS[title])
    chunks = build_chunks(title, config)
    offsets = _locate_chunk_offsets(source, chunks)

    total = len(chunks)
    located = 0
    starts_mid_word = 0
    ends_mid_word = 0
    ends_mid_sentence = 0

    for position, (chunk, (start, end)) in enumerate(zip(chunks, offsets)):
        if start == -1:
            continue

        located += 1

        # A boundary splits a word when alphanumeric characters sit on both
        # sides of it.
        if start > 0 and source[start - 1].isalnum() and source[start].isalnum():
            starts_mid_word += 1

        is_final = position == total - 1

        if not is_final and end < len(source):
            if source[end - 1].isalnum() and source[end].isalnum():
                ends_mid_word += 1

            if chunk.content.rstrip()[-1:] not in {".", "!", "?", ":", ";"}:
                ends_mid_sentence += 1

    non_final = max(total - 1, 0)

    return {
        "chunks": total,
        "located": located,
        "unlocated": total - located,
        "starts_mid_word": starts_mid_word,
        "ends_mid_word": ends_mid_word,
        "ends_mid_sentence": ends_mid_sentence,
        "starts_mid_word_ratio": (
            starts_mid_word / non_final if non_final else 0.0
        ),
        "ends_mid_word_ratio": (
            ends_mid_word / non_final if non_final else 0.0
        ),
        "ends_mid_sentence_ratio": (
            ends_mid_sentence / non_final if non_final else 0.0
        ),
    }


def chunk_statistics(config: ChunkingConfig) -> dict:
    """
    Structural statistics for a configuration across the whole corpus.

    Computed from the chunker alone, without touching the database, so it can be
    inspected before deciding whether a configuration is worth seeding.
    """
    per_document: dict[str, int] = {}
    lengths: list[int] = []

    starts_mid_word = 0
    ends_mid_word = 0
    ends_mid_sentence = 0
    boundary_denominator = 0

    for title in SOURCE_DOCUMENTS:
        chunks = build_chunks(title, config)
        per_document[title] = len(chunks)
        lengths.extend(len(chunk.content) for chunk in chunks)

        integrity = measure_boundary_integrity(title, config)
        starts_mid_word += integrity["starts_mid_word"]
        ends_mid_word += integrity["ends_mid_word"]
        ends_mid_sentence += integrity["ends_mid_sentence"]
        boundary_denominator += max(len(chunks) - 1, 0)

    return {
        "configuration": config.as_dict(),
        "documents": len(per_document),
        "total_chunks": sum(per_document.values()),
        "chunks_per_document": per_document,
        "mean_chunks_per_document": (
            statistics.mean(per_document.values()) if per_document else 0.0
        ),
        "chunk_length": {
            "min": min(lengths) if lengths else 0,
            "max": max(lengths) if lengths else 0,
            "mean": round(statistics.mean(lengths), 1) if lengths else 0.0,
            "median": statistics.median(lengths) if lengths else 0,
        },
        "boundary_integrity": {
            "non_final_chunks": boundary_denominator,
            "starts_mid_word": starts_mid_word,
            "ends_mid_word": ends_mid_word,
            "ends_mid_sentence": ends_mid_sentence,
            "starts_mid_word_ratio": (
                round(starts_mid_word / boundary_denominator, 4)
                if boundary_denominator
                else 0.0
            ),
            "ends_mid_word_ratio": (
                round(ends_mid_word / boundary_denominator, 4)
                if boundary_denominator
                else 0.0
            ),
            "ends_mid_sentence_ratio": (
                round(ends_mid_sentence / boundary_denominator, 4)
                if boundary_denominator
                else 0.0
            ),
        },
    }


def seed_configuration(config: ChunkingConfig) -> dict:
    """
    Seed the isolated corpus for one chunking configuration.

    Every configuration receives byte-identical source documents; only the
    chunking parameters differ. Chunks are replaced wholesale inside a
    transaction, mirroring ``process_document_task``, so re-seeding is
    idempotent and never mixes chunks from two runs.
    """
    from apps.accounts.models import User
    from apps.organizations.models import Organization

    with transaction.atomic():
        organization, _ = Organization.objects.get_or_create(
            slug=config.organization_slug,
            defaults={
                "name": f"Chunking Evaluation ({config.name})",
            },
        )

        user, _ = User.objects.get_or_create(
            username=f"{CHUNKING_USER_PREFIX}_{config.name}",
            defaults={
                "email": (
                    f"chunking-eval-{config.name}@knowledgeos.local"
                ),
                "organization": organization,
                "role": User.Role.ADMIN,
                "is_active": True,
            },
        )

        if user.organization_id != organization.id:
            user.organization = organization
            user.save(update_fields=["organization"])

        seeded: dict[str, int] = {}

        for title in SOURCE_DOCUMENTS:
            normalized = normalize_text(SOURCE_DOCUMENTS[title])
            chunks = build_chunks(title, config)

            if not chunks:
                raise ValueError(
                    f"Configuration '{config.name}' produced no chunks "
                    f"for '{title}'."
                )

            document, _ = Document.objects.get_or_create(
                organization=organization,
                title=title,
                defaults={
                    "file": (
                        "documents/chunking-evaluation/"
                        f"{title.lower().replace(' ', '-')}.txt"
                    ),
                    "file_type": "text/plain",
                    "file_size": len(normalized.encode("utf-8")),
                    "uploaded_by": user,
                    "status": Document.Status.COMPLETED,
                },
            )

            document.uploaded_by = user
            document.status = Document.Status.COMPLETED
            document.extracted_text = normalized
            document.file_size = len(normalized.encode("utf-8"))
            document.save(
                update_fields=[
                    "uploaded_by",
                    "status",
                    "extracted_text",
                    "file_size",
                    "updated_at",
                ]
            )

            embeddings = embed_texts([chunk.content for chunk in chunks])

            if len(embeddings) != len(chunks):
                raise ValueError(
                    "Embedding service returned an unexpected number of "
                    f"embeddings for '{title}' ({len(embeddings)} vs "
                    f"{len(chunks)})."
                )

            DocumentChunk.objects.filter(document=document).delete()

            DocumentChunk.objects.bulk_create(
                [
                    DocumentChunk(
                        document=document,
                        chunk_index=chunk.index,
                        content=chunk.content,
                        embedding=embedding,
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ]
            )

            seeded[title] = len(chunks)

    return {
        "configuration": config.as_dict(),
        "organization_id": organization.id,
        "organization_slug": organization.slug,
        "documents": len(seeded),
        "total_chunks": sum(seeded.values()),
        "chunks_per_document": seeded,
    }


def _organization_id(config: ChunkingConfig) -> int:
    from apps.organizations.models import Organization

    try:
        return Organization.objects.get(
            slug=config.organization_slug,
        ).id
    except Organization.DoesNotExist as exc:
        raise ValueError(
            f"Configuration '{config.name}' has not been seeded. "
            "Run seed_chunking_experiment first."
        ) from exc


def _stored_chunk_totals(organization_id: int) -> dict:
    """Chunk counts as actually persisted, independent of the chunker."""
    counts = {
        title: DocumentChunk.objects.filter(
            document__organization_id=organization_id,
            document__title=title,
        ).count()
        for title in SOURCE_DOCUMENTS
    }

    return {
        "total_chunks": sum(counts.values()),
        "chunks_per_document": counts,
    }


def _benchmark_for_strategy(
    strategy: str,
    organization_id: int,
    limit: int,
) -> dict:
    """
    Run one benchmark with retrieval settings held fixed across configurations.
    """
    if strategy == "semantic":
        return run_benchmark(
            organization_id=organization_id,
            limit=limit,
        )

    if strategy == "hybrid":
        return run_hybrid_benchmark(
            organization_id=organization_id,
            limit=limit,
            semantic_weight=0.7,
            lexical_weight=0.3,
        )

    if strategy == "rrf":
        return run_rrf_benchmark(
            organization_id=organization_id,
            limit=limit,
            k=60,
        )

    raise ValueError(
        f"Unknown ranking strategy '{strategy}'. "
        f"Available: {', '.join(RANKING_STRATEGIES)}"
    )


def run_chunking_experiment(
    config_names: list[str] | None = None,
    limit: int = 5,
    strategy: str = "semantic",
) -> dict[str, dict]:
    """
    Benchmark each chunking configuration under a single fixed ranking strategy.

    The ranking strategy, retrieval limit, embedding model, and evaluation cases
    are identical for every configuration, so differences in the reported
    metrics are attributable to chunking.
    """
    names = config_names or [config.name for config in CHUNKING_CONFIGS]

    results: dict[str, dict] = {}

    for name in names:
        config = get_config(name)
        organization_id = _organization_id(config)

        report = _benchmark_for_strategy(
            strategy=strategy,
            organization_id=organization_id,
            limit=limit,
        )

        stored = _stored_chunk_totals(organization_id)

        results[name] = {
            **report,
            "configuration": {
                **config.as_dict(),
                "limit": limit,
                "ranking_strategy": strategy,
            },
            "chunk_statistics": {
                **chunk_statistics(config),
                "stored": stored,
            },
        }

    return results


def run_attribution_matrix(
    config_names: list[str] | None = None,
    strategies: list[str] | None = None,
    limit: int = 5,
) -> dict[tuple[str, str], dict]:
    """
    Cross chunking configurations with ranking strategies.

    This is what separates the two effects. Reading down a strategy column shows
    the chunking effect with ranking held fixed; reading across a configuration
    row shows the ranking effect with chunking held fixed. Without both, an
    improvement cannot be attributed to either factor.
    """
    names = config_names or [config.name for config in CHUNKING_CONFIGS]
    strategy_names = strategies or list(RANKING_STRATEGIES)

    matrix: dict[tuple[str, str], dict] = {}

    for name in names:
        config = get_config(name)
        organization_id = _organization_id(config)

        for strategy in strategy_names:
            report = _benchmark_for_strategy(
                strategy=strategy,
                organization_id=organization_id,
                limit=limit,
            )

            matrix[(name, strategy)] = {
                "summary": report["summary"],
                "by_category": report["by_category"],
                "configuration": {
                    **config.as_dict(),
                    "limit": limit,
                    "ranking_strategy": strategy,
                },
            }

    return matrix
