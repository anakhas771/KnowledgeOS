from django.test import SimpleTestCase

from apps.knowledge.services.rrf import _fuse_rankings


class ReciprocalRankFusionTestCase(SimpleTestCase):
    def test_shared_top_rank_gets_strongest_fusion_score(self):
        semantic = [
            {
                "chunk_id": 1,
                "document_id": 10,
                "document_title": "Shared",
                "content": "shared",
                "score": 0.9,
            },
            {
                "chunk_id": 2,
                "document_id": 20,
                "document_title": "Semantic",
                "content": "semantic",
                "score": 0.8,
            },
        ]

        lexical = [
            {
                "chunk_id": 1,
                "document_id": 10,
                "document_title": "Shared",
                "content": "shared",
                "score": 0.5,
            },
            {
                "chunk_id": 3,
                "document_id": 30,
                "document_title": "Lexical",
                "content": "lexical",
                "score": 0.4,
            },
        ]

        ranked = _fuse_rankings(
            semantic,
            lexical,
            k=60,
        )

        self.assertEqual(
            ranked[0]["chunk_id"],
            1,
        )

    def test_rank_positions_are_used_not_raw_scores(self):
        semantic = [
            {
                "chunk_id": 1,
                "document_id": 10,
                "document_title": "A",
                "content": "a",
                "score": 0.99,
            },
            {
                "chunk_id": 2,
                "document_id": 20,
                "document_title": "B",
                "content": "b",
                "score": 0.98,
            },
        ]

        lexical = [
            {
                "chunk_id": 2,
                "document_id": 20,
                "document_title": "B",
                "content": "b",
                "score": 1.0,
            },
            {
                "chunk_id": 3,
                "document_id": 30,
                "document_title": "C",
                "content": "c",
                "score": 0.1,
            },
        ]

        ranked = _fuse_rankings(
            semantic,
            lexical,
            k=60,
        )

        self.assertEqual(
            ranked[0]["chunk_id"],
            2,
        )

    def test_invalid_k_is_rejected(self):
        with self.assertRaises(ValueError):
            _fuse_rankings([], [], k=0)