import logging
import os

from haystack import Document

from ..categories.classifier import classify_document
from ..file_registry import (
    mark_indexed,
    mark_failed,
    get_connection as _get_registry_connection,
)
from ..services.cache_service import clear_cache
from ..services.dedup_service import compute_content_hash
from ..services.nextcloud_service import TEXT_INDEXABLE
from ..services.metadata_service import build_chunk_meta
from ..services.parser_service import parse_with_docling, read_text_file

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Ingest Service — orkiestracja: parse → chunk → embed → store
# Wydzielony z routes/ingest.py (A1b refaktoryzacja)
# ---------------------------------------------------------------------------


def ingest_file_background(file_path: str) -> None:
    """Indeksuje plik do Qdrant w tle.

    Wywoływany przez BackgroundTasks po zapisaniu do uploads.
    """
    from ..services import get_indexing_pipeline
    from ..services.qdrant import ensure_indexed

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

        # W3 Vector Cache: sprawdź czy ten sam tekst był już zaindeksowany
        text_hash = compute_content_hash(markdown_text)
        with _get_registry_connection() as _c:
            hit = _c.execute(
                "SELECT path FROM files WHERE content_hash = ? AND status = 'indexed' LIMIT 1",
                (text_hash,),
            ).fetchone()
        if hit:
            logger.info("[BG] ✅ Vector cache hit: %s (hash=%s…)", filename, text_hash[:12])
            mark_indexed(file_path, 0)
            return

        logger.info(
            "[BG] Vector cache miss: %s (hash=%s…) — uruchamiam embedding",
            filename,
            text_hash[:12],
        )
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
        result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
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

    except Exception as e:
        mark_failed(file_path, str(e)[:200])
        logger.exception("[BG] ❌ Błąd indeksowania %s: %s", filename, e)


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
    result = get_indexing_pipeline().run({"splitter": {"documents": docs}})
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
