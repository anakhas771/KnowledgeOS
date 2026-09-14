from django.test import SimpleTestCase

from apps.knowledge.evaluation.metrics import (
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


class RetrievalMetricsTestCase(SimpleTestCase):
    def test_recall_at_k(self):
        self.assertEqual(
            recall_at_k(
                retrieved_ids=[10, 20, 30],
                relevant_ids=[20, 30],
                k=3,
            ),
            1.0,
        )

    def test_recall_at_k_partial(self):
        self.assertEqual(
            recall_at_k(
                retrieved_ids=[10, 20, 30],
                relevant_ids=[20, 40],
                k=3,
            ),
            0.5,
        )

    def test_precision_at_k(self):
        self.assertEqual(
            precision_at_k(
                retrieved_ids=[10, 20, 30],
                relevant_ids=[20],
                k=3,
            ),
            1 / 3,
        )

    def test_reciprocal_rank(self):
        self.assertEqual(
            reciprocal_rank(
                retrieved_ids=[10, 20, 30],
                relevant_ids=[20],
            ),
            0.5,
        )

    def test_missing_relevant_document(self):
        self.assertEqual(
            reciprocal_rank(
                retrieved_ids=[10, 30, 40],
                relevant_ids=[20],
            ),
            0.0,
        )

    def test_mean_reciprocal_rank(self):
        self.assertEqual(
            mean_reciprocal_rank(
                rankings=[
                    [10, 20, 30],
                    [30, 40, 50],
                ],
                relevant_sets=[
                    [20],
                    [50],
                ],
            ),
            (0.5 + (1 / 3)) / 2,
        )

    def test_invalid_k(self):
        with self.assertRaises(ValueError):
            recall_at_k([1, 2], [1], 0)

        with self.assertRaises(ValueError):
            precision_at_k([1, 2], [1], 0)

    def test_empty_relevant_ids(self):
        self.assertEqual(recall_at_k([1, 2, 3], [], 3), 0.0)
        self.assertEqual(reciprocal_rank([1, 2, 3], []), 0.0)
