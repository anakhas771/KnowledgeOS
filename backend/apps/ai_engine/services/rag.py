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

def _truncate_history(history_lines: list[str], max_chars: int = 2000) -> str:
    """
    Truncates the history from oldest to newest to fit within max_chars.
    Keeps the most recent messages.
    """
    if not history_lines:
        return ""

    selected_lines = []
    current_length = 0
    # Process from newest (end) to oldest (start)
    for line in reversed(history_lines):
        if current_length + len(line) + 1 > max_chars:
            break
        selected_lines.insert(0, line)
        current_length += len(line) + 1

    return "\n".join(selected_lines)


def build_rag_prompt(query: str, chunks: list[dict], history: list[dict] | None = None) -> str:
    """
    Build a RAG prompt from a user query, retrieved document chunks, and optional history.

    Args:
        query:  The raw user question (already validated / stripped).
        chunks: List of retrieval result dicts.
        history: Optional list of previous messages dicts. Format:
                 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]

    Returns:
        A formatted string prompt ready to send to the LLM.
    """
    # 1. Format Context
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

    # 2. Format History
    history_block = ""
    if history:
        history_lines = []
        for msg in history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            history_lines.append(f"{role}: {content}")

        truncated_history = _truncate_history(history_lines, max_chars=2000)
        if truncated_history:
            history_block = f"CONVERSATION HISTORY:\n{truncated_history}\n\n"

    prompt = (
        f"SYSTEM:\n{_SYSTEM_BLOCK}\n\n"
        f"{history_block}"
        f"CONTEXT:\n{context_block}\n\n"
        f"USER QUESTION:\n{query}"
    )
    return prompt
