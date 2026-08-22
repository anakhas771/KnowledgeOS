from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model once per worker process.
    """

    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """
    Generate a normalized embedding for a single text chunk.
    """

    model = get_embedding_model()

    embedding = model.encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()
