import json
import logging
import time
from typing import Dict, Tuple, Optional

from duckduckgo_search import DDGS
from fastapi import APIRouter, Depends, HTTPException, Request
from haystack import Document as HaystackDocument

from ..config import settings
from ..models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    ChatMessage,
    QueryRequest,
    CodeQueryRequest,
)
from ..services import rag_pipeline, doc_store, text_embedder
from ..services.llm import get_llm_component
from ..utils.rate_limit import apply_rate_limit, get_client_id
from ..utils.dependencies import require_api_key, get_request_id
from ..utils.tools import tool_instructions, maybe_parse_tool_request, execute_tool
from ..monitoring import log_stats

router = APIRouter(tags=["chat"])
logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Cache odpowiedzi z TTL i limitem rozmiaru
# ---------------------------------------------------------------------------

_answer_cache: Dict[str, Tuple[str, float]] = {}
CACHE_TTL = 3600          # 1 godzina
CACHE_MAX_SIZE = 500


def get_cached(query: str) -> Optional[str]:
    if query in _answer_cache:
        answer, ts = _answer_cache[query]
        if time.time() - ts < CACHE_TTL:
            return answer
        del _answer_cache[query]
    return None


def set_cached(query: str, answer: str) -> None:
    if len(_answer_cache) >= CACHE_MAX_SIZE:
        # Usuń najstarszy wpis
        oldest = min(_answer_cache, key=lambda k: _answer_cache[k][1])
        del _answer_cache[oldest]
    _answer_cache[query] = (answer, time.time())


def clear_cache() -> None:
    global _answer_cache
    _answer_cache.clear()
    logger.info("Cache odpowiedzi wyczyszczony")


# ---------------------------------------------------------------------------
# System prompt RAG
# ---------------------------------------------------------------------------

RAG_PROMPT = """Jesteś pomocnym asystentem AI z dostępem do bazy wiedzy RAG.
Odpowiadaj na podstawie dostarczonego kontekstu. Jeśli nie znajdziesz odpowiedzi w kontekście,
powiedz o tym szczerze. Odpowiadaj po polsku, chyba że użytkownik pyta w innym języku."""


# ---------------------------------------------------------------------------
# GET /v1/models — wymagane przez Open WebUI
# ---------------------------------------------------------------------------

@router.get("/v1/models")
async def list_models():
    """Zwraca dostępne modele — wymagane przez klientów OpenAI-compatible (np. OWUI)."""
    model_name = settings.llm_model_name or "klimtech-bielik"
    return {
        "object": "list",
        "data": [
            {
                "id": model_name,
                "object": "model",
                "created": 1700000000,
                "owned_by": "klimtechrag",
                "permission": [],
                "root": model_name,
                "parent": None,
            }
        ],
    }


# ---------------------------------------------------------------------------
# POST /v1/embeddings — wymagane przez OWUI RAG (Wariant C)
# ---------------------------------------------------------------------------

@router.post("/v1/embeddings")
async def create_embeddings(body: dict, req: Request):
    """
    OpenAI-compatible embeddings endpoint.
    OWUI używa go do tworzenia wektorów przy ingeście do Knowledge Base
    oraz przy wyszukiwaniu RAG.
    Model: intfloat/multilingual-e5-large (wymiar 1024) — ten sam co klimtech_docs.
    """
    input_data = body.get("input", "")

    # input może być stringiem lub listą stringów
    if isinstance(input_data, str):
        inputs = [input_data]
    elif isinstance(input_data, list):
        inputs = input_data
    else:
        raise HTTPException(status_code=400, detail="'input' must be string or list of strings")

    embeddings = []
    for i, text in enumerate(inputs):
        try:
            result = text_embedder.run(text=str(text))
            embedding = result["embedding"]
            embeddings.append({
                "object": "embedding",
                "embedding": embedding,
                "index": i,
            })
        except Exception as e:
            logger.exception("[Embeddings] Błąd dla inputu %d: %s", i, e)
            raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

    total_tokens = sum(len(str(t).split()) for t in inputs)
    return {
        "object": "list",
        "data": embeddings,
        "model": settings.embedding_model,
        "usage": {
            "prompt_tokens": total_tokens,
            "total_tokens": total_tokens,
        },
    }


# ---------------------------------------------------------------------------
# POST /query — podstawowy RAG query
# ---------------------------------------------------------------------------

