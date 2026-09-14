"""
Phase 7 focused tests — RAG answer evaluation.

Covers dataset schema, deterministic checks (points, forbidden claims,
abstention, source alignment), and combined evaluate_case behavior.
Does NOT change production retrieval / generation behavior.
"""
from django.test import SimpleTestCase

from apps.knowledge.evaluation.rag_evaluation_dataset import (
    RAG_EVALUATION_CASES,
    get_cases,
    RAGEvaluationCase,
)
from apps.knowledge.evaluation.rag_evaluator import (
    check_answer_points,
    check_forbidden_claims,
    check_abstention_behavior,
    check_source_alignment,
    evaluate_case,
)


class RAGDatasetSchemaTestCase(SimpleTestCase):
    def test_cases_exist(self):
        self.assertGreater(len(RAG_EVALUATION_CASES), 0)

    def test_case_fields_present(self):
        case = RAG_EVALUATION_CASES[0]
        self.assertTrue(case.case_id)
        self.assertTrue(case.query)
        self.assertIn(case.category, ("direct", "paraphrased", "lexical", "multi_relevant", "hard_negative"))
        self.assertIn(case.answer_category, ("factual", "multi_source", "unanswerable", "groundedness"))

    def test_unanswerable_case_present(self):
        cases = [c for c in RAG_EVALUATION_CASES if c.unanswerable]
        self.assertTrue(len(cases) > 0, "At least one unanswerable case required for abstention evaluation")

    def test_filter_by_category(self):
        multi = get_cases("multi_relevant")
        self.assertTrue(all(c.category == "multi_relevant" for c in multi))
        direct = get_cases("direct")
        self.assertTrue(all(c.category == "direct" for c in direct))


class RAGDeterministicChecksTestCase(SimpleTestCase):
    def test_points_found_for_expected_text(self):
        result = check_answer_points(
            "KnowledgeOS provides semantic search and AI-assisted answers.",
            ("semantic search", "AI-assisted answers"),
        )
        self.assertTrue(result["found_points"])
        self.assertGreaterEqual(result["score"], 1.0)

    def test_points_missing_for_unrelated_text(self):
        result = check_answer_points(
            "The weather is sunny today.",
            ("semantic search",),
        )
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["found_points"], [])

    def test_forbidden_claim_detected(self):
        result = check_forbidden_claims(
            "There are exactly 42 active users.",
            ("exactly 42 active users",),
        )
        self.assertTrue(len(result["violations"]) > 0 or result["passed"] is False)

    def test_forbidden_claim_not_violated(self):
        result = check_forbidden_claims(
            "KnowledgeOS uses JWT authentication.",
            ("exactly 42 active users",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_abstention_detected_for_unanswerable(self):
        case = RAGEvaluationCase(
            case_id="test_abstain",
            query="How many users?",
            relevant_document_titles=(),
            category="direct",
            unanswerable=True,
        )
        result = check_abstention_behavior(
            "The available knowledge does not contain that information.",
            case,
        )
        self.assertTrue(result["expected_abstain"])
        self.assertTrue(result["detected_abstain"])
        self.assertTrue(result["passed"])

    def test_abstention_not_expected_for_answerable(self):
        case = RAGEvaluationCase(
            case_id="test_answerable",
            query="What is it?",
            relevant_document_titles=("Overview",),
            category="direct",
            unanswerable=False,
        )
        result = check_abstention_behavior("KnowledgeOS provides semantic search.", case)
        self.assertFalse(result["expected_abstain"])
        self.assertFalse(result["detected_abstain"])

    def test_source_alignment_records_mentions(self):
        result = check_source_alignment(
            "The Authentication and RBAC document explains JWT.",
            ("Authentication and RBAC", "Document Processing"),
        )
        self.assertIn("Authentication and RBAC", result["mentioned_in_answer"])
        self.assertGreaterEqual(result["citation_coverage"], 0.5)

    def test_evaluate_case_combined_result(self):
        case = RAG_EVALUATION_CASES[0]
        result = evaluate_case(
            case,
            "KnowledgeOS is an enterprise knowledge intelligence platform providing semantic search.",
            case.relevant_document_titles,
        )
        self.assertIn("passed", result)
        self.assertIn("expected_points_result", result)
        self.assertIn("source_alignment_result", result)

    def test_empty_answer_handles_cleanly(self):
        case = RAG_EVALUATION_CASES[0]
        result = evaluate_case(case, "", case.relevant_document_titles)
        self.assertIn("passed", result)
        self.assertEqual(result["expected_points_result"]["score"], 0.0)

    def test_missing_sources_handles_cleanly(self):
        case = RAG_EVALUATION_CASES[0]
        result = evaluate_case(case, "KnowledgeOS provides semantic search.", ())
        self.assertIn("source_alignment_result", result)
        self.assertEqual(result["source_alignment_result"]["citation_coverage"], 1.0)

    def test_malformed_evaluation_no_crash(self):
        case = RAGEvaluationCase(
            case_id="malformed",
            query="",
            relevant_document_titles=(),
            category="direct",
        )
        result = evaluate_case(case, "", ())
        self.assertIn("passed", result)
