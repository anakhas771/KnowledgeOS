from django.test import SimpleTestCase

from apps.documents.services.embeddings import embed_text


class EmbeddingTests(SimpleTestCase):

    def test_embedding_dimension(self):
        embedding = embed_text(
            "KnowledgeOS enterprise knowledge platform."
        )

        self.assertEqual(
            len(embedding),
            384,
        )

    def test_embedding_values_are_numeric(self):
        embedding = embed_text(
            "KnowledgeOS test document."
        )

        self.assertTrue(
            all(
                isinstance(value, float)
                for value in embedding
            )
        )
