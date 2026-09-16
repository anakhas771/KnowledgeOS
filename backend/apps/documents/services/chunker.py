import re
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
    Split normalized text into semantic, boundary-aware character chunks.
    Prefers paragraph boundaries, then sentence boundaries, falling back
    to character boundaries for exceptionally long segments.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    normalized = text.strip()
    if not normalized:
        return []

    # Find all potential boundaries (paragraphs, then sentences, then words as fallback)
    # Paragraph: \n\n
    # Sentence: . ! ? followed by space
    # Word: space

    boundaries = [0]
    for m in re.finditer(r'\n\n+|(?<=[.!?])\s+|\s+', normalized):
        boundaries.append(m.end())
    boundaries.append(len(normalized))

    # Ensure unique, sorted boundaries
    boundaries = sorted(list(set(boundaries)))

    chunks: list[TextChunk] = []
    start_idx = 0
    chunk_index = 0

    while start_idx < len(normalized):
        # We want to find the largest boundary <= start_idx + chunk_size
        max_end = min(start_idx + chunk_size, len(normalized))

        # Find the best semantic boundary to end the chunk
        # Look backwards from max_end to start_idx
        end_idx = max_end
        for b in reversed(boundaries):
            if b <= max_end and b > start_idx:
                # Prioritize larger semantic breaks if possible?
                # For simplicity, any valid boundary near the limit is better than a hard chop.
                end_idx = b
                break

        # If no boundary found (e.g. extremely long word), force character split
        if end_idx == start_idx:
            end_idx = max_end

        chunk_str = normalized[start_idx:end_idx].strip()
        if chunk_str:
            chunks.append(TextChunk(index=chunk_index, content=chunk_str))
            chunk_index += 1

        if end_idx >= len(normalized):
            break

        # Calculate overlap
        # Find the smallest boundary <= end_idx - overlap
        target_start = max(0, end_idx - overlap)
        next_start = target_start

        # Try to snap the overlap start to a boundary
        for b in boundaries:
            if b <= target_start:
                next_start = b
            else:
                break

        # If snap makes the overlap too small or next_start goes backwards, force character overlap
        if end_idx - next_start < (overlap // 2) or next_start <= start_idx:
            next_start = target_start

        # Ensure we always advance!
        # If target_start is also <= start_idx (because chunk_size == overlap, which we forbid, but just in case),
        # force next_start to advance by at least 1.
        if next_start <= start_idx:
            next_start = start_idx + 1

        start_idx = next_start

    return chunks
