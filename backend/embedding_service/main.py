from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .service import embed_texts, get_model


app = FastAPI(
    title="KnowledgeOS Embedding Service",
    version="1.0.0",
)


class EmbeddingRequest(BaseModel):
    texts: list[str] = Field(
        min_length=1,
        max_length=64,
    )


class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]]
    dimensions: int


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "knowledgeos-embedding",
    }


@app.post("/embed", response_model=EmbeddingResponse)
def embed(request: EmbeddingRequest):
    cleaned = [
        text.strip()
        for text in request.texts
        if text.strip()
    ]

    if not cleaned:
        raise HTTPException(
            status_code=400,
            detail="At least one non-empty text is required.",
        )

    embeddings = embed_texts(cleaned)

    return {
        "embeddings": embeddings,
        "dimensions": len(embeddings[0]),
    }