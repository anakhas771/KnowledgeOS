from __future__ import annotations

from apps.knowledge.services.query_embedding import embed_query
from apps.knowledge.services.retrieval import search_similar_chunks
from apps.organizations.models import Organization


EVALUATION_ORG_SLUG = "knowledgeos-retrieval-evaluation"

DIAGNOSTIC_QUERIES = (
    "How are relevant knowledge chunks found using vectors?",
    "How does the platform prevent API requests from accessing another organization's knowledge?",
    "How does the AI assistant retrieve organizational knowledge before generating an answer?",
)


def run_diagnostics() -> None:
    organization = Organization.objects.get(
        slug=EVALUATION_ORG_SLUG,
    )

    for query in DIAGNOSTIC_QUERIES:
        embedding = embed_query(query)

        results = search_similar_chunks(
            organization_id=organization.id,
            query_embedding=embedding,
            limit=10,
        )

        print("\n" + "=" * 70)
        print(f"Query: {query}")
        print("=" * 70)

        for rank, result in enumerate(results, start=1):
            print(
                f"{rank:>2}. "
                f"document_id={result['document_id']} | "
                f"title={result['document_title']} | "
                f"score={result['score']:.4f}"
            )