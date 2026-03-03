import json
import logging
from typing import Dict

from ddgs import DDGS
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
answer_cache: Dict[str, str] = {}

RAG_PROMPT = """Jesteś pomocnym asystentem AI z dostępem do bazy wiedzy RAG.
Odpowiadaj na podstawie dostarczonego kontekstu. Jeśli nie znajdziesz odpowiedzi w kontekście,
powiedz o tym szczerze. Odpowiadaj po polsku, chyba że użytkownik pyta w innym języku."""


def clear_cache():
    global answer_cache
    answer_cache.clear()
    logger.info("Cache odpowiedzi wyczyszczony")


@router.post("/query")
async def query_rag(
    request: QueryRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    cached = answer_cache.get(request.query)
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
            web_doc = HaystackDocument(
                content=web_snippet, meta={"source": "Web Search"}
            )
            final_docs.append(web_doc)

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
                + "\n\nNow answer the user question using the TOOL_RESULT. Do NOT request another tool unless strictly necessary."
            )

        answer_cache[request.query] = answer
        return {"answer": answer, "cached": False}
    except Exception as e:
        logger.exception("Error in /query: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


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
            {
                "embedder": {"text": request.query},
                "prompt_builder": {"query": request.query},
            },
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
                + "\n\nNow answer the code question using the TOOL_RESULT. Do NOT request another tool unless strictly necessary."
            )

        return {"answer": answer}
    except Exception as e:
        logger.exception(
            "Error in /code_query: %s", e, extra={"request_id": request_id}
        )
        raise HTTPException(status_code=500, detail=str(e))


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
            query_embedding = text_embedder.run(text=user_message)

            from haystack_integrations.components.retrievers.qdrant import (
                QdrantEmbeddingRetriever,
            )

            retriever = QdrantEmbeddingRetriever(
                document_store=doc_store, top_k=request.top_k
            )
            retrieval_result = retriever.run(
                query_embedding=query_embedding["embedding"]
            )

            docs = retrieval_result.get("documents", [])
            if docs:
                contents = [doc.content for doc in docs if doc.content]
                if contents:
                    context_text = "\n\n---\n\n".join(contents)
                sources = []
                for doc in docs:
                    src = "unknown"
                    if doc.meta and "source" in doc.meta:
                        src = str(doc.meta["source"])
                    sources.append(src)
                logger.info(
                    "[RAG] Znaleziono %d dokumentów: %s",
                    len(docs),
                    ", ".join(sources),
                    extra={"request_id": request_id},
                )
        except Exception as e:
            logger.warning(
                "[RAG] Błąd retrieval: %s", str(e), extra={"request_id": request_id}
            )

    if context_text:
        full_prompt = f"""{RAG_PROMPT}

=== KONTEKST Z BAZY WIEDZY ===
{context_text}
=== KONIEC KONTEKSTU ===

PYTANIE UŻYTKOWNIKA: {user_message}

ODPOWIEDŹ:"""
    else:
        full_prompt = f"{RAG_PROMPT}\n\nPYTANIE: {user_message}\n\nODPOWIEDŹ:"

    try:
        llm_component = get_llm_component()
        llm_result = llm_component.run(prompt=full_prompt)
        answer = llm_result["replies"][0]

        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(role="assistant", content=answer)
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=len(full_prompt.split()),
                completion_tokens=len(answer.split()),
                total_tokens=len(full_prompt.split()) + len(answer.split()),
            ),
        )
    except Exception as e:
        logger.exception(
            "Error in /v1/chat/completions: %s", e, extra={"request_id": request_id}
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag/debug")
async def rag_debug(query: str = "test"):
    import requests
    from haystack_integrations.components.retrievers.qdrant import (
        QdrantEmbeddingRetriever,
    )

    result = {}

    qdrant_info = requests.get(
        f"{settings.qdrant_url}/collections/{settings.qdrant_collection}", timeout=5
    ).json()
    result["qdrant_points"] = qdrant_info.get("result", {}).get("points_count", 0)
    result["qdrant_indexed"] = qdrant_info.get("result", {}).get(
        "indexed_vectors_count", 0
    )

    try:
        embedding_result = text_embedder.run(text=query)
        retriever = QdrantEmbeddingRetriever(document_store=doc_store, top_k=3)
        retrieval_result = retriever.run(query_embedding=embedding_result["embedding"])
        docs = retrieval_result.get("documents", [])
        result["retrieved_docs"] = len(docs)
        result["sample"] = docs[0].content[:200] if docs else None
        result["sources"] = (
            [doc.meta.get("source", "unknown") for doc in docs] if docs else []
        )
    except Exception as e:
        result["retrieval_error"] = str(e)

    return result
