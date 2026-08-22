from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[TextChunk]:
    """
    Split normalized text into overlapping character-based chunks.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0:
        raise ValueError("overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size."
        )

    normalized = text.strip()

    if not normalized:
        return []

    chunks: list[TextChunk] = []

    start = 0
    chunk_index = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = normalized[start:end].strip()

        if chunk:
            chunks.append(
                TextChunk(
                    index=chunk_index,
                    content=chunk,
                )
            )
            chunk_index += 1

        if end >= text_length:
            break

        start = end - overlap

    return chunks
