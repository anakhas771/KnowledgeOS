"""
Enhanced RAG evaluation tests for the fixed evaluator.

These tests verify that the enhanced forbidden claim detection and abstention
logic work correctly, specifically addressing the false positives identified
in the Phase 9 benchmark.
"""
from django.test import SimpleTestCase
from apps.knowledge.evaluation.rag_evaluator import (
    check_forbidden_claims_enhanced,
    check_abstention_behavior_enhanced,
    evaluate_case,
)
from apps.knowledge.evaluation.rag_evaluation_dataset import (
    RAGEvaluationCase,
    RAG_EVALUATION_CASES,
)


class EnhancedForbiddenClaimsTestCase(SimpleTestCase):
    """Test enhanced forbidden claims detection."""

    def test_forbidden_phrase_asserted_violation(self):
        """Test that forbidden phrases are detected when truly asserted."""
        case = RAGEvaluationCase(
            case_id="test_violation",
            query="Test query",
            relevant_document_titles=("Test Doc",),
            category="direct",
            forbidden_claims=("request can override organization",),
        )

        # When the forbidden phrase is asserted, it should be a violation
        answer = "A request can override the organization. This is the rule."
        result = check_forbidden_claims_enhanced(answer, case.forbidden_claims)
        self.assertTrue(result["violations"])  # Should have violation
        self.assertFalse(result["passed"])   # Should fail

    def test_forbidden_phrase_explicitly_negated_no_violation(self):
        """Test that forbidden phrases are NOT violations when explicitly negated."""
        case = RAGEvaluationCase(
            case_id="test_no_violation",
            query="Test query",
            relevant_document_titles=("Test Doc",),
            category="direct",
            forbidden_claims=("request can override organization",),
        )

        # When the forbidden phrase is explicitly negated, should NOT be violation
        answer = "A request cannot override the organization. It is against policy."
        result = check_forbidden_claims_enhanced(answer, case.forbidden_claims)
        self.assertEqual(result["violations"], [])  # Should have no violations
        self.assertTrue(result["passed"])          # Should pass

    def test_forbidden_phrase_denied_with_explanatory_context_no_violation(self):
        """Test that forbidden phrases are NOT violations when explained as not true."""
        case = RAGEvaluationCase(
            case_id="test_explanatory",
            query="Test query",
            relevant_document_titles=("Test Doc",),
            category="direct",
            forbidden_claims=("authentication decides role",),
        )

        # When explained as not true, should NOT be violation
        answer = "Authentication does not decide the role; permission checks evaluate the role."
        result = check_forbidden_claims_enhanced(answer, case.forbidden_claims)
        self.assertEqual(result["violations"], [])  # Should have no violations
        self.assertTrue(result["passed"])          # Should pass

    def test_unanswerable_answer_mentioning_missing_fact_no_violation(self):
        """Test that unanswerable answers mentioning missing facts don't violate forbidden claims."""
        case = RAGEvaluationCase(
            case_id="test_unanswerable",
            query="Test query",
            relevant_document_titles=(),
            category="direct",
            forbidden_claims=("exact number",),
            unanswerable=True,
        )

        # When answer says context doesn't contain the exact number, should NOT be violation
        answer = "The context does not contain the exact number. I cannot provide this information."
        result = check_forbidden_claims_enhanced(answer, case.forbidden_claims)
        self.assertEqual(result["violations"], [])  # Should have no violations
        self.assertTrue(result["passed"])          # Should pass

    def test_genuine_unsupported_claim_violation(self):
        """Test that genuinely unsupported claims in unanswerable answers ARE violations."""
        case = RAGEvaluationCase(
            case_id="test_genuine_violation",
            query="Test query",
            relevant_document_titles=(),
            category="direct",
            forbidden_claims=("exact number",),
            unanswerable=True,
        )

        # When unanswerable answer still provides the forbidden claim, should be violation
        answer = "The exact number is 42. However, this information is not in the context."
        result = check_forbidden_claims_enhanced(answer, case.forbidden_claims)
        self.assertTrue(result["violations"])  # Should have violation
        self.assertFalse(result["passed"])   # Should fail

    def test_hard_negative_negation_no_violation(self):
        """Test that hard-negative cases with explicit negation don't trigger false violations."""
        case = RAGEvaluationCase(
            case_id="test_hard_negative",
            query="Can a user widen access?",
            relevant_document_titles=("Tenant Isolation",),
            category="hard_negative",
            forbidden_claims=("request can override organization",),
        )

        # When the answer explicitly states the request CANNOT override organization
        answer = "No, a user cannot widen access by providing a different organization identifier. The organization context is determined by the authenticated user."
        result = check_forbidden_claims_enhanced(answer, case.forbidden_claims)
        self.assertEqual(result["violations"], [])  # Should have no violations
        self.assertTrue(result["passed"])          # Should pass

    def test_various_negation_patterns(self):
        """Test various negation patterns that should prevent violations."""
        test_cases = [
            # (answer, should_have_violation, description)
            ("The request cannot override organization", False, "cannot keyword"),
            ("A request can not override organization", False, "can not keyword"),
            ("Request does not override organization", False, "does not keyword"),
            ("Authentication does not decide role", False, "does not with different phrase"),
            ("The fact that authentication decides role is false", False, "is false negation"),
            ("There is no case where request overrides organization", False, "there is no negation"),
            ("I cannot provide the authentication decision", False, "cannot provide negation"),
        ]

        for answer, should_violate, description in test_cases:
            case = RAGEvaluationCase(
                case_id=f"test_{description}",
                query="Test query",
                relevant_document_titles=("Test Doc",),
                category="direct",
                forbidden_claims=("request can override organization", "authentication decides role"),
            )

            result = check_forbidden_claims_enhanced(answer, case.forbidden_claims)
            has_violation = bool(result["violations"])

            if should_violate:
                self.assertTrue(has_violation, f"Should have violation for: {description}")
            else:
                self.assertFalse(has_violation, f"Should NOT have violation for: {description}")


