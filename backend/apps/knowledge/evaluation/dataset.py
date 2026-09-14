from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    relevant_document_titles: tuple[str, ...]
    category: str = "general"


EVALUATION_CASES = (
    # Direct queries
    RetrievalEvaluationCase(
        query="What is KnowledgeOS?",
        relevant_document_titles=("KnowledgeOS Overview",),
        category="direct",
    ),
    RetrievalEvaluationCase(
        query="How does JWT authentication work?",
        relevant_document_titles=("Authentication and RBAC",),
        category="direct",
    ),
    RetrievalEvaluationCase(
        query="How are documents processed?",
        relevant_document_titles=("Document Processing",),
        category="direct",
    ),
    RetrievalEvaluationCase(
        query="How does tenant isolation work?",
        relevant_document_titles=("Tenant Isolation",),
        category="direct",
    ),
    RetrievalEvaluationCase(
        query="How does semantic search work?",
        relevant_document_titles=("Search and Retrieval",),
        category="direct",
    ),

    # Paraphrased queries
    RetrievalEvaluationCase(
        query="What does KnowledgeOS provide for an organization's knowledge?",
        relevant_document_titles=("KnowledgeOS Overview",),
        category="paraphrased",
    ),
    RetrievalEvaluationCase(
        query="How does a user authenticate to the API?",
        relevant_document_titles=("Authentication and RBAC",),
        category="paraphrased",
    ),
    RetrievalEvaluationCase(
        query="What happens to a file after it is uploaded?",
        relevant_document_titles=("Document Processing",),
        category="paraphrased",
    ),
    RetrievalEvaluationCase(
        query="What prevents one organization's documents from being exposed to another?",
        relevant_document_titles=("Tenant Isolation",),
        category="paraphrased",
    ),
    RetrievalEvaluationCase(
        query="How are relevant knowledge chunks found using vectors?",
        relevant_document_titles=("Search and Retrieval",),
        category="paraphrased",
    ),

    # More lexical/distractor-heavy queries
    RetrievalEvaluationCase(
        query="Which part of the platform handles organization roles and protected API access?",
        relevant_document_titles=("Authentication and RBAC",),
        category="lexical",
    ),
    RetrievalEvaluationCase(
        query="Which component turns extracted document text into searchable chunks?",
        relevant_document_titles=("Document Processing",),
        category="lexical",
    ),
    RetrievalEvaluationCase(
        query="How is knowledge scoped to the logged-in user's company?",
        relevant_document_titles=("Tenant Isolation",),
        category="lexical",
    ),
    RetrievalEvaluationCase(
        query="What database technology is used for vector similarity retrieval?",
        relevant_document_titles=("Search and Retrieval",),
        category="lexical",
    ),
    RetrievalEvaluationCase(
        query="What technologies power the knowledge assistant from ingestion through generation?",
        relevant_document_titles=("KnowledgeOS Overview",),
        category="lexical",
    ),
        # Multi-relevant cases
    RetrievalEvaluationCase(
        query="What happens between document upload and semantic search?",
        relevant_document_titles=(
            "Document Processing",
            "Document Extraction",
            "Chunking and Embeddings",
            "Search and Retrieval",
        ),
        category="multi_relevant",
    ),
    RetrievalEvaluationCase(
        query="How does KnowledgeOS authenticate users and control access to protected APIs?",
        relevant_document_titles=(
            "Authentication and RBAC",
            "Authorization and Permissions",
            "API Security",
        ),
        category="multi_relevant",
    ),
    RetrievalEvaluationCase(
        query="How does a user's organization membership affect knowledge access?",
        relevant_document_titles=(
            "Organization Membership",
            "Tenant Isolation",
            "Authentication and RBAC",
        ),
        category="multi_relevant",
    ),
    RetrievalEvaluationCase(
        query="How are documents transformed into vectors and made available for semantic retrieval?",
        relevant_document_titles=(
            "Document Processing",
            "Chunking and Embeddings",
            "Vector Database",
            "Search and Retrieval",
        ),
        category="multi_relevant",
    ),
    RetrievalEvaluationCase(
        query="How does the AI assistant retrieve organizational knowledge before generating an answer?",
        relevant_document_titles=(
            "AI Assistant Architecture",
            "Knowledge Retrieval Architecture",
            "Semantic Search",
            "Search and Retrieval",
        ),
        category="multi_relevant",
    ),
    # Hard-negative cases
    RetrievalEvaluationCase(
        query="Which mechanism determines a user's role when accessing protected APIs?",
        relevant_document_titles=("Authentication and RBAC",),
        category="hard_negative",
    ),
    RetrievalEvaluationCase(
        query="Which database capability supports vector similarity search?",
        relevant_document_titles=("Search and Retrieval",),
        category="hard_negative",
    ),
    RetrievalEvaluationCase(
        query="What happens when uploaded document text is split into chunks before embedding?",
        relevant_document_titles=("Document Processing",),
        category="hard_negative",
    ),
    RetrievalEvaluationCase(
        query="How does the platform prevent API requests from accessing another organization's knowledge?",
        relevant_document_titles=("Tenant Isolation",),
        category="hard_negative",
    ),
    RetrievalEvaluationCase(
        query="Which part of KnowledgeOS turns company knowledge into AI-generated answers?",
        relevant_document_titles=("KnowledgeOS Overview",),
        category="hard_negative",
    ),
)