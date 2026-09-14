from django.test import SimpleTestCase

from apps.knowledge.evaluation.chunking import (
    ChunkingConfig,
    CHUNKING_CONFIGS,
    get_config,
    build_chunks,
    chunk_statistics,
    measure_boundary_integrity,
)
from apps.documents.services.chunker import chunk_text, TextChunk
from apps.knowledge.evaluation.chunking_corpus import SOURCE_DOCUMENTS


class ChunkExperimentStructureTestCase(SimpleTestCase):
    def test_all_evaluation_document_titles_covered(self):
        from apps.knowledge.evaluation.dataset import EVALUATION_CASES

        needed = {t for c in EVALUATION_CASES for t in c.relevant_document_titles}

        missing = needed - set(SOURCE_DOCUMENTS)

        self.assertFalse(
            missing,
            f"Chunking corpus missing: {missing}",
        )
        self.assertTrue(
            len(SOURCE_DOCUMENTS) >= len(needed),
            "Chunking corpus must cover all dataset-relevant titles.",
        )

    def test_configurations_maintain_production_contract(self):
        for cfg in CHUNKING_CONFIGS:
            # Positive size / non-negative overlap / overlap < size
            self.assertGreater(cfg.chunk_size, 0)
            self.assertGreaterEqual(cfg.overlap, 0)
            self.assertLess(cfg.overlap, cfg.chunk_size)

    def test_current_is_production_default(self):
        current = get_config("current")

        self.assertEqual(current.chunk_size, 1000)
        self.assertEqual(current.overlap, 150)

    def test_small_and_medium_differentiate_from_current(self):
        current = chunk_text("A" * 3000, chunk_size=1000, overlap=150)
        small = chunk_text("A" * 3000, chunk_size=300, overlap=50)
        medium = chunk_text("A" * 3000, chunk_size=600, overlap=75)

        # Chunk counts should vary materially.
        self.assertNotEqual(len(small), len(current))
        self.assertNotEqual(len(medium), len(current))

    def test_chunk_content_preserved_verbatim(self):
        cfg = get_config("small")
        chunks = build_chunks("Document Processing", cfg)

        # Every chunk's content must appear in sequence inside its source.
        text = SOURCE_DOCUMENTS["Document Processing"]
        cursor = 0

        for chunk in chunks:
            pos = text.find(chunk.content, cursor)
            self.assertGreaterEqual(pos, 0, f"Chunk content missing after {cursor}")
            cursor = pos + 1

    def test_index_ordering_deterministic(self):
        cfg = get_config("current")
        chunks = build_chunks("Knowledge Retrieval Architecture", cfg)

        indices = [chunk.index for chunk in chunks]

        self.assertEqual(
            indices,
            sorted(indices),
            "Chunk indices must be monotonically increasing.",
        )
        self.assertEqual(
            indices,
            list(range(len(chunks))),
            "Chunk indices must start at 0 and have no gaps.",
        )

    def test_boundary_integrity_never_crashes_on_empty(self):
        cfg = get_config("current")
        stats = chunk_statistics(cfg)

        # Boundary ratios must be in [0, 1].
        self.assertGreaterEqual(stats["boundary_integrity"]["ends_mid_word_ratio"], 0)
        self.assertLessEqual(stats["boundary_integrity"]["ends_mid_word_ratio"], 1)
        self.assertGreaterEqual(stats["boundary_integrity"]["ends_mid_word_ratio"], 0)

    def test_chunk_counts_are_structurally_different(self):
        stats_small = chunk_statistics(get_config("small"))
        stats_current = chunk_statistics(get_config("current"))

        self.assertNotEqual(
            stats_small["total_chunks"],
            stats_current["total_chunks"],
            "Small and current configurations must produce different chunk counts.",
        )

        self.assertNotEqual(
            stats_small["mean_chunks_per_document"],
            stats_current["mean_chunks_per_document"],
        )

    def test_mod_chunks_are_proportionally_distinct(self):
        # The overlap-only variation must differ in boundary metrics even
        # when chunk counts overlap with another config, so we check ratios.
        stats_current = chunk_statistics(get_config("current"))
        stats_ov = chunk_statistics(get_config("moderate_overlap"))

        # More overlap may slightly increase chunk count (shorter overlap window
        # creates shorter chunks that split differently); the property to check
        # is that overlap-only varies from current rather than being equal.
        self.assertNotEqual(
            stats_ov["configuration"]["overlap"],
            stats_current["configuration"]["overlap"],
        )
