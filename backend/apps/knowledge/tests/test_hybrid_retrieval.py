from django.test import SimpleTestCase

from apps.knowledge.services.hybrid import (
    _merge_candidates,
    _min_max_normalize,
)


class HybridRankingTestCase(SimpleTestCase):
    def test_min_max_normalization(self):
        self.assertEqual(
            _min_max_normalize([10.0, 20.0, 30.0]),
            [0.0, 0.5, 1.0],
        )

    def test_equal_scores_are_stable(self):
        self.assertEqual(
            _min_max_normalize([5.0, 5.0, 5.0]),
            [1.0, 1.0, 1.0],
        )

    def test_hybrid_fusion_combines_signals(self):
        semantic = [
            {
                "chunk_id": 1,
                "document_id": 10,
                "document_title": "Semantic",
                "content": "semantic",
                "score": 0.9,
            },
            {
                "chunk_id": 2,
                "document_id": 20,
                "document_title": "Other",
                "content": "other",
                "score": 0.2,
            },
        ]

        lexical = [
            {
                "chunk_id": 2,
                "document_id": 20,
                "document_title": "Other",
                "content": "other",
                "score": 1.0,
            },
            {
                "chunk_id": 1,
                "document_id": 10,
                "document_title": "Semantic",
                "content": "semantic",
                "score": 0.1,
            },
        ]

        ranked = _merge_candidates(
            semantic_results=semantic,
            lexical_results=lexical,
            semantic_weight=0.7,
            lexical_weight=0.3,
        )

        self.assertEqual(
            {result["chunk_id"] for result in ranked},
            {1, 2},
        )

        self.assertEqual(
            ranked[0]["chunk_id"],
            1,
        )

    def test_candidate_existing_in_both_sources_is_merged(self):
        semantic = [
            {
                "chunk_id": 1,
                "document_id": 10,
                "document_title": "Shared",
                "content": "shared",
                "score": 0.8,
            }
        ]

        lexical = [
            {
                "chunk_id": 1,
                "document_id": 10,
                "document_title": "Shared",
                "content": "shared",
                "score": 0.4,
            }
        ]

        ranked = _merge_candidates(
            semantic_results=semantic,
            lexical_results=lexical,
            semantic_weight=0.7,
            lexical_weight=0.3,
        )

        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0]["chunk_id"], 1)
        self.assertEqual(ranked[0]["semantic_score"], 0.8)
        self.assertEqual(ranked[0]["lexical_score"], 0.4)