from django.core.management.base import BaseCommand

from apps.knowledge.evaluation.benchmark import (
    run_benchmark,
    run_hybrid_benchmark,
    run_hybrid_weight_sweep,
    run_lexical_benchmark,
    run_reranked_benchmark,
    run_rerank_candidate_pool_sweep,
    run_rrf_benchmark,
)
from apps.knowledge.evaluation.rerank import RerankConfig
from apps.knowledge.evaluation.artifact import (
    build_experiment_artifact,
    build_pool_sweep_artifact,
    write_artifact_atomic,
)

EVALUATION_ORG_SLUG = "knowledgeos-retrieval-evaluation"

RERANK_STRATEGY = "semantic+rerank(experimental)"

DEFAULT_RERANK_CONFIG = RerankConfig()

COMPARISON_METRICS = (
    ("recall_at_1", "Recall@1"),
    ("recall_at_3", "Recall@3"),
    ("recall_at_5", "Recall@5"),
    ("precision_at_5", "Precision@5"),
    ("mrr", "MRR"),
    ("median_latency_ms", "Median latency (ms)"),
)


class Command(BaseCommand):
    help = "Benchmark semantic, lexical, score-fusion, and RRF retrieval."

    def add_arguments(self, parser):
        parser.add_argument(
            "--artifact",
            type=str,
            default=None,
            help="Write benchmark results to this JSON artifact path",
        )
        parser.add_argument(
            "--benchmark-id",
            type=str,
            default="benchmark-run",
            help="Stable identifier for this experiment",
        )
        parser.add_argument(
            "--rerank",
            action="store_true",
            help=(
                "Run the experimental query-aware reranking benchmark and "
                "compare it against the semantic baseline"
            ),
        )
        parser.add_argument(
            "--candidate-pool-size",
            type=int,
            default=DEFAULT_RERANK_CONFIG.candidate_pool_size,
            help="Semantic candidate pool size retrieved before reranking",
        )
        parser.add_argument(
            "--rerank-semantic-weight",
            type=float,
            default=DEFAULT_RERANK_CONFIG.semantic_weight,
            help="Weight applied to the normalized semantic similarity",
        )
        parser.add_argument(
            "--rerank-lexical-weight",
            type=float,
            default=DEFAULT_RERANK_CONFIG.lexical_weight,
            help="Weight applied to query/content token overlap",
        )
        parser.add_argument(
            "--rerank-title-weight",
            type=float,
            default=DEFAULT_RERANK_CONFIG.title_weight,
            help="Weight applied to query/title token overlap",
        )
        parser.add_argument(
            "--rerank-pools",
            nargs="+",
            type=int,
            default=None,
            help=(
                "Candidate-pool sizes to sweep, e.g. --rerank-pools 5 10 "
                "15 20. Omit to skip the sweep."
            ),
        )
        parser.add_argument(
            "--rerank-artifact",
            type=str,
            default=None,
            help=(
                "Write the reranking experiment results to this JSON "
                "artifact path"
            ),
        )
        parser.add_argument(
            "--sweep-artifact",
            type=str,
            default=None,
            help=(
                "Write the candidate-pool sweep results to this JSON "
                "artifact path (requires --rerank-pools)"
            ),
        )

    def handle(self, *args, **options):
        from apps.organizations.models import Organization

        organization = Organization.objects.get(
            slug=EVALUATION_ORG_SLUG,
        )

        semantic_report = run_benchmark(
            organization_id=organization.id,
            limit=5,
        )

        lexical_report = run_lexical_benchmark(
            organization_id=organization.id,
            limit=5,
        )

        hybrid_report = run_hybrid_benchmark(
            organization_id=organization.id,
            limit=5,
            semantic_weight=0.7,
            lexical_weight=0.3,
        )
        hybrid_sweep = run_hybrid_weight_sweep(
            organization_id=organization.id,
            limit=5,
        )

        rrf_report = run_rrf_benchmark(
            organization_id=organization.id,
            limit=5,
            k=60,
        )

        self._print_report(
            "Semantic Retrieval",
            semantic_report,
        )

        self._print_report(
            "Lexical Retrieval",
            lexical_report,
        )

        self._print_report(
            "Hybrid Retrieval (70/30)",
            hybrid_report,
        )

        self._print_report(
            "RRF Hybrid (k=60)",
            rrf_report,
        )

        self._print_hybrid_weight_sweep(
            hybrid_sweep,
        )

        reranked_report = None
        sweep_results = None

        if options.get("rerank"):
            rerank_config = RerankConfig(
                candidate_pool_size=options["candidate_pool_size"],
                semantic_weight=options["rerank_semantic_weight"],
                lexical_weight=options["rerank_lexical_weight"],
                title_weight=options["rerank_title_weight"],
            )

            reranked_report = run_reranked_benchmark(
                organization_id=organization.id,
                limit=5,
                config=rerank_config,
            )

            self._print_report(
                "Semantic + Query-Aware Reranking (experimental)",
                reranked_report,
            )

            self._print_comparison(
                baseline_report=semantic_report,
                candidate_report=reranked_report,
            )

        if options.get("rerank_pools"):
            # Deduplicate and validate the requested pool sizes.
            pool_sizes_raw = options["rerank_pools"]
            validated_pools = []
            seen_pools: set[int] = set()
            for s in pool_sizes_raw:
                if s < 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Ignoring non-positive pool size: {s}"
                        )
                    )
                    continue
                if s in seen_pools:
                    continue
                seen_pools.add(s)
                validated_pools.append(s)

            if not validated_pools:
                self.stdout.write(
                    self.style.ERROR(
                        "No valid pool sizes provided for sweep."
                    )
                )
            else:
                sweep_config = RerankConfig(
                    semantic_weight=options["rerank_semantic_weight"],
                    lexical_weight=options["rerank_lexical_weight"],
                    title_weight=options["rerank_title_weight"],
                )
                sweep_results = run_rerank_candidate_pool_sweep(
                    organization_id=organization.id,
                    pool_sizes=validated_pools,
                    limit=5,
                    config=sweep_config,
                )
                self._print_pool_sweep(sweep_results)

        if options.get("artifact"):
            artifact_path = options["artifact"]
            artifact = build_experiment_artifact(
                benchmark_id=options.get("benchmark_id", "benchmark-run"),
                strategy="hybrid",
                config={
                    "semantic_weight": 0.7,
                    "lexical_weight": 0.3,
                    "limit": 5,
                    "k_rrf": 60,
                },
                report=semantic_report,
                corpus_slug=EVALUATION_ORG_SLUG,
            )
            write_artifact_atomic(artifact, artifact_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Artifact written to {artifact_path}"
                )
            )

        if options.get("rerank_artifact") and reranked_report is not None:
            rerank_artifact_path = options["rerank_artifact"]
            rerank_artifact = build_experiment_artifact(
                benchmark_id=options.get("benchmark_id", "benchmark-run"),
                strategy=RERANK_STRATEGY,
                config=reranked_report["configuration"],
                report=reranked_report,
                corpus_slug=EVALUATION_ORG_SLUG,
            )
            write_artifact_atomic(rerank_artifact, rerank_artifact_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Rerank artifact written to {rerank_artifact_path}"
                )
            )
        elif options.get("rerank_artifact"):
            self.stdout.write(
                self.style.WARNING(
                    "--rerank-artifact requires --rerank; nothing written."
                )
            )

        if sweep_results is not None and options.get("sweep_artifact"):
            sweep_artifact_path = options["sweep_artifact"]
            sweep_artifact = build_pool_sweep_artifact(
                benchmark_id=options.get("benchmark_id", "benchmark-run"),
                strategy=RERANK_STRATEGY,
                reports_by_pool=sweep_results,
                final_k=5,
                corpus_slug=EVALUATION_ORG_SLUG,
            )
            write_artifact_atomic(sweep_artifact, sweep_artifact_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Pool sweep artifact written to {sweep_artifact_path}"
                )
            )
        elif options.get("sweep_artifact"):
            self.stdout.write(
                self.style.WARNING(
                    "--sweep-artifact requires --rerank-pools; "
                    "nothing written."
                )
            )

    def _print_pool_sweep(
        self,
        results: dict[int, dict],
    ) -> None:
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Candidate Pool Size Sweep (Fixed K=5)")
        self.stdout.write("=" * 60)

        header_line = (
            f"{'Pool':>8} | "
            f"{'R@1':>6} | {'R@3':>6} | {'R@5':>6} | "
            f"{'P@5':>6} | {'MRR':>6} | {'Latency(ms)':>14}"
        )
        self.stdout.write(header_line)
        self.stdout.write("-" * len(header_line))

        for size in sorted(results.keys()):
            summary = results[size]["summary"]
            self.stdout.write(
                f"{size:>8} | "
                f"{summary['recall_at_1']:>6.3f} | "
                f"{summary['recall_at_3']:>6.3f} | "
                f"{summary['recall_at_5']:>6.3f} | "
                f"{summary['precision_at_5']:>6.3f} | "
                f"{summary['mrr']:>6.3f} | "
                f"{summary['median_latency_ms']:>14.2f}"
            )

        # Print category-level comparison for the smallest and largest pools
        if len(sorted(results.keys())) > 1:
            min_size = min(results)
            max_size = max(results)
            self.stdout.write(
                f"\nCategory-level comparison: pool={min_size} vs {max_size}"
            )
            for category in sorted(results[min_size]["by_category"]):
                if category not in results[max_size]["by_category"]:
                    continue
                self.stdout.write(f"\n[{category}]")
                for (key, label) in COMPARISON_METRICS:
                    min_val = results[min_size]["by_category"][category][key]
                    max_val = results[max_size]["by_category"][category][key]
                    delta = max_val - min_val
                    self.stdout.write(
                        f"  {label}: {min_val:.3f} -> {max_val:.3f} "
                        f"({delta:+.3f})"
                    )

    def _print_comparison(
        self,
        baseline_report: dict,
        candidate_report: dict,
    ) -> None:
        """
        Print reranked metrics against the semantic baseline.

        Both reports are produced from the same corpus, cases, and evaluation
        limit, so the deltas isolate the reranking stage.
        """
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Reranking vs Semantic Baseline")
        self.stdout.write("=" * 60)

        baseline_summary = baseline_report["summary"]
        candidate_summary = candidate_report["summary"]

        self.stdout.write("\nOverall:")

        for key, label in COMPARISON_METRICS:
            baseline_value = baseline_summary[key]
            candidate_value = candidate_summary[key]
            delta = candidate_value - baseline_value

            self.stdout.write(
                f"{label}: {baseline_value:.3f} -> {candidate_value:.3f} "
                f"({delta:+.3f})"
            )

        self.stdout.write("\nBy category:")

        baseline_categories = baseline_report["by_category"]
        candidate_categories = candidate_report["by_category"]

        for category in sorted(candidate_categories):
            if category not in baseline_categories:
                continue

            self.stdout.write(f"\n[{category}]")

            for key, label in COMPARISON_METRICS:
                baseline_value = baseline_categories[category][key]
                candidate_value = candidate_categories[category][key]
                delta = candidate_value - baseline_value

                self.stdout.write(
                    f"{label}: {baseline_value:.3f} -> "
                    f"{candidate_value:.3f} ({delta:+.3f})"
                )

    def _print_hybrid_weight_sweep(
        self,
        reports: dict[tuple[float, float], dict],
    ) -> None:
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("Hybrid Weight Sweep")
        self.stdout.write("=" * 60)

        for (semantic_weight, lexical_weight), report in reports.items():
            summary = report["summary"]

            self.stdout.write(
                f"\nSemantic/Lexical: "
                f"{semantic_weight:.1f}/{lexical_weight:.1f}"
            )
            self.stdout.write(
                f"Recall@1: {summary['recall_at_1']:.3f}"
            )
            self.stdout.write(
                f"Recall@3: {summary['recall_at_3']:.3f}"
            )
            self.stdout.write(
                f"Recall@5: {summary['recall_at_5']:.3f}"
            )
            self.stdout.write(
                f"Precision@5: {summary['precision_at_5']:.3f}"
            )
            self.stdout.write(
                f"MRR: {summary['mrr']:.3f}"
            )
            self.stdout.write(
                f"Median latency: "
                f"{summary['median_latency_ms']:.2f} ms"
            )

            self.stdout.write("\nCategory Breakdown:")

            for category, metrics in report["by_category"].items():
                self.stdout.write(f"\n[{category}]")
                self.stdout.write(
                    f"Recall@1: {metrics['recall_at_1']:.3f}"
                )
                self.stdout.write(
                    f"Recall@3: {metrics['recall_at_3']:.3f}"
                )
                self.stdout.write(
                    f"Recall@5: {metrics['recall_at_5']:.3f}"
                )
                self.stdout.write(
                    f"Precision@5: {metrics['precision_at_5']:.3f}"
                )
                self.stdout.write(
                    f"MRR: {metrics['mrr']:.3f}"
                )

    def _print_report(
        self,
        name: str,
        report: dict,
    ) -> None:
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write(name)
        self.stdout.write("=" * 60)

        for row in report["cases"]:
            self.stdout.write(
                f"\nQuery: {row['query']}\n"
                f"Retrieved: {row['retrieved_document_ids']}\n"
                f"Relevant: {row['relevant_document_ids']}\n"
                f"Recall@1: {row['recall_at_1']:.3f}\n"
                f"Recall@3: {row['recall_at_3']:.3f}\n"
                f"Recall@5: {row['recall_at_5']:.3f}\n"
                f"Precision@5: {row['precision_at_5']:.3f}\n"
                f"RR: {row['reciprocal_rank']:.3f}\n"
                f"Latency: {row['latency_ms']:.2f} ms"
            )

        summary = report["summary"]

        self.stdout.write("\nSummary:")
        self.stdout.write(
            f"Recall@1: {summary['recall_at_1']:.3f}"
        )
        self.stdout.write(
            f"Recall@3: {summary['recall_at_3']:.3f}"
        )
        self.stdout.write(
            f"Recall@5: {summary['recall_at_5']:.3f}"
        )
        self.stdout.write(
            f"Precision@5: {summary['precision_at_5']:.3f}"
        )
        self.stdout.write(
            f"MRR: {summary['mrr']:.3f}"
        )
        self.stdout.write(
            f"Median retrieval latency: "
            f"{summary['median_latency_ms']:.2f} ms"
        )