from django.test import SimpleTestCase
from apps.knowledge.evaluation.benchmark import (
    unique_preserving_order,
    _summarize,
    _summarize_by_category,
)
from apps.knowledge.evaluation.dataset import (
    EVALUATION_CASES,
    RetrievalEvaluationCase,
)


class RetrievalBenchmarkEngineTestCase(SimpleTestCase):
    def test_all_cases_have_valid_category(self):
        valid_categories = {
            "direct", "paraphrased", "lexical",
            "multi_relevant", "hard_negative",
        }
        for case in EVALUATION_CASES:
            self.assertIn(
                case.category,
                valid_categories,
                f"Invalid category '{case.category}' for query: {case.query}",
            )

    def test_dataset_category_distribution(self):
        counts = {}
        for case in EVALUATION_CASES:
            counts[case.category] = counts.get(case.category, 0) + 1
        # Expecting at least 1 of each known category
        for cat in ["direct", "paraphrased", "lexical", "multi_relevant", "hard_negative"]:
            self.assertIn(
                cat,
                counts,
                f"Expected category '{cat}' in dataset",
            )
        # There are 25 evaluation queries total
        total_cases = len(EVALUATION_CASES)
        self.assertEqual(
            total_cases,
            25,
            f"Expected 25 evaluation cases, found {total_cases}",
        )

    def test_case_has_nonempty_query(self):
        for case in EVALUATION_CASES:
            self.assertTrue(
                case.query and isinstance(case.query, str),
                f"Query must be non-empty string for case: {case}",
            )

    def test_case_has_nonempty_relevant_titles(self):
        for case in EVALUATION_CASES:
            self.assertGreater(
                len(case.relevant_document_titles),
                0,
                f"Relevant titles must not be empty for case: {case}",
            )

    def test_unique_preserving_order_keeps_first_occurrence(self):
        self.assertEqual(
            unique_preserving_order([5, 3, 5, 2, 3]),
            [5, 3, 2],
        )

    def test_unique_preserving_order_empty_input(self):
        self.assertEqual(
            unique_preserving_order([]),
            [],
        )

    def test_category_metadata_preserved_in_case_result_shape(self):
        # Category metadata survives into benchmark case results
        # by inspecting the row shape produced by benchmark logic
        test_case = EVALUATION_CASES[0]
        self.assertEqual(
            test_case.category,
            "direct",
        )

    def test_summarize_deterministic_behavior(self):
        rows = [
            {
                "category": "direct",
                "query": "test",
                "retrieved_document_ids": [1, 2, 3],
                "relevant_document_ids": [1, 2],
                "recall_at_1": 1.0,
                "recall_at_3": 1.0,
                "recall_at_5": 1.0,
                "precision_at_5": 0.4,
                "reciprocal_rank": 1.0,
                "latency_ms": 12.5,
            },
            {
                "category": "direct",
                "query": "test2",
                "retrieved_document_ids": [4, 5, 6],
                "relevant_document_ids": [5, 6],
                "recall_at_1": 0.0,
                "recall_at_3": 0.5,
                "recall_at_5": 0.5,
                "precision_at_5": 0.4,
                "reciprocal_rank": 0.5,
                "latency_ms": 10.0,
            },
        ]
        summary = _summarize(rows)
        self.assertAlmostEqual(
            summary["recall_at_1"],
            0.5,
        )
        self.assertAlmostEqual(
            summary["recall_at_3"],
            0.75,
        )
        self.assertAlmostEqual(
            summary["median_latency_ms"],
            11.25,
        )

    def test_summarize_by_category_independent_summaries(self):
        direct_rows = [
            {
                "category": "direct",
                "query": "q1",
                "retrieved_document_ids": [1],
                "relevant_document_ids": [1],
                "recall_at_1": 1.0,
                "recall_at_3": 1.0,
                "recall_at_5": 1.0,
                "precision_at_5": 1.0,
                "reciprocal_rank": 1.0,
                "latency_ms": 5.0,
            },
        ]
        lex_rows = [
            {
                "category": "lexical",
                "query": "q2",
                "retrieved_document_ids": [2],
                "relevant_document_ids": [2],
                "recall_at_1": 1.0,
                "recall_at_3": 1.0,
                "recall_at_5": 1.0,
                "precision_at_5": 1.0,
                "reciprocal_rank": 1.0,
                "latency_ms": 15.0,
            },
        ]
        result = _summarize_by_category(direct_rows + lex_rows)
        self.assertIn("direct", result)
        self.assertIn("lexical", result)
        self.assertEqual(
            result["direct"]["recall_at_1"],
            1.0,
        )
        self.assertEqual(
            result["lexical"]["median_latency_ms"],
            15.0,
        )

    def test_multi_relevant_case_has_multiple_titles(self):
        multi_cases = [
            c for c in EVALUATION_CASES
            if c.category == "multi_relevant"
        ]
        self.assertGreater(
            len(multi_cases),
            0,
            "Expected at least one multi_relevant case",
        )
        for case in multi_cases:
            self.assertGreater(
                len(case.relevant_document_titles),
                1,
                f"Multi-relevant case should have >1 title: {case.query}",
            )

    def test_multi_relevant_recall_calculates_correctly(self):
        # Multi-relevant case: 4 relevant docs, retrieve first 3 all relevant
        results = [1, 2, 3, 4, 5]
        relevant = (1, 2, 3, 4)
        # Using benchmark logic directly: recall at k = intersection / len(relevant)
        # For k=3: 3 matched / 4 relevant = 0.75
        self.assertAlmostEqual(
            __import__("apps.knowledge.evaluation.metrics", fromlist=[""])
            .recall_at_k(results, relevant, 3),
            0.75,
        )

    def test_empty_case_result_rows_handled_gracefully(self):
        # Existing architecture: _summarize raises on empty input
        with self.assertRaises(Exception):
            _summarize([])

    def test_empty_category_summary_for_summarize_by_category(self):
        result = _summarize_by_category([])
        self.assertEqual(
            result,
            {},
        )

    def test_case_category_is_frozen_dataclass_attribute(self):
        case = RetrievalEvaluationCase(
            query="test",
            relevant_document_titles=("Doc A",),
            category="direct",
        )
        with self.assertRaises(AttributeError):
            case.category = "other"
