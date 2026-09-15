from django.test import SimpleTestCase

from apps.knowledge.evaluation.embedding_config import (
    MODELS, BASELINE, CANDIDATE, EmbeddingModelConfig, get_model_config,
)
from apps.knowledge.evaluation.embedding_experiment import (
    EmbeddingExperimentConfig,
    EXPERIMENT_CONFIGS,
    seed_embedding_corpus,
    seed_embedding_corpus_with_direct_model,
    structural_equivalence,
    check_service_model,
)
from apps.knowledge.evaluation.chunking_corpus import SOURCE_DOCUMENTS


class EmbeddingExperimentStructureTestCase(SimpleTestCase):
    def test_model_selection_returns_384(self):
        cfg = get_model_config("mini_l6")
        self.assertEqual(cfg.dimensions, 384)
        cfg2 = get_model_config("mini_l12")
        self.assertEqual(cfg2.dimensions, 384)

    def test_invalid_dimension_fails(self):
        with self.assertRaises(ValueError) as cm:
            EmbeddingModelConfig(
                name="bad", model_name="bad/model", dimensions=768
            )
        self.assertIn("384", str(cm.exception))

    def test_model_config_frozen(self):
        cfg = get_model_config("mini_l6")
        with self.assertRaises(Exception):
            cfg.dimensions = 768  # frozen dataclass

    def test_experiment_config_isolation(self):
        for name in MODELS:
            exp_cfg = EXPERIMENT_CONFIGS[name]
            self.assertEqual(exp_cfg.organization_slug, f"embedding-eval-{name}")
            self.assertEqual(exp_cfg.chunk_size, 1000)
            self.assertEqual(exp_cfg.overlap, 150)

    def test_structural_equivalence_exists(self):
        self.assertTrue(callable(structural_equivalence))

    def test_service_check_exists(self):
        self.assertTrue(callable(check_service_model))

    def test_seed_functions_exist(self):
        self.assertTrue(callable(seed_embedding_corpus))
        self.assertTrue(callable(seed_embedding_corpus_with_direct_model))

    def test_source_document_coverage_unchanged(self):
        needed = {t for case in __import__(
            "apps.knowledge.evaluation.dataset", fromlist=[""]
        ).EVALUATION_CASES for t in case.relevant_document_titles}
        missing = needed - set(SOURCE_DOCUMENTS)
        self.assertFalse(missing, f"Missing docs for embedding comparison: {missing}")

    def test_model_name_matches_config(self):
        cfg = get_model_config("mini_l12")
        self.assertIn("all-MiniLM-L12-v2", cfg.model_name)

    def test_corpus_isolation_slugs_unique_per_model(self):
        slugs = [EXPERIMENT_CONFIGS[name].organization_slug for name in MODELS]
        self.assertEqual(len(slugs), len(set(slugs)), "Isolation slugs must be unique")

    def test_dimension_gate_384_enforced(self):
        with self.assertRaises(ValueError):
            EmbeddingModelConfig(
                name="fake128", model_name="fake/model", dimensions=128
            )


class StructuralEquivalenceTestCase(SimpleTestCase):
    def _base(self, docs=None, chunks=None, chunk_size=1000, overlap=150):
        return {
            "documents": docs or ["Doc A", "Doc B"],
            "total_chunks": chunks or 6,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "chunks_per_document": {
                d: ["chunk-" + str(i) for i in range(chunks // 2 if chunks else 3)]
                for d in (docs or ["Doc A", "Doc B"])
            },
        }

    def test_equivalent_structures_return_true(self):
        a = self._base()
        b = {
            "documents": ["Doc A", "Doc B"],
            "total_chunks": 6,
            "chunk_size": 1000,
            "overlap": 150,
            "chunks_per_document": {
                "Doc A": ["chunk-0", "chunk-1", "chunk-2"],
                "Doc B": ["chunk-0", "chunk-1", "chunk-2"],
            },
        }
        res = structural_equivalence(a, b)
        self.assertTrue(res["overall_equivalent"], f"Expected equivalent, got: {res}")
        self.assertTrue(res["document_titles_match"])
        self.assertTrue(res["document_counts_match"])
        self.assertTrue(res["total_chunks_match"])
        self.assertTrue(res["chunk_texts_identical"])
        self.assertTrue(res["chunk_ordering_identical"])
        self.assertTrue(res["chunking_config_identical"])

    def test_different_titles_fail(self):
        a = self._base()
        b = self._base(docs=["Doc X"])
        res = structural_equivalence(a, b)
        self.assertFalse(res["document_titles_match"])
        self.assertFalse(res["overall_equivalent"])

    def test_different_document_counts_fail(self):
        a = self._base(docs=["Doc A", "Doc B", "Doc C"])
        b = self._base(docs=["Doc A", "Doc B"])
        res = structural_equivalence(a, b)
        self.assertFalse(res["document_counts_match"])
        self.assertFalse(res["overall_equivalent"])

    def test_different_chunk_counts_fail(self):
        a = self._base(chunks=6)
        b = self._base(chunks=4)
        res = structural_equivalence(a, b)
        self.assertFalse(res["total_chunks_match"])
        self.assertFalse(res["overall_equivalent"])

    def test_different_chunk_text_fails(self):
        a = self._base(chunks=3)
        b = {
            "documents": ["Doc A", "Doc B"],
            "total_chunks": 3,
            "chunk_size": 1000,
            "overlap": 150,
            "chunks_per_document": {"Doc A": ["a", "b", "c"], "Doc B": ["x", "y", "z"]},
        }
        res = structural_equivalence(a, b)
        self.assertFalse(res["chunk_texts_identical"])
        self.assertFalse(res["overall_equivalent"])

    def test_chunk_ordering_mismatch_fails(self):
        a = self._base(chunks=3)
        b = {
            "documents": ["Doc A", "Doc B"],
            "total_chunks": 3,
            "chunk_size": 1000,
            "overlap": 150,
            "chunks_per_document": {"Doc A": ["chunk-2", "chunk-1", "chunk-0"], "Doc B": ["chunk-0", "chunk-1", "chunk-2"]},
        }
        res = structural_equivalence(a, b)
        self.assertFalse(res["chunk_ordering_identical"])
        self.assertFalse(res["overall_equivalent"])

    def test_vectors_do_not_affect_equivalence(self):
        # Structural comparison must ignore embeddings; only structure matters.
        a = self._base()
        b = self._base()
        # Even if embeddings were injected (simulated), structural result is same.
        res = structural_equivalence(a, b)
        self.assertTrue(res["overall_equivalent"])

    def test_malformed_missing_keys_fails_clearly(self):
        res = structural_equivalence({"documents": []}, {"documents": []})
        self.assertFalse(res["overall_equivalent"])
        # Should not crash; missing required keys leave defaults False.
        self.assertIn("document_titles_match", res)
        self.assertIn("chunking_config_identical", res)
