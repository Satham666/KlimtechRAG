import logging
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket
from fastapi.responses import JSONResponse

from ..utils.dependencies import require_api_key
from ..config import settings
from ..services import doc_store
from ..file_registry import (
    get_connection as _get_registry_connection,
    init_db as init_file_registry,
    list_files,
    get_pending_files,
    get_stats as get_file_stats,
    sync_with_filesystem,
)
from ..utils.dependencies import require_api_key

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
    req: Request,
    source: Optional[str] = None,
    doc_id: Optional[str] = None,
):
    require_api_key(req)
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
    api_key = ws.headers.get("X-API-Key") or ""
    if settings.api_key and not secrets.compare_digest(api_key, settings.api_key):
        await ws.close(code=4001, reason="Unauthorized")
        return
    await ws.accept()
    try:
        while True:
            health = await health_check()
            await ws.send_json(health)
            await ws.receive_text()
    except Exception:
        await ws.close()


@router.get("/files/stats")
async def files_stats(req: Request = None):
    require_api_key(req)
    stats = get_file_stats()
    try:
        import requests as _req

        r = _req.get(
            f"{settings.qdrant_url}/collections/{settings.qdrant_collection}", timeout=3
        ).json()
        result = r.get("result", {})
        stats["qdrant_points"] = result.get("points_count", 0)
        stats["qdrant_indexed"] = result.get("indexed_vectors_count", 0)
    except Exception:
        stats["qdrant_points"] = None
        stats["qdrant_indexed"] = None
    return stats


@router.get("/files/list")
async def files_list(
    ext: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
    req: Request = None,
):
    require_api_key(req)
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
async def files_sync(req: Request = None):
    require_api_key(req)
    count = sync_with_filesystem()
    return {"registered": count, "message": f"Zsynchronizowano {count} plików"}


@router.get("/files/pending")
async def files_pending(req: Request = None):
    require_api_key(req)
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


# ---------------------------------------------------------------------------
# E1: DELETE /v1/ingest/{doc_id} — usuwanie dokumentu z RAG
# ---------------------------------------------------------------------------

@router.delete("/v1/ingest/{doc_id}")
async def delete_ingest(
    doc_id: str,
    delete_file: bool = Query(False, description="Usuń też plik źródłowy"),
    _: str = Depends(require_api_key),
):
    """Usuwa dokument z Qdrant (po meta.source) i file_registry.

    ?delete_file=true → usuwa też plik fizyczny.
    """
    if not doc_id or not doc_id.strip():
        raise HTTPException(status_code=422, detail="doc_id nie może być pusty")

    deleted_qdrant = 0
    deleted_registry = 0
    deleted_file = False
    file_path_to_delete: Optional[str] = None

    # Usuń z Qdrant (filtr po meta.source == doc_id)
    try:
        doc_store.delete_by_filter(
            {"field": "meta.source", "operator": "==", "value": doc_id}
        )
        deleted_qdrant = 1
        logger.info("[E1] Usunięto z Qdrant: %s", doc_id)
    except Exception as e:
        logger.warning("[E1] Błąd Qdrant delete: %s", e)

    # Usuń z file_registry
    try:
        with _get_registry_connection() as conn:
            row = conn.execute(
                "SELECT path FROM files WHERE filename = ? LIMIT 1", (doc_id,)
            ).fetchone()
            if row:
                file_path_to_delete = row["path"]
            result = conn.execute("DELETE FROM files WHERE filename = ?", (doc_id,))
            deleted_registry = result.rowcount
            conn.commit()
        logger.info("[E1] Usunięto z registry: %s (%d wierszy)", doc_id, deleted_registry)
    except Exception as e:
        logger.warning("[E1] Błąd registry delete: %s", e)

    # Opcjonalnie usuń plik fizyczny
    if delete_file and file_path_to_delete and os.path.isfile(file_path_to_delete):
        try:
            os.remove(file_path_to_delete)
            deleted_file = True
            logger.info("[E1] Usunięto plik: %s", file_path_to_delete)
        except Exception as e:
            logger.warning("[E1] Błąd usuwania pliku: %s", e)

    return {
        "status": "ok",
        "doc_id": doc_id,
        "deleted_from_qdrant": deleted_qdrant > 0,
        "deleted_from_registry": deleted_registry > 0,
        "file_deleted": deleted_file,
    }


# ---------------------------------------------------------------------------
# E2: GET /v1/ingest/list — lista zaindeksowanych dokumentów
# ---------------------------------------------------------------------------

@router.get("/v1/ingest/list")
async def ingest_list(
    status: Optional[str] = Query(None, description="indexed | pending | error | failed"),
    source: Optional[str] = Query(None, description="Nazwa pliku (częściowe dopasowanie)"),
    extension: Optional[str] = Query(None, description="Rozszerzenie, np. .pdf"),
    limit: int = Query(100, ge=1, le=1000),
    _: str = Depends(require_api_key),
):
    """Zwraca listę dokumentów z file_registry z metadanymi.

    Zgodny z formatem OpenAI-style.
    """
    files = list_files(extension=extension, status=status, limit=limit)

    # Filtr po source (częściowe dopasowanie nazwy)
    if source:
        source_lower = source.lower()
        files = [f for f in files if source_lower in f.filename.lower()]

    data = [
        {
            "doc_id": f.filename,
            "source": f.filename,
            "path": f.path,
            "status": f.status,
            "chunks_count": f.chunks_count,
            "extension": f.extension,
            "size_kb": round(f.size_bytes / 1024, 1),
            "indexed_at": f.indexed_at,
            "content_hash": f.content_hash or "",
            "collection": "klimtech_docs",
        }
        for f in files
    ]

    return {
        "object": "list",
        "total": len(data),
        "data": data,
    }


# ---------------------------------------------------------------------------
# W5: Batch queue stats
# ---------------------------------------------------------------------------

@router.get("/v1/batch/stats")
async def batch_stats(_: str = Depends(require_api_key)):
    """Zwraca statystyki kolejki batch (W5)."""
    from ..services.batch_service import get_batch_queue
    return get_batch_queue().stats()
