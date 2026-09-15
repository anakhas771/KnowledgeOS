from django.test import SimpleTestCase
from unittest import mock

from apps.knowledge.evaluation.benchmark import (
    run_reranked_benchmark,
    run_rerank_candidate_pool_sweep,
)
from apps.knowledge.evaluation.rerank import (
    RerankConfig,
    rerank_candidates,
    rerank_pool,
    token_overlap,
    tokenize,
    with_weights,
)


def make_candidate(
    chunk_id: int,
    document_id: int,
    content: str = "",
    title: str = "",
    score: float = 0.0,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "document_title": title,
        "content": content,
        "score": score,
    }


class TokenizationTestCase(SimpleTestCase):
    def test_tokenize_is_case_insensitive(self):
        self.assertEqual(
            tokenize("JWT Authentication", ignore_stopwords=False),
            {"jwt", "authentication"},
        )

    def test_tokenize_strips_punctuation(self):
        self.assertEqual(
            tokenize("How does JWT work?", ignore_stopwords=False),
            {"how", "does", "jwt", "work"},
        )

    def test_tokenize_removes_stopwords(self):
        self.assertEqual(
            tokenize("How does the pipeline work?"),
            {"pipeline", "work"},
        )

    def test_tokenize_falls_back_when_all_stopwords(self):
        # An all-stopword query must not collapse to an empty signal.
        self.assertEqual(
            tokenize("how does the"),
            {"how", "does", "the"},
        )

    def test_tokenize_empty_and_none(self):
        self.assertEqual(tokenize(""), set())
        self.assertEqual(tokenize(None), set())


class TokenOverlapTestCase(SimpleTestCase):
    def test_full_overlap(self):
        self.assertAlmostEqual(
            token_overlap("pgvector similarity", "pgvector similarity search"),
            1.0,
        )

    def test_partial_overlap_is_fraction_of_query_terms(self):
        # Query contributes {pgvector, similarity}; only pgvector matches.
        self.assertAlmostEqual(
            token_overlap("pgvector similarity", "pgvector index"),
            0.5,
        )

    def test_zero_overlap(self):
        self.assertEqual(
            token_overlap("pgvector", "unrelated content"),
            0.0,
        )

    def test_overlap_ignores_case_and_punctuation(self):
        self.assertAlmostEqual(
            token_overlap("JWT, authentication!", "jwt authentication"),
            1.0,
        )

    def test_empty_query_and_empty_text(self):
        self.assertEqual(token_overlap("", "anything"), 0.0)
        self.assertEqual(token_overlap("anything", ""), 0.0)
        self.assertEqual(token_overlap("anything", None), 0.0)

    def test_stopwords_do_not_inflate_overlap(self):
        # Without stopword removal "how does the" would match almost anything.
        with_stopwords = token_overlap(
            "how does the pgvector index work",
            "the system does how things",
            ignore_stopwords=False,
        )
        without_stopwords = token_overlap(
            "how does the pgvector index work",
            "the system does how things",
        )
        self.assertGreater(with_stopwords, without_stopwords)
        self.assertEqual(without_stopwords, 0.0)


class RerankConfigTestCase(SimpleTestCase):
    def test_defaults(self):
        config = RerankConfig()
        self.assertTrue(config.enabled)
        self.assertEqual(config.candidate_pool_size, 10)
        self.assertAlmostEqual(config.semantic_weight, 0.5)
        self.assertAlmostEqual(config.lexical_weight, 0.3)
        self.assertAlmostEqual(config.title_weight, 0.2)
        self.assertTrue(config.ignore_stopwords)

    def test_as_dict_is_serializable_and_complete(self):
        import json

        payload = RerankConfig().as_dict()
        self.assertEqual(
            set(payload),
            {
                "enabled",
                "candidate_pool_size",
                "semantic_weight",
                "lexical_weight",
                "title_weight",
                "ignore_stopwords",
            },
        )
        # Must survive JSON round-tripping for artifact persistence.
        self.assertEqual(json.loads(json.dumps(payload)), payload)

    def test_rejects_negative_weight(self):
        with self.assertRaises(ValueError):
            RerankConfig(semantic_weight=-0.1)

    def test_rejects_all_zero_weights(self):
        with self.assertRaises(ValueError):
            RerankConfig(
                semantic_weight=0.0,
                lexical_weight=0.0,
                title_weight=0.0,
            )

    def test_rejects_invalid_pool_size(self):
        with self.assertRaises(ValueError):
            RerankConfig(candidate_pool_size=0)

    def test_with_weights_returns_new_config(self):
        base = RerankConfig()
        derived = with_weights(base, 1.0, 0.0, 0.0)
        self.assertAlmostEqual(base.semantic_weight, 0.5)
        self.assertAlmostEqual(derived.semantic_weight, 1.0)
        self.assertEqual(
            derived.candidate_pool_size,
            base.candidate_pool_size,
        )


