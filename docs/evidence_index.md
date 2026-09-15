# KnowledgeOS Evidence Index

This index maps key technical claims about the KnowledgeOS platform to the concrete engineering evidence stored in the repository. It is designed to make the project defensible in technical reviews and interviews.

| Claim | Evidence Source | Description |
|---|---|---|
| **Semantic retrieval is the production baseline** | `apps/knowledge/evaluation/production_decision.md` | Decision matrix concluding that lexical/hybrid/reranking features lack the universal dominance to replace the semantic baseline. |
| **20-case RAG benchmark achieved 90% pass rate** | `phase9_artifact_runA.json` & `phase9_artifact_runB.json` | Final output artifacts from the Phase 9 benchmark showing stable, deterministic 90% correctness. |
| **0% unsupported claims and 100% correct abstention** | `phase9_artifact_runA.json` & `phase9_artifact_runB.json` | The Phase 9 evaluation runs explicitly measure and confirm flawless safety and abstention metrics. |
| **Evaluator effectively prevents false positives** | `apps/knowledge/evaluation/rag_evaluator.py` | Contains the deterministic, negation-aware logic used to parse contrastive claims and prevent false positive hallucination flags. |
| **Reranking was not promoted** | `apps/knowledge/evaluation/rerank.py` | The cross-encoder reranking implementation exists as an experiment, but `production_decision.py` logs its deferment due to latency and mixed metric gains. |
| **Larger candidate pools (K>5) increase latency without sufficient quality gain** | `apps/knowledge/evaluation/production_decision.md` | Phase 4 candidate pool sensitivity sweep evidence detailing diminishing returns for K=10, 15, 20. |
| **L12 migration was deferred** | `apps/documents/services/embeddings.py` & `production_decision.py` | The L6 embedding model is active in production code. The L12 infrastructure exists but its adoption is formally deferred pending empirical comparison. |
| **End-to-end latency is overwhelmingly dominated by generation** | `phase9_artifact.json` | Empirical latency metrics showing median retrieval at ~15ms and generation at ~10,000ms. |
| **Production configuration matches documented baseline** | `apps/knowledge/tests/test_production_decision.py` | Automated tests explicitly asserting that the `PRODUCTION_CONFIG` strictly enforces the verified semantic baseline. |
