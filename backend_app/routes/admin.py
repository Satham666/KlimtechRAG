import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse

from ..config import settings
from ..services import doc_store
from ..file_registry import (
    init_db as init_file_registry,
    sync_with_filesystem,
    get_stats as get_file_stats,
    list_files,
    get_pending_files,
)

router = APIRouter(tags=["admin"])
logger = logging.getLogger("klimtechrag")

metrics = {
    "ingest_requests": 0,
    "query_requests": 0,
    "code_query_requests": 0,
}


@router.get("/health")
async def health_check():
    qdrant_ok = False
    llm_ok = False

    try:
        count = doc_store.count_documents()
        qdrant_ok = count >= 0
    except Exception:
        qdrant_ok = False

    llm_ok = True

    status = qdrant_ok and llm_ok
    return {
        "status": "ok" if status else "degraded",
        "qdrant": qdrant_ok,
        "llm": llm_ok,
    }


@router.get("/metrics")
async def metrics_endpoint():
    return {
        "ingest_requests": metrics["ingest_requests"],
        "query_requests": metrics["query_requests"],
        "code_query_requests": metrics["code_query_requests"],
    }


@router.delete("/documents")
async def delete_documents(
    source: Optional[str] = None,
    doc_id: Optional[str] = None,
):
    if not source and not doc_id:
        raise HTTPException(
            status_code=400, detail="Provide at least source or doc_id filter"
        )

    filters = {}
    if source:
        filters = {"field": "meta.source", "operator": "==", "value": source}
    if doc_id:
        filters = {"field": "id", "operator": "==", "value": doc_id}
    if source and doc_id:
        filters = {
            "operator": "AND",
            "conditions": [
                {"field": "meta.source", "operator": "==", "value": source},
                {"field": "id", "operator": "==", "value": doc_id},
            ],
        }

    doc_store.delete_by_filter(filters)
    return {"status": "ok"}


@router.websocket("/ws/health")
async def websocket_health(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            health = await health_check()
            await ws.send_json(health)
            await ws.receive_text()
    except Exception:
        await ws.close()

@router.get("/files/stats")
async def files_stats():
    stats = get_file_stats()
    try:
        import requests as _req
        r = _req.get(
            f"{settings.qdrant_url}/collections/{settings.qdrant_collection}",
            timeout=3
        ).json()
        result = r.get("result", {})
        stats["qdrant_points"]  = result.get("points_count", 0)
        stats["qdrant_indexed"] = result.get("indexed_vectors_count", 0)
    except Exception:
        stats["qdrant_points"]  = None
        stats["qdrant_indexed"] = None
    return stats


@router.get("/files/list")
async def files_list(
    ext: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
):
    files = list_files(extension=ext, status=status, limit=limit)
    return {
        "count": len(files),
        "files": [
            {
                "filename": f.filename,
                "extension": f.extension,
                "size_kb": round(f.size_bytes / 1024, 1),
                "size_bytes": f.size_bytes,
                "content_hash": f.content_hash,
                "status": f.status,
                "chunks": f.chunks_count,
                "indexed_at": f.indexed_at,
            }
            for f in files
        ],
    }


@router.post("/files/sync")
async def files_sync():
    count = sync_with_filesystem()
    return {"registered": count, "message": f"Zsynchronizowano {count} plików"}


@router.get("/files/pending")
async def files_pending():
    files = get_pending_files()
    return {
        "count": len(files),
        "files": [
            {
                "path": f.path,
                "filename": f.filename,
                "extension": f.extension,
                "size_kb": round(f.size_bytes / 1024, 1),
            }
            for f in files
        ],
    }