class RerankCandidatesTestCase(SimpleTestCase):
    def test_empty_candidates(self):
        self.assertEqual(rerank_candidates([], "anything"), [])

    def test_preserves_every_candidate(self):
        candidates = [
            make_candidate(1, 10, content="alpha", score=0.9),
            make_candidate(2, 20, content="beta", score=0.5),
            make_candidate(3, 30, content="gamma", score=0.1),
        ]
        result = rerank_candidates(candidates, "alpha")
        self.assertEqual(len(result), 3)
        self.assertEqual(
            {row["chunk_id"] for row in result},
            {1, 2, 3},
        )

    def test_does_not_mutate_input_candidates(self):
        candidates = [
            make_candidate(1, 10, content="alpha", score=0.5),
            make_candidate(2, 20, content="beta", score=0.4),
        ]
        snapshot = [dict(candidate) for candidate in candidates]

        rerank_candidates(candidates, "alpha")

        self.assertEqual(candidates, snapshot)
        for candidate in candidates:
            self.assertNotIn("rerank_score", candidate)

    def test_lexical_overlap_promotes_candidate_over_semantic_leader(self):
        # Candidate 2 has lower semantic score but exact term match.
        candidates = [
            make_candidate(1, 10, content="unrelated text", score=1.0),
            make_candidate(2, 20, content="pgvector cosine", score=0.9),
        ]
        result = rerank_candidates(
            candidates,
            "pgvector cosine",
            config=RerankConfig(
                semantic_weight=0.2,
                lexical_weight=0.8,
                title_weight=0.0,
            ),
        )
        self.assertEqual(result[0]["chunk_id"], 2)

    def test_semantic_only_weights_preserve_baseline_order(self):
        # With zero overlap weights the reranker must be a no-op on ordering.
        candidates = [
            make_candidate(1, 10, content="exact query terms", score=0.9),
            make_candidate(2, 20, content="nothing alike", score=0.8),
            make_candidate(3, 30, content="exact query terms", score=0.7),
        ]
        result = rerank_candidates(
            candidates,
            "exact query terms",
            config=RerankConfig(
                semantic_weight=1.0,
                lexical_weight=0.0,
                title_weight=0.0,
            ),
        )
        self.assertEqual(
            [row["chunk_id"] for row in result],
            [1, 2, 3],
        )

    def test_equal_scores_preserve_input_order(self):
        candidates = [
            make_candidate(5, 10, content="same", score=0.5),
            make_candidate(3, 20, content="same", score=0.5),
            make_candidate(9, 30, content="same", score=0.5),
        ]
        result = rerank_candidates(candidates, "same")
        # Stable sort: identical scores keep the incoming semantic order.
        self.assertEqual(
            [row["chunk_id"] for row in result],
            [5, 3, 9],
        )

    def test_is_deterministic_across_repeated_runs(self):
        candidates = [
            make_candidate(1, 10, content="alpha beta", title="Alpha", score=0.7),
            make_candidate(2, 20, content="beta gamma", title="Beta", score=0.7),
            make_candidate(3, 30, content="alpha", title="Gamma", score=0.4),
        ]
        first = rerank_candidates(candidates, "alpha beta")
        for _ in range(5):
            repeat = rerank_candidates(candidates, "alpha beta")
            self.assertEqual(
                [row["chunk_id"] for row in first],
                [row["chunk_id"] for row in repeat],
            )
            self.assertEqual(
                [row["rerank_score"] for row in first],
                [row["rerank_score"] for row in repeat],
            )

    def test_score_components_are_exposed(self):
        result = rerank_candidates(
            [make_candidate(1, 10, content="pgvector", title="Vector DB", score=0.8)],
            "pgvector",
        )
        row = result[0]
        self.assertIn("rerank_score", row)
        self.assertIn("content_overlap", row)
        self.assertIn("title_overlap", row)
        self.assertIn("semantic_score_normalized", row)

    def test_score_matches_weighted_formula(self):
        config = RerankConfig(
            semantic_weight=0.5,
            lexical_weight=0.3,
            title_weight=0.2,
        )
        candidates = [
            make_candidate(
                1, 10, content="pgvector index", title="Vector Database", score=1.0
            ),
            make_candidate(2, 20, content="nothing", title="Other", score=0.0),
        ]
        result = rerank_candidates(candidates, "pgvector", config=config)
        top = next(row for row in result if row["chunk_id"] == 1)
        # Single-term query fully present in content, absent from title.
        # Normalized semantic score for the max-scoring candidate is 1.0.
        expected = 0.5 * 1.0 + 0.3 * 1.0 + 0.2 * 0.0
        self.assertAlmostEqual(top["rerank_score"], expected)

    def test_identical_semantic_scores_normalize_without_error(self):
        candidates = [
            make_candidate(1, 10, content="alpha", score=0.42),
            make_candidate(2, 20, content="beta", score=0.42),
        ]
        result = rerank_candidates(candidates, "alpha")
        self.assertEqual(len(result), 2)
        for row in result:
            self.assertEqual(row["semantic_score_normalized"], 1.0)

    def test_missing_content_and_title_do_not_raise(self):
        candidates = [
            {"chunk_id": 1, "document_id": 10, "score": 0.5},
            make_candidate(2, 20, content="", title="", score=0.4),
        ]
        result = rerank_candidates(candidates, "anything")
        self.assertEqual(len(result), 2)
        for row in result:
            self.assertEqual(row["content_overlap"], 0.0)
            self.assertEqual(row["title_overlap"], 0.0)

    def test_missing_score_is_treated_as_zero(self):
        candidates = [
            {"chunk_id": 1, "document_id": 10, "content": "alpha"},
            make_candidate(2, 20, content="alpha", score=0.9),
        ]
        result = rerank_candidates(candidates, "alpha")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["chunk_id"], 2)

    def test_title_signal_contributes_independently(self):
        # Title-only match must still rank when the title weight is non-zero.
        candidates = [
            make_candidate(1, 10, content="unrelated", title="Unrelated", score=0.5),
            make_candidate(2, 20, content="unrelated", title="Tenant Isolation", score=0.5),
        ]
        result = rerank_candidates(
            candidates,
            "tenant isolation",
            config=RerankConfig(
                semantic_weight=0.0,
                lexical_weight=0.0,
                title_weight=1.0,
            ),
        )
        self.assertEqual(result[0]["chunk_id"], 2)
        self.assertAlmostEqual(result[0]["rerank_score"], 1.0)

    def test_zero_overlap_scores_reduce_to_semantic_component(self):
        config = RerankConfig(
            semantic_weight=0.5,
            lexical_weight=0.3,
            title_weight=0.2,
        )
        candidates = [
            make_candidate(1, 10, content="alpha", title="Alpha", score=1.0),
            make_candidate(2, 20, content="beta", title="Beta", score=0.0),
        ]
        result = rerank_candidates(candidates, "zzz", config=config)
        for row in result:
            self.assertEqual(row["content_overlap"], 0.0)
            self.assertEqual(row["title_overlap"], 0.0)
            self.assertAlmostEqual(
                row["rerank_score"],
                0.5 * row["semantic_score_normalized"],
            )


