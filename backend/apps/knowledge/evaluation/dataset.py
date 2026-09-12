from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    relevant_document_ids: tuple[int, ...]


# Document IDs are intentionally placeholders.
#
# Before running the benchmark, replace these with IDs belonging
# to the controlled evaluation dataset for the target organization.
EVALUATION_CASES = (
    RetrievalEvaluationCase(
        query="What is KnowledgeOS?",
        relevant_document_ids=(),
    ),
    RetrievalEvaluationCase(
        query="How does authentication work?",
        relevant_document_ids=(),
    ),
    RetrievalEvaluationCase(
        query="How are documents processed?",
        relevant_document_ids=(),
    ),
    RetrievalEvaluationCase(
        query="How does tenant isolation work?",
        relevant_document_ids=(),
    ),
)