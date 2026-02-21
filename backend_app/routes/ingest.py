import logging
import os
import shutil
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

from ..config import settings
from ..models import IngestPathRequest
from ..services import indexing_pipeline, doc_store, text_embedder
from ..services.qdrant import ensure_indexed
from ..utils.rate_limit import apply_rate_limit, get_client_id
from ..utils.dependencies import require_api_key, get_request_id
from ..monitoring import log_stats
from ..file_registry import (
    mark_indexed,
    mark_failed,
    get_pending_files,
)

router = APIRouter(tags=["ingest"])
logger = logging.getLogger("klimtechrag")


def clean_text(text: str) -> str:
    import re

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def extract_pdf_text(file_path: str) -> str:
    import subprocess

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
    except Exception:
        pass

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

    logger.info("[PDF] pdftotext pusty, używam Docling OCR...")
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


def parse_pdf_with_images(
    file_path: str,
    extract_images: bool = True,
    describe_images: bool = False,
    max_images: int = 10,
) -> str:
    """Parsuje PDF z opcjonalną obsługą obrazów przez VLM."""

    if not extract_images and not describe_images:
        return parse_with_docling(file_path)

    try:
        from ..ingest.image_handler import process_pdf_with_images

        result = process_pdf_with_images(
            pdf_path=file_path,
            extract_images=extract_images,
            describe_images=describe_images,
            max_images=max_images,
        )

        combined = result.get("combined_content", "")
        images_info = result.get("images", [])

        if describe_images and images_info:
            described = len([i for i in images_info if i.get("description")])
            logger.info(
                "[PDF+VLM] Tekst=%d znaków, obrazy=%d, opisane=%d",
                len(result.get("text", "")),
                len(images_info),
                described,
            )
        else:
            logger.info(
                "[PDF+IMG] Tekst=%d znaków, obrazy=%d",
                len(result.get("text", "")),
                len(images_info),
            )

        return clean_text(combined) if combined else parse_with_docling(file_path)

    except Exception as e:
        logger.warning("[PDF+IMG] Błąd, fallback do zwykłego parsera: %s", e)
        return parse_with_docling(file_path)


RAG_UPLOAD_BASE = settings.upload_base

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


