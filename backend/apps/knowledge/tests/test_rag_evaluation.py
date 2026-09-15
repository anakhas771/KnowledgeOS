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

# Phase 8 regression: dataset expanded; count/balance checks
class RAGDatasetExpandedTestCase(SimpleTestCase):
    def test_case_count_20(self):
        from apps.knowledge.evaluation.rag_evaluation_dataset import RAG_EVALUATION_CASES
        self.assertEqual(len(RAG_EVALUATION_CASES), 20)

    def test_unique_ids(self):
        from apps.knowledge.evaluation.rag_evaluation_dataset import RAG_EVALUATION_CASES
        ids = [c.case_id for c in RAG_EVALUATION_CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_unanswerable_present(self):
        from apps.knowledge.evaluation.rag_evaluation_dataset import RAG_EVALUATION_CASES
        unans = [c for c in RAG_EVALUATION_CASES if c.unanswerable]
        self.assertGreaterEqual(len(unans), 3)

    def test_category_distribution(self):
        from apps.knowledge.evaluation.rag_evaluation_dataset import RAG_EVALUATION_CASES
        counts = {}
        for c in RAG_EVALUATION_CASES:
            counts[c.category] = counts.get(c.category, 0) + 1
        self.assertIn("direct", counts)
        self.assertIn("paraphrased", counts)
        self.assertIn("lexical", counts)
        self.assertIn("multi_relevant", counts)
        self.assertIn("hard_negative", counts)


# ---------------------------------------------------------------------------
# Phase 9 regression tests — forbidden-claim detection with negation/contrast
# ---------------------------------------------------------------------------

class RAGPhase9ForbiddenClaimRegressionTestCase(SimpleTestCase):
    """
    Focused tests for Phase 9 defect fixes:

    1.  Import compatibility  — check_forbidden_claims / check_abstention_behavior
    2.  Genuine assertion     → violation
    3.  Explicit negation     → no violation
    4.  Contrastive/separate  → no violation
    5.  rag_h01 wording       → no false positive
    6.  Unanswerable refusal  → no false positive
    7.  Unsupported claim in unanswerable answer → violation
    8.  Phase 7/8 existing behavior preserved
    """

    # ------------------------------------------------------------------ #
    # 1. Import compatibility                                              #
    # ------------------------------------------------------------------ #

    def test_import_check_forbidden_claims(self):
        """check_forbidden_claims must be importable (alias for enhanced)."""
        from apps.knowledge.evaluation.rag_evaluator import (
            check_forbidden_claims,
            check_forbidden_claims_enhanced,
        )
        self.assertIs(check_forbidden_claims, check_forbidden_claims_enhanced)

    def test_import_check_abstention_behavior(self):
        """check_abstention_behavior must be importable (alias for enhanced)."""
        from apps.knowledge.evaluation.rag_evaluator import (
            check_abstention_behavior,
            check_abstention_behavior_enhanced,
        )
        self.assertIs(check_abstention_behavior, check_abstention_behavior_enhanced)

    # ------------------------------------------------------------------ #
    # 2. Genuine forbidden assertion → violation                          #
    # ------------------------------------------------------------------ #

    def test_genuine_assertion_authentication_decides_role(self):
        """'Authentication determines the user's role.' must be a violation."""
        result = check_forbidden_claims(
            "Authentication determines the user's role when accessing APIs.",
            ("authentication decides role",),
        )
        self.assertFalse(result["passed"], msg="Genuine assertion must be a violation")
        self.assertGreater(len(result["violations"]), 0)

    def test_genuine_assertion_request_overrides_org(self):
        """'The request can override the organization.' must be a violation."""
        result = check_forbidden_claims(
            "The request body can override the organization for retrieval.",
            ("request can override organization",),
        )
        self.assertFalse(result["passed"], msg="Genuine assertion must be a violation")
        self.assertGreater(len(result["violations"]), 0)

    def test_genuine_assertion_exact_user_count(self):
        """Stating an exact user count must be a violation."""
        result = check_forbidden_claims(
            "There are exactly 42 active users in the system.",
            ("exactly 42 active users",),
        )
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["violations"]), 0)

    # ------------------------------------------------------------------ #
    # 3. Explicit negation → no violation                                 #
    # ------------------------------------------------------------------ #

    def test_explicit_negation_does_not_determine(self):
        """'Authentication does not determine the role.' must pass."""
        result = check_forbidden_claims(
            "Authentication does not determine the user's role; "
            "that is handled by the authorization layer.",
            ("authentication decides role",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_explicit_negation_does_not_decide(self):
        """'X does not decide Y' phrasing must pass."""
        result = check_forbidden_claims(
            "Authentication does not decide which role a user holds.",
            ("authentication decides role",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_explicit_negation_cannot_override(self):
        """'Request cannot override org' must pass."""
        result = check_forbidden_claims(
            "The request body cannot override the organization; "
            "the scope is always read from the authenticated user record.",
            ("request can override organization",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    # ------------------------------------------------------------------ #
    # 4. Contrastive/separating statements → no violation                 #
    # ------------------------------------------------------------------ #

    def test_contrastive_while_separation(self):
        """'X verifies identity, while Y evaluates role' must pass."""
        result = check_forbidden_claims(
            "Authentication verifies identity, while authorization evaluates "
            "the user's role and decides which actions are permitted.",
            ("authentication decides role",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_contrastive_separation_distinct(self):
        """'X is distinct from Y' must pass."""
        result = check_forbidden_claims(
            "Authentication is distinct from role assignment; "
            "roles are determined by the permission layer.",
            ("authentication decides role",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_contrastive_separation_separate_from(self):
        """'X is separate from Y' must pass."""
        result = check_forbidden_claims(
            "Identity verification is separate from role evaluation.",
            ("authentication decides role",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_contrastive_handles_partition(self):
        """'X handles identity; Y handles role' must pass."""
        result = check_forbidden_claims(
            "Authentication handles identity verification; "
            "role-based authorization handles access control.",
            ("authentication decides role",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_contrastive_not_for_phrasing(self):
        """'Authentication is not for deciding roles' must pass."""
        result = check_forbidden_claims(
            "Authentication is not for deciding roles; it only verifies identity.",
            ("authentication decides role",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    # ------------------------------------------------------------------ #
    # 5. rag_h01 exact live answer → no false positive                    #
    # ------------------------------------------------------------------ #

    def test_rag_h01_no_false_positive(self):
        """
        The exact rag_h01 live answer that was producing a false positive
        must now pass without a forbidden-claim violation.
        """
        answer = (
            "Role-based authorization determines a user's role when accessing "
            "protected APIs. This mechanism separates identity verification from "
            "permission checks and uses roles to determine which protected actions "
            "a user may perform."
        )
        result = check_forbidden_claims(
            answer,
            ("authentication decides role",),
        )
        self.assertTrue(
            result["passed"],
            msg=(
                "rag_h01 answer should NOT be a forbidden-claim violation. "
                f"Got violations: {result['violations']}"
            ),
        )

    # ------------------------------------------------------------------ #
    # 6. Unanswerable refusal mentioning the missing fact → no violation  #
    # ------------------------------------------------------------------ #

    def test_unanswerable_refusal_no_forbidden_violation(self):
        """
        An answer that refuses to state an exact number must not be a
        forbidden-claim violation even if it mentions 'exact' or 'users'.
        """
        result = check_forbidden_claims(
            "The knowledge base does not contain information about the exact "
            "number of active users. I cannot provide that figure.",
            ("Provides a specific user count", "exact number"),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    # ------------------------------------------------------------------ #
    # 7. Genuine unsupported claim in an 'unanswerable' answer → violation#
    # ------------------------------------------------------------------ #

    def test_genuine_claim_in_unanswerable_answer(self):
        """
        Even in a nominally unanswerable case, an answer that genuinely
        asserts the forbidden claim must still be flagged.

        The claim keywords ("authentication", "decides", "role") all appear
        in the assertive answer, and the answer uses no negation or contrastive
        language -- so the violation must be reported.
        """
        # Direct genuine assertion: "authentication decides role"
        # This is the same claim as rag_h01 but without contrastive context.
        result = check_forbidden_claims(
            "Authentication decides the user's role when accessing APIs.",
            ("authentication decides role",),
        )
        self.assertFalse(result["passed"])
        self.assertGreater(len(result["violations"]), 0)

    # ------------------------------------------------------------------ #
    # 8. Phase 7/8 behavior preserved                                     #
    # ------------------------------------------------------------------ #

    def test_phase7_unrelated_answer_passes(self):
        """Original Phase 7 test: unrelated answer must not be flagged."""
        result = check_forbidden_claims(
            "KnowledgeOS uses JWT authentication.",
            ("exactly 42 active users",),
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])

    def test_phase7_matching_claim_detected(self):
        """Original Phase 7 test: literal forbidden claim must be detected."""
        result = check_forbidden_claims(
            "There are exactly 42 active users.",
            ("exactly 42 active users",),
        )
        self.assertFalse(result["passed"])

    def test_phase8_evaluate_case_keys_present(self):
        """evaluate_case must still return all expected keys."""
        case = RAG_EVALUATION_CASES[0]
        result = evaluate_case(
            case,
            "KnowledgeOS is an enterprise knowledge intelligence platform "
            "providing semantic search and AI-assisted answers.",
            case.relevant_document_titles,
        )
        for key in ("passed", "expected_points_result", "forbidden_result",
                    "abstention_result", "source_alignment_result"):
            self.assertIn(key, result)

    def test_phase8_hard_negative_h01_dataset_entry(self):
        """rag_h01 dataset entry must have the expected forbidden claim."""
        from apps.knowledge.evaluation.rag_evaluation_dataset import RAG_EVALUATION_CASES
        h01 = next((c for c in RAG_EVALUATION_CASES if c.case_id == "rag_h01"), None)
        self.assertIsNotNone(h01)
        self.assertIn("authentication decides role", h01.forbidden_claims)