class RerankPoolTestCase(SimpleTestCase):
    def test_empty_candidates(self):
        self.assertEqual(rerank_pool([], "anything", limit=5), [])

    def test_truncates_to_candidate_pool_before_reranking(self):
        # Candidate 12 has the best lexical match but sits outside the pool,
        # so it must not appear in the final ranking.
        candidates = [
            make_candidate(i, i, content="filler", score=1.0 - i * 0.01)
            for i in range(1, 12)
        ]
        candidates.append(
            make_candidate(12, 12, content="pgvector", score=0.1)
        )
        result = rerank_pool(
            candidates,
            "pgvector",
            limit=5,
            config=RerankConfig(candidate_pool_size=10),
        )
        self.assertEqual(len(result), 5)
        self.assertNotIn(12, [row["chunk_id"] for row in result])

    def test_returns_final_top_k(self):
        candidates = [
            make_candidate(i, i, content="filler", score=1.0 - i * 0.01)
            for i in range(1, 11)
        ]
        result = rerank_pool(candidates, "filler", limit=3)
        self.assertEqual(len(result), 3)

    def test_pool_smaller_than_k_returns_all_candidates(self):
        candidates = [
            make_candidate(1, 10, content="alpha", score=0.5),
            make_candidate(2, 20, content="beta", score=0.4),
        ]
        result = rerank_pool(candidates, "alpha", limit=5)
        self.assertEqual(len(result), 2)

    def test_pool_size_smaller_than_limit(self):
        candidates = [
            make_candidate(i, i, content="filler", score=0.5)
            for i in range(1, 11)
        ]
        result = rerank_pool(
            candidates,
            "filler",
            limit=5,
            config=RerankConfig(candidate_pool_size=2),
        )
        self.assertEqual(len(result), 2)

    def test_disabled_config_returns_baseline_order(self):
        candidates = [
            make_candidate(1, 10, content="unrelated", score=0.9),
            make_candidate(2, 20, content="pgvector", score=0.8),
        ]
        result = rerank_pool(
            candidates,
            "pgvector",
            limit=2,
            config=RerankConfig(enabled=False),
        )
        self.assertEqual([row["chunk_id"] for row in result], [1, 2])
        # Disabled reranking must not annotate results.
        self.assertNotIn("rerank_score", result[0])

    def test_duplicate_document_ids_are_preserved_at_chunk_level(self):
        # Deduplication is the benchmark's responsibility, not the reranker's.
        candidates = [
            make_candidate(1, 100, content="alpha", score=0.9),
            make_candidate(2, 100, content="alpha", score=0.8),
            make_candidate(3, 200, content="alpha", score=0.7),
        ]
        result = rerank_pool(candidates, "alpha", limit=3)
        self.assertEqual(
            [row["document_id"] for row in result],
            [100, 100, 200],
        )

    def test_rejects_invalid_limit(self):
        with self.assertRaises(ValueError):
            rerank_pool([make_candidate(1, 10)], "alpha", limit=0)

    def test_does_not_mutate_input_collection(self):
        candidates = [
            make_candidate(1, 10, content="alpha", score=0.9),
            make_candidate(2, 20, content="beta", score=0.8),
        ]
        snapshot = [dict(candidate) for candidate in candidates]

        rerank_pool(candidates, "alpha", limit=1)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates, snapshot)

    def test_query_with_punctuation_and_mixed_case(self):
        candidates = [
            make_candidate(1, 10, content="unrelated filler", score=0.9),
            make_candidate(
                2, 20, content="JWT authentication protects endpoints", score=0.85
            ),
        ]
        result = rerank_pool(
            candidates,
            "How does JWT Authentication work?!",
            limit=2,
            config=RerankConfig(
                semantic_weight=0.2,
                lexical_weight=0.8,
                title_weight=0.0,
            ),
        )
        self.assertEqual(result[0]["chunk_id"], 2)


