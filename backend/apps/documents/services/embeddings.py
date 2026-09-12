import os

import httpx


EMBEDDING_SERVICE_URL = os.getenv(
    "EMBEDDING_SERVICE_URL",
    "http://embedding-service:8100",
)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    response = httpx.post(
        f"{EMBEDDING_SERVICE_URL}/embed",
        json={"texts": texts},
        timeout=120.0,
    )

    response.raise_for_status()

    payload = response.json()

    embeddings = payload["embeddings"]

    if not embeddings:
        raise ValueError("Embedding service returned no embeddings.")

    if len(embeddings[0]) != 384:
        raise ValueError(
            "Unexpected embedding dimensions: "
            f"{len(embeddings[0])}"
        )

    return embeddings


def embed_text(text: str) -> list[float]:
    if not text.strip():
        raise ValueError("Text cannot be empty.")

    return embed_texts([text])[0]