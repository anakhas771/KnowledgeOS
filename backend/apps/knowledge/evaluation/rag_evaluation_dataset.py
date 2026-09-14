"""
Phase 7 RAG evaluation dataset.

Derived from existing evaluation cases (EVALUATION_CASES) with added
answer-evaluation fields. Focused (not expansive); structured and auditable.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RAGEvaluationCase:
    case_id: str
    query: str
    relevant_document_titles: tuple[str, ...]
    category: str  # direct / paraphrased / lexical / multi_relevant / hard_negative
    answer_category: str = "factual"  # factual / multi_source / unanswerable / groundedness
    expected_answer_points: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    unanswerable: bool = False
    notes: str = ""


RAG_EVALUATION_CASES: tuple[RAGEvaluationCase, ...] = (
    RAGEvaluationCase(
        case_id="rag_direct_01",
        query="What is KnowledgeOS?",
        relevant_document_titles=("KnowledgeOS Overview",),
        category="direct",
        answer_category="factual",
        expected_answer_points=(
            "KnowledgeOS is an enterprise knowledge intelligence platform",
            "Provides semantic search and AI-assisted answers",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_paraphrased_01",
        query="How does a user authenticate to the API?",
        relevant_document_titles=("Authentication and RBAC",),
        category="paraphrased",
        answer_category="factual",
        expected_answer_points=(
            "JWT-based authentication",
            "Token is validated before endpoint access",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_multi_01",
        query="How does KnowledgeOS authenticate users and control access to protected APIs?",
        relevant_document_titles=(
            "Authentication and RBAC",
            "Authorization and Permissions",
            "API Security",
        ),
        category="multi_relevant",
        answer_category="multi_source",
        expected_answer_points=(
            "JWT authentication establishes identity",
            "Role-based permissions control access",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_unanswerable_01",
        query="What is the exact number of active users right now?",
        relevant_document_titles=(),
        category="direct",
        answer_category="unanswerable",
        unanswerable=True,
        expected_answer_points=(),
        forbidden_claims=("Provides a specific user count",),
        notes="Not present in evaluation corpus; expected behavior is abstention / insufficient evidence.",
    ),
    RAGEvaluationCase(
        case_id="rag_hardneg_01",
        query="Which mechanism determines a user's role when accessing protected APIs?",
        relevant_document_titles=("Authentication and RBAC",),
        category="hard_negative",
        answer_category="factual",
        expected_answer_points=(
            "Role checks happen after authentication",
            "Permission layer evaluates role",
        ),
    ),
)


def get_cases(category: str | None = None) -> tuple[RAGEvaluationCase, ...]:
    cases = RAG_EVALUATION_CASES
    if category is not None:
        cases = tuple(c for c in cases if c.category == category)
    return cases
