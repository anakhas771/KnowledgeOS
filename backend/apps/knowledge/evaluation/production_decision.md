# KnowledgeOS Retrieval & RAG Production Decision (Phase 10)

## Executive Summary

Phase 10 represents a formal production decision gate. Over the previous nine phases, we established deterministic evaluation frameworks, measured semantic, lexical, hybrid, and RRF retrieval strategies, tested candidate pool and chunking variants, prepared embedding models, and benchmarked end-to-end RAG correctness and abstention.

This document consolidates that evidence to explicitly declare our production baseline configuration. Our guiding principle is conservative engineering: **we only adopt changes when the evidence proves robust quality improvement without unacceptable latency or maintenance costs.**

## Evidence Reviewed

1. **Retrieval Baselines (Phases 1-2):** Evaluated semantic vs. lexical vs. hybrid (RRF). Semantic retrieval established a strong R@1 and MRR baseline.
2. **Query-Aware Reranking (Phase 3):** Showed R@1/MRR improvements but mixed categorical effects and slight P@5 decline, adding 50-100ms API overhead.
3. **Candidate-Pool Sensitivity (Phase 4):** Evaluated pool sizes (K=5, 10, 15, 20). No reliable overall improvement; latency increased linearly with pool size.
4. **Chunking Sweep (Phase 5):** Evaluated 300/50, 600/75, 1000/150 (baseline), 1000/300. Results were mixed with no universally dominant config.
5. **Embedding Model (Phase 6):** Set up infrastructure for L6 (baseline) vs L12 testing, but actual quality comparison remained blocked/deferred.
6. **RAG End-to-End Benchmark (Phase 7-9):** Final corrected benchmark runs across 20 cases yielded a 90% overall pass rate, 0% unsupported claim rate, and 100% correct abstention behavior on unanswerable queries.

---

## Production Baseline

Based on the evidence, the core production baseline remains focused, fast, and robust. We prioritize a clean semantic retrieval pipeline that supports high-accuracy generation.

## Retrieval Decisions

**Decision:** `KEEP BASELINE` (Semantic Retrieval)

**Rationale:** The semantic baseline reliably retrieves high-quality context for our RAG generation (90% end-to-end pass rate, 80% groundedness). Lexical, Hybrid, and RRF retrieval methods were evaluated in Phase 2 but showed they require specific tuning or introduce overhead without dominating the baseline universally across our current dataset.

- Lexical, Hybrid, and RRF are marked as **KEEP EXPERIMENTAL**.

## Reranking Decision

**Decision:** `KEEP EXPERIMENTAL`

**Rationale:** While query-aware reranking (Phase 3) improved R@1 and MRR, it caused a slight decline in Precision@5 and exhibited mixed category effects. It also adds significant API overhead (50-100ms). Without a uniform win across all categories, it is deferred for targeted use-cases rather than standard production.

## Candidate-Pool Decision

**Decision:** `KEEP BASELINE` (K=5)

**Rationale:** Phase 4 demonstrated that increasing candidate pool sizes (K=10, 15, 20) produced diminishing returns and did not reliably improve overall quality. However, it consistently increased latency. The evaluation provides no evidence that larger candidate pools justify their added latency, so K=5 remains the production baseline.

## Chunking Decision

**Decision:** `KEEP BASELINE` (1000/150)

**Rationale:** Phase 5's chunking experiment (300/50, 600/75, 1000/150, 1000/300) yielded mixed results. No configuration proved universally dominant. Since changing chunk sizes requires a costly database migration and re-embedding of the corpus, we retain the 1000/150 baseline which currently performs solidly.

## Embedding Decision

**Decision:** `DEFER`

**Rationale:** The transition from `all-MiniLM-L6-v2` to the L12 candidate model was prepared in Phase 6, but the actual quality comparison was deferred. We **DO NOT** claim L12 is better or worse. We will not migrate production vectors. This decision is deferred until an empirical quality measurement explicitly justifies the heavier L12 model.

## RAG Generation Decision

**Decision:** `KEEP BASELINE`

**Rationale:** The Phase 9 corrected benchmark established very high quality metrics for the current prompt and generation model (`qwen3:4b-instruct`):

- Correctness: 90%
- Groundedness: 80%
- Source Alignment: 72%
- Correct Abstention: 100%
- Unsupported Claim Rate: 0%

There are two remaining generation-quality failures (`rag_p02`, `rag_h01`) where the model misses expected answer points. However, the model successfully avoids hallucination and unsupported claims. The generation path remains unchanged, with targeted generation improvements deferred to a later phase.

## Latency Findings

**Median Latencies (Phase 9 Benchmark):**

- Retrieval: ~5-15 ms
- Generation: ~8,500-10,500 ms
- Total Request: ~9,000-13,600 ms

**Conclusion:** End-to-end latency is overwhelmingly dominated by local LLM generation; retrieval contributes only a small fraction of the observed request latency. Optimizing retrieval latency (e.g., from 15ms to 5ms) will have no practical impact on user experience. Future optimization efforts must focus strictly on the generation path (e.g., streaming, smaller/faster models, caching).

---

## Deferred Experiments

1. **Embedding L12 Evaluation:** Needs actual empirical quality comparison vs L6.
2. **Query-Aware Reranking:** May be evaluated for specific targeted query classes rather than general retrieval.
3. **Generation Improvement:** Targeted prompt/model tuning for the remaining missing-point failures (`rag_p02`, `rag_h01`).

## Risks and Limitations

1. **Generation Quality:** Two edge cases still fail to retrieve full expected points.
2. **Lexical Gaps:** Semantic retrieval struggles with exact ID or keyword matches (partially mitigated by RAG, but remains a known limitation of purely semantic baselines).

---

## Final Production Configuration

The following configuration has been audited and remains actively deployed in the repository codebase:

- **Retrieval Strategy:** Semantic Retrieval Only
- **Reranker Active:** False
- **Hybrid/RRF Active:** False
- **Candidate Pool (K):** 5
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Vector Dimension:** 384
- **Chunk Size:** 1000
- **Chunk Overlap:** 150
- **Generation Model:** `qwen3:4b-instruct-2507-q4_K_M`

_(Programmatically verified via `apps/knowledge/tests/test_production_decision.py`)_
