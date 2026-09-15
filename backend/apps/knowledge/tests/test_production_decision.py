from django.test import SimpleTestCase

from apps.knowledge.evaluation.production_decision import (
    DECISION_MATRIX,
    PRODUCTION_CONFIG,
    DecisionStatus,
)


class ProductionDecisionConsistencyTestCase(SimpleTestCase):
    """
    Validates that the production decisions and configurations
    are consistent with the current production state.
    """

    def test_decision_matrix_coverage(self):
        """Ensure all required capabilities are covered in the decision matrix."""
        capabilities = [d.capability for d in DECISION_MATRIX]

        required = [
            "Semantic Baseline",
            "Lexical Retrieval",
            "Hybrid Retrieval",
            "RRF (Reciprocal Rank Fusion)",
            "Query-aware Reranking",
            "Candidate-pool Size",
            "Chunking Configuration",
            "Embedding Model (L6 vs L12)",
            "RAG Generation",
            "Abstention Behavior"
        ]
        
        for req in required:
            self.assertIn(req, capabilities, f"Missing decision for {req}")

    def test_l12_deferred(self):
        """Ensure the L12 embedding experiment is explicitly DEFERRED."""
        embedding_decision = next(
            (d for d in DECISION_MATRIX if "Embedding Model" in d.capability), None
        )
        self.assertIsNotNone(embedding_decision)
        self.assertEqual(
            embedding_decision.decision,
            DecisionStatus.DEFER,
            "L12 embedding model decision must be DEFER, not adopted."
        )

    def test_production_config_consistency(self):
        """Ensure production config dictates the correct verified baseline settings."""
        self.assertEqual(PRODUCTION_CONFIG["retrieval_strategy"], "semantic")
        self.assertEqual(PRODUCTION_CONFIG["embedding_model"], "all-MiniLM-L6-v2")
        self.assertEqual(PRODUCTION_CONFIG["vector_dimension"], 384)
        self.assertEqual(PRODUCTION_CONFIG["chunk_size"], 1000)
        self.assertEqual(PRODUCTION_CONFIG["chunk_overlap"], 150)
        self.assertFalse(PRODUCTION_CONFIG["reranker_active"])
        self.assertFalse(PRODUCTION_CONFIG["hybrid_active"])
        self.assertFalse(PRODUCTION_CONFIG["rrf_active"])
        self.assertEqual(PRODUCTION_CONFIG["generation_model"], "qwen3:4b-instruct-2507-q4_K_M")

