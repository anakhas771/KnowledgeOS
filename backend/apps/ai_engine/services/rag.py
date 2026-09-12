"""
RAG prompt builder for KnowledgeOS.

Produces a compact, structured prompt that:
  - Instructs the model to answer ONLY from the supplied context
  - Asks the model to say so when the context is insufficient
  - Includes document title and chunk content for each source
  - Avoids verbosity and never exposes embedding vectors or internal IDs
"""

from __future__ import annotations

_SYSTEM_BLOCK = """\
You are KnowledgeOS, an enterprise knowledge assistant.
Answer only from the supplied knowledge context below.
If the context does not contain enough information to answer confidently, say so clearly.
Do not invent facts. Do not reference information outside the context.\
"""


def build_rag_prompt(query: str, chunks: list[dict]) -> str:
    """
    Build a RAG prompt from a user query and retrieved document chunks.

    Args:
        query:  The raw user question (already validated / stripped).
        chunks: List of retrieval result dicts, each containing at minimum:
                  - document_title (str)
                  - content (str)
                The chunk dicts may also contain chunk_id, document_id, and
                score, but those fields are intentionally excluded from the
                prompt text.

    Returns:
        A formatted string prompt ready to send to the LLM.
    """
    context_lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        title = chunk.get("document_title", "Unknown Document")
        content = chunk.get("content", "").strip()
        context_lines.append(
            f"[Source {idx}]\n"
            f"Document: {title}\n"
            f"Content: {content}"
        )

    context_block = "\n\n".join(context_lines) if context_lines else "(No context retrieved.)"

    prompt = (
        f"SYSTEM:\n{_SYSTEM_BLOCK}\n\n"
        f"CONTEXT:\n{context_block}\n\n"
        f"USER QUESTION:\n{query}"
    )
    return prompt
