"""
Embedding model evaluation — evaluation-only, isolated corpora.
Actual controlled experiment (Phase 6): separate embedded corpora per model,
fixed chunking (1000/150), same retrieval, same cases, same ranking.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from django.db import connection

# Import config only (no benchmark import here to avoid circular issues at top level).
from apps.knowledge.evaluation.embedding_config import (
    MODELS, BASELINE, CANDIDATE, get_model_config,
)
from apps.knowledge.evaluation.chunking_corpus import SOURCE_DOCUMENTS
from apps.knowledge.evaluation.benchmark import run_benchmark
from apps.knowledge.evaluation.artifact import (
    build_experiment_artifact,
    write_artifact_atomic,
)


# Check which model the embedding service is actually serving.
# This determines whether we can generate isolated corpora for both.

# Small config object for seed_embedding_corpus (used when EXPERIMENT_CONFIGS missing)
EXPERIMENT_CONFIGS = {
    cfg.name: cfg
    for cfg in (
        __import__("apps.knowledge.evaluation.embedding_config", fromlist=[""]).MODELS.values()
    )
} if False else None  # placeholder; we import properly below

# Actually build from embedding_config import
from apps.knowledge.evaluation.embedding_config import (
    MODELS, BASELINE, CANDIDATE, get_model_config,
    EmbeddingModelConfig,
)

@dataclass(frozen=True)
class EmbeddingExperimentConfig:
    """Fixed chunking wrapper for embedding comparison."""
    name: str
    chunk_size: int = 1000
    overlap: int = 150
    description: str = "Fixed chunking for embedding comparison"

    @property
    def organization_slug(self) -> str:
        return f"embedding-eval-{self.name}"

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "chunk_size": self.chunk_size,
            "overlap": self.overlap,
            "description": self.description,
        }

# Build experiment configs from model names
EXPERIMENT_CONFIGS: dict[str, EmbeddingExperimentConfig] = {
    name: EmbeddingExperimentConfig(name=name) for name in MODELS
}


def check_service_model():
    from apps.documents.services.embeddings import EMBEDDING_SERVICE_URL
    import httpx
    try:
        r = httpx.get(f"{EMBEDDING_SERVICE_URL}/health", timeout=5)
        if r.status_code == 200:
            model_check = r.json().get("model", "unknown")
            return "service_reachable", r.json()
    except Exception as exc:
        return "service_unreachable", str(exc)
    return "unknown", None


# We do NOT change production service defaults.
# We seed isolated corpora by calling embed_texts, which hits the
# embedding service (currently L6). For L12 isolation we would need
# either service reconfiguration or direct model load. The user said
# "do NOT silently substitute another model" and "do NOT fabricate results".
# So we must report the actual blocker when L12 is unavailable.


def run_isolated_benchmark(model_name: str, ranking: str = "semantic", limit: int = 5) -> dict:
    info = seed_embedding_corpus(model_name)
    from apps.knowledge.evaluation.chunking import (
        ChunkingConfig,
    )
    report = run_benchmark(
        organization_id=info["organization_id"],
        limit=limit,
    )
    return {
        "benchmark": report,
        "corpus_info": info,
    }


def run_phase6():
    # Confirm both model configurations are 384-dimensional.
    for name in MODELS:
        cfg = get_model_config(name)
        if cfg.dimensions != 384:
            raise ValueError(
                f"Dimension mismatch for {name}: {cfg.dimensions} (expected 384)"
            )

    # Check service reachability and actual served model.
    service_status, service_details = check_service_model()

    # Try to load the candidate locally to verify it exists in the container.
    candidate_available = False
    candidate_load_error = None
    try:
        from sentence_transformers import SentenceTransformer
        m_l12 = SentenceTransformer(CANDIDATE.model_name)
        test_emb = m_l12.encode("test", normalize_embeddings=True, convert_to_numpy=True)
        if len(test_emb.tolist()[0]) == 384:
            candidate_available = True
    except Exception as exc:
        candidate_load_error = f"{type(exc).__name__}: {exc}"

    results = {}
    # Always try baseline (L6) via seed + benchmark.
    print(f"\n=== Seeding and benchmarking BASELINE: {BASELINE.name} ===")
    results[BASELINE.name] = {
        "benchmark": None,
        "corpus_info": None,
        "service_status": service_status,
    }
    # Actually run the baseline benchmark (this will succeed if L6 service is up).
    try:
        baseline_result = run_isolated_benchmark(BASELINE.name)
        results[BASELINE.name]["benchmark"] = baseline_result["benchmark"]
        results[BASELINE.name]["corpus_info"] = baseline_result["corpus_info"]
        print(f"Baseline benchmark complete. Corpus chunks={baseline_result['corpus_info']['total_chunks']}")
    except Exception as exc:
        results[BASELINE.name]["benchmark_error"] = f"{type(exc).__name__}: {exc}"
        print(f"Baseline benchmark FAILED: {exc}")

    # For candidate (L12): attempt seeding. If service serves L6 only,
    # seed_embedding_corpus will embed with L6 weights, which violates the
    # isolation rule. We must detect and report that.
    print(f"\n=== Checking candidate: {CANDIDATE.name} ===")
    print(f"Candidate locally available: {candidate_available}")
    if candidate_load_error:
        print(f"Candidate load blocker: {candidate_load_error}")

    results[CANDIDATE.name] = {
        "benchmark": None,
        "corpus_info": None,
        "candidate_available": candidate_available,
        "candidate_load_error": candidate_load_error,
        "service_status": service_status,
        "service_details": service_details,
        "note": (
            "Full isolated retrieval for L12 requires either (a) a separate "
            "embedding-service instance loaded with L12, or (b) direct embedding "
            "into the isolated DB using locally-loaded L12 weights. The container's "
            "service currently serves L6 only."
        ),
    }

    # If candidate is locally loadable, seed its isolated corpus using direct
    # embeddings (not the L6-served service), then benchmark against it.
    if candidate_available:
        try:
            print("Candidate locally loadable — seeding isolated L12 corpus with direct embeddings.")
            # We must embed directly. Modify seed path temporarily for this run only.
            # To keep the mechanism clean and avoid production changes, we'll create
            # the corpus by directly embedding using the loaded L12 model.
            direct_l12_result = seed_embedding_corpus_with_direct_model(CANDIDATE.name)
            results[CANDIDATE.name]["corpus_info"] = direct_l12_result
            # Benchmark
            benchmark_result = run_benchmark(
                organization_id=direct_l12_result["organization_id"],
                limit=5,
            )
            results[CANDIDATE.name]["benchmark"] = benchmark_result
            print(f"Candidate benchmark complete. Corpus chunks={direct_l12_result['total_chunks']}")
        except Exception as exc:
            results[CANDIDATE.name]["benchmark_error"] = f"{type(exc).__name__}: {exc}"
            print(f"Candidate benchmark FAILED: {exc}")
    else:
        results[CANDIDATE.name]["note"] += (
            " Candidate model is NOT available in this container (see load error). "
            "No fabricated benchmark results produced."
        )
        print(f"Candidate unavailable — no fabricated results produced.")

    return results


def seed_embedding_corpus(model_name: str) -> dict:
    """
    Seed isolated corpus using the service endpoint (production L6 by default).
    For L12 isolation, direct model load is required (see seed_embedding_corpus_with_direct_model).
    """
    cfg = get_model_config(model_name)
    exp_cfg = EXPERIMENT_CONFIGS.get(model_name)
    if exp_cfg is None:
        # Build temporary experiment config using fixed chunking
        from dataclasses import dataclass
        @dataclass(frozen=True)
        class _ExpCfg:
            name: str
            chunk_size: int = 1000
            overlap: int = 150
            @property
            def organization_slug(self): return f"embedding-eval-{self.name}"
        exp_cfg = _ExpCfg(name=model_name)

    from apps.accounts.models import User
    from apps.organizations.models import Organization

    with transaction.atomic():
        org, _ = Organization.objects.get_or_create(
            slug=exp_cfg.organization_slug,
            defaults={"name": f"Embedding Evaluation ({model_name})"},
        )
        user, _ = User.objects.get_or_create(
            username=f"embedding_eval_{model_name}",
            defaults={
                "email": f"embedding-eval-{model_name}@knowledgeos.local",
                "organization": org,
                "role": User.Role.ADMIN,
                "is_active": True,
            },
        )
        if user.organization_id != org.id:
            user.organization = org
            user.save(update_fields=["organization"])

        seeded = {}
        for title in SOURCE_DOCUMENTS:
            normalized = normalize_text(SOURCE_DOCUMENTS[title])
            chunks = chunk_text(normalized, chunk_size=1000, overlap=150)
            if not chunks:
                raise ValueError(f"No chunks produced for {title}")

            doc, _ = Document.objects.get_or_create(
                organization=org,
                title=title,
                defaults={
                    "file": f"documents/embedding-eval/{model_name}/{title.lower().replace(' ', '-')}.txt",
                    "file_type": "text/plain",
                    "file_size": len(normalized.encode("utf-8")),
                    "uploaded_by": user,
                    "status": Document.Status.COMPLETED,
                },
            )
            doc.uploaded_by = user
            doc.status = Document.Status.COMPLETED
            doc.extracted_text = normalized
            doc.file_size = len(normalized.encode("utf-8"))
            doc.save(update_fields=["uploaded_by", "status", "extracted_text", "file_size", "updated_at"])

            embeddings = embed_texts([c.content for c in chunks])
            if len(embeddings) != len(chunks):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)}")
            for emb in embeddings:
                if len(emb) != 384:
                    raise ValueError(f"Dimension mismatch: expected 384, got {len(emb)}")

            DocumentChunk.objects.filter(document=doc).delete()
            DocumentChunk.objects.bulk_create([
                DocumentChunk(
                    document=doc,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=embedding,
                )
                for chunk, embedding in zip(chunks, embeddings)
            ])
            seeded[title] = len(chunks)

    return {
        "model_name": model_name,
        "organization_id": org.id,
        "organization_slug": org.slug,
        "documents": len(seeded),
        "total_chunks": sum(seeded.values()),
        "chunks_per_document": seeded,
        "chunk_size": 1000,
        "overlap": 150,
    }


def seed_embedding_corpus_with_direct_model(model_name: str) -> dict:
    """Seed isolated corpus using directly-loaded model, not service."""
    cfg = get_model_config(model_name)
    exp_cfg = EXPERIMENT_CONFIGS[model_name]
    from apps.accounts.models import User
    from apps.organizations.models import Organization
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(cfg.model_name)

    with transaction.atomic():
        org, _ = Organization.objects.get_or_create(
            slug=exp_cfg.organization_slug,
            defaults={"name": f"Embedding Evaluation ({model_name})"},
        )
        user, _ = User.objects.get_or_create(
            username=f"embedding_eval_{model_name}",
            defaults={
                "email": f"embedding-eval-{model_name}@knowledgeos.local",
                "organization": org,
                "role": User.Role.ADMIN,
                "is_active": True,
            },
        )
        if user.organization_id != org.id:
            user.organization = org
            user.save(update_fields=["organization"])

        seeded = {}
        for title in SOURCE_DOCUMENTS:
            normalized = normalize_text(SOURCE_DOCUMENTS[title])
            chunks = chunk_text(normalized, chunk_size=1000, overlap=150)
            if not chunks:
                raise ValueError(f"No chunks produced for {title}")

            doc, _ = Document.objects.get_or_create(
                organization=org,
                title=title,
                defaults={
                    "file": f"documents/embedding-eval/{model_name}/{title.lower().replace(' ', '-')}.txt",
                    "file_type": "text/plain",
                    "file_size": len(normalized.encode("utf-8")),
                    "uploaded_by": user,
                    "status": Document.Status.COMPLETED,
                },
            )
            doc.uploaded_by = user
            doc.status = Document.Status.COMPLETED
            doc.extracted_text = normalized
            doc.file_size = len(normalized.encode("utf-8"))
            doc.save(update_fields=["uploaded_by", "status", "extracted_text", "file_size", "updated_at"])

            embeddings = model.encode(
                [c.content for c in chunks],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            embeddings = embeddings.tolist()
            if len(embeddings) != len(chunks):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)}")
            for emb in embeddings:
                if len(emb) != 384:
                    raise ValueError(f"Dimension mismatch: expected 384, got {len(emb)}")

            DocumentChunk.objects.filter(document=doc).delete()
            DocumentChunk.objects.bulk_create([
                DocumentChunk(
                    document=doc,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=embedding,
                )
                for chunk, embedding in zip(chunks, embeddings)
            ])
            seeded[title] = len(chunks)

    return {
        "model_name": model_name,
        "organization_id": org.id,
        "organization_slug": org.slug,
        "documents": len(seeded),
        "total_chunks": sum(seeded.values()),
        "chunks_per_document": seeded,
        "chunk_size": 1000,
        "overlap": 150,
    }


def structural_equivalence(structure_a, structure_b):
    result = {
        'document_titles_match': False,
        'document_counts_match': False,
        'total_chunks_match': False,
        'chunk_texts_identical': False,
        'chunk_ordering_identical': False,
        'chunking_config_identical': False,
        'overall_equivalent': False,
    }
    required_a = {'documents', 'total_chunks', 'chunk_size', 'overlap', 'chunks_per_document'}
    required_b = {'documents', 'total_chunks', 'chunk_size', 'overlap', 'chunks_per_document'}
    if not required_a.issubset(structure_a) or not required_b.issubset(structure_b):
        return result
    docs_a = set(structure_a.get('documents', []))
    docs_b = set(structure_b.get('documents', []))
    result['document_titles_match'] = docs_a == docs_b
    result['document_counts_match'] = len(docs_a) == len(docs_b)
    result['total_chunks_match'] = structure_a.get('total_chunks') == structure_b.get('total_chunks')
    result['chunking_config_identical'] = (structure_a.get('chunk_size') == structure_b.get('chunk_size') and structure_a.get('overlap') == structure_b.get('overlap') and structure_a.get('chunk_size', 0) > 0 and structure_a.get('overlap', 0) >= 0)
    chunks_a = structure_a.get('chunks_per_document', {})
    chunks_b = structure_b.get('chunks_per_document', {})
    all_texts_match = True
    ordering_match = True
    for title in docs_a & docs_b:
        texts_a = chunks_a.get(title, [])
        texts_b = chunks_b.get(title, [])
        if not isinstance(texts_a, list) or not isinstance(texts_b, list):
            all_texts_match = False; ordering_match = False; continue
        if len(texts_a) != len(texts_b):
            all_texts_match = False; ordering_match = False; continue
        for ta, tb in zip(texts_a, texts_b):
            if ta != tb:
                all_texts_match = False; ordering_match = False
    result['chunk_texts_identical'] = all_texts_match
    result['chunk_ordering_identical'] = ordering_match
    result['overall_equivalent'] = (result['document_titles_match'] and result['document_counts_match'] and result['total_chunks_match'] and result['chunk_texts_identical'] and result['chunk_ordering_identical'] and result['chunking_config_identical'])
    return result

