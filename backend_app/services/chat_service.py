import json
import logging
from typing import List, Tuple

from haystack import Document as HaystackDocument

from .cache_service import get_cached, set_cached
from .retrieval_service import retrieve_rag, retrieve_web
from .prompt_service import build_rag_prompt, build_query_prompt, build_code_prompt, merge_context

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Chat Service — orkiestracja: cache → retrieval → prompt → LLM → response
# Wydzielony z routes/chat.py (A1a refaktoryzacja)
# ---------------------------------------------------------------------------


def run_tool_loop(
    llm_component,
    initial_prompt: str,
    request_id: str = "-",
    label: str = "Tool",
    max_iterations: int = 3,
) -> str:
    """Wykonuje pętlę LLM + tool calling (max 3 iteracje).

    Zwraca finalną odpowiedź jako string.
    """
    from ..utils.tools import maybe_parse_tool_request, execute_tool

    current_prompt = initial_prompt
    answer: str = ""
    for iteration in range(max_iterations):
        llm_result = llm_component.run(prompt=current_prompt)
        answer = llm_result["replies"][0]
        tool_req = maybe_parse_tool_request(answer)
        if not tool_req:
            break
        try:
            tool_out = execute_tool(tool_req)
            logger.debug(
                "[%s] Iteration %d: %s",
                label,
                iteration + 1,
                tool_req.get("function", "unknown"),
                extra={"request_id": request_id},
            )
        except Exception as e:
            tool_out = {"tool_error": str(e), "tool_request": tool_req}
        current_prompt = (
            current_prompt
            + "\n\nTOOL_RESULT (JSON):\n"
            + json.dumps(tool_out, ensure_ascii=False)[:8000]
            + "\n\nNow answer the user question using the TOOL_RESULT."
        )
    return answer


def handle_query(
    query: str,
    request_id: str = "-",
) -> Tuple[str, bool]:
    """Obsługuje /query — RAG + web search + tool calling.

    Zwraca (answer, cached).
    """
    from ..services import get_text_embedder
    from ..services.qdrant import get_qdrant_retriever
    from ..utils.tools import tool_instructions
    from ddgs import DDGS

    cached = get_cached(query)
    if cached:
        return cached, True

    # Retrieve z Qdrant
    from ..services.retrieval_service import retrieve_rag as _retrieve_rag
    query_embedding = get_text_embedder().run(text=query)
    retriever = get_qdrant_retriever()
    retrieval_result = retriever.run(query_embedding=query_embedding["embedding"])
    local_docs = retrieval_result.get("documents", [])
    logger.info(
        "[RAG] Minimal retrieval: %d dokumentów", len(local_docs),
        extra={"request_id": request_id},
    )

    # Web search
    web_doc, _ = retrieve_web(query, request_id=request_id)
    all_docs = list(local_docs)
    if web_doc:
        all_docs.append(web_doc)

    # Build prompt + LLM
    from ..services import get_llm_component
    prompt = build_query_prompt(query, all_docs, tool_instructions())
    answer = run_tool_loop(get_llm_component(), prompt, request_id=request_id, label="Query")

    set_cached(query, answer)
    return answer, False


def handle_chat_completions(
    user_message: str,
    use_rag: bool,
    web_search: bool,
    top_k: int,
    embedding_model: str,
    request_id: str = "-",
) -> Tuple[str, List[str]]:
    """Obsługuje /v1/chat/completions — opcjonalny RAG + web + LLM.

    Zwraca (answer, sources).
    """
    from ..services import get_llm_component

    rag_docs: List[HaystackDocument] = []
    sources: List[str] = []
    web_doc = None

    if use_rag:
        rag_docs, rag_sources = retrieve_rag(
            user_message, top_k=top_k,
            embedding_model=embedding_model,
            request_id=request_id,
        )
        sources.extend(rag_sources)

    if web_search:
        web_doc, web_sources = retrieve_web(user_message, request_id=request_id)
        sources.extend(web_sources)

    context_text = merge_context(rag_docs, web_doc)
    full_prompt = build_rag_prompt(user_message, context_text)

    llm_result = get_llm_component().run(prompt=full_prompt)
    answer = llm_result["replies"][0]
    return answer, sources


def handle_code_query(
    query: str,
    request_id: str = "-",
) -> str:
    """Obsługuje /code_query — RAG + tool calling dla kodu.

    Zwraca answer jako string.
    """
    from ..services import get_text_embedder, get_llm_component
    from ..services.qdrant import get_qdrant_retriever
    from ..utils.tools import tool_instructions

    query_embedding = get_text_embedder().run(text=query)
    retriever = get_qdrant_retriever()
    retrieval_result = retriever.run(query_embedding=query_embedding["embedding"])
    local_docs = retrieval_result.get("documents", [])
    logger.info(
        "[Code Query] Minimal retrieval: %d dokumentów", len(local_docs),
        extra={"request_id": request_id},
    )

    prompt = build_code_prompt(query, local_docs, tool_instructions())
    return run_tool_loop(
        get_llm_component(), prompt, request_id=request_id, label="Code Tool"
    )
