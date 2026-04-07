import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from ..config import settings
from ..fs_tools import resolve_path, FsSecurityError
from ..models import IngestPathRequest
from ..models.schemas import IngestItem, IngestResponse
from ..services.ingest_service import (
    IngestError,
    check_file_in_registry,
    get_vlm_status,
    ingest_file_background,
    ingest_pdf_vlm_sync,
    list_active_ingest_tasks,
    prepare_progress_ingest,
    process_all_pending,
    process_path_ingest,
    process_temp_ingest,
    process_upload,
)
from ..services.nextcloud_service import rescan_nextcloud
from ..utils.dependencies import get_request_id, require_api_key
from ..utils.rate_limit import apply_rate_limit, get_client_id

router = APIRouter(tags=["ingest"])
logger = logging.getLogger("klimtechrag")


def _get_embedding_model(request: Request) -> str:
    """Zwraca embedding model z nagłówka X-Embedding-Model lub wartość domyślną."""
    return request.headers.get("X-Embedding-Model", settings.embedding_model).strip()


def _to_http(e: IngestError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/upload")
async def upload_file_to_rag(
    file: UploadFile, req: Request, background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id),
):
    """Przyjmuje plik, zapisuje do Nextcloud/uploads, indeksuje do Qdrant w tle."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    cl = req.headers.get("content-length")
    if cl and int(cl) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="Plik za duży")
    try:
        content = await file.read()
        result = process_upload(content, file.filename or "", request_id)
        if result.get("duplicate"):
            return {"message": "Plik juz istnieje", "duplicate": True,
                    "filename": result["filename"], "existing_path": result["existing_path"]}
        background_tasks.add_task(rescan_nextcloud, result["subdir"])
        if result["will_index"]:
            background_tasks.add_task(ingest_file_background, result["target_path"])
        return IngestResponse(data=[IngestItem(
            doc_id=result["safe_filename"], source=file.filename or "",
            status=result["status_val"], chunks_count=0,
        )])
    except IngestError as e:
        raise _to_http(e)
    except Exception as e:
        logger.exception("[Upload] Błąd: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_file(file: UploadFile, request: Request, request_id: str = Depends(get_request_id)):
    """Klasyczny endpoint: parsuje i indeksuje bezpośrednio (bez zapisu do Nextcloud)."""
    require_api_key(request)
    apply_rate_limit(get_client_id(request))
    try:
        return process_temp_ingest(file.file, file.filename or "", _get_embedding_model(request), request_id)
    except IngestError as e:
        raise _to_http(e)


@router.post("/ingest_path")
async def ingest_by_path(body: IngestPathRequest, req: Request, request_id: str = Depends(get_request_id)):
    """Indeksuje plik z dysku (watchdog, OWUI function)."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        file_path = resolve_path(settings.base_path, body.path)
    except FsSecurityError:
        raise HTTPException(status_code=403, detail="Path outside allowed directory")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    try:
        result = process_path_ingest(file_path, _get_embedding_model(req))
        if result.get("status") == "indexed":
            return IngestResponse(data=[IngestItem(
                doc_id=result["filename"], source=result["filename"],
                status="indexed", chunks_count=result["chunks_processed"],
            )])
        return result
    except IngestError as e:
        raise _to_http(e)


@router.get("/files/check")
async def check_file_status(path: str, req: Request):
    """Sprawdza status pliku w file_registry. Używane przez n8n."""
    require_api_key(req)
    return check_file_in_registry(path)


@router.post("/ingest_all")
async def ingest_all_pending(req: Request, limit: int = 10):
    """Indeksuje pending pliki z inteligentną selekcją embeddera i zarządzaniem VRAM."""
    require_api_key(req)
    results = process_all_pending(limit)
    return IngestResponse(data=[
        IngestItem(
            doc_id=r.get("filename", "unknown"),
            source=r.get("filename", "unknown"),
            status="indexed" if "ok" in r.get("status", "") else r.get("status", "error"),
            chunks_count=r.get("chunks", 0),
        )
        for r in results
    ])


@router.post("/ingest_pdf_vlm")
async def ingest_pdf_with_vlm(
    body: IngestPathRequest, req: Request, max_images: int = 10,
    request_id: str = Depends(get_request_id),
):
    """Indeksuje PDF z opisem obrazów przez VLM."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        file_path = resolve_path(settings.base_path, body.path)
    except FsSecurityError:
        raise HTTPException(status_code=403, detail="Path outside allowed directory")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    filename = os.path.basename(file_path)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Tylko pliki PDF")
    try:
        return ingest_pdf_vlm_sync(file_path, filename, max_images)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/start")
async def ingest_start(
    file: UploadFile, req: Request, background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id),
):
    """Przyjmuje plik, zwraca task_id do śledzenia postępu przez SSE."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        content = await file.read()
        prep = prepare_progress_ingest(content, file.filename or "")
    except IngestError as e:
        raise _to_http(e)
    task = prep["task"]
    background_tasks.add_task(rescan_nextcloud, prep["subdir"])
    if prep["will_index"]:
        background_tasks.add_task(ingest_file_background, prep["target_path"], task)
    else:
        task.finish(0, f"Format {prep['ext']} zapisany (nie wymaga embeddingu)")
    logger.info("[D2] ingest/start: %s → task_id=%s", prep["safe_filename"], task.task_id,
                extra={"request_id": request_id})
    return {"task_id": task.task_id, "filename": prep["safe_filename"], "status": "started"}


@router.get("/ingest/progress/{task_id}")
async def ingest_progress(task_id: str, req: Request):
    """SSE stream postępu ingestowania dla danego task_id."""
    require_api_key(req)
    from ..services.progress_service import stream_progress
    return StreamingResponse(
        stream_progress(task_id),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.get("/vlm/status")
async def vlm_status():
    return get_vlm_status()


@router.get("/ingest/active")
async def list_active_tasks_endpoint(_: str = Depends(require_api_key)):
    """Zwraca listę aktywnych zadań ingestowania z ProgressTracker."""
    return list_active_ingest_tasks()
