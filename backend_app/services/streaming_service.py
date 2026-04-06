import json
import logging
import time
from typing import AsyncGenerator

import httpx

from ..config import settings

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Streaming Service — SSE token-by-token streaming do llama-server
# D1: Server-Sent Events w formacie OpenAI
# ---------------------------------------------------------------------------

_CHAT_ID_PREFIX = "chatcmpl-klimtech-"


async def stream_llm_response(
    prompt: str,
    model: str = "",
    request_id: str = "-",
) -> AsyncGenerator[str, None]:
    """Streamuje odpowiedź z llama-server jako SSE events w formacie OpenAI.

    Każdy yield to jeden event SSE gotowy do wysłania klientowi:
        data: {"id":"...","choices":[{"delta":{"content":"token"}}]}
    Ostatni event: data: [DONE]
    """
    model_name = model or settings.llm_model_name or "klimtech-bielik"
    chat_id = f"{_CHAT_ID_PREFIX}{int(time.time_ns())}"
    created = int(time.time())

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    url = f"{settings.llm_base_url}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    logger.error(
                        "[Stream] llama-server %d: %s",
                        response.status_code,
                        body[:200],
                        extra={"request_id": request_id},
                    )
                    yield _sse_error(chat_id, created, f"LLM error {response.status_code}")
                    yield "data: [DONE]\n\n"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                    else:
                        data = line

                    if data.strip() == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return

                    # Przepisz chunk z llama-server jako nasz SSE event
                    try:
                        chunk = json.loads(data)
                        delta_content = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta_content:
                            yield _sse_chunk(chat_id, created, model_name, delta_content)
                    except json.JSONDecodeError:
                        # Ignoruj niepoprawne linie (llama-server może wysyłać puste pings)
                        pass

        yield "data: [DONE]\n\n"

    except httpx.ConnectError:
        logger.error(
            "[Stream] llama-server niedostępny na %s", url,
            extra={"request_id": request_id},
        )
        yield _sse_error(chat_id, created, "LLM server unavailable")
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.exception(
            "[Stream] Nieoczekiwany błąd: %s", e, extra={"request_id": request_id}
        )
        yield _sse_error(chat_id, created, "Internal streaming error")
        yield "data: [DONE]\n\n"


def _sse_chunk(chat_id: str, created: int, model: str, content: str) -> str:
    """Formatuje jeden token jako SSE event w formacie OpenAI."""
    payload = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _sse_error(chat_id: str, created: int, message: str) -> str:
    """Formatuje błąd jako SSE event."""
    payload = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": "error",
        "choices": [
            {
                "index": 0,
                "delta": {"content": f"\n\n[Błąd: {message}]"},
                "finish_reason": "stop",
            }
        ],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
