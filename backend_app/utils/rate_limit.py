import time
from typing import Dict, List

from fastapi import HTTPException, Request

from ..config import settings

rate_limit_store: Dict[str, List[float]] = {}


def get_client_id(request: Request) -> str:
    return request.client.host or "unknown"


def apply_rate_limit(client_id: str) -> None:
    now = time.time()
    window = settings.rate_limit_window_seconds
    max_requests = settings.rate_limit_max_requests

    timestamps = rate_limit_store.get(client_id, [])
    timestamps = [t for t in timestamps if now - t <= window]
    if len(timestamps) >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    timestamps.append(now)
    rate_limit_store[client_id] = timestamps
