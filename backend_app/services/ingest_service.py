import logging
import os
import re
import shutil
import tempfile

from haystack import Document

from ..config import settings
from ..categories.classifier import classify_document
from ..file_registry import (
    mark_indexed,
    mark_failed,
    register_file,
    find_duplicate_by_hash,
    get_pending_files,
    get_connection as _get_registry_connection,
)
from ..services.cache_service import clear_cache
from ..services.dedup_service import hash_bytes, hash_file, compute_content_hash
from ..services.nextcloud_service import (
    EXT_TO_DIR,
    TEXT_INDEXABLE,
    save_to_uploads,
)
from ..services.enrichment_service import ENRICHMENT_ENABLED, enrich_chunks
from ..services.metadata_service import build_chunk_meta
from ..services.parser_service import parse_with_docling, read_text_file

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Ingest Service — orkiestracja: parse → chunk → embed → store
# Wydzielony z routes/ingest.py (A1b refaktoryzacja)
# ---------------------------------------------------------------------------


class IngestError(Exception):
    """Błąd w warstwie ingest service. Zawiera status_code do mapowania na HTTP."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _sanitize_filename(filename: str) -> str:
    """Zwraca bezpieczną nazwę pliku (usuwa znaki specjalne, ścieżki)."""
    return re.sub(r"[^\w\-_\.]", "_", os.path.basename(filename))


def _is_colpali(model_name: str) -> bool:
    return model_name.lower().startswith("vidore/colpali")


def _run_indexing(docs: list) -> dict:
    """Uruchamia indexing pipeline, opcjonalnie z C4 Contextual Enrichment.

    Jeśli KLIMTECH_CONTEXTUAL_ENRICHMENT=true:
        split ręcznie → enrich → embedder → writer
    Normalnie:
        splitter → embedder → writer (cały pipeline)
    """
    from ..services import get_indexing_pipeline
    pipeline = get_indexing_pipeline()
    if ENRICHMENT_ENABLED:
        from haystack.components.preprocessors import DocumentSplitter as _DS

        splitter = _DS(split_by="word", split_length=200, split_overlap=30)
        split_result = splitter.run(documents=docs)
        enriched = enrich_chunks(split_result["documents"])
        return pipeline.run({"embedder": {"documents": enriched}})
    return pipeline.run({"splitter": {"documents": docs}})


def ingest_file_background(file_path: str, task: "ProgressTask | None" = None) -> None:
    """Indeksuje plik do Qdrant w tle.

    Wywoływany przez BackgroundTasks po zapisaniu do uploads.
    Opcjonalny parametr task — jeśli podany, emituje eventy SSE postępu (D2).
    """
    from ..services import get_indexing_pipeline
    from ..services.qdrant import ensure_indexed

    def _emit(stage: str, msg: str, cur: int = 0, tot: int = 0) -> None:
        if task:
            task.emit(stage, msg, cur, tot)

    filename = os.path.basename(file_path)
    suffix = os.path.splitext(filename)[1].lower()

    if suffix not in TEXT_INDEXABLE:
        logger.info(
            "[BG] %s — format %s nie jest jeszcze indeksowalny (plik zapisany)",
            filename,
            suffix,
        )
        if task:
            task.finish(0, f"Format {suffix} nie jest indeksowalny")
        return

    try:
        _emit("parsing", f"Parsowanie {filename}…")
        if suffix == ".pdf":
            markdown_text = parse_with_docling(file_path)
        else:
            markdown_text = read_text_file(file_path, suffix)

        if not markdown_text or not markdown_text.strip():
            mark_indexed(file_path, 0)
            logger.info("[BG] Plik pusty: %s", filename)
            if task:
                task.finish(0, "Plik pusty")
            return

        # W3 Vector Cache: sprawdź czy ten sam tekst był już zaindeksowany
        _emit("hashing", "Sprawdzanie cache…")
        text_hash = compute_content_hash(markdown_text)
        with _get_registry_connection() as _c:
            hit = _c.execute(
                "SELECT path FROM files WHERE content_hash = ? AND status = 'indexed' LIMIT 1",
                (text_hash,),
            ).fetchone()
        if hit:
            logger.info("[BG] ✅ Vector cache hit: %s (hash=%s…)", filename, text_hash[:12])
            mark_indexed(file_path, 0)
            if task:
                task.finish(0, "Cache hit — plik już zaindeksowany")
            return

        logger.info(
            "[BG] Vector cache miss: %s (hash=%s…) — uruchamiam embedding",
            filename,
            text_hash[:12],
        )
        _emit("classifying", "Klasyfikacja kategorii…")
        category = classify_document(filepath=file_path, content=markdown_text)
        # C6: rozszerzone metadane (title, author, page_count, language, indexed_at)
        meta = build_chunk_meta(
            source=filename,
            chunk_index=0,
            total_chunks=0,
            text=markdown_text,
            file_path=file_path,
            extra={"type": suffix, "category": category},
        )
        docs = [Document(content=markdown_text, meta=meta)]
        _emit("embedding", "Embedding i zapis do Qdrant…")
        result = _run_indexing(docs)
        chunks = result["writer"]["documents_written"]

        mark_indexed(file_path, chunks)
        # W3 Vector Cache: zapisz hash treści dla przyszłych lookupów
        with _get_registry_connection() as _c:
            _c.execute(
                "UPDATE files SET content_hash = ? WHERE path = ?",
                (text_hash, file_path),
            )
            _c.commit()
        ensure_indexed()
        clear_cache()
        logger.info(
            "[BG] ✅ %s → %d chunków w Qdrant (kategoria: %s)", filename, chunks, category
        )
        if task:
            task.finish(chunks)

    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[BG] ❌ Błąd indeksowania %s: %s", filename, e)
        if task:
            task.finish(0, str(e)[:120])


def ingest_text_docs(file_path: str, filename: str, suffix: str, model_name: str) -> int:
    """Indeksuje plik tekstowy za pomocą RAG pipeline (e5-large lub bge-large).

    Zwraca liczbę zapisanych chunków.
    """
    from ..services import get_indexing_pipeline

    if suffix == ".pdf":
        markdown_text = parse_with_docling(file_path)
    else:
        markdown_text = read_text_file(file_path, suffix)

    if not markdown_text or not markdown_text.strip():
        mark_indexed(file_path, 0)
        logger.info("⚪ Empty: %s", filename)
        return 0

    # C6: rozszerzone metadane (title, author, page_count, language, indexed_at)
    meta = build_chunk_meta(
        source=filename,
        chunk_index=0,
        total_chunks=0,
        text=markdown_text,
        file_path=file_path,
        extra={"type": suffix, "embedding_model": model_name},
    )
    docs = [Document(content=markdown_text, meta=meta)]
    result = _run_indexing(docs)
    chunks = result["writer"]["documents_written"]
    mark_indexed(file_path, chunks)
    logger.info("✅ %s: %s (%d chunks)", model_name, filename, chunks)
    return chunks


def ingest_colpali_batch(file_batch, metadata: dict) -> list[dict]:
    """Indeksuje batch plików PDF przez ColPali.

    Zwraca listę wyników per plik.
    """
    from ..services.colpali_embedder import index_pdf as colpali_index_pdf
    from ..services.embedder_pool import get_embedder, unload_embedder

    results = []
    try:
        get_embedder("colpali")
        for f in file_batch:
            if f.extension != ".pdf":
                logger.warning("[ColPali] Skip non-PDF %s", f.filename)
                mark_indexed(f.path, 0)
                results.append({"filename": f.filename, "chunks": 0, "status": "skipped"})
                continue
            try:
                pages = colpali_index_pdf(
                    pdf_path=f.path, doc_id=f.filename, model_name=metadata["name"]
                )
                mark_indexed(f.path, pages)
                results.append({"filename": f.filename, "chunks": pages, "status": "ok_colpali"})
                logger.info("✅ ColPali: %s (%d pages)", f.filename, pages)
            except Exception as e:
                mark_failed(f.path, str(e)[:100])
                results.append(
                    {"filename": f.filename, "chunks": 0, "status": "error_colpali", "error": str(e)[:100]}
                )
                logger.exception("❌ ColPali: %s", f.filename)
        unload_embedder("colpali")
        logger.info("[ColPali] Model zwolniony z VRAM (pool)")
    except ImportError:
        logger.warning("[ColPali] colpali_embedder import error, skip batch")
        for f in file_batch:
            mark_indexed(f.path, 0)
            results.append({"filename": f.filename, "chunks": 0, "status": "skipped_colpali_unavailable"})
    return results


def ingest_pdf_vlm_sync(file_path: str, filename: str, max_images: int = 10) -> dict:
    """Indeksuje PDF z opisem obrazów przez VLM (synchronicznie).

    Zwraca słownik z wynikiem: message, chunks_processed, filename, vlm_used.
    Wydzielone z routes/ingest.py (A1b refaktoryzacja).
    """
    from ..ingest.image_handler import start_vlm_server, stop_vlm_server, process_pdf_with_images
    from ..services.parser_service import clean_text
    from ..services import get_indexing_pipeline
    from ..services.qdrant import ensure_indexed
    from haystack import Document

    vlm_started = False
    try:
        logger.info("[PDF+VLM] Uruchamiam VLM server...")
        vlm_started = start_vlm_server()

        if not vlm_started:
            logger.warning("[PDF+VLM] VLM niedostępny, używam zwykłego parsera")
            markdown_text = parse_with_docling(file_path)
        else:
            result_data = process_pdf_with_images(
                pdf_path=file_path, extract_images=True,
                describe_images=True, max_images=max_images,
            )
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
        raise
    finally:
        if vlm_started:
            stop_vlm_server()


def ingest_semantic_batch(file_batch, model_name: str) -> list[dict]:
    """Indeksuje batch plików tekstowych (e5-large / bge-large).

    Zwraca listę wyników per plik.
    """
    from ..services.embedder_pool import unload_embedder

    results = []
    try:
        for f in file_batch:
            try:
                chunks = ingest_text_docs(f.path, f.filename, f.extension, model_name)
                results.append(
                    {"filename": f.filename, "chunks": chunks, "status": f"ok_{model_name}" if chunks else "empty"}
                )
            except Exception as e:
                mark_failed(f.path, str(e)[:100])
                results.append(
                    {"filename": f.filename, "chunks": 0, "status": "error", "error": str(e)[:100]}
                )
                logger.exception("❌ %s: %s", model_name, f.filename)
    except Exception as e:
        logger.exception("❌ %s batch error: %s", model_name, e)
        for f in file_batch:
            mark_failed(f.path, str(e)[:100])
            results.append({"filename": f.filename, "chunks": 0, "status": "error", "error": str(e)[:100]})
    finally:
        unload_embedder(model_name)
        logger.info("[%s] Model zwolniony z VRAM (pool)", model_name)
    return results


# ---------------------------------------------------------------------------
# Orkiestracja endpointów (A1b dokończenie) — wydzielone z routes/ingest.py
# ---------------------------------------------------------------------------


def _ingest_colpali_single(file_path: str, doc_id: str, model_name: str) -> int:
    """Indeksuje pojedynczy PDF przez ColPali. Zwraca liczbę stron."""
    from ..services.colpali_embedder import index_pdf as colpali_index_pdf, unload_model
    try:
        return colpali_index_pdf(pdf_path=file_path, doc_id=doc_id, model_name=model_name)
    finally:
        unload_model()


def process_upload(content: bytes, original_filename: str, request_id: str = "-") -> dict:
    """Walidacja + zapis pliku do uploads + dispatch flag.

    Zwraca dict: target_path, subdir, safe_filename, will_index, status_val.
    Rzuca IngestError przy błędzie walidacji/duplikacie.
    """
    if not original_filename:
        raise IngestError("Brak nazwy pliku", 400)

    safe_filename = _sanitize_filename(original_filename)
    if not safe_filename or safe_filename.startswith("."):
        raise IngestError("Nieprawidłowa nazwa pliku", 400)

    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in EXT_TO_DIR:
        raise IngestError(
            f"Nieobsługiwane rozszerzenie: {ext}. Dozwolone: {', '.join(sorted(EXT_TO_DIR.keys()))}",
            400,
        )

    file_size = len(content)
    if file_size > settings.max_file_size_bytes:
        raise IngestError(
            f"Plik za duży: {file_size / 1024 / 1024:.1f} MB (limit {settings.max_file_size_bytes / 1024 / 1024:.0f} MB)",
            413,
        )

    file_hash = hash_bytes(content)
    existing = find_duplicate_by_hash(file_hash)
    if existing:
        return {"duplicate": True, "existing_path": existing, "filename": original_filename}

    target_path, subdir = save_to_uploads(content, safe_filename, ext)
    register_file(target_path)
    with _get_registry_connection() as _c:
        _c.execute("UPDATE files SET content_hash=? WHERE path=?", (file_hash, target_path))
        _c.commit()

    will_index = ext in TEXT_INDEXABLE
    status_val = "pending" if will_index else "skipped"
    logger.info(
        "[Upload] %s → Nextcloud/%s (%.1f KB) | status=%s",
        original_filename, subdir, file_size / 1024, status_val,
        extra={"request_id": request_id},
    )
    return {
        "duplicate": False,
        "target_path": target_path,
        "subdir": subdir,
        "safe_filename": safe_filename,
        "will_index": will_index,
        "status_val": status_val,
        "ext": ext,
    }


def process_temp_ingest(
    file_obj, original_filename: str, embedding_model: str, request_id: str = "-"
) -> dict:
    """Klasyczny /ingest — zapisuje multipart do temp file, indeksuje bezpośrednio.

    Zwraca dict zgodny z formatem /ingest. Rzuca IngestError przy błędach.
    """
    if not original_filename:
        raise IngestError("Filename is missing", 400)

    suffix = os.path.splitext(original_filename)[1].lower()
    if suffix not in settings.allowed_extensions_docs:
        raise IngestError(f"File format not allowed: {original_filename}", 400)

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file_obj, tmp)
            temp_file_path = tmp.name

        file_size = os.path.getsize(temp_file_path)
        if file_size > settings.max_file_size_bytes:
            raise IngestError(f"File too large: {file_size} bytes", 413)

        if _is_colpali(embedding_model):
            if suffix != ".pdf":
                raise IngestError("ColPali obsługuje tylko pliki PDF", 400)
            pages = _ingest_colpali_single(temp_file_path, original_filename, embedding_model)
            return {"message": "Zaindeksowano przez ColPali", "pages_processed": pages, "collection": "klimtech_colpali"}

        if suffix not in TEXT_INDEXABLE:
            return {"message": f"Format {suffix} not text-indexable", "chunks_processed": 0}

        logger.info("[ingest] Embedding %s", original_filename, extra={"request_id": request_id})
        chunks = ingest_text_docs(temp_file_path, original_filename, suffix, embedding_model)
        if chunks == 0:
            return {"message": "File empty (Scanned PDF?)", "chunks_processed": 0}
        logger.info("[ingest] %s → %d chunków", original_filename, chunks, extra={"request_id": request_id})
        return {"message": "File ingested successfully", "chunks_processed": chunks}
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


def process_path_ingest(file_path: str, embedding_model: str) -> dict:
    """Logika /ingest_path — indeksuje plik z dysku z dedup, ColPali/text routing.

    Zwraca dict zgodny z formatem endpointu. Rzuca IngestError przy błędach.
    """
    from ..services.qdrant import ensure_indexed

    filename = os.path.basename(file_path)
    suffix = os.path.splitext(filename)[1].lower()

    if suffix not in settings.allowed_extensions_docs:
        raise IngestError(f"Extension not allowed: {suffix}", 400)

    if suffix not in TEXT_INDEXABLE:
        return {"message": f"Format {suffix} not text-indexable yet", "chunks_processed": 0, "filename": filename}

    content_hash = hash_file(file_path)
    existing_path = find_duplicate_by_hash(content_hash)

    if existing_path and existing_path != file_path:
        return {
            "message": "Plik o takim hash'u już istnieje w bazie",
            "duplicate": True, "existing_path": existing_path,
            "filename": filename, "chunks_processed": 0,
        }

    if existing_path == file_path:
        with _get_registry_connection() as _c:
            row = _c.execute("SELECT status FROM files WHERE path = ?", (file_path,)).fetchone()
            if row and row["status"] == "indexed":
                return {
                    "message": "Plik już zaindeksowany (taki sam hash)",
                    "already_indexed": True,
                    "filename": filename, "chunks_processed": 0,
                }

    register_file(file_path, compute_hash=False)
    with _get_registry_connection() as _c:
        _c.execute("UPDATE files SET content_hash=? WHERE path=?", (content_hash, file_path))
        _c.commit()

    if _is_colpali(embedding_model):
        if suffix != ".pdf":
            raise IngestError("ColPali obsługuje tylko pliki PDF", 400)
        pages = _ingest_colpali_single(file_path, filename, embedding_model)
        mark_indexed(file_path, pages)
        ensure_indexed()
        clear_cache()
        return {"message": "OK (ColPali)", "chunks_processed": pages, "filename": filename}

    try:
        chunks = ingest_text_docs(file_path, filename, suffix, embedding_model)
        ensure_indexed()
        clear_cache()
        logger.info("[ingest_path] %s → %d chunks", filename, chunks)
        return {"filename": filename, "chunks_processed": chunks, "status": "indexed"}
    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[ingest_path] Error: %s", e)
        raise IngestError(str(e), 500)


def process_all_pending(limit: int = 10) -> list[dict]:
    """Indeksuje pending pliki z grupowaniem po modelu embeddera.

    Zwraca listę dict per plik (filename, chunks, status).
    """
    from ..services.model_selector import select_model_for_file, get_model_metadata
    from ..services.qdrant import ensure_indexed

    files = get_pending_files()[:limit]
    results: list[dict] = []
    if not files:
        return results

    files_by_model: dict = {}
    for f in files:
        if f.extension not in TEXT_INDEXABLE:
            mark_indexed(f.path, 0)
            results.append({"filename": f.filename, "chunks": 0, "status": "skipped_format"})
            continue
        model_name = select_model_for_file(f.path)
        files_by_model.setdefault(model_name, []).append(f)

    logger.info(
        "📦 Grupowanie plików: %d modeli, %d plików",
        len(files_by_model), sum(len(v) for v in files_by_model.values()),
    )

    for model_name, file_batch in files_by_model.items():
        metadata = get_model_metadata(model_name)
        logger.info(
            "🔄 [%s] Indeksowanie %d plików (%s, %dD, %dMB VRAM)",
            model_name, len(file_batch), metadata["type"],
            metadata["dimension"], metadata["vram_mb"],
        )
        if model_name == "colpali":
            results.extend(ingest_colpali_batch(file_batch, metadata))
        else:
            results.extend(ingest_semantic_batch(file_batch, model_name))

    ensure_indexed()
    clear_cache()
    indexed_count = len([r for r in results if "ok" in r.get("status", "")])
    logger.info("🎯 Indeksowanie skończone: %d/%d sukces", indexed_count, len(results))
    return results


def check_file_in_registry(path: str) -> dict:
    """Sprawdza status pliku w file_registry. Logika /files/check."""
    with _get_registry_connection() as conn:
        row = conn.execute(
            "SELECT path, filename, content_hash, status, indexed_at, chunks_count FROM files WHERE path = ?",
            (path,),
        ).fetchone()
    if not row:
        return {"exists": False, "path": path, "status": "not_registered", "should_index": True}
    return {
        "exists": True,
        "path": row["path"],
        "filename": row["filename"],
        "content_hash": row["content_hash"],
        "status": row["status"],
        "indexed_at": row["indexed_at"],
        "chunks_count": row["chunks_count"],
        "should_index": row["status"] not in ("indexed", "pending"),
    }


def prepare_progress_ingest(content: bytes, original_filename: str) -> dict:
    """Walidacja + zapis pliku dla D2 progress streaming.

    Zwraca dict: target_path, subdir, safe_filename, ext, will_index, task.
    Rzuca IngestError przy walidacji.
    """
    from ..services.progress_service import get_tracker

    if not original_filename:
        raise IngestError("Brak nazwy pliku", 400)

    safe_filename = _sanitize_filename(original_filename)
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in EXT_TO_DIR:
        raise IngestError(f"Nieobsługiwane rozszerzenie: {ext}", 400)

    if len(content) > settings.max_file_size_bytes:
        raise IngestError("Plik za duży", 413)

    target_path, subdir = save_to_uploads(content, safe_filename, ext)
    register_file(target_path)

    task = get_tracker().create_task(safe_filename)
    return {
        "target_path": target_path,
        "subdir": subdir,
        "safe_filename": safe_filename,
        "ext": ext,
        "will_index": ext in TEXT_INDEXABLE,
        "task": task,
    }


def list_active_ingest_tasks() -> dict:
    """Logika /ingest/active — lista aktywnych tasków z ProgressTracker."""
    import time as _time
    from ..services.progress_service import get_tracker

    tracker = get_tracker()
    tasks = []
    for task_id, task in list(tracker._tasks.items()):
        tasks.append({
            "task_id": task_id,
            "filename": task.filename,
            "done": task.done,
            "age_seconds": int(_time.monotonic() - task.created_at),
        })
    running = [t for t in tasks if not t["done"]]
    return {"tasks": tasks, "running": len(running), "total": len(tasks)}


def get_vlm_status() -> dict:
    """Logika /vlm/status — sprawdza czy VLM server żyje."""
    import requests as _requests
    try:
        from ..ingest.image_handler import VLM_PORT
        r = _requests.get(f"http://localhost:{VLM_PORT}/health", timeout=2)
        return {"vlm_running": r.status_code == 200, "port": VLM_PORT}
    except Exception:
        return {"vlm_running": False, "port": 8083}