@router.post("/query")
async def query_rag(
    request: QueryRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    cached = get_cached(request.query)
    if cached:
        return {"answer": cached, "cached": True}

    try:
        rag_result = rag_pipeline.run(
            {
                "embedder": {"text": request.query},
                "prompt_builder": {"query": request.query},
            },
            include_outputs_from={"retriever"},
        )
        local_docs = rag_result["retriever"]["documents"]

        web_snippet = ""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(request.query, max_results=2))
                if results:
                    web_snippet = " | ".join([res.get("body", "") for res in results])
        except Exception as e:
            logger.warning("Web search error: %s", e, extra={"request_id": request_id})

        final_docs = list(local_docs)
        if web_snippet:
            final_docs.append(HaystackDocument(content=web_snippet, meta={"source": "Web Search"}))

        prompt_text = ""
        for doc in final_docs:
            prompt_text += f"{doc.content}\n"
        prompt_text += "\n\n" + tool_instructions() + "\n\n"
        prompt_text += f"USER_QUESTION: {request.query}\n"

        llm_component = get_llm_component()
        current_prompt = prompt_text
        answer: str = ""
        for _ in range(3):
            llm_result = llm_component.run(prompt=current_prompt)
            answer = llm_result["replies"][0]
            tool_req = maybe_parse_tool_request(answer)
            if not tool_req:
                break
            try:
                tool_out = execute_tool(tool_req)
            except Exception as e:
                tool_out = {"tool_error": str(e), "tool_request": tool_req}
            current_prompt = (
                current_prompt
                + "\n\nTOOL_RESULT (JSON):\n"
                + json.dumps(tool_out, ensure_ascii=False)[:8000]
                + "\n\nNow answer the user question using the TOOL_RESULT."
            )

        set_cached(request.query, answer)
        return {"answer": answer, "cached": False}

    except Exception as e:
        logger.exception("Error in /query: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /v1/chat/completions — OpenAI-compatible (główny endpoint OWUI)
# ---------------------------------------------------------------------------

@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def openai_chat_completions(
    request: ChatCompletionRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    context_text = ""
    sources = []

    if request.use_rag:
        try:
            from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
            query_embedding = text_embedder.run(text=user_message)
            retriever = QdrantEmbeddingRetriever(document_store=doc_store, top_k=request.top_k)
            retrieval_result = retriever.run(query_embedding=query_embedding["embedding"])
            docs = retrieval_result.get("documents", [])
            if docs:
                context_text = "\n\n---\n\n".join(doc.content for doc in docs if doc.content)
                sources = [doc.meta.get("source", "unknown") for doc in docs]
                logger.info("[RAG] %d dokumentów: %s", len(docs), ", ".join(sources),
                            extra={"request_id": request_id})
        except Exception as e:
            logger.warning("[RAG] Błąd retrieval: %s", str(e), extra={"request_id": request_id})

    if context_text:
        full_prompt = (
            f"{RAG_PROMPT}\n\n"
            f"=== KONTEKST Z BAZY WIEDZY ===\n{context_text}\n=== KONIEC KONTEKSTU ===\n\n"
            f"PYTANIE UŻYTKOWNIKA: {user_message}\n\nODPOWIEDŹ:"
        )
    else:
        full_prompt = f"{RAG_PROMPT}\n\nPYTANIE: {user_message}\n\nODPOWIEDŹ:"

    try:
        llm_component = get_llm_component()
        llm_result = llm_component.run(prompt=full_prompt)
        answer = llm_result["replies"][0]

        return ChatCompletionResponse(
            model=request.model,
            choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=answer))],
            usage=ChatCompletionUsage(
                prompt_tokens=len(full_prompt.split()),
                completion_tokens=len(answer.split()),
                total_tokens=len(full_prompt.split()) + len(answer.split()),
            ),
        )
    except Exception as e:
        logger.exception("Error in /v1/chat/completions: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /code_query
# ---------------------------------------------------------------------------

@router.post("/code_query")
async def query_code_agent(
    request: CodeQueryRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    try:
        rag_result = rag_pipeline.run(
            {"embedder": {"text": request.query}, "prompt_builder": {"query": request.query}},
            include_outputs_from={"retriever"},
        )
        local_docs = rag_result["retriever"]["documents"]

        prompt_text = "You are a Senior Python Developer. Analyze the following code/docs strictly.\n\nContext:\n"
        for doc in local_docs:
            prompt_text += f"{doc.content}\n"
        prompt_text += "\n\n" + tool_instructions() + "\n\n"
        prompt_text += f"CODE_QUESTION: {request.query}\n\nProvide a technical answer."

        llm_component = get_llm_component()
        current_prompt = prompt_text
        answer: str = ""
        for _ in range(3):
            llm_result = llm_component.run(prompt=current_prompt)
            answer = llm_result["replies"][0]
            tool_req = maybe_parse_tool_request(answer)
            if not tool_req:
                break
            try:
                tool_out = execute_tool(tool_req)
            except Exception as e:
                tool_out = {"tool_error": str(e), "tool_request": tool_req}
            current_prompt = (
                current_prompt
                + "\n\nTOOL_RESULT (JSON):\n"
                + json.dumps(tool_out, ensure_ascii=False)[:8000]
                + "\n\nNow answer the code question using the TOOL_RESULT."
            )

        return {"answer": answer}

    except Exception as e:
        logger.exception("Error in /code_query: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /rag/debug — diagnostyka pipeline RAG
# ---------------------------------------------------------------------------

@router.get("/rag/debug")
async def rag_debug(query: str = "test"):
    import requests as _requests
    from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

    result: dict = {}

    # Stan Qdrant
    try:
        qdrant_info = _requests.get(
            f"{settings.qdrant_url}/collections/{settings.qdrant_collection}", timeout=5
        ).json()
        result["qdrant_points"] = qdrant_info.get("result", {}).get("points_count", 0)
        result["qdrant_indexed"] = qdrant_info.get("result", {}).get("indexed_vectors_count", 0)
        result["qdrant_ok"] = result["qdrant_points"] > 0
    except Exception as e:
        result["qdrant_error"] = str(e)

    # Test retrieval
    try:
        embedding_result = text_embedder.run(text=query)
        retriever = QdrantEmbeddingRetriever(document_store=doc_store, top_k=3)
        retrieval_result = retriever.run(query_embedding=embedding_result["embedding"])
        docs = retrieval_result.get("documents", [])
        result["retrieved_docs"] = len(docs)
        result["sample"] = docs[0].content[:200] if docs else None
        result["sources"] = [doc.meta.get("source", "unknown") for doc in docs] if docs else []
    except Exception as e:
        result["retrieval_error"] = str(e)

    # Cache stats
    result["cache_size"] = len(_answer_cache)
    result["cache_ttl_seconds"] = CACHE_TTL

    return result