class EnhancedAbstentionTestCase(SimpleTestCase):
    """Test enhanced abstention detection."""

    def test_unanswerable_case_with_proper_abstention(self):
        """Test that unanswerable cases with proper abstention pass."""
        case = RAGEvaluationCase(
            case_id="test_unanswerable_pass",
            query="What is the exact number?",
            relevant_document_titles=(),
            category="direct",
            unanswerable=True,
        )

        answer = "The context does not contain the exact number. I cannot provide this information."
        result = check_abstention_behavior_enhanced(answer, case)

        self.assertTrue(result["expected_abstain"])  # Should expect abstention
        self.assertTrue(result["detected_abstain"])  # Should detect proper abstention
        self.assertTrue(result["passed"])            # Should pass

    def test_unanswerable_case_with_improper_abstention(self):
        """Test that unanswerable cases with improper abstention fail."""
        case = RAGEvaluationCase(
            case_id="test_unanswerable_fail",
            query="What is the exact number?",
            relevant_document_titles=(),
            category="direct",
            unanswerable=True,
        )

        answer = "The exact number is 42."  # Claims the number despite being unanswerable
        result = check_abstention_behavior_enhanced(answer, case)

        self.assertTrue(result["expected_abstain"])  # Should expect abstention
        self.assertFalse(result["detected_abstain"]) # Should NOT detect proper abstention
        self.assertFalse(result["passed"])           # Should fail

    def test_answerable_case_never_expects_abstention(self):
        """Test that answerable cases never expect abstention."""
        case = RAGEvaluationCase(
            case_id="test_answerable",
            query="How does authentication work?",
            relevant_document_titles=("Auth Doc",),
            category="direct",
            unanswerable=False,
        )

        answer = "Authentication uses JWT tokens."  # Normal answer
        result = check_abstention_behavior_enhanced(answer, case)

        self.assertFalse(result["expected_abstain"])  # Should not expect abstention
        self.assertFalse(result["detected_abstain"]) # Should not detect abstention
        self.assertTrue(result.get("passed", True))   # Should pass (default)

    def test_comprehensive_abstention_patterns(self):
        """Test various patterns that indicate proper abstention."""
        test_cases = [
            # (answer, should_detect_abstention, description)
            ("I don't know the exact number", True, "don't know"),
            ("I do not know", True, "do not know"),
            ("The context does not contain information", True, "does not contain"),
            ("I cannot determine this", True, "cannot determine"),
            ("Not enough information is available", True, "not enough information"),
            ("There is no evidence", True, "no evidence"),
            ("Insufficient data", True, "insufficient"),
            ("I cannot provide an answer", True, "cannot provide"),
            ("I'm not able to answer", True, "not able to answer"),
            ("The exact number is 42", False, "provides forbidden claim"),
            ("Here is the exact number: 42", False, "provides number"),
            ("This information is not available", True, "not available"),
        ]

        for answer, should_detect, description in test_cases:
            case = RAGEvaluationCase(
                case_id=f"abstention_{description}",
                query="Test query",
                relevant_document_titles=(),
                category="direct",
                unanswerable=True,
                forbidden_claims=("exact number",) if "exact number" in description.lower() else (),
            )

            result = check_abstention_behavior_enhanced(answer, case)
            detected = result["detected_abstain"]

            if should_detect:
                self.assertTrue(detected, f"Should detect abstention for: {description}")
            else:
                self.assertFalse(detected, f"Should NOT detect abstention for: {description}")


