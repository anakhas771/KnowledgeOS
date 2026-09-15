from dataclasses import dataclass
from enum import Enum


class DecisionStatus(Enum):
    ADOPT = "ADOPT"
    KEEP_BASELINE = "KEEP BASELINE"
    KEEP_EXPERIMENTAL = "KEEP EXPERIMENTAL"
    DEFER = "DEFER"
    REJECT_FOR_NOW = "REJECT FOR NOW"


@dataclass
class ProductionDecision:
    capability: str
    evidence: str
    quality_effect: str
    latency_cost: str
    decision: DecisionStatus
    rationale: str


DECISION_MATRIX = [
    ProductionDecision(
        capability="Semantic Baseline",
        evidence="Phase 1-2 benchmarks, Phase 9 end-to-end",
        quality_effect="Consistent R@1 and MRR, pass rate 0.90 end-to-end",
        latency_cost="~11-15ms retrieval",
        decision=DecisionStatus.KEEP_BASELINE,
        rationale="Strong baseline performance, low latency, no robust evidence to replace."
    ),
    ProductionDecision(
        capability="Lexical Retrieval",
        evidence="Phase 2 baseline tests",
        quality_effect="Good exact match, struggles with semantics",
        latency_cost="Low",
        decision=DecisionStatus.KEEP_EXPERIMENTAL,
        rationale="Not superior to semantic baseline alone, but useful component for hybrid."
    ),
    ProductionDecision(
        capability="Hybrid Retrieval",
        evidence="Phase 2 tests",
        quality_effect="Can improve specific queries but requires tuning",
        latency_cost="Increases latency (2x queries)",
        decision=DecisionStatus.KEEP_EXPERIMENTAL,
        rationale="Not yet proven to dominate semantic baseline universally across our dataset."
    ),
    ProductionDecision(
        capability="RRF (Reciprocal Rank Fusion)",
        evidence="Phase 2 tests",
        quality_effect="Combines scores but sensitive to parameter K",
        latency_cost="Compute overhead for rank combination",
        decision=DecisionStatus.KEEP_EXPERIMENTAL,
        rationale="Needs specific tuning, unproven overall superiority."
    ),
    ProductionDecision(
        capability="Query-aware Reranking",
        evidence="Phase 3 experiment",
        quality_effect="Improves R@1 and MRR, but slight P@5 decline and mixed category effects",
        latency_cost="Adds ~50-100ms API overhead depending on batch size",
        decision=DecisionStatus.KEEP_EXPERIMENTAL,
        rationale="No uniform win across all categories. Better for specific query classes, deferred for targeted use."
    ),
    ProductionDecision(
        capability="Candidate-pool Size",
        evidence="Phase 4 sensitivity sweep (5, 10, 15, 20)",
        quality_effect="Larger pools did not produce reliable overall improvement",
        latency_cost="Increased latency with larger pools",
        decision=DecisionStatus.KEEP_BASELINE,
        rationale="Larger pools showed no reliable overall quality improvement and increased latency, so K=5 remains the production baseline."
    ),
    ProductionDecision(
        capability="Chunking Configuration",
        evidence="Phase 5 sweep (300/50, 600/75, 1000/150, 1000/300)",
        quality_effect="Mixed results; no universally dominant configuration",
        latency_cost="Smaller chunks increase DB index size and embedding costs",
        decision=DecisionStatus.KEEP_BASELINE,
        rationale="Current 1000/150 provides solid performance without evidence justifying a costly migration."
    ),
    ProductionDecision(
        capability="Embedding Model (L6 vs L12)",
        evidence="Phase 6 evaluation framework prepared",
        quality_effect="Not empirically evaluated yet",
        latency_cost="L12 would be heavier and slower than L6",
        decision=DecisionStatus.DEFER,
        rationale="L6 remains baseline. Actual quality comparison between L6 and L12 remains blocked/deferred."
    ),
    ProductionDecision(
        capability="RAG Generation",
        evidence="Phase 9 corrected end-to-end benchmark (Run A & B)",
        quality_effect="90% correctness, 0% unsupported claims, 100% correct abstention",
        latency_cost="~8.5-10.5s generation (dominates total latency)",
        decision=DecisionStatus.KEEP_BASELINE,
        rationale="High quality metrics and zero unsupported claims. Remaining 2 failures are missing expected points, requiring targeted generation improvements later."
    ),
    ProductionDecision(
        capability="Abstention Behavior",
        evidence="Phase 9 corrected end-to-end benchmark",
        quality_effect="100% correct abstention on unanswerable queries",
        latency_cost="N/A",
        decision=DecisionStatus.KEEP_BASELINE,
        rationale="Evaluator verified abstention works flawlessly with current prompt and model."
    ),
]


PRODUCTION_CONFIG = {
    "retrieval_strategy": "semantic",
    "embedding_model": "all-MiniLM-L6-v2",
    "vector_dimension": 384,
    "chunk_size": 1000,
    "chunk_overlap": 150,
    "reranker_active": False,
    "hybrid_active": False,
    "rrf_active": False,
    "generation_model": "qwen3:4b-instruct-2507-q4_K_M"
}
