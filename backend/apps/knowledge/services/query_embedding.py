from apps.documents.services.embeddings import embed_text


def embed_query(query: str) -> list[float]:
    query = query.strip()

    if not query:
        raise ValueError(
            "Query cannot be empty or whitespace only."
        )

    return embed_text(query)