class EndToEndEnhancedEvaluationTestCase(SimpleTestCase):
    """Test end-to-end evaluation with the enhanced evaluator."""

    def test_original_false_positive_cases_now_pass(self):
        """Test that the original false positive cases from Phase 9 now pass."""

        # Test case 1: rag_u01 original false positive
        rag_u01 = next(c for c in RAG_EVALUATION_CASES if c.case_id == "rag_u01")
        u01_answer = "The provided context does not contain the exact number. Therefore, I cannot answer this question."

        # Using the actual evaluate_case function which now uses enhanced checks
        result = evaluate_case(rag_u01, u01_answer, ())

        # Previously this would have failed due to false positive on "exact number"
        # Now it should pass because "cannot answer" is detected as proper abstention
        self.assertTrue(result["passed"], f"rag_u01 should pass with enhanced evaluator: {result}")

    def test_rag_u02_false_positive_fixed(self):
        """Test that rag_u02 false positive is fixed."""
        rag_u02 = next(c for c in RAG_EVALUATION_CASES if c.case_id == "rag_u02")
        u02_answer = "The provided context does not contain information about specific employees or specific dates. Therefore, I cannot answer this question."

        result = evaluate_case(rag_u02, u02_answer, ())

        # Previously this would have failed due to false positives on "specific date" and "specific employee registered"
        # Now it should pass because "cannot answer" is detected as proper abstention
        self.assertTrue(result["passed"], f"rag_u02 should pass with enhanced evaluator: {result}")

    def test_rag_h02_hard_negative_fixed(self):
        """Test that rag_h02 hard negative false positive is fixed."""
        rag_h02 = next(c for c in RAG_EVALUATION_CASES if c.case_id == "rag_h02")
        h02_answer = "No, a user cannot widen access by providing a different organization identifier. The organization context is determined by the authenticated user, not by the request body."

        result = evaluate_case(rag_h02, h02_answer, ("Tenant Isolation", "API Security"))

        # Previously this would have failed with false positive on "request can override organization"
        # Now it should pass because "cannot" is detected as negation
        self.assertTrue(result["passed"], f"rag_h02 should pass with enhanced evaluator: {result}")

    def test_category_aggregation_includes_unanswerable(self):
        """Test that unanswerable cases are properly categorized."""
        # Count unanswerable cases by their answer_category
        unanswerable_cases = [c for c in RAG_EVALUATION_CASES if c.answer_category == "unanswerable"]

        self.assertEqual(len(unanswerable_cases), 3, "Should be exactly 3 unanswerable cases")

        # Verify they have unanswerable=True
        for case in unanswerable_cases:
            self.assertTrue(case.unanswerable, f"{case.case_id} should have unanswerable=True")
            self.assertIn(case.case_id, ["rag_u01", "rag_u02", "rag_u03"],
                         f"Unanswerable case {case.case_id} should be one of the expected cases")