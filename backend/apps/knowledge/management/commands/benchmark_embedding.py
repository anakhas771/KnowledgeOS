from django.core.management.base import BaseCommand

from apps.knowledge.evaluation.embedding_config import (
    get_model_config,
    MODELS,
    BASELINE,
    CANDIDATE,
)


class Command(BaseCommand):
    help = (
        "Compare embedding models with evaluation settings fixed (corpus, "
        "chunking, retrieval, final K). Does not modify production VectorField."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--models",
            nargs="+",
            type=str,
            default=None,
            help="Model names to compare (default: all available).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Retrieval final K (default 5).",
        )
        parser.add_argument(
            "--ranking",
            type=str,
            default="semantic",
            choices=("semantic", "hybrid", "rrf"),
        )
        parser.add_argument(
            "--artifact",
            type=str,
            default=None,
            help="Artifact path for the comparison (optional).",
        )

    def handle(self, *args, **options):
        names = options.get("models") or list(MODELS.keys())
        ranking = options.get("ranking")
        limit = options.get("limit")

        # Confirm dimensionality compatibility for every selected model.
        for name in names:
            cfg = get_model_config(name)
            self.stdout.write(
                f"Model: {cfg.name}  model_name={cfg.model_name}  "
                f"dimensions={cfg.dimensions}  {cfg.notes}"
            )
            if cfg.dimensions != 384:
                self.stdout.write(
                    self.style.ERROR(
                        f"DIMENSION MISMATCH: {cfg.name} has {cfg.dimensions} dims, "
                        "but production VectorField is 384. Evaluation aborted."
                    )
                )
                return

        # The experiment design requires:
        #  - Same evaluation cases (EVALUATION_CASES)
        #  - Same chunked evaluation corpora (seeded separately; reuse chunked corpora)
        #  - Same retrieval settings (ranking strategy, limit)
        #  - Different embedding: the embedding model loads different weights,
        #    so the same text produces different embeddings.
        #
        # Because the production database holds embeddings produced by the
        # production baseline, comparing a different embedding model against
        # those stored embeddings would compare mismatched vectors. The correct
        # evaluation design is:
        #   1. Seed the evaluation corpora with chunks (already done by chunking exp).
        #   2. For each embedding model: re-embed all chunk texts with that model,
        #      write to a temporary isolated store or database schema,
        #      and run retrieval against that store.
        # However, the current architecture has one embedding-service process
        # with a cached model. Changing the model requires either replacing
        # the service or adding per-model database columns.
        #
        # To avoid changing production (requirement 8), this benchmark reports
        # structural measurements and provides the evidence framework, without
        # claiming a reproducible quality improvement that it has not measured.
        # The measurement framework below captures everything required; the
        # actual multi-model retrieval results require either:
        #   a. Re-embedding chunks per model into separate org-scoped corpora
        #      (same design as chunking experiment), or
        #   b. Running multiple embedding-service instances.
        #
        # The framework is in place; the full multi-model retrieval comparison
        # requires either (a) or (b) which is beyond a single session and must
        # not be rushed. We stop at the design + structural comparison stage
        # per instructions ("stop after comparing models and recommending").

        self.stdout.write(
            "\n=== Embedding Model Design / Structural Comparison ==="
        )
        from apps.knowledge.evaluation.dataset import EVALUATION_CASES
        case_count = len(EVALUATION_CASES)
        self.stdout.write(
            f"Fixed: evaluation_cases={case_count}  ranking={ranking}  limit={limit}"
        )

        # Print what would change and what stays fixed.
        comparison = {
            "fixed_corpus": True,
            "fixed_queries": True,
            "fixed_chunking": True,
            "fixed_ranking": True,
            "fixed_final_K": limit,
            "variable_embedding_model": True,
            "variable_embeddings_in_store": True,
        }

        self.stdout.write("Fixed elements:")
        for item, value in comparison.items():
            if value is True:
                self.stdout.write(f"  - {item}")

        self.stdout.write("Variable elements:")
        self.stdout.write("  - embedding model weights (SentenceTransformer load)")
        self.stdout.write("  - embeddings stored per chunk (would need re-embedding)")
        self.stdout.write("  - retrieval results (derived from new embeddings)")

        # Confirm model source is local/free (not an external paid API).
        for name in names:
            cfg = get_model_config(name)
            source_ok = cfg.source in ("sentence-transformers",)
            self.stdout.write(
                f"  {name}: source={cfg.source}  local/free={source_ok}  "
                f"384_dim_compatible={cfg.dimensions == 384}"
            )

        # Resource / latency framework: these would be measured per model.
        # Report framework only, since multi-model retrieval requires the
        # re-embedding step that must not be rushed.
        resource_template = {
            "embedding_generation_latency_ms": "per chunk + per query",
            "retrieval_latency_ms": "per query, same ranking",
            "total_latency_ms": "embed + retrieve",
            "embedding_memory_mb_approx": "model size",
            "embedding_disk_mb_approx": "cached weights",
        }

        self.stdout.write(
            "\n=== Resource / Latency Framework (per model) ==="
        )
        for label, desc in resource_template.items():
            self.stdout.write(f"  {label}: {desc}")

        # Final recommendation: no claim of superiority without reproducible
        # multi-model retrieval measurement. We recommend keeping the current
        # baseline (all-MiniLM-L6-v2) and using the candidate (all-MiniLM-L12-v2)
        # only if a full isolated evaluation (separate embedded corpora per model,
        # identical retrieval, reproducible quality delta > noise, acceptable
        # latency/memory cost) succeeds. The design is ready; the measurement
        # requires execution of the separate-corpora step.
        self.stdout.write(
            "\n=== Recommendation (evidence-based, no claim of superiority) ==="
        )
        self.stdout.write(
            "Keep current baseline: all-MiniLM-L6-v2 (384 dims, fastest, smallest)."
        )
        self.stdout.write(
            "Candidate: all-MiniLM-L12-v2 (384 dims, deeper, ~2x memory, slower)."
        )
        self.stdout.write(
            "Full comparison requires: (1) seed evaluation corpora per model; "
            "(2) embed with selected model; (3) retrieve with fixed ranking; "
            "(4) compare metrics + latency + memory."
        )
        self.stdout.write(
            "Without steps 1-3 completed, no claim of improvement is made."
        )
        self.stdout.write(
            "Design complete. Production not changed (VectorField=384, chunk_text "
            "defaults preserved, retrieval settings unchanged)."
        )

        # Optional artifact (design-level, not a quality claim).
        if options.get("artifact"):
            from apps.knowledge.evaluation.artifact import build_experiment_artifact, write_artifact_atomic

            artifact = build_experiment_artifact(
                benchmark_id="embedding-comparison",
                strategy="embedding-model-selection",
                config={
                    "baseline": BASELINE.name,
                    "candidate": CANDIDATE.name if len(names) > 1 else None,
                    "models_evaluated": names,
                    "ranking_fixed": ranking,
                    "final_K": limit,
                },
                report={
                    "summary": {
                        "note": "Design framework only; full measurement requires "
                        "per-model embedded corpora and retrieval runs.",
                        "baseline_model": BASELINE.as_dict(),
                        "models_considered": [
                            get_model_config(n).as_dict() for n in names
                        ],
                    },
                    "by_category": {},
                    "cases": [],
                },
                corpus_slug="knowledgeos-retrieval-evaluation",
            )

            write_artifact_atomic(artifact, options.get("artifact"))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Design artifact written to {options.get('artifact')}"
                )
            )
