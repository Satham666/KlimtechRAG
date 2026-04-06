import logging
import os
import shutil
import tempfile

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from haystack import Document

from ..categories.classifier import classify_document
from ..config import settings
from ..fs_tools import resolve_path, FsSecurityError
from ..models import IngestPathRequest
from ..models.schemas import IngestItem, IngestResponse
from ..services import get_indexing_pipeline, doc_store, get_text_embedder
from ..services.cache_service import clear_cache
from ..services.dedup_service import hash_bytes, hash_file, compute_content_hash
from ..services.ingest_service import ingest_file_background, ingest_colpali_batch, ingest_semantic_batch
from ..services.nextcloud_service import EXT_TO_DIR, TEXT_INDEXABLE, save_to_uploads, rescan_nextcloud
from ..services.parser_service import parse_with_docling, read_text_file
from ..services.qdrant import ensure_indexed
from ..services.embedder_pool import get_embedder, unload_embedder
from ..utils.rate_limit import apply_rate_limit, get_client_id
from ..utils.dependencies import require_api_key, get_request_id
from ..monitoring import log_stats
from ..file_registry import (
    mark_indexed,
    mark_failed,
    get_pending_files,
    register_file,
    find_duplicate_by_hash,
    get_connection as _get_registry_connection,
)

router = APIRouter(tags=["ingest"])
logger = logging.getLogger("klimtechrag")


def _get_embedding_model(request: Request) -> str:
    """Zwraca embedding model z nagłówka X-Embedding-Model lub wartość domyślną."""
    return request.headers.get("X-Embedding-Model", settings.embedding_model).strip()


# ---------------------------------------------------------------------------
# POST /upload — przyjmuje plik, zapisuje do uploads, indeksuje w tle
# ---------------------------------------------------------------------------


