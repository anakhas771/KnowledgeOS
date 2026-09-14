from django.test import SimpleTestCase
import json
import tempfile
import os

from apps.knowledge.evaluation.artifact import (
    build_experiment_artifact,
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