@router.post("/ingest")
async def ingest_file(
    file: UploadFile,
    request: Request,
    request_id: str = Depends(get_request_id),
):
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
    markdown_text = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_file_path = tmp.name

        file_size = os.path.getsize(temp_file_path)
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size} bytes (limit {settings.max_file_size_bytes})",
            )

        if suffix == ".pdf":
            logger.info(
                "[Backend] Parsowanie PDF %s | %s",
                file.filename,
                log_stats("Start"),
                extra={"request_id": request_id},
            )
            markdown_text = parse_with_docling(temp_file_path)
            logger.info(
                "[Backend] PDF sparsowany | %s",
                log_stats("Po parsowaniu"),
                extra={"request_id": request_id},
            )
        else:
            logger.info(
                "[Backend] Parsowanie tekstu %s | %s",
                file.filename,
                log_stats("Start"),
                extra={"request_id": request_id},
            )
            with open(temp_file_path, "r", encoding="utf-8") as f:
                markdown_text = clean_text(f.read())

        if not markdown_text or len(markdown_text.strip()) == 0:
            logger.warning(
                "[Backend] Plik pusty (skan bez tekstu): %s",
                file.filename,
                extra={"request_id": request_id},
            )
            return {"message": "File empty (Scanned PDF?)", "chunks_processed": 0}

        docs = [
            Document(
                content=markdown_text, meta={"source": file.filename, "type": suffix}
            )
        ]
        logger.info(
            "[Backend] Embedding/Indeksowanie | %s",
            log_stats("Start"),
            extra={"request_id": request_id},
        )
        result = indexing_pipeline.run({"splitter": {"documents": docs}})
        logger.info(
            "[Backend] Zaindeksowano %d chunków | %s",
            result["writer"]["documents_written"],
            log_stats("Koniec"),
            extra={"request_id": request_id},
        )

        return {
            "message": "File ingested successfully",
            "chunks_processed": result["writer"]["documents_written"],
        }
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@router.post("/upload")
async def upload_file_to_rag(
    file: UploadFile,
    req: Request,
    background_tasks: BackgroundTasks,
    request_id: str = Depends(get_request_id),
):
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    if not file.filename:
        raise HTTPException(status_code=400, detail="Brak nazwy pliku")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in EXT_TO_DIR:
        raise HTTPException(
            status_code=400,
            detail=f"Nieobsługiwane rozszerzenie: {ext}. Dozwolone: {', '.join(EXT_TO_DIR.keys())}",
        )

    subdir = EXT_TO_DIR[ext]
    target_dir = os.path.join(RAG_UPLOAD_BASE, subdir)
    os.makedirs(target_dir, exist_ok=True)

    target_path = os.path.join(target_dir, file.filename)

    counter = 1
    base_name = os.path.splitext(file.filename)[0]
    while os.path.exists(target_path):
        target_path = os.path.join(target_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    try:
        with open(target_path, "wb") as f:
            content = await file.read()
            f.write(content)

        file_size = os.path.getsize(target_path)
        logger.info(
            "[Upload] Zapisano %s do %s (%.1f KB)",
            os.path.basename(target_path),
            EXT_TO_DIR[ext],
            file_size / 1024,
            extra={"request_id": request_id},
        )

        background_tasks.add_task(ingest_file_background, target_path)

        return {
            "status": "ok",
            "filename": os.path.basename(target_path),
            "directory": EXT_TO_DIR[ext],
            "size_bytes": file_size,
            "message": f"Plik zapisany w {EXT_TO_DIR[ext]}. Indeksowanie w tle...",
        }
    except Exception as e:
        logger.exception("[Upload] Błąd: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


def ingest_file_background(file_path: str):
    from ..routes.chat import clear_cache

    try:
        filename = os.path.basename(file_path)
        suffix = os.path.splitext(filename)[1].lower()

        if suffix not in settings.allowed_extensions_docs:
            logger.warning("[Background] Rozszerzenie niedozwolone: %s", suffix)
            return

        if suffix == ".pdf":
            markdown_text = parse_with_docling(file_path)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_text = clean_text(f.read())

        if not markdown_text or len(markdown_text.strip()) == 0:
            mark_indexed(file_path, 0)
            logger.info("[Background] Plik pusty: %s", filename)
            return

        docs = [
            Document(content=markdown_text, meta={"source": filename, "type": suffix})
        ]
        result = indexing_pipeline.run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]

        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[Background] Zaindeksowano %s -> %d chunks", filename, chunks)
    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[Background] Błąd indeksowania %s: %s", file_path, e)


@router.post("/ingest_path")
async def ingest_by_path(
    body: IngestPathRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    from ..routes.chat import clear_cache

    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    file_path = body.path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    suffix = os.path.splitext(filename)[1].lower()

    if suffix not in settings.allowed_extensions_docs:
        raise HTTPException(status_code=400, detail=f"Extension not allowed: {suffix}")

    try:
        if suffix == ".pdf":
            markdown_text = parse_with_docling(file_path)
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                markdown_text = clean_text(f.read())

        if not markdown_text or len(markdown_text.strip()) == 0:
            mark_indexed(file_path, 0)
            return {
                "message": "File empty",
                "chunks_processed": 0,
                "filename": filename,
            }

        docs = [
            Document(content=markdown_text, meta={"source": filename, "type": suffix})
        ]
        result = indexing_pipeline.run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]

        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[ingest_path] %s -> %d chunks", filename, chunks)

        return {"message": "OK", "chunks_processed": chunks, "filename": filename}
    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[ingest_path] Error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest_pdf_vlm")
async def ingest_pdf_with_vlm(
    body: IngestPathRequest,
    req: Request,
    max_images: int = 10,
    request_id: str = Depends(get_request_id),
):
    """Indeksuje PDF z opisem obrazów przez VLM."""
    from ..routes.chat import clear_cache
    from ..ingest.image_handler import start_vlm_server, stop_vlm_server

    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    file_path = body.path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    suffix = os.path.splitext(filename)[1].lower()

    if suffix != ".pdf":
        raise HTTPException(
            status_code=400, detail="This endpoint only accepts PDF files"
        )

    vlm_started = False
    try:
        logger.info("[PDF+VLM] Uruchamiam VLM server...")
        vlm_started = start_vlm_server()

        if not vlm_started:
            logger.warning("[PDF+VLM] VLM nie dostępny, używam zwykłego parsera")
            markdown_text = parse_with_docling(file_path)
        else:
            logger.info("[PDF+VLM] Przetwarzam %s z opisem obrazów...", filename)
            markdown_text = parse_pdf_with_images(
                file_path,
                extract_images=True,
                describe_images=True,
                max_images=max_images,
            )

        if not markdown_text or len(markdown_text.strip()) == 0:
            mark_indexed(file_path, 0)
            return {
                "message": "File empty",
                "chunks_processed": 0,
                "filename": filename,
            }

        docs = [
            Document(
                content=markdown_text,
                meta={"source": filename, "type": suffix, "vlm": "true"},
            )
        ]
        result = indexing_pipeline.run({"splitter": {"documents": docs}})
        chunks = result["writer"]["documents_written"]

        mark_indexed(file_path, chunks)
        ensure_indexed()
        clear_cache()
        logger.info("[PDF+VLM] %s -> %d chunks", filename, chunks)

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
            logger.info("[PDF+VLM] Zatrzymuję VLM server...")
            stop_vlm_server()


@router.get("/vlm/status")
async def vlm_status():
    """Sprawdza czy VLM server działa."""
    import requests

    try:
        from ..ingest.image_handler import VLM_PORT

        r = requests.get(f"http://localhost:{VLM_PORT}/health", timeout=2)
        return {"vlm_running": r.status_code == 200, "port": VLM_PORT}
    except Exception:
        return {"vlm_running": False, "port": 8083}


@router.post("/ingest_all")
async def ingest_all_pending(
    req: Request,
    limit: int = 10,
):
    from ..routes.chat import clear_cache

    require_api_key(req)
    files = get_pending_files()[:limit]

    results = []
    for f in files:
        try:
            if f.extension == ".pdf":
                markdown_text = parse_with_docling(f.path)
            else:
                with open(f.path, "r", encoding="utf-8") as file:
                    markdown_text = clean_text(file.read())

            if not markdown_text or len(markdown_text.strip()) == 0:
                mark_indexed(f.path, 0)
                results.append({"filename": f.filename, "chunks": 0, "status": "empty"})
                continue

            docs = [
                Document(
                    content=markdown_text,
                    meta={"source": f.filename, "type": f.extension},
                )
            ]
            result = indexing_pipeline.run({"splitter": {"documents": docs}})
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

    ensure_indexed()
    clear_cache()
    return {"indexed": len(results), "results": results}