@router.post("/upload")
async def upload_file_to_rag(
    file: UploadFile,
    req: Request,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id),
):
    """Przyjmuje plik, zapisuje do Nextcloud/uploads, indeksuje do Qdrant w tle."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    if not file.filename:
        raise HTTPException(status_code=400, detail="Brak nazwy pliku")

    import re as _re
    safe_filename = _re.sub(r"[^\w\-_\.]", "_", os.path.basename(file.filename))
    if not safe_filename or safe_filename.startswith("."):
        raise HTTPException(status_code=400, detail="Nieprawidłowa nazwa pliku")

    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in EXT_TO_DIR:
        raise HTTPException(
            status_code=400,
            detail=f"Nieobsługiwane rozszerzenie: {ext}. Dozwolone: {', '.join(sorted(EXT_TO_DIR.keys()))}",
        )

    try:
        cl = req.headers.get("content-length")
        if cl and int(cl) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Plik za duży (limit {settings.max_file_size_bytes // 1024 // 1024} MB)",
            )

        content = await file.read()
        file_size = len(content)

        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Plik za duży: {file_size / 1024 / 1024:.1f} MB (limit {settings.max_file_size_bytes / 1024 / 1024:.0f} MB)",
            )

        _h = hash_bytes(content)
        _ex = find_duplicate_by_hash(_h)
        if _ex:
            return {"message": "Plik juz istnieje", "duplicate": True, "filename": file.filename, "existing_path": _ex}

        target_path, subdir = save_to_uploads(content, safe_filename, ext)
        register_file(target_path)

        with _get_registry_connection() as _c:
            _c.execute("UPDATE files SET content_hash=? WHERE path=?", (_h, target_path))
            _c.commit()

        background_tasks.add_task(rescan_nextcloud, subdir)

        if ext in TEXT_INDEXABLE:
            background_tasks.add_task(ingest_file_background, target_path)
            status_val = "pending"
        else:
            status_val = "skipped"

        logger.info(
            "[Upload] %s → Nextcloud/%s (%.1f KB) | status=%s",
            file.filename, subdir, file_size / 1024, status_val,
            extra={"request_id": request_id},
        )
        return IngestResponse(data=[IngestItem(
            doc_id=safe_filename,
            source=file.filename,
            status=status_val,
            chunks_count=0,
        )])

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[Upload] Błąd: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /ingest — klasyczny endpoint (multipart, temp file)
# ---------------------------------------------------------------------------


@router.post("/ingest")
async def ingest_file(
    file: UploadFile,
    request: Request,
    request_id: str = Depends(get_request_id),
):
    """Klasyczny endpoint: parsuje i indeksuje bezpośrednio (bez zapisu do Nextcloud)."""
    require_api_key(request)
    apply_rate_limit(get_client_id(request))

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in settings.allowed_extensions_docs:
        raise HTTPException(status_code=400, detail=f"File format not allowed: {file.filename}")

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_file_path = tmp.name

        file_size = os.path.getsize(temp_file_path)
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(status_code=413, detail=f"File too large: {file_size} bytes")

        embedding_model = _get_embedding_model(request)
        if embedding_model.lower().startswith("vidore/colpali"):
            if suffix != ".pdf":
                raise HTTPException(status_code=400, detail="ColPali obsługuje tylko pliki PDF")
            from ..services.colpali_embedder import index_pdf as colpali_index_pdf, unload_model
            try:
                pages = colpali_index_pdf(pdf_path=temp_file_path, doc_id=file.filename, model_name=embedding_model)
            finally:
                unload_model()
            return {"message": "Zaindeksowano przez ColPali", "pages_processed": pages, "collection": "klimtech_colpali"}

        if suffix == ".pdf":
            markdown_text = parse_with_docling(temp_file_path)
        elif suffix in TEXT_INDEXABLE:
            markdown_text = read_text_file(temp_file_path, suffix)
        else:
            return {"message": f"Format {suffix} not text-indexable", "chunks_processed": 0}

        if not markdown_text or not markdown_text.strip():
            return {"message": "File empty (Scanned PDF?)", "chunks_processed": 0}

        category = classify_document(filepath=file.filename, content=markdown_text)
        docs = [Document(content=markdown_text, meta={"source": file.filename, "type": suffix, "category": category})]
        logger.info("[ingest] Embedding %s | %s", file.filename, log_stats("Start"), extra={"request_id": request_id})
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]
        logger.info("[ingest] %s → %d chunków | %s", file.filename, chunks, log_stats("Koniec"), extra={"request_id": request_id})
        return {"message": "File ingested successfully", "chunks_processed": chunks}

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


# ---------------------------------------------------------------------------
# POST /ingest_path — indeksuje plik z dysku (watchdog, OWUI function)
# ---------------------------------------------------------------------------


@router.post("/ingest_path")
async def ingest_by_path(
    body: IngestPathRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    try:
        file_path = resolve_path(settings.base_path, body.path)
    except FsSecurityError:
        raise HTTPException(status_code=403, detail="Path outside allowed directory")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    suffix = os.path.splitext(filename)[1].lower()

    if suffix not in settings.allowed_extensions_docs:
        raise HTTPException(status_code=400, detail=f"Extension not allowed: {suffix}")

    if suffix not in TEXT_INDEXABLE:
        return {"message": f"Format {suffix} not text-indexable yet", "chunks_processed": 0, "filename": filename}

    content_hash = hash_file(file_path)
    existing_path = find_duplicate_by_hash(content_hash)

    if existing_path and existing_path != file_path:
        return {"message": "Plik o takim hash'u już istnieje w bazie", "duplicate": True, "existing_path": existing_path, "filename": filename, "chunks_processed": 0}

    if existing_path == file_path:
        from ..file_registry import get_connection as _get_conn
        with _get_conn() as _c:
            row = _c.execute("SELECT status FROM files WHERE path = ?", (file_path,)).fetchone()
            if row and row["status"] == "indexed":
                return {"message": "Plik już zaindeksowany (taki sam hash)", "already_indexed": True, "filename": filename, "chunks_processed": 0}

    register_file(file_path, compute_hash=False)
    with _get_registry_connection() as _c:
        _c.execute("UPDATE files SET content_hash=? WHERE path=?", (content_hash, file_path))
        _c.commit()

    embedding_model = _get_embedding_model(req)
    if embedding_model.lower().startswith("vidore/colpali"):
        if suffix != ".pdf":
            raise HTTPException(status_code=400, detail="ColPali obsługuje tylko pliki PDF")
        from ..services.colpali_embedder import index_pdf as colpali_index_pdf, unload_model
        try:
            pages = colpali_index_pdf(pdf_path=file_path, doc_id=filename, model_name=embedding_model)
        finally:
            unload_model()
        mark_indexed(file_path, pages)
        ensure_indexed()
        clear_cache()
        return {"message": "OK (ColPali)", "chunks_processed": pages, "filename": filename}

    try:
        if suffix == ".pdf":
            markdown_text = parse_with_docling(file_path)
        else:
            markdown_text = read_text_file(file_path, suffix)

        if not markdown_text or not markdown_text.strip():
            mark_indexed(file_path, 0)
            return {"message": "File empty", "chunks_processed": 0, "filename": filename}

        category = classify_document(filepath=file_path, content=markdown_text)
        docs = [Document(content=markdown_text, meta={"source": filename, "type": suffix, "category": category})]
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]
        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[ingest_path] %s → %d chunks (kategoria: %s)", filename, chunks, category)
        return IngestResponse(data=[IngestItem(
            doc_id=filename,
            source=filename,
            status="indexed",
            chunks_count=chunks,
        )])

    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[ingest_path] Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /files/check — sprawdza status pliku w file_registry
# ---------------------------------------------------------------------------


@router.get("/files/check")
async def check_file_status(path: str, req: Request):
    """Sprawdza status pliku w file_registry. Używane przez n8n."""
    require_api_key(req)

    with _get_registry_connection() as conn:
        row = conn.execute(
            "SELECT path, filename, content_hash, status, indexed_at, chunks_count FROM files WHERE path = ?",
            (path,),
        ).fetchone()

    if not row:
        return {"exists": False, "path": path, "status": "not_registered", "should_index": True}

    should_index = row["status"] not in ("indexed", "pending")
    return {
        "exists": True,
        "path": row["path"],
        "filename": row["filename"],
        "content_hash": row["content_hash"],
        "status": row["status"],
        "indexed_at": row["indexed_at"],
        "chunks_count": row["chunks_count"],
        "should_index": should_index,
    }


# ---------------------------------------------------------------------------
# POST /ingest_all — indeksuje wszystkie pending z file_registry
# ---------------------------------------------------------------------------


@router.post("/ingest_all")
async def ingest_all_pending(req: Request, limit: int = 10):
    """Indeksuje pending pliki z inteligentną selekcją embeddera i zarządzaniem VRAM."""
    from ..services.model_selector import select_model_for_file, is_model_implemented, get_model_metadata

    require_api_key(req)
    files = get_pending_files()[:limit]
    results = []

    if not files:
        return {"indexed": 0, "results": []}

    # Grupuj pliki po modelu embeddera
    files_by_model: dict = {}
    for f in files:
        if f.extension not in TEXT_INDEXABLE:
            mark_indexed(f.path, 0)
            results.append({"filename": f.filename, "chunks": 0, "status": "skipped_format"})
            continue
        model_name = select_model_for_file(f.path)
        files_by_model.setdefault(model_name, []).append(f)

    logger.info("📦 Grupowanie plików: %d modeli, %d plików", len(files_by_model), sum(len(v) for v in files_by_model.values()))

    for model_name, file_batch in files_by_model.items():
        metadata = get_model_metadata(model_name)
        logger.info("🔄 [%s] Indeksowanie %d plików (%s, %dD, %dMB VRAM)", model_name, len(file_batch), metadata["type"], metadata["dimension"], metadata["vram_mb"])

        if model_name == "colpali":
            results.extend(ingest_colpali_batch(file_batch, metadata))
        else:
            results.extend(ingest_semantic_batch(file_batch, model_name))

    ensure_indexed()
    clear_cache()

    indexed_count = len([r for r in results if "ok" in r.get("status", "")])
    logger.info("🎯 Indeksowanie skończone: %d/%d sukces", indexed_count, len(results))
    return IngestResponse(data=[
        IngestItem(
            doc_id=r.get("filename", "unknown"),
            source=r.get("filename", "unknown"),
            status="indexed" if "ok" in r.get("status", "") else r.get("status", "error"),
            chunks_count=r.get("chunks", 0),
        )
        for r in results
    ])


# ---------------------------------------------------------------------------
# POST /ingest_pdf_vlm — PDF z opisem obrazów przez VLM
# ---------------------------------------------------------------------------


@router.post("/ingest_pdf_vlm")
async def ingest_pdf_with_vlm(
    body: IngestPathRequest,
    req: Request,
    max_images: int = 10,
    request_id: str = Depends(get_request_id),
):
    """Indeksuje PDF z opisem obrazów przez VLM."""
    from ..ingest.image_handler import start_vlm_server, stop_vlm_server
    from ..services.parser_service import clean_text

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

    vlm_started = False
    try:
        logger.info("[PDF+VLM] Uruchamiam VLM server...")
        vlm_started = start_vlm_server()

        if not vlm_started:
            logger.warning("[PDF+VLM] VLM niedostępny, używam zwykłego parsera")
            markdown_text = parse_with_docling(file_path)
        else:
            from ..ingest.image_handler import process_pdf_with_images
            result_data = process_pdf_with_images(pdf_path=file_path, extract_images=True, describe_images=True, max_images=max_images)
            markdown_text = clean_text(result_data.get("combined_content", "")) or parse_with_docling(file_path)

        if not markdown_text or not markdown_text.strip():
            mark_indexed(file_path, 0)
            return {"message": "File empty", "chunks_processed": 0, "filename": filename}

        docs = [Document(content=markdown_text, meta={"source": filename, "type": ".pdf", "vlm": str(vlm_started)})]
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]
        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[PDF+VLM] %s → %d chunks", filename, chunks)
        return {"message": "OK", "chunks_processed": chunks, "filename": filename, "vlm_used": vlm_started}

    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[PDF+VLM] Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if vlm_started:
            stop_vlm_server()


# ---------------------------------------------------------------------------
# D2: Streaming postępu ingestu — SSE endpoint
# POST /ingest/start → {task_id}  →  GET /ingest/progress/{task_id} → SSE
# ---------------------------------------------------------------------------


@router.post("/ingest/start")
async def ingest_start(
    file: UploadFile,
    req: Request,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id),
):
    """Przyjmuje plik, zwraca task_id do śledzenia postępu przez SSE.

    Plik jest zapisywany do uploads i indeksowany w tle z pełnym śledzeniem.
    """
    from ..services.progress_service import get_tracker

    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    if not file.filename:
        raise HTTPException(status_code=400, detail="Brak nazwy pliku")

    import re as _re
    safe_filename = _re.sub(r"[^\w\-_\.]", "_", os.path.basename(file.filename))
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in EXT_TO_DIR:
        raise HTTPException(status_code=400, detail=f"Nieobsługiwane rozszerzenie: {ext}")

    content = await file.read()
    if len(content) > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="Plik za duży")

    target_path, subdir = save_to_uploads(content, safe_filename, ext)
    register_file(target_path)

    tracker = get_tracker()
    task = tracker.create_task(safe_filename)

    background_tasks.add_task(rescan_nextcloud, subdir)
    if ext in TEXT_INDEXABLE:
        background_tasks.add_task(ingest_file_background, target_path, task)
    else:
        task.finish(0, f"Format {ext} zapisany (nie wymaga embeddingu)")

    logger.info("[D2] ingest/start: %s → task_id=%s", safe_filename, task.task_id,
                extra={"request_id": request_id})
    return {"task_id": task.task_id, "filename": safe_filename, "status": "started"}


@router.get("/ingest/progress/{task_id}")
async def ingest_progress(
    task_id: str,
    req: Request,
):
    """SSE stream postępu ingestowania dla danego task_id.

    Eventy: parsing → hashing → classifying → embedding → done/error
    """
    require_api_key(req)
    from ..services.progress_service import stream_progress

    return StreamingResponse(
        stream_progress(task_id),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.get("/vlm/status")
async def vlm_status():
    import requests as _requests
    try:
        from ..ingest.image_handler import VLM_PORT
        r = _requests.get(f"http://localhost:{VLM_PORT}/health", timeout=2)
        return {"vlm_running": r.status_code == 200, "port": VLM_PORT}
    except Exception:
        return {"vlm_running": False, "port": 8083}
