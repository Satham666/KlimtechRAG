from typing import List

from haystack import Document as HaystackDocument

# ---------------------------------------------------------------------------
# Prompt Service — budowanie promptów do LLM
# Wydzielony z routes/chat.py (A1a refaktoryzacja)
# ---------------------------------------------------------------------------

RAG_PROMPT = """Jesteś pomocnym asystentem AI z dostępem do bazy wiedzy RAG.
Odpowiadaj na podstawie dostarczonego kontekstu. Jeśli nie znajdziesz odpowiedzi w kontekście,
powiedz o tym szczerze. Odpowiadaj po polsku, chyba że użytkownik pyta w innym języku."""

CODE_PROMPT = "You are a Senior Python Developer. Analyze the following code/docs strictly."


def build_rag_prompt(user_message: str, context_text: str) -> str:
    """Buduje prompt dla endpointu /v1/chat/completions z opcjonalnym kontekstem RAG."""
    if context_text:
        return (
            f"{RAG_PROMPT}\n\n"
            f"=== KONTEKST Z BAZY WIEDZY ===\n{context_text}\n=== KONIEC KONTEKSTU ===\n\n"
            f"PYTANIE UŻYTKOWNIKA: {user_message}\n\nODPOWIEDŹ:"
        )
    return f"{RAG_PROMPT}\n\nPYTANIE: {user_message}\n\nODPOWIEDŹ:"


def build_query_prompt(query: str, docs: List[HaystackDocument], tool_instructions: str) -> str:
    """Buduje prompt dla endpointu /query z tool calling."""
    prompt = ""
    for doc in docs:
        prompt += f"{doc.content}\n"
    prompt += f"\n\n{tool_instructions}\n\n"
    prompt += f"USER_QUESTION: {query}\n"
    return prompt


def build_code_prompt(query: str, docs: List[HaystackDocument], tool_instructions: str) -> str:
    """Buduje prompt dla endpointu /code_query z tool calling."""
    prompt = f"{CODE_PROMPT}\n\nContext:\n"
    for doc in docs:
        prompt += f"{doc.content}\n"
    prompt += f"\n\n{tool_instructions}\n\n"
    prompt += f"CODE_QUESTION: {query}\n\nProvide a technical answer."
    return prompt


def merge_context(rag_docs: List[HaystackDocument], web_doc: HaystackDocument | None) -> str:
    """Łączy dokumenty RAG i wynik web search w jeden string kontekstu."""
    parts = [doc.content for doc in rag_docs if doc.content]
    if web_doc:
        parts.append(web_doc.content)
    return "\n\n---\n\n".join(parts)
