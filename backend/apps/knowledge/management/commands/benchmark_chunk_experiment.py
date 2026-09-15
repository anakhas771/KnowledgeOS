from django.core.management.base import BaseCommand

from apps.knowledge.evaluation.chunking import (
    run_chunking_experiment,
    run_attribution_matrix,
    chunk_statistics,
)
from apps.knowledge.evaluation.artifact import build_pool_sweep_artifact


class Command(BaseCommand):
    help = (
        "Run the evaluation-only chunking comparison. Produces a comparison "
        "table (not a production-retrieval change) and an optional artifact."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--configs",
            nargs="+",
            type=str,
            default=None,
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
        )
        parser.add_argument(
            "--ranking",
            type=str,
            default="semantic",
            choices=("semantic", "hybrid", "rrf"),
            help="Fixed ranking strategy for the comparison.",
        )
        parser.add_argument(
            "--attribution",
            action="store_true",
            help="Run a chunking x ranking attribution matrix.",
        )
        parser.add_argument(
            "--artifact",
            type=str,
            default=None,
            help="Write a chunking comparison artifact.",
        )

    def handle(self, *args, **options):
        configs = options.get("configs")
        limit = options.get("limit")
        ranking = options.get("ranking")

        # 1. Structural statistics for every configuration (before seeding,
        #    since these come from chunk_text alone). These are the numbers that
        #    explain whether retrieval differences are structural.
        self.stdout.write("\n=== Chunk statistics (chunk_text only) ===")
        for name in (configs or None):
            from apps.knowledge.evaluation.chunking import (
                CHUNKING_CONFIGS,
                CONFIGS_BY_NAME,
                chunk_statistics,
            )
            cfg = (
                CONFIGS_BY_NAME[name]
                if name
                else CHUNKING_CONFIGS[int(configs[0]) - 1]
            )
            stats = chunk_statistics(cfg)
            # Print header row for visibility; full print handled below

        # For simplicity and reliability, print the full statistics per config.
        if configs is None:
            names = [c.name for c in __import__(
                "apps.knowledge.evaluation.chunking", fromlist=[""]
            ).CHUNKING_CONFIGS]
        else:
            names = list(configs)

        self.stdout.write(
            f"{'Config':<20} {'Chunks':>6} "
            f"{'Chunks/doc':>11} {'Mid-word%':>10} "
            f"{'Mid-sent%':>11}"
        )
        for name in names:
            cfg = __import__(
                "apps.knowledge.evaluation.chunking", fromlist=[""]
            ).get_config(name)
            stats = chunk_statistics(cfg)
            self.stdout.write(
                f"{name:<20} "
                f"{stats['total_chunks']:>6} "
                f"{stats['mean_chunks_per_document']:>11.2f} "
                f"{stats['boundary_integrity']['ends_mid_word_ratio']:>10.2%} "
                f"{stats['boundary_integrity']['ends_mid_sentence_ratio']:>11.2%}"
            )

        # 2. Benchmark comparison (isolated corpora required; these must have
        #    been seeded by ``seed_chunking_experiment``).
        self.stdout.write(
            "\n=== Benchmark comparison (ranking fixed: " + ranking + ") ==="
        )
        self.stdout.write(
            "This table isolates the chunking effect; ranking is held constant."
        )

        results = run_chunking_experiment(
            config_names=names,
            limit=limit,
            strategy=ranking,
        )

        header_line = (
            f"{'Config':<18} | R@1 | R@3 | R@5 | P@5 | MRR | Latency(ms)"
        )
        self.stdout.write(header_line)
        self.stdout.write("-" * len(header_line))

        for name in sorted(results):
            summary = results[name]["summary"]
            self.stdout.write(
                f"{name:<18} | "
                f"{summary['recall_at_1']:>5.3f} | "
                f"{summary['recall_at_3']:>5.3f} | "
                f"{summary['recall_at_5']:>5.3f} | "
                f"{summary['precision_at_5']:>5.3f} | "
                f"{summary['mrr']:>5.3f} | "
                f"{summary['median_latency_ms']:>10.1f}"
            )

        # 3. Category comparison (single relevant vs multi relevant)
        self.stdout.write(
            "\n=== Analysis: did retrieval improve because of better chunks? ==="
        )
        self.stdout.write(
            "Compare chunk statistics with benchmark results. If chunk counts "
            "change significantly and quality improves (same ranking), "
            "the improvement is structural, not a ranking strategy effect."
        )

        # 4. Attribution matrix (optional)
        if options.get("attribution"):
            self.stdout.write(
                "\n=== Chunking x Ranking attribution matrix (summary) ==="
            )
            matrix = run_attribution_matrix(
                config_names=names,
                strategies=["semantic", "hybrid", "rrf"],
                limit=limit,
            )

            for (cfg_name, strategy) in sorted(matrix):
                r = matrix[(cfg_name, strategy)]
                self.stdout.write(
                    f"{cfg_name:<15} x {strategy:<6} | "
                    f"R@1={r['summary']['recall_at_1']:>5.3f} "
                    f"R@3={r['summary']['recall_at_3']:>5.3f} "
                    f"R@5={r['summary']['recall_at_5']:>5.3f}"
                )

        # 5. Boundary observation
        self.stdout.write(
            "\n=== Semantic-boundary observations ==="
        )
        for name in names:
            cfg = (
                __import__(
                    "apps.knowledge.evaluation.chunking",
                    fromlist=[""],
                ).get_config(name)
            )
            stats = chunk_statistics(cfg)
            self.stdout.write(
                f"{name:<18} | chunks={stats['total_chunks']:>3} | "
                f"ends-mid-word={stats['boundary_integrity']['ends_mid_word_ratio']:>6.1%} | "
                f"ends-mid-sentence={stats['boundary_integrity']['ends_mid_sentence_ratio']:>6.1%}"
            )

        # 6. Artifact
        if options.get("artifact"):
            artifact_path = options.get("artifact")
            # Use the pool sweep artifact builder; it clearly identifies every
            # measurement with benchmark_id, pool_size equivalent (config),
            # final_K, overall/category metrics.
            artifact = build_pool_sweep_artifact(
                benchmark_id="chunking-comparison",
                strategy=f"chunking({ranking})",
                reports_by_pool={
                    name: {
                        "summary": results[name]["summary"],
                        "by_category": results[name]["by_category"],
                        "configuration": results[name]["configuration"],
                        "cases": results[name].get("cases", []),
                    }
                    for name in results
                },
                final_k=limit,
            )

            from apps.knowledge.evaluation.artifact import (
                write_artifact_atomic,
            )

            write_artifact_atomic(artifact, artifact_path)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nChunking comparison artifact written to {artifact_path}"
                )
            )

        # 7. Recommendation (evidence-based, no definitive claims)
        self.stdout.write(
            "\n=== Recommendation ==="
        )
        self.stdout.write(
            "This comparison isolates chunking effect (ranking held fixed) and "
            "supports evaluating whether a change improves retrieval because of "
            "better chunks or because of a different ranking strategy. No claim is "
            "made that any one configuration is definitively optimal; results "
            "depend on the evaluation set size and query distribution."
        )