class RerankedBenchmarkIntegrationTestCase(SimpleTestCase):
    """
    Exercise the benchmark wiring without a database by substituting the
    corpus lookup, the embedding call, and the production retrieval call.
    """

    def setUp(self):
        patcher = mock.patch(
            "apps.knowledge.evaluation.benchmark._get_title_to_id",
            return_value={"Doc A": 1, "Doc B": 2},
        )
        self.addCleanup(patcher.stop)
        self.title_to_id = patcher.start()

        embedding_patcher = mock.patch(
            "apps.knowledge.evaluation.benchmark.embed_query",
            return_value=[0.0] * 4,
        )
        self.addCleanup(embedding_patcher.stop)
        self.embed_query = embedding_patcher.start()

    def _case(self, query: str):
        from apps.knowledge.evaluation.dataset import RetrievalEvaluationCase

        return RetrievalEvaluationCase(
            query=query,
            relevant_document_titles=("Doc A",),
            category="direct",
        )

    def _run(self, candidates, cases, search_limit_spy=None, **kwargs):
        def fake_search(organization_id, query_embedding, limit):
            if search_limit_spy is not None:
                search_limit_spy.append(limit)
            return [dict(candidate) for candidate in candidates]

        with mock.patch(
            "apps.knowledge.evaluation.benchmark.search_similar_chunks",
            side_effect=fake_search,
        ), mock.patch(
            "apps.knowledge.evaluation.benchmark.EVALUATION_CASES",
            tuple(cases),
        ):
            return run_reranked_benchmark(
                organization_id=1,
                limit=kwargs.pop("limit", 5),
                **kwargs,
            )

    def test_report_records_configuration(self):
        cases = [self._case("alpha")]
        candidates = [
            make_candidate(1, 1, content="alpha", title="Doc A", score=0.9),
            make_candidate(2, 2, content="beta", title="Doc B", score=0.8),
        ]
        config = RerankConfig(
            candidate_pool_size=7,
            semantic_weight=0.4,
            lexical_weight=0.4,
            title_weight=0.2,
        )
        report = self._run(candidates, cases, config=config, limit=3)

        self.assertEqual(
            report["configuration"],
            {**config.as_dict(), "limit": 3},
        )

    def test_default_configuration_is_applied(self):
        cases = [self._case("alpha")]
        candidates = [
            make_candidate(1, 1, content="alpha", title="Doc A", score=0.9),
        ]
        report = self._run(candidates, cases)

        self.assertEqual(
            report["configuration"],
            {**RerankConfig().as_dict(), "limit": 5},
        )

    def test_retrieves_full_candidate_pool_before_reranking(self):
        cases = [self._case("alpha")]
        candidates = [
            make_candidate(i, i, content="alpha", score=1.0 - i * 0.01)
            for i in range(1, 13)
        ]
        limits: list[int] = []

        self._run(
            candidates,
            cases,
            search_limit_spy=limits,
            config=RerankConfig(candidate_pool_size=12),
            limit=5,
        )

        # The pool must be retrieved at pool size, not at the evaluation limit.
        self.assertEqual(limits, [12])

    def test_report_has_expected_shape(self):
        cases = [
            self._case("alpha"),
            self._case("beta"),
        ]
        candidates = [
            make_candidate(1, 1, content="alpha", title="Doc A", score=0.9),
            make_candidate(2, 2, content="beta", title="Doc B", score=0.8),
        ]
        report = self._run(candidates, cases)

        self.assertEqual(
            set(report),
            {"cases", "summary", "by_category", "configuration"},
        )
        self.assertEqual(len(report["cases"]), 2)
        self.assertIn("direct", report["by_category"])

        for key in (
            "recall_at_1",
            "recall_at_3",
            "recall_at_5",
            "precision_at_5",
            "mrr",
            "median_latency_ms",
        ):
            self.assertIn(key, report["summary"])

    def test_document_level_deduplication_preserved(self):
        # Two chunks of the same document must collapse to one ranked id.
        cases = [self._case("alpha")]
        candidates = [
            make_candidate(1, 1, content="alpha", title="Doc A", score=0.9),
            make_candidate(2, 1, content="alpha", title="Doc A", score=0.85),
            make_candidate(3, 2, content="alpha", title="Doc B", score=0.8),
        ]
        report = self._run(candidates, cases, limit=5)

        retrieved = report["cases"][0]["retrieved_document_ids"]
        self.assertEqual(len(retrieved), len(set(retrieved)))
        self.assertEqual(retrieved, [1, 2])

    def test_final_top_k_is_respected(self):
        cases = [self._case("alpha")]
        candidates = [
            make_candidate(i, i, content="alpha", score=1.0 - i * 0.01)
            for i in range(1, 11)
        ]
        report = self._run(
            candidates,
            cases,
            config=RerankConfig(candidate_pool_size=10),
            limit=3,
        )

        self.assertLessEqual(
            len(report["cases"][0]["retrieved_document_ids"]),
            3,
        )

    def test_missing_embedding_raises(self):
        cases = [self._case("alpha")]

        with mock.patch(
            "apps.knowledge.evaluation.benchmark.embed_query",
            return_value=None,
        ), mock.patch(
            "apps.knowledge.evaluation.benchmark.search_similar_chunks",
        ), mock.patch(
            "apps.knowledge.evaluation.benchmark.EVALUATION_CASES",
            tuple(cases),
        ):
            with self.assertRaises(ValueError):
                run_reranked_benchmark(
                    organization_id=1,
                    limit=5,
                )


