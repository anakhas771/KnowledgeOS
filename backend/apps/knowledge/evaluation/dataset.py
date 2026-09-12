from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    relevant_document_titles: tuple[str, ...]


EVALUATION_CASES = (
    # Direct queries
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

    # Paraphrased queries
    RetrievalEvaluationCase(
        query="What does KnowledgeOS provide for an organization's knowledge?",
        relevant_document_titles=("KnowledgeOS Overview",),
    ),
    RetrievalEvaluationCase(
        query="How does a user authenticate to the API?",
        relevant_document_titles=("Authentication and RBAC",),
    ),
    RetrievalEvaluationCase(
        query="What happens to a file after it is uploaded?",
        relevant_document_titles=("Document Processing",),
    ),
    RetrievalEvaluationCase(
        query="What prevents one organization's documents from being exposed to another?",
        relevant_document_titles=("Tenant Isolation",),
    ),
    RetrievalEvaluationCase(
        query="How are relevant knowledge chunks found using vectors?",
        relevant_document_titles=("Search and Retrieval",),
    ),

    # More lexical/distractor-heavy queries
    RetrievalEvaluationCase(
        query="Which part of the platform handles organization roles and protected API access?",
        relevant_document_titles=("Authentication and RBAC",),
    ),
    RetrievalEvaluationCase(
        query="Which component turns extracted document text into searchable chunks?",
        relevant_document_titles=("Document Processing",),
    ),
    RetrievalEvaluationCase(
        query="How is knowledge scoped to the logged-in user's company?",
        relevant_document_titles=("Tenant Isolation",),
    ),
    RetrievalEvaluationCase(
        query="What database technology is used for vector similarity retrieval?",
        relevant_document_titles=("Search and Retrieval",),
    ),
    RetrievalEvaluationCase(
        query="What technologies power the knowledge assistant from ingestion through generation?",
        relevant_document_titles=("KnowledgeOS Overview",),
    ),
    # Multi-relevant cases
    RetrievalEvaluationCase(
        query="What happens between document upload and semantic search?",
        relevant_document_titles=(
            "Document Processing",
            "Search and Retrieval",
        ),
    ),
    RetrievalEvaluationCase(
        query="How does KnowledgeOS authenticate users and isolate their organization's knowledge?",
        relevant_document_titles=(
            "Authentication and RBAC",
            "Tenant Isolation",
        ),
    ),
    RetrievalEvaluationCase(
        query="What technologies are involved from document ingestion through semantic retrieval?",
        relevant_document_titles=(
            "KnowledgeOS Overview",
            "Document Processing",
            "Search and Retrieval",
        ),
    ),
    RetrievalEvaluationCase(
        query="Which parts of the system control API access and organization-scoped retrieval?",
        relevant_document_titles=(
            "Authentication and RBAC",
            "Tenant Isolation",
        ),
    ),
    RetrievalEvaluationCase(
        query="How are uploaded documents turned into searchable knowledge and then retrieved?",
        relevant_document_titles=(
            "Document Processing",
            "Search and Retrieval",
        ),
    ),
)