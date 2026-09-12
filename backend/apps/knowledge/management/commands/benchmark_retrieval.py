from django.core.management.base import BaseCommand

from apps.knowledge.evaluation.benchmark import (
    run_benchmark,
    run_hybrid_benchmark,
    run_lexical_benchmark,
    run_rrf_benchmark,
)


EVALUATION_ORG_SLUG = "knowledgeos-retrieval-evaluation"


class Command(BaseCommand):
    help = "Benchmark semantic, lexical, score-fusion, and RRF retrieval."

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
                f"\nCategory: {row['category']}\n"
                f"Query: {row['query']}\n"
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
            self.stdout.write(
                f"Median latency: "
                f"{metrics['median_latency_ms']:.2f} ms"
            )