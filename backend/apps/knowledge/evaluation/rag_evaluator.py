"""
Phase 7 RAG answer evaluator.

Provides deterministic checks against expected points, forbidden claims,
and basic source-alignment detection. Uses the existing corpus structures.
Optional local judge notes are clearly separated (not treated as truth).
"""
from __future__ import annotations

import re
from typing import Any

from apps.knowledge.evaluation.rag_evaluation_dataset import RAGEvaluationCase


# ---------------------------------------------------------------------------
# Deterministic checks
# ---------------------------------------------------------------------------

def check_answer_points(answer_text: str, expected: tuple[str, ...]) -> dict:
    """Simple keyword/presence heuristic (not semantic judge)."""
    found = []
    missing = []
    lower_answer = answer_text.lower()
    for point in expected:
        keywords = [w.lower() for w in point.split() if len(w) > 3]
        hits = sum(1 for k in keywords if k in lower_answer)
        matched = hits >= max(1, len(keywords) // 2)
        if matched:
            found.append(point)
        else:
            missing.append(point)
    return {
        "found_points": found,
        "missing_points": missing,
        "score": len(found) / len(expected) if expected else 1.0,
    }


def check_forbidden_claims(answer_text: str, forbidden: tuple[str, ...]) -> dict:
    lower_answer = answer_text.lower()
    violations = []
    for claim in forbidden:
        keywords = [w.lower() for w in claim.split() if len(w) > 3]
        hits = sum(1 for k in keywords if k in lower_answer)
        if hits >= max(1, len(keywords) // 2):
            violations.append(claim)
    return {
        "violations": violations,
        "passed": len(violations) == 0,
    }


def check_abstention_behavior(answer_text: str, case: RAGEvaluationCase) -> dict:
    if not case.unanswerable:
        return {"expected_abstain": False, "detected_abstain": False}
    abstain_indicators = (
        "insufficient", "not available", "does not contain",
        "no evidence", "i don't know", "i do not know",
        "cannot determine", "not enough information",
    )
    detected = any(ind in answer_text.lower() for ind in abstain_indicators)
    return {"expected_abstain": True, "detected_abstain": detected, "passed": detected}


def check_source_alignment(answer_text: str, retrieved_titles: tuple[str, ...]) -> dict:
    """Basic citation alignment: check cited title names appear in retrieved sources."""
    lower_text = answer_text.lower()
    mentioned = [
        t for t in retrieved_titles
        if t.lower() in lower_text
        or any(w.lower() in lower_text for w in t.split() if len(w) > 2)
    ]
    return {
        "retrieved_titles": list(retrieved_titles),
        "mentioned_in_answer": mentioned,
        "citation_coverage": len(mentioned) / len(retrieved_titles) if retrieved_titles else 1.0,
    }


# ---------------------------------------------------------------------------
# Aggregate evaluator
# ---------------------------------------------------------------------------

def evaluate_case(
    case: RAGEvaluationCase,
    answer_text: str,
    retrieved_titles: tuple[str, ...],
) -> dict[str, Any]:
    point_result = check_answer_points(answer_text, case.expected_answer_points)
    forbidden_result = check_forbidden_claims(answer_text, case.forbidden_claims)
    abstain_result = check_abstention_behavior(answer_text, case)
    alignment_result = check_source_alignment(answer_text, retrieved_titles)

    passed = (
        point_result["score"] >= 0.5
        and forbidden_result["passed"]
        and (not case.unanswerable or abstain_result["detected_abstain"])
    )

    return {
        "case_id": case.case_id,
        "category": case.category,
        "answer_category": case.answer_category,
        "expected_points_result": point_result,
        "forbidden_result": forbidden_result,
        "abstention_result": abstain_result,
        "source_alignment_result": alignment_result,
        "passed": passed,
    }
