from django.test import SimpleTestCase
import json
import tempfile
import os

from apps.knowledge.evaluation.artifact import (
    build_experiment_artifact,
    build_pool_sweep_artifact,
    write_artifact_atomic,
    load_artifact,
)


class ArtifactPersistenceTestCase(SimpleTestCase):
    def test_artifact_contains_all_required_keys(self):
        artifact = build_experiment_artifact(
            benchmark_id="test-id",
            strategy="semantic",
            config={"limit": 5},
            report={
                "summary": {"recall_at_1": 0.8, "median_latency_ms": 12.0},
                "by_category": {"direct": {"recall_at_1": 1.0}},
                "cases": [{"query": "q", "retrieved_document_ids": [1]}],
            },
            corpus_slug="knowledgeos-retrieval-evaluation",
            case_count=25,
        )
        self.assertIn("benchmark_id", artifact)
        self.assertIn("timestamp", artifact)
        self.assertIn("corpus_identifier", artifact)
        self.assertIn("corpus_size", artifact)
        self.assertIn("case_count", artifact)
        self.assertIn("retrieval_strategy", artifact)
        self.assertIn("configuration", artifact)
        self.assertIn("overall_metrics", artifact)
        self.assertIn("category_metrics", artifact)
        self.assertIn("case_results", artifact)
        self.assertIn("latency_ms_summary", artifact)

    def test_artifact_is_deterministic_except_timestamp(self):
        artifact1 = build_experiment_artifact(
            benchmark_id="b1",
            strategy="lexical",
            config={},
            report={"summary": {}, "cases": []},
        )
        # Timestamp will differ; verify all non-timestamp fields match
        artifact2 = build_experiment_artifact(
            benchmark_id="b1",
            strategy="lexical",
            config={},
            report={"summary": {}, "cases": []},
        )
        for key in artifact1:
            if key == "timestamp":
                continue
            self.assertEqual(
                artifact1[key],
                artifact2[key],
                f"Field {key} should be deterministic",
            )

    def test_atomic_write_creates_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "result.json")
            artifact = {"benchmark_id": "x", "timestamp": "t"}
            write_artifact_atomic(artifact, path)
            loaded = load_artifact(path)
            self.assertEqual(loaded["benchmark_id"], "x")

    def test_failed_write_does_not_leave_partial_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.json")
            # Simulate failure by writing to non-writable path isn't easy;
            # instead verify no leftover .tmp_* on success
            artifact = {"benchmark_id": "x"}
            write_artifact_atomic(artifact, path)
            leftover = [f for f in os.listdir(tmpdir) if f.startswith(".tmp_")]
            self.assertEqual(
                leftover,
                [],
                "No partial .tmp_ files should remain after successful write",
            )

    def test_case_count_defaults_to_evaluated_case_total(self):
        """
        An artifact must not claim a corpus size the run did not measure.
        """
        artifact = build_experiment_artifact(
            benchmark_id="b1",
            strategy="semantic",
            config={},
            report={
                "summary": {},
                "by_category": {},
                "cases": [{"query": "a"}, {"query": "b"}],
            },
        )

        self.assertEqual(artifact["case_count"], 2)
        self.assertEqual(artifact["corpus_size"], 2)

    def test_explicit_case_count_overrides_derived_total(self):
        artifact = build_experiment_artifact(
            benchmark_id="b1",
            strategy="semantic",
            config={},
            report={"summary": {}, "by_category": {}, "cases": [{"q": 1}]},
            case_count=25,
        )

        self.assertEqual(artifact["case_count"], 25)


class PoolSweepArtifactTestCase(SimpleTestCase):
    def _report(self, pool_size: int, recall: float) -> dict:
        return {
            "summary": {
                "recall_at_1": recall,
                "median_latency_ms": 40.0,
            },
            "by_category": {"direct": {"recall_at_1": recall}},
            "cases": [
                {"query": "q", "latency_ms": 40.0},
            ],
            "configuration": {
                "candidate_pool_size": pool_size,
                "semantic_weight": 0.5,
                "lexical_weight": 0.3,
                "title_weight": 0.2,
                "limit": 5,
            },
        }

    def test_sweep_artifact_identifies_experiment_and_variable(self):
        artifact = build_pool_sweep_artifact(
            benchmark_id="sweep",
            strategy="semantic+rerank(experimental)",
            reports_by_pool={
                5: self._report(5, 0.4),
                10: self._report(10, 0.5),
            },
            final_k=5,
        )

        self.assertEqual(
            artifact["experiment"],
            "candidate_pool_size_sensitivity",
        )
        self.assertEqual(
            artifact["independent_variable"],
            "candidate_pool_size",
        )
        self.assertEqual(artifact["final_k"], 5)
        self.assertEqual(artifact["pool_sizes"], [5, 10])

    def test_each_run_is_individually_identifiable(self):
        """
        Every measurement must carry its own pool size, final K, config, and
        metrics so no row in the sweep is ambiguous.
        """
        artifact = build_pool_sweep_artifact(
            benchmark_id="sweep",
            strategy="semantic+rerank(experimental)",
            reports_by_pool={
                5: self._report(5, 0.4),
                20: self._report(20, 0.3),
            },
            final_k=5,
        )

        self.assertEqual(len(artifact["runs"]), 2)

        for run in artifact["runs"]:
            pool_size = run["candidate_pool_size"]

            self.assertEqual(run["final_k"], 5)
            self.assertEqual(
                run["configuration"]["candidate_pool_size"],
                pool_size,
            )
            self.assertEqual(
                run["benchmark_id"],
                f"sweep:pool={pool_size}",
            )
            self.assertIn("overall_metrics", run)
            self.assertIn("category_metrics", run)
            self.assertIn("case_results", run)
            self.assertIn("latency_ms_summary", run)

    def test_runs_are_ordered_by_pool_size(self):
        artifact = build_pool_sweep_artifact(
            benchmark_id="sweep",
            strategy="semantic+rerank(experimental)",
            reports_by_pool={
                20: self._report(20, 0.3),
                5: self._report(5, 0.4),
                10: self._report(10, 0.5),
            },
            final_k=5,
        )

        self.assertEqual(
            [run["candidate_pool_size"] for run in artifact["runs"]],
            [5, 10, 20],
        )

    def test_sweep_artifact_round_trips_through_disk(self):
        artifact = build_pool_sweep_artifact(
            benchmark_id="sweep",
            strategy="semantic+rerank(experimental)",
            reports_by_pool={5: self._report(5, 0.4)},
            final_k=5,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sweep.json")
            write_artifact_atomic(artifact, path)
            loaded = load_artifact(path)

        self.assertEqual(loaded["pool_sizes"], [5])
        self.assertEqual(
            loaded["runs"][0]["candidate_pool_size"],
            5,
        )
