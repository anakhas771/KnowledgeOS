from apps.documents.services.embeddings import get_embedding_model

def embed_query(query: str) -> list[float]:
    """
    Generate an embedding for a user query.
    Validates empty queries and reuses the cached model.
    """
    query = query.strip()
    if not query:
        raise ValueError("Query cannot be empty or whitespace only.")
    
    model = get_embedding_model()
    
    embedding = model.encode(
        query,
        normalize_embeddings=True,
    )
    
    return embedding.tolist()
