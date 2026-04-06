import logging

import requests as _requests
from fastapi import APIRouter, Depends, HTTPException, Request
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

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
from ..services import doc_store, get_text_embedder
from ..services.cache_service import cache_size, clear_cache, CACHE_TTL
from ..services.chat_service import handle_chat_completions, handle_code_query, handle_query
from ..utils.rate_limit import apply_rate_limit, get_client_id
from ..utils.dependencies import require_api_key, get_request_id
from ..monitoring import log_stats

router = APIRouter(tags=["chat"])
logger = logging.getLogger("klimtechrag")


# ---------------------------------------------------------------------------
# GET /models — wymagane przez Nextcloud integration_openai
# ---------------------------------------------------------------------------


@router.get("/models")
async def list_models_no_v1(req: Request, _=Depends(require_api_key)):
    """Zwraca dostępne modele — wymagane przez Nextcloud."""
    return await list_models(req, _)


# ---------------------------------------------------------------------------
# GET /v1/models — wymagane przez Open WebUI
# ---------------------------------------------------------------------------


@router.get("/v1/models")
async def list_models(req: Request = None, _=Depends(require_api_key)):
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
async def create_embeddings(body: dict, req: Request, _=Depends(require_api_key)):
    """OpenAI-compatible embeddings endpoint."""
    input_data = body.get("input", "")
    if isinstance(input_data, str):
        inputs = [input_data]
    elif isinstance(input_data, list):
        inputs = input_data
    else:
        raise HTTPException(
            status_code=400, detail="'input' must be string or list of strings"
        )

    embeddings = []
    for i, text in enumerate(inputs):
        try:
            result = get_text_embedder().run(text=str(text))
            embeddings.append({"object": "embedding", "embedding": result["embedding"], "index": i})
        except Exception as e:
            logger.exception("[Embeddings] Błąd dla inputu %d: %s", i, e)
            raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

    total_tokens = sum(len(str(t).split()) for t in inputs)
    return {
        "object": "list",
        "data": embeddings,
        "model": settings.embedding_model,
        "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
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
    """Podstawowy RAG query z tool calling."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        answer, cached = handle_query(request.query, request_id=request_id)
        return {"answer": answer, "cached": cached}
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

    embedding_model = req.headers.get(
        "X-Embedding-Model", settings.embedding_model
    ).strip()

    try:
        answer, sources = handle_chat_completions(
            user_message=user_message,
            use_rag=request.use_rag,
            web_search=request.web_search,
            top_k=request.top_k,
            embedding_model=embedding_model,
            request_id=request_id,
        )
        return ChatCompletionResponse(
            model=request.model,
            choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=answer))],
            usage=ChatCompletionUsage(
                prompt_tokens=len(answer.split()),
                completion_tokens=len(answer.split()),
                total_tokens=len(answer.split()) * 2,
            ),
            sources=sources,
        )
    except Exception as e:
        logger.exception(
            "Error in /v1/chat/completions: %s", e, extra={"request_id": request_id}
        )
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
    """Code analysis query z tool calling."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        answer = handle_code_query(request.query, request_id=request_id)
        return {"answer": answer}
    except Exception as e:
        logger.exception(
            "Error in /code_query: %s", e, extra={"request_id": request_id}
        )
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /rag/debug — diagnostyka pipeline RAG
# ---------------------------------------------------------------------------


@router.get("/rag/debug")
async def rag_debug(req: Request, query: str = "test", _=Depends(require_api_key)):
    result: dict = {}

    try:
        qdrant_info = _requests.get(
            f"{settings.qdrant_url}/collections/{settings.qdrant_collection}", timeout=5
        ).json()
        result["qdrant_points"] = qdrant_info.get("result", {}).get("points_count", 0)
        result["qdrant_indexed"] = qdrant_info.get("result", {}).get("indexed_vectors_count", 0)
        result["qdrant_ok"] = result["qdrant_points"] > 0
    except Exception as e:
        result["qdrant_error"] = str(e)

    try:
        embedding_result = get_text_embedder().run(text=query)
        retriever = QdrantEmbeddingRetriever(document_store=doc_store, top_k=3)
        retrieval_result = retriever.run(query_embedding=embedding_result["embedding"])
        docs = retrieval_result.get("documents", [])
        result["retrieved_docs"] = len(docs)
        result["sample"] = docs[0].content[:200] if docs else None
        result["sources"] = [doc.meta.get("source", "unknown") for doc in docs] if docs else []
    except Exception as e:
        result["retrieval_error"] = str(e)

    result["cache_size"] = cache_size()
    result["cache_ttl_seconds"] = CACHE_TTL

    return result