class RerankArtifactSerializationTestCase(SimpleTestCase):
    def test_rerank_artifact_identifies_strategy_and_configuration(self):
        from apps.knowledge.evaluation.artifact import build_experiment_artifact

        from apps.knowledge.management.commands.benchmark_retrieval import (
            RERANK_STRATEGY,
        )

        config = {**RerankConfig().as_dict(), "limit": 5}
        report = {
            "summary": {"recall_at_1": 0.8, "median_latency_ms": 12.0},
            "by_category": {"direct": {"recall_at_1": 1.0}},
            "cases": [{"query": "q", "retrieved_document_ids": [1]}],
        }

        artifact = build_experiment_artifact(
            benchmark_id="rerank-run",
            strategy=RERANK_STRATEGY,
            config=config,
            report=report,
        )

        self.assertEqual(artifact["retrieval_strategy"], RERANK_STRATEGY)
        self.assertIn("rerank", artifact["retrieval_strategy"])
        self.assertEqual(artifact["configuration"], config)
        self.assertIn("candidate_pool_size", artifact["configuration"])
        self.assertIn("semantic_weight", artifact["configuration"])
        self.assertIn("lexical_weight", artifact["configuration"])
        self.assertIn("title_weight", artifact["configuration"])



class CandidatePoolSweepTestCase(SimpleTestCase):
    """Focused tests for the Phase 4 pool-size sensitivity experiment."""

    def setUp(self):
        patcher = mock.patch(
            "apps.knowledge.evaluation.benchmark._get_title_to_id",
            return_value={"Doc A": 1, "Doc B": 2, "Doc C": 3},
        )
        self.addCleanup(patcher.stop)
        self.title_to_id = patcher.start()

        embedding_patcher = mock.patch(
            "apps.knowledge.evaluation.benchmark.embed_query",
            return_value=[0.0] * 4,
        )
        self.addCleanup(embedding_patcher.stop)
        self.embed_query = embedding_patcher.start()

    def _case(self, query="test"):
        from apps.knowledge.evaluation.dataset import RetrievalEvaluationCase
        return RetrievalEvaluationCase(query=query, relevant_document_titles=("Doc A",), category="direct")

    def _run_sweep(self, pool_sizes, candidates, cases=None, **kwargs):
        cases = cases or [self._case()]
        with mock.patch(
            "apps.knowledge.evaluation.benchmark.search_similar_chunks",
            side_effect=lambda organization_id, query_embedding, limit, **kw: [dict(c) for c in candidates],
        ), mock.patch(
            "apps.knowledge.evaluation.benchmark.EVALUATION_CASES",
            tuple(cases),
        ):
            return run_rerank_candidate_pool_sweep(
                organization_id=1,
                pool_sizes=pool_sizes,
                limit=5,
                config=kwargs.get("config", RerankConfig()),
            )

    def test_sweep_evaluates_all_configured_pool_sizes(self):
        results = self._run_sweep([5, 10, 15], [
            make_candidate(i, i, content="test", score=0.9) for i in range(1, 6)
        ])
        self.assertEqual(sorted(results.keys()), [5, 10, 15])
        for size in [5, 10, 15]:
            self.assertIn("summary", results[size])
            self.assertIn("by_category", results[size])
            self.assertIn("configuration", results[size])

    def test_pool_size_is_recorded_in_result_configuration(self):
        results = self._run_sweep([5], [
            make_candidate(1, 1, content="test", score=0.9)
        ])
        self.assertEqual(
            results[5]["configuration"]["candidate_pool_size"],
            5,
        )
        self.assertEqual(
            results[5]["configuration"]["limit"],
            5,
        )

    def test_final_limit_remains_fixed(self):
        results = self._run_sweep([5, 10, 20], [
            make_candidate(i, i, content="test", score=1.0 - i*0.01)
            for i in range(1, 25)
        ])
        for size in results:
            # The benchmark's final top-K must stay 5 regardless of pool.
            for case_result in results[size]["cases"]:
                self.assertLessEqual(
                    len(case_result["retrieved_document_ids"]),
                    5,
                )

    def test_pool_larger_than_available_candidates(self):
        # Corpus only has 3 chunks; requesting pool=20 must not crash.
        results = self._run_sweep([20], [
            make_candidate(1, 1, content="a", score=0.9),
            make_candidate(2, 2, content="b", score=0.8),
            make_candidate(3, 3, content="c", score=0.7),
        ])
        self.assertIn(20, results)
        # The result should include the available chunks (at most 3).
        retrieved = results[20]["cases"][0]["retrieved_document_ids"]
        self.assertLessEqual(len(retrieved), 3)

    def test_pool_size_less_than_final_k_works(self):
        results = self._run_sweep([2], [
            make_candidate(1, 1, content="test", score=0.9),
            make_candidate(2, 2, content="test", score=0.8),
        ])
        self.assertIn(2, results)
        self.assertEqual(len(results[2]["cases"]), 1)

    def test_duplicate_pool_sizes_are_deduplicated(self):
        results = self._run_sweep([5, 5, 10, 10, 5], [
            make_candidate(1, 1, content="test", score=0.9)
        ])
        # Deduplicated pool list means only 5 and 10 should appear.
        self.assertEqual(sorted(results.keys()), [5, 10])

    def test_empty_pool_list_raises(self):
        with self.assertRaises(ValueError):
            run_rerank_candidate_pool_sweep(
                organization_id=1, pool_sizes=[], limit=5
            )

    def test_non_positive_pool_size_raises(self):
        with self.assertRaises(ValueError):
            run_rerank_candidate_pool_sweep(
                organization_id=1, pool_sizes=[-1], limit=5
            )
        with self.assertRaises(ValueError):
            run_rerank_candidate_pool_sweep(
                organization_id=1, pool_sizes=[0], limit=5
            )

    def test_pool_size_equal_to_final_k(self):
        results = self._run_sweep([5], [
            make_candidate(i, i, content="test", score=0.9)
            for i in range(1, 10)
        ])
        # When pool == K (5), no truncation beyond ranking occurs.
        self.assertEqual(len(results[5]["cases"][0]["retrieved_document_ids"]), 5)

    def test_same_corpus_and_case_conditions_across_pools(self):
        # By using the same mock cases and retrieval function, we prove
        # the only varying input is pool_size.
        results_small = self._run_sweep([5], [
            make_candidate(i, i, content="test", score=0.9) for i in range(1, 8)
        ])
        results_large = self._run_sweep([15], [
            make_candidate(i, i, content="test", score=0.9) for i in range(1, 8)
        ])
        # Confirm results are present for requested pool sizes
        self.assertIn(5, results_small)
        self.assertIn(15, results_large)
        for r in (results_small, results_large):
            for s in r:
                self.assertEqual(len(r[s]["cases"]), 1)

    def test_configuration_not_mutated_between_pool_sizes(self):
        results = self._run_sweep([5, 15], [
            make_candidate(1, 1, content="a", title="Doc", score=0.9)
        ], config=RerankConfig(semantic_weight=0.5, lexical_weight=0.3, title_weight=0.2))
        for size in [5, 15]:
            conf = results[size]["configuration"]
            self.assertAlmostEqual(conf["semantic_weight"], 0.5)
            self.assertAlmostEqual(conf["lexical_weight"], 0.3)
            self.assertAlmostEqual(conf["title_weight"], 0.2)
            self.assertTrue(conf["enabled"])
