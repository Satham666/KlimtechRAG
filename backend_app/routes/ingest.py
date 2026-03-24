import hashlib
import logging
import os
import shutil
import subprocess
import tempfile

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    UploadFile,
)
from haystack import Document
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

from ..categories.classifier import classify_document
from ..config import settings
from ..fs_tools import resolve_path, FsSecurityError
from ..models import IngestPathRequest
from ..services import get_indexing_pipeline, doc_store, get_text_embedder
from ..services.qdrant import ensure_indexed
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


def _hash_bytes(data: bytes) -> str:
    """Oblicza SHA-256 hash z bajtow pliku."""
    return hashlib.sha256(data).hexdigest()


def _hash_file(file_path: str) -> str:
    """Oblicza SHA-256 hash z zawartosci pliku."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Mapowanie rozszerzeń → podfoldery Nextcloud / uploads
# ---------------------------------------------------------------------------

EXT_TO_DIR = {
    ".pdf": "pdf_RAG",
    ".txt": "txt_RAG",
    ".md": "txt_RAG",
    ".py": "txt_RAG",
    ".js": "txt_RAG",
    ".ts": "txt_RAG",
    ".json": "json_RAG",
    ".yml": "txt_RAG",
    ".yaml": "txt_RAG",
    ".mp3": "Audio_RAG",
    ".wav": "Audio_RAG",
    ".ogg": "Audio_RAG",
    ".flac": "Audio_RAG",
    ".mp4": "Video_RAG",
    ".avi": "Video_RAG",
    ".mkv": "Video_RAG",
    ".mov": "Video_RAG",
    ".jpg": "Images_RAG",
    ".jpeg": "Images_RAG",
    ".png": "Images_RAG",
    ".gif": "Images_RAG",
    ".bmp": "Images_RAG",
    ".webp": "Images_RAG",
    ".doc": "Doc_RAG",
    ".docx": "Doc_RAG",
    ".odt": "Doc_RAG",
    ".rtf": "Doc_RAG",
}

# Rozszerzenia które ingest potrafi przetworzyć na tekst
TEXT_INDEXABLE = {
    ".pdf",
    ".txt",
    ".md",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yml",
    ".yaml",
    ".doc",
    ".docx",
    ".odt",
    ".rtf",
}

# ---------------------------------------------------------------------------
# Helpery tekstu
# ---------------------------------------------------------------------------


def _get_embedding_model(request: Request) -> str:
    """Zwraca embedding model z nagłówka X-Embedding-Model lub wartość domyślną."""
    return request.headers.get("X-Embedding-Model", settings.embedding_model).strip()


def clean_text(text: str) -> str:
    import re

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def extract_pdf_text(file_path: str) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", file_path, "-"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        text = result.stdout.strip()
        if len(text) > 100:
            return text
    except subprocess.TimeoutExpired:
        logger.warning("[PDF] pdftotext timeout po 30s dla: %s", file_path)
    except Exception as e:
        logger.warning("[PDF] pdftotext błąd: %s", e)
    return ""


def parse_with_docling(file_path: str) -> str:
    text = extract_pdf_text(file_path)
    if text:
        logger.info("[PDF] Użyto pdftotext (szybkie)")
        return clean_text(text)

    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter

    logger.info("[PDF] pdftotext pusty → Docling OCR...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.ocr_options = RapidOcrOptions(
        lang=["english", "polish"],
        force_full_page_ocr=True,
        bitmap_area_threshold=0.0,
        backend="onnxruntime",
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(file_path)
    return clean_text(result.document.export_to_markdown())


def read_text_file(file_path: str, suffix: str) -> str:
    """Odczytuje pliki tekstowe / docx / odt."""
    if suffix in {".doc", ".docx", ".odt", ".rtf"}:
        try:
            import mammoth

            with open(file_path, "rb") as f:
                result = mammoth.extract_raw_text(f)
            return clean_text(result.value)
        except Exception as e:
            logger.warning("[TEXT] mammoth nie powiódł się (%s), czytam jako tekst", e)
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return clean_text(f.read())


# ---------------------------------------------------------------------------
# Helpery zapisu plików
# ---------------------------------------------------------------------------


def save_to_uploads(file_content: bytes, filename: str, ext: str) -> tuple[str, str]:
    """
    Zapisuje plik do odpowiedniego podfolderu na podstawie rozszerzenia.
    Zwraca (ścieżka_docelowa, nazwa_podfolderu).
    """
    subdir = EXT_TO_DIR.get(ext, "Doc_RAG")
    target_dir = os.path.join(settings.upload_base, subdir)
    os.makedirs(target_dir, exist_ok=True)

    target_path = os.path.join(target_dir, filename)
    base_name = os.path.splitext(filename)[0]
    counter = 1
    while os.path.exists(target_path):
        target_path = os.path.join(target_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    with open(target_path, "wb") as f:
        f.write(file_content)

    logger.info("[Upload] Zapisano: %s → %s", filename, target_path)
    return target_path, subdir


def rescan_nextcloud(subdir: str) -> None:
    """
    Wywołuje `occ files:scan` przez Podman żeby Nextcloud zobaczył nowe pliki.
    Nieblokujące — błąd nie zatrzymuje pipeline.
    """
    try:
        nc_path = f"/{settings.nextcloud_user}/files/RAG_Dane/{subdir}"
        result = subprocess.run(
            [
                "podman",
                "exec",
                settings.nextcloud_container,
                "php",
                "occ",
                "files:scan",
                "--path",
                nc_path,
                "--shallow",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("[NC] Rescan OK: %s", nc_path)
        else:
            logger.warning("[NC] Rescan błąd (nie krytyczny): %s", result.stderr[:200])
    except subprocess.TimeoutExpired:
        logger.warning(
            "[NC] Rescan timeout — Nextcloud może pokazać plik z opóźnieniem"
        )
    except Exception as e:
        logger.warning("[NC] Rescan wyjątek: %s", e)


# ---------------------------------------------------------------------------
# Background indexing (wspólny dla /upload i watchdog)
# ---------------------------------------------------------------------------


def ingest_file_background(file_path: str) -> None:
    """
    Indeksuje plik do Qdrant w tle.
    Wywoływany przez BackgroundTasks po zapisaniu do Nextcloud.
    """
    from ..routes.chat import clear_cache

    filename = os.path.basename(file_path)
    suffix = os.path.splitext(filename)[1].lower()

    if suffix not in TEXT_INDEXABLE:
        logger.info(
            "[BG] %s — format %s nie jest jeszcze indeksowalny (plik zapisany)",
            filename,
            suffix,
        )
        return

    try:
        if suffix == ".pdf":
            markdown_text = parse_with_docling(file_path)
        else:
            markdown_text = read_text_file(file_path, suffix)

        if not markdown_text or not markdown_text.strip():
            mark_indexed(file_path, 0)
            logger.info("[BG] Plik pusty: %s", filename)
            return

        category = classify_document(filepath=file_path, content=markdown_text)
        docs = [
            Document(content=markdown_text, meta={
                "source": filename,
                "type": suffix,
                "category": category,
            })
        ]
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]

        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[BG] ✅ %s → %d chunków w Qdrant (kategoria: %s)", filename, chunks, category)

    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[BG] ❌ Błąd indeksowania %s: %s", filename, e)


# ---------------------------------------------------------------------------
# Endpoint /upload — przyjmuje plik, zapisuje do Nextcloud, indeksuje w tle
# ---------------------------------------------------------------------------


@router.post("/upload")
async def upload_file_to_rag(
    file: UploadFile,
    req: Request,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id),
):
    """
    Przyjmuje plik z OWUI lub formularza.
    1. Zapisuje oryginalny plik do odpowiedniego folderu Nextcloud (RAG_Dane/<subdir>/)
    2. Triggeruje occ files:scan żeby plik pojawił się w Nextcloud UI
    3. Indeksuje do Qdrant w tle (BackgroundTask)
    """
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
        # Wczesny check z Content-Length przed wczytaniem do RAM
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

        # 0. Dedup — sprawdz czy plik o takim hasha juz istnieje
        _h = _hash_bytes(content)
        _ex = find_duplicate_by_hash(_h)
        if _ex:
            return {
                "message": "Plik juz istnieje",
                "duplicate": True,
                "filename": file.filename,
                "existing_path": _ex,
            }

        # 1. Zapisz do Nextcloud
        target_path, subdir = save_to_uploads(content, safe_filename, ext)
        register_file(target_path)

        # Zapisz hash do rejestru plikow
        with _get_registry_connection() as _c:
            _c.execute(
                "UPDATE files SET content_hash=? WHERE path=?", (_h, target_path)
            )
            _c.commit()

        # 2. Odśwież Nextcloud (w tle — nie blokuje odpowiedzi)
        background_tasks.add_task(rescan_nextcloud, subdir)

        # 3. Indeksuj do Qdrant (w tle)
        if ext in TEXT_INDEXABLE:
            background_tasks.add_task(ingest_file_background, target_path)
            index_msg = "Indeksowanie do RAG w tle..."
        else:
            index_msg = f"Format {ext} zapisany w Nextcloud (indeksowanie audio/video/obrazów wymaga dedykowanego pipeline)"

        logger.info(
            "[Upload] %s → Nextcloud/%s (%.1f KB) | %s",
            file.filename,
            subdir,
            file_size / 1024,
            index_msg,
            extra={"request_id": request_id},
        )
        return {
            "message": "Plik zapisany",
            "filename": file.filename,
            "duplicate": False,
            "size_bytes": file_size,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[Upload] Błąd: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Endpoint /ingest — stary endpoint (multipart, temp file). Zostaje dla kompatybilności.
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
        raise HTTPException(
            status_code=400, detail=f"File format not allowed: {file.filename}"
        )

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_file_path = tmp.name

        file_size = os.path.getsize(temp_file_path)
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413, detail=f"File too large: {file_size} bytes"
            )

        # Sprawdzenie czy użytkownik wybrał ColPali
        embedding_model = _get_embedding_model(request)
        if embedding_model.lower().startswith("vidore/colpali"):
            if suffix != ".pdf":
                raise HTTPException(
                    status_code=400, detail="ColPali obsługuje tylko pliki PDF"
                )
            from ..services.colpali_embedder import (
                index_pdf as colpali_index_pdf,
                unload_model,
            )

            try:
                pages = colpali_index_pdf(
                    pdf_path=temp_file_path,
                    doc_id=file.filename,
                    model_name=embedding_model,
                )
            finally:
                unload_model()
            return {
                "message": "Zaindeksowano przez ColPali",
                "pages_processed": pages,
                "collection": "klimtech_colpali",
            }

        if suffix == ".pdf":
            markdown_text = parse_with_docling(temp_file_path)
        elif suffix in TEXT_INDEXABLE:
            markdown_text = read_text_file(temp_file_path, suffix)
        else:
            return {
                "message": f"Format {suffix} not text-indexable",
                "chunks_processed": 0,
            }

        if not markdown_text or not markdown_text.strip():
            return {"message": "File empty (Scanned PDF?)", "chunks_processed": 0}

        category = classify_document(filepath=safe_filename, content=markdown_text)
        docs = [
            Document(
                content=markdown_text, meta={
                    "source": file.filename,
                    "type": suffix,
                    "category": category,
                }
            )
        ]
        logger.info(
            "[ingest] Embedding %s | %s",
            file.filename,
            log_stats("Start"),
            extra={"request_id": request_id},
        )
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]
        logger.info(
            "[ingest] %s → %d chunków | %s",
            file.filename,
            chunks,
            log_stats("Koniec"),
            extra={"request_id": request_id},
        )

        return {"message": "File ingested successfully", "chunks_processed": chunks}

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


# ---------------------------------------------------------------------------
# Endpoint /ingest_path — indeksuje plik z dysku (używany przez watchdog i OWUI function)
# ---------------------------------------------------------------------------


@router.post("/ingest_path")
async def ingest_by_path(
    body: IngestPathRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    from ..routes.chat import clear_cache

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
        return {
            "message": f"Format {suffix} not text-indexable yet",
            "chunks_processed": 0,
            "filename": filename,
        }

    # === SPRAWDZENIE HASHY - deduplikacja ===
    content_hash = _hash_file(file_path)
    existing_path = find_duplicate_by_hash(content_hash)
    
    if existing_path and existing_path != file_path:
        return {
            "message": "Plik o takim hash'u już istnieje w bazie",
            "duplicate": True,
            "existing_path": existing_path,
            "filename": filename,
            "chunks_processed": 0,
        }
    
    if existing_path == file_path:
        from ..file_registry import get_connection as _get_conn
        with _get_conn() as _c:
            row = _c.execute(
                "SELECT status FROM files WHERE path = ?", (file_path,)
            ).fetchone()
            if row and row["status"] == "indexed":
                return {
                    "message": "Plik już zaindeksowany (taki sam hash)",
                    "already_indexed": True,
                    "filename": filename,
                    "chunks_processed": 0,
                }

    # Zarejestruj plik jeśli nie istnieje
    register_file(file_path, compute_hash=False)
    with _get_registry_connection() as _c:
        _c.execute(
            "UPDATE files SET content_hash=? WHERE path=?", (content_hash, file_path)
        )
        _c.commit()

    # Sprawdzenie czy użytkownik wybrał ColPali
    embedding_model = _get_embedding_model(req)
    if embedding_model.lower().startswith("vidore/colpali"):
        if suffix != ".pdf":
            raise HTTPException(
                status_code=400, detail="ColPali obsługuje tylko pliki PDF"
            )
        from ..services.colpali_embedder import (
            index_pdf as colpali_index_pdf,
            unload_model,
        )
        from ..routes.chat import clear_cache

        try:
            pages = colpali_index_pdf(
                pdf_path=file_path, doc_id=filename, model_name=embedding_model
            )
        finally:
            unload_model()
        mark_indexed(file_path, pages)
        ensure_indexed()
        clear_cache()
        return {
            "message": "OK (ColPali)",
            "chunks_processed": pages,
            "filename": filename,
        }

    try:
        if suffix == ".pdf":
            markdown_text = parse_with_docling(file_path)
        else:
            markdown_text = read_text_file(file_path, suffix)

        if not markdown_text or not markdown_text.strip():
            mark_indexed(file_path, 0)
            return {
                "message": "File empty",
                "chunks_processed": 0,
                "filename": filename,
            }

        category = classify_document(filepath=file_path, content=markdown_text)
        docs = [
            Document(content=markdown_text, meta={
                "source": filename,
                "type": suffix,
                "category": category,
            })
        ]
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]

        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[ingest_path] %s → %d chunks (kategoria: %s)", filename, chunks, category)

        return {"message": "OK", "chunks_processed": chunks, "filename": filename}

    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[ingest_path] Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Endpoint /files/check — sprawdza status pliku w file_registry
# ---------------------------------------------------------------------------


@router.get("/files/check")
async def check_file_status(path: str, req: Request):
    """
    Sprawdza status pliku w file_registry.
    Używane przez n8n workflow do sprawdzania hashy przed indeksowaniem.
    """
    require_api_key(req)
    
    with _get_registry_connection() as conn:
        row = conn.execute(
            "SELECT path, filename, content_hash, status, indexed_at, chunks_count FROM files WHERE path = ?",
            (path,)
        ).fetchone()
    
    if not row:
        return {
            "exists": False,
            "path": path,
            "status": "not_registered",
            "should_index": True,
        }
    
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
# Endpoint /ingest_all — indeksuje wszystkie pending z file_registry
# ---------------------------------------------------------------------------


@router.post("/ingest_all")
async def ingest_all_pending(req: Request, limit: int = 10):
    from ..routes.chat import clear_cache

    require_api_key(req)
    files = get_pending_files()[:limit]
    results = []

    # Sprawdzenie czy użytkownik wybrał ColPali
    embedding_model = _get_embedding_model(req)
    use_colpali = embedding_model.lower().startswith("vidore/colpali")

    for f in files:
        if f.extension not in TEXT_INDEXABLE:
            mark_indexed(f.path, 0)  # oznacz jako skipped żeby nie wracać
            results.append(
                {"filename": f.filename, "chunks": 0, "status": "skipped_format"}
            )
            continue

        # Obsługa ColPali dla PDF
        if f.extension == ".pdf" and use_colpali:
            try:
                from ..services.colpali_embedder import index_pdf as colpali_index_pdf

                pages = colpali_index_pdf(
                    pdf_path=f.path, doc_id=f.filename, model_name=embedding_model
                )
                mark_indexed(f.path, pages)
                results.append(
                    {"filename": f.filename, "chunks": pages, "status": "ok_colpali"}
                )
            except Exception as e:
                mark_failed(f.path, str(e)[:100])
                results.append(
                    {
                        "filename": f.filename,
                        "chunks": 0,
                        "status": "error",
                        "error": str(e)[:100],
                    }
                )
            continue

        try:
            if f.extension == ".pdf":
                markdown_text = parse_with_docling(f.path)
            else:
                markdown_text = read_text_file(f.path, f.extension)

            if not markdown_text or not markdown_text.strip():
                mark_indexed(f.path, 0)
                results.append({"filename": f.filename, "chunks": 0, "status": "empty"})
                continue

            docs = [
                Document(
                    content=markdown_text,
                    meta={"source": f.filename, "type": f.extension},
                )
            ]
            result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
            chunks = result["writer"]["documents_written"]
            mark_indexed(f.path, chunks)
            results.append({"filename": f.filename, "chunks": chunks, "status": "ok"})

        except Exception as e:
            mark_failed(f.path, str(e)[:100])
            results.append(
                {
                    "filename": f.filename,
                    "chunks": 0,
                    "status": "error",
                    "error": str(e)[:100],
                }
            )

    # Zwolnij VRAM z ColPali przed powrotem
    if use_colpali:
        from ..services.colpali_embedder import unload_model

        unload_model()

    ensure_indexed()
    clear_cache()
    return {"indexed": len(results), "results": results}


# ---------------------------------------------------------------------------
# Endpoint /ingest_pdf_vlm — PDF z opisem obrazów przez VLM
# ---------------------------------------------------------------------------


@router.post("/ingest_pdf_vlm")
async def ingest_pdf_with_vlm(
    body: IngestPathRequest,
    req: Request,
    max_images: int = 10,
    request_id: str = Depends(get_request_id),
):
    """Indeksuje PDF z opisem obrazów przez VLM (LFM2.5-VL lub podobny)."""
    from ..routes.chat import clear_cache
    from ..ingest.image_handler import start_vlm_server, stop_vlm_server

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

            result_data = process_pdf_with_images(
                pdf_path=file_path,
                extract_images=True,
                describe_images=True,
                max_images=max_images,
            )
            markdown_text = clean_text(
                result_data.get("combined_content", "")
            ) or parse_with_docling(file_path)

        if not markdown_text or not markdown_text.strip():
            mark_indexed(file_path, 0)
            return {
                "message": "File empty",
                "chunks_processed": 0,
                "filename": filename,
            }

        docs = [
            Document(
                content=markdown_text,
                meta={"source": filename, "type": ".pdf", "vlm": str(vlm_started)},
            )
        ]
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]

        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[PDF+VLM] %s → %d chunks", filename, chunks)

        return {
            "message": "OK",
            "chunks_processed": chunks,
            "filename": filename,
            "vlm_used": vlm_started,
        }

    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[PDF+VLM] Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if vlm_started:
            stop_vlm_server()


@router.get("/vlm/status")
async def vlm_status():
    import requests as _requests

    try:
        from ..ingest.image_handler import VLM_PORT

        r = _requests.get(f"http://localhost:{VLM_PORT}/health", timeout=2)
        return {"vlm_running": r.status_code == 200, "port": VLM_PORT}
    except Exception:
        return {"vlm_running": False, "port": 8083}
