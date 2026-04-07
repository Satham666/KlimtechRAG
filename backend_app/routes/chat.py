import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

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
from ..services.chat_service import (
    embed_texts,
    get_rag_debug_info,
    handle_chat_completions,
    handle_chat_completions_stream,
    handle_code_query,
    handle_query,
)
from ..utils.rate_limit import apply_rate_limit, get_client_id
from ..utils.dependencies import require_api_key, get_request_id

router = APIRouter(tags=["chat"])
logger = logging.getLogger("klimtechrag")


@router.get("/models")
@router.get("/v1/models")
async def list_models(req: Request = None, _=Depends(require_api_key)):
    """Zwraca dostępne modele — wymagane przez Nextcloud / Open WebUI."""
    model_name = settings.llm_model_name or "klimtech-bielik"
    return {
        "object": "list",
        "data": [{"id": model_name, "object": "model", "created": 1700000000,
                  "owned_by": "klimtechrag", "permission": [], "root": model_name, "parent": None}],
    }


@router.post("/v1/embeddings")
async def create_embeddings(body: dict, req: Request, _=Depends(require_api_key)):
    """OpenAI-compatible embeddings endpoint."""
    input_data = body.get("input", "")
    inputs = [input_data] if isinstance(input_data, str) else input_data
    if not isinstance(inputs, list):
        raise HTTPException(status_code=400, detail="'input' must be string or list of strings")
    try:
        embeddings = embed_texts(inputs)
    except Exception as e:
        logger.exception("[Embeddings] Błąd: %s", e)
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")
    total_tokens = sum(len(str(t).split()) for t in inputs)
    return {"object": "list", "data": embeddings, "model": settings.embedding_model,
            "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens}}


@router.post("/query")
async def query_rag(request: QueryRequest, req: Request, request_id: str = Depends(get_request_id)):
    """Podstawowy RAG query z tool calling."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        answer, cached = handle_query(request.query, request_id=request_id)
        return {"answer": answer, "cached": cached}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def openai_chat_completions(
    request: ChatCompletionRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """OpenAI-compatible chat completions (główny endpoint OWUI)."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    user_message = next((m.content for m in reversed(request.messages) if m.role == "user"), "")
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    embedding_model = req.headers.get("X-Embedding-Model", settings.embedding_model).strip()

    if request.stream:
        return StreamingResponse(
            handle_chat_completions_stream(
                user_message=user_message, use_rag=request.use_rag,
                web_search=request.web_search, top_k=request.top_k,
                embedding_model=embedding_model, model=request.model,
                request_id=request_id,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        answer, sources = handle_chat_completions(
            user_message=user_message, use_rag=request.use_rag,
            web_search=request.web_search, top_k=request.top_k,
            embedding_model=embedding_model, request_id=request_id,
            session_id=request.session_id,
        )
        return ChatCompletionResponse(
            model=request.model,
            choices=[ChatCompletionChoice(message=ChatMessage(role="assistant", content=answer))],
            usage=ChatCompletionUsage(prompt_tokens=len(answer.split()),
                                      completion_tokens=len(answer.split()),
                                      total_tokens=len(answer.split()) * 2),
            sources=sources,
        )
    except Exception as e:
        logger.exception("Error in /v1/chat/completions: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code_query")
async def query_code_agent(
    request: CodeQueryRequest, req: Request, request_id: str = Depends(get_request_id)
):
    """Code analysis query z tool calling."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        return {"answer": handle_code_query(request.query, request_id=request_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/debug")
async def rag_debug(req: Request, query: str = "test", _=Depends(require_api_key)):
    """Diagnostyka pipeline RAG — Qdrant, retrieval, cache."""
    return get_rag_debug_info(query)
