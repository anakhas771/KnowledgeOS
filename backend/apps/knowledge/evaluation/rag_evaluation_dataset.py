"""
Phase 8 expanded RAG evaluation dataset.

20 focused cases derived from existing chunking corpus / evaluation corpus.
Balanced by category; unanswerable cases included; expected points
and forbidden claims specified where useful.
Every case is auditable against the evaluation-only document set.
Does NOT change production retrieval/generation/embedding/chunking.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

@dataclass(frozen=True)
class RAGEvaluationCase:
    case_id: str
    query: str
    relevant_document_titles: tuple[str, ...]
    category: str  # direct / paraphrased / lexical / multi_relevant / hard_negative / unanswerable
    answer_category: str = "factual"  # factual / multi_source / unanswerable / groundedness
    expected_answer_points: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    unanswerable: bool = False
    notes: str = ""

    # Define allowed categories for validation
    ALLOWED_CATEGORIES: ClassVar[tuple[str, ...]] = (
        "direct", "paraphrased", "lexical", "multi_relevant",
        "hard_negative", "unanswerable"
    )

    ALLOWED_ANSWER_CATEGORIES: ClassVar[tuple[str, ...]] = (
        "factual", "multi_source", "unanswerable", "groundedness"
    )

    def __post_init__(self):
        # Validate categories to catch inconsistencies
        if self.category not in self.ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'. Must be one of {self.ALLOWED_CATEGORIES}")
        if self.answer_category not in self.ALLOWED_ANSWER_CATEGORIES:
            raise ValueError(f"Invalid answer_category '{self.answer_category}'. Must be one of {self.ALLOWED_ANSWER_CATEGORIES}")


RAG_EVALUATION_CASES: tuple[RAGEvaluationCase, ...] = (
    # --- 4 direct factual ---
    RAGEvaluationCase(
        case_id="rag_d01",
        query="What is KnowledgeOS?",
        relevant_document_titles=("KnowledgeOS Overview",),
        category="direct",
        answer_category="factual",
        expected_answer_points=(
            "enterprise knowledge intelligence platform",
            "semantic search and AI-assisted answers",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_d02",
        query="How does document ingestion work in KnowledgeOS?",
        relevant_document_titles=("Document Processing", "Ingestion Pipeline"),
        category="direct",
        answer_category="factual",
        expected_answer_points=(
            "asynchronous processing through a task queue",
            "documents converted into retrieval-ready form",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_d03",
        query="What is the purpose of chunking and embeddings?",
        relevant_document_titles=("Chunking and Embeddings",),
        category="direct",
        answer_category="factual",
        expected_answer_points=(
            "divide documents into retrieval units",
            "convert into dense vector representations",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_d04",
        query="How is retrieval filtered by tenant?",
        relevant_document_titles=("Tenant Isolation",),
        category="direct",
        answer_category="factual",
        expected_answer_points=(
            "retrieval is filtered by organization on every query",
            "one tenant's knowledge invisible to another",
        ),
    ),

    # --- 4 paraphrased ---
    RAGEvaluationCase(
        case_id="rag_p01",
        query="How does a user authenticate to the API?",
        relevant_document_titles=("Authentication and RBAC",),
        category="paraphrased",
        answer_category="factual",
        expected_answer_points=(
            "JWT-based authentication",
            "token validated before endpoint access",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_p02",
        query="What controls whether a user can use protected APIs?",
        relevant_document_titles=("Authorization and Permissions",),
        category="paraphrased",
        answer_category="factual",
        expected_answer_points=(
            "role-based permissions",
            "permission layer evaluates role",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_p03",
        query="How is organizational membership managed?",
        relevant_document_titles=("Organization Membership",),
        category="paraphrased",
        answer_category="factual",
        expected_answer_points=(
            "administrator manages organization configuration and membership",
            "organization read from user record rather than request",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_p04",
        query="What happens when a document is uploaded?",
        relevant_document_titles=("Ingestion Pipeline", "Document Processing"),
        category="paraphrased",
        answer_category="factual",
        expected_answer_points=(
            "processed asynchronously",
            "extracted, normalized, chunked, embedded",
        ),
    ),

    # --- 4 lexical / keyword-heavy ---
    RAGEvaluationCase(
        case_id="rag_l01",
        query="JWT token signature expiry validation endpoint access",
        relevant_document_titles=("Authentication and RBAC", "API Security"),
        category="lexical",
        answer_category="factual",
        expected_answer_points=(
            "token signature and expiry validated",
            "rejected before reaching knowledge logic",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_l02",
        query="pgvector cosine similarity retrieval chunk embedding",
        relevant_document_titles=("Vector Database", "Chunking and Embeddings"),
        category="lexical",
        answer_category="factual",
        expected_answer_points=(
            "cosine similarity search",
            "dense vector representations stored in pgvector",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_l03",
        query="organization tenant isolation retrieval filter user record",
        relevant_document_titles=("Tenant Isolation",),
        category="lexical",
        answer_category="factual",
        expected_answer_points=(
            "retrieval filtered by organization",
            "organization read from authenticated user",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_l04",
        query="semantic search AI-assisted answers grounding context",
        relevant_document_titles=("Semantic Search", "Knowledge Retrieval Architecture"),
        category="lexical",
        answer_category="factual",
        expected_answer_points=(
            "semantic search over organization knowledge",
            "answers grounded in retrieved chunks",
        ),
    ),

    # --- 3 multi-relevant / multi-source ---
    RAGEvaluationCase(
        case_id="rag_m01",
        query="How does KnowledgeOS authenticate users and control access to protected APIs?",
        relevant_document_titles=("Authentication and RBAC", "Authorization and Permissions", "API Security"),
        category="multi_relevant",
        answer_category="multi_source",
        expected_answer_points=(
            "JWT authentication establishes identity",
            "role-based permissions control access",
            "layered mechanisms combine authentication, authorization, and tenant filtering",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_m02",
        query="How does document ingestion lead from upload to retrieval?",
        relevant_document_titles=("Document Processing", "Ingestion Pipeline", "Chunking and Embeddings", "Vector Database"),
        category="multi_relevant",
        answer_category="multi_source",
        expected_answer_points=(
            "asynchronous ingestion pipeline",
            "chunking and embedding produce dense vectors",
            "pgvector stores and retrieves via cosine similarity",
        ),
    ),
    RAGEvaluationCase(
        case_id="rag_m03",
        query="What makes retrieval both accurate and secure?",
        relevant_document_titles=("Search and Retrieval", "Tenant Isolation", "API Security"),
        category="multi_relevant",
        answer_category="multi_source",
        expected_answer_points=(
            "semantic search using embeddings and cosine similarity",
            "tenant filtering restricts to user's organization",
            "authorization layered after authentication",
        ),
    ),

    # --- 2 hard-negative ---
    RAGEvaluationCase(
        case_id="rag_h01",
        query="Which mechanism determines a user's role when accessing protected APIs?",
        relevant_document_titles=("Authentication and RBAC",),
        category="hard_negative",
        answer_category="factual",
        expected_answer_points=(
            "role checks happen after authentication succeeds",
            "permission layer evaluates role, not authentication",
        ),
        forbidden_claims=("authentication decides role",),
    ),
    RAGEvaluationCase(
        case_id="rag_h02",
        query="Can a user widen access by providing a different organization identifier?",
        relevant_document_titles=("Tenant Isolation", "API Security"),
        category="hard_negative",
        answer_category="factual",
        expected_answer_points=(
            "organization read from user record, not request",
            "scope never taken from request body",
        ),
        forbidden_claims=("request can override organization",),
    ),

    # --- 3 unanswerable / insufficient-evidence ---
    RAGEvaluationCase(
        case_id="rag_u01",
        query="What is the exact number of active users right now?",
        relevant_document_titles=(),
        category="unanswerable",
        answer_category="unanswerable",
        unanswerable=True,
        expected_answer_points=(),
        forbidden_claims=("Provides a specific user count", "exact number"),
        notes="Not present in evaluation corpus; expected abstention.",
    ),
    RAGEvaluationCase(
        case_id="rag_u02",
        query="Which specific employee registered document X on which exact date?",
        relevant_document_titles=(),
        category="unanswerable",
        answer_category="unanswerable",
        unanswerable=True,
        expected_answer_points=(),
        forbidden_claims=("specific date", "specific employee registered"),
        notes="No ingestion audit log or per-document registration metadata in corpus.",
    ),
    RAGEvaluationCase(
        case_id="rag_u03",
        query="How many chunks does the organization currently have in total?",
        relevant_document_titles=(),
        category="unanswerable",
        answer_category="unanswerable",
        unanswerable=True,
        expected_answer_points=(),
        forbidden_claims=("total chunks", "current count"),
        notes="No aggregate chunk count in corpus; retrieval does not expose totals.",
    ),
)
def get_cases(category: str | None = None) -> tuple[RAGEvaluationCase, ...]:
    cases = RAG_EVALUATION_CASES
    if category is not None:
        cases = tuple(c for c in cases if c.category == category)
    return cases