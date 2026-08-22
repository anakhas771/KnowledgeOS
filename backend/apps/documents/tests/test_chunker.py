from django.test import SimpleTestCase

from apps.documents.services.chunker import chunk_text


class ChunkingTests(SimpleTestCase):

    def test_empty_text_returns_no_chunks(self):
        self.assertEqual(
            chunk_text(""),
            [],
        )

    def test_text_is_split_into_chunks(self):
        text = "A" * 2500

        chunks = chunk_text(
            text,
            chunk_size=1000,
            overlap=100,
        )

        self.assertGreater(
            len(chunks),
            2,
        )

        self.assertEqual(
            chunks[0].index,
            0,
        )

        self.assertEqual(
            chunks[1].index,
            1,
        )

    def test_overlap_is_present(self):
        text = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        chunks = chunk_text(
            text,
            chunk_size=10,
            overlap=3,
        )

        self.assertGreaterEqual(
            len(chunks),
            3,
        )

        self.assertTrue(
            set(chunks[0].content[-3:])
            & set(chunks[1].content[:3])
        )

    def test_invalid_overlap_raises(self):
        with self.assertRaises(ValueError):
            chunk_text(
                "KnowledgeOS",
                chunk_size=10,
                overlap=10,
            )
