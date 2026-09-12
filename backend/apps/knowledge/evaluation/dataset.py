from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    relevant_document_titles: tuple[str, ...]


EVALUATION_CASES = (
    RetrievalEvaluationCase(
        query="What is KnowledgeOS?",
        relevant_document_titles=("KnowledgeOS Overview",),
    ),
    RetrievalEvaluationCase(
        query="How does JWT authentication work?",
        relevant_document_titles=("Authentication and RBAC",),
    ),
    RetrievalEvaluationCase(
        query="How are documents processed?",
        relevant_document_titles=("Document Processing",),
    ),
    RetrievalEvaluationCase(
        query="How does tenant isolation work?",
        relevant_document_titles=("Tenant Isolation",),
    ),
    RetrievalEvaluationCase(
        query="How does semantic search work?",
        relevant_document_titles=("Search and Retrieval",),
    ),
)