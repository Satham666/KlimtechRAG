import secrets

from fastapi import Depends, HTTPException, Request

from ..config import settings


def require_api_key(request: Request) -> None:
    if not settings.api_key:
        return
    # Sprawdź X-API-Key header (KlimtechRAG UI)
    key = request.headers.get("X-API-Key")
    # Fallback: Authorization: Bearer <key> (Nextcloud integration_openai)
    if not key:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:]
    if not secrets.compare_digest(key or "", settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def get_request_id(request: Request) -> str:
    request_id = request.headers.get("X-Request-ID") or str(id(request))
    request.state.request_id = request_id
    return request_id
