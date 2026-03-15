"""
backend_app/services/colpali_embedder.py

ColPali — multi-vector PDF page embedder.
Każda strona PDF → obraz → lista wektorów dim=128 (late interaction / ColBERT-style).
Kolekcja Qdrant: klimtech_colpali (oddzielna od klimtech_docs).

Wymagania:
    pip install transformers torch pillow pymupdf qdrant-client --break-system-packages

Zmienne środowiskowe (opcjonalne):
    COLPALI_MODEL   = vidore/colpali-v1.3-hf   (domyślnie)
    COLPALI_DEVICE  = cuda:0 / cpu             (domyślnie auto-detect)
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import List, Tuple

import fitz  # PyMuPDF
import torch
from PIL import Image
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    MultiVectorComparator,
    MultiVectorConfig,
    PointStruct,
    ScoredPoint,
    VectorParams,
)
from transformers import ColPaliForRetrieval, ColPaliProcessor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stałe
# ---------------------------------------------------------------------------

COLPALI_COLLECTION = "klimtech_colpali"
DEFAULT_MODEL      = os.getenv("COLPALI_MODEL", "vidore/colpali-v1.3-hf")
QDRANT_URL         = os.getenv("KLIMTECH_QDRANT_URL", "http://localhost:6333")


def is_colpali_model(model_name: str) -> bool:
    """Zwraca True dla każdego modelu vidore/colpali-*."""
    return model_name.lower().startswith("vidore/colpali")


# ---------------------------------------------------------------------------
# Singleton — model ładowany raz
# ---------------------------------------------------------------------------

_model: ColPaliForRetrieval | None = None
_processor: ColPaliProcessor | None = None
_device: torch.device | None = None


def _get_device() -> torch.device:
    env = os.getenv("COLPALI_DEVICE", "auto")
    if env != "auto":
        return torch.device(env)
    if torch.cuda.is_available():
        return torch.device("cuda:0")
    return torch.device("cpu")


def load_model(model_name: str = DEFAULT_MODEL) -> Tuple[ColPaliForRetrieval, ColPaliProcessor]:
    global _model, _processor, _device
    if _model is not None:
        return _model, _processor

    _device = _get_device()
    logger.info("[ColPali] Ładuję model %s na %s ...", model_name, _device)

    _processor = ColPaliProcessor.from_pretrained(model_name)
    _model = ColPaliForRetrieval.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map=str(_device),
    )
    _model.eval()
    logger.info("[ColPali] Model załadowany ✅")
    return _model, _processor


def unload_model() -> None:
    """Zwalnia VRAM — wywołaj przed załadowaniem LLM."""
    global _model, _processor
    if _model is not None:
        del _model
        _model = None
    if _processor is not None:
        del _processor
        _processor = None
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("[ColPali] Model zwolniony (VRAM wolny)")


# ---------------------------------------------------------------------------
# Embedding stron (obrazy → multi-wektory)
# ---------------------------------------------------------------------------

def embed_pages(
    images: List[Image.Image],
    model_name: str = DEFAULT_MODEL,
) -> List[List[List[float]]]:
    """
    Przyjmuje listę obrazów PIL (stron PDF).
    Zwraca listę multi-wektorów kształt: [num_pages, num_patches, 128].
    """
    model, processor = load_model(model_name)
    inputs = processor(images=images).to(model.device)
    with torch.no_grad():
        embeddings = model(**inputs).embeddings  # [batch, seq_len, 128]

    result = []
    for emb in embeddings:
        result.append(emb.float().cpu().tolist())
    return result


def embed_query(
    query: str,
    model_name: str = DEFAULT_MODEL,
) -> List[List[float]]:
    """
    Embedduje zapytanie tekstowe → lista wektorów dim=128.
    Kształt: [seq_len_query, 128]
    """
    model, processor = load_model(model_name)
    inputs = processor(text=query).to(model.device)
    with torch.no_grad():
        embeddings = model(**inputs).embeddings  # [1, seq_len, 128]
    return embeddings[0].float().cpu().tolist()


# ---------------------------------------------------------------------------
# Qdrant — kolekcja multi-vector
# ---------------------------------------------------------------------------

def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection(client: QdrantClient | None = None) -> None:
    """Tworzy kolekcję klimtech_colpali jeśli nie istnieje."""
    if client is None:
        client = get_qdrant_client()

    existing = [c.name for c in client.get_collections().collections]
    if COLPALI_COLLECTION in existing:
        return

    client.create_collection(
        collection_name=COLPALI_COLLECTION,
        vectors_config=VectorParams(
            size=128,
            distance=Distance.COSINE,
            multivector_config=MultiVectorConfig(
                comparator=MultiVectorComparator.MAX_SIM,
            ),
        ),
    )
    logger.info("[ColPali] Kolekcja %s utworzona ✅", COLPALI_COLLECTION)


# ---------------------------------------------------------------------------
# PDF → obrazy stron
# ---------------------------------------------------------------------------

def pdf_to_images(pdf_path: str, dpi: int = 150) -> List[Image.Image]:
    """
    Konwertuje każdą stronę PDF na obraz PIL.
    dpi=150: dobry kompromis jakość/szybkość dla A4.
    """
    doc = fitz.open(pdf_path)
    images = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


# ---------------------------------------------------------------------------
# Indeksowanie dokumentu
# ---------------------------------------------------------------------------

def index_pdf(
    pdf_path: str,
    doc_id: str | None = None,
    batch_size: int = 4,
    model_name: str = DEFAULT_MODEL,
    client: QdrantClient | None = None,
) -> int:
    """
    Indeksuje PDF — każda strona = jeden punkt Qdrant z multi-wektorem.

    Args:
        pdf_path:   Ścieżka do pliku PDF
        doc_id:     Identyfikator dokumentu (domyślnie nazwa pliku)
        batch_size: Stron na batch (zależnie od VRAM)
        model_name: Model ColPali
        client:     QdrantClient (tworzony automatycznie jeśli None)

    Returns:
        Liczba zaindeksowanych stron
    """
    if client is None:
        client = get_qdrant_client()
    if doc_id is None:
        doc_id = os.path.basename(pdf_path)

    ensure_collection(client)

    images = pdf_to_images(pdf_path)
    total_pages = len(images)
    # Deterministyczny ID bazowy z nazwy pliku (hashlib zamiast hash() aby uniknąć randomizacji)
    point_id_base = int(hashlib.md5(doc_id.encode()).hexdigest(), 16) % (10 ** 9)
    points: List[PointStruct] = []

    for batch_start in range(0, total_pages, batch_size):
        batch_imgs = images[batch_start: batch_start + batch_size]
        batch_embs = embed_pages(batch_imgs, model_name)

        for i, emb in enumerate(batch_embs):
            page_num = batch_start + i
            points.append(
                PointStruct(
                    id=point_id_base + page_num,
                    vector=emb,          # List[List[float]] — multi-vector
                    payload={
                        "doc_id":      doc_id,
                        "file_path":   pdf_path,
                        "page":        page_num,
                        "total_pages": total_pages,
                        "model":       model_name,
                        "embed_type":  "colpali",
                    },
                )
            )
        logger.info(
            "[ColPali] Strony %d–%d / %d  (%s)",
            batch_start, batch_start + len(batch_imgs) - 1, total_pages, doc_id,
        )

    client.upsert(collection_name=COLPALI_COLLECTION, points=points)
    logger.info("[ColPali] ✅ %d stron zaindeksowano → %s", total_pages, COLPALI_COLLECTION)
    return total_pages


# ---------------------------------------------------------------------------
# Wyszukiwanie (retrieval)
# ---------------------------------------------------------------------------

def search(
    query: str,
    top_k: int = 5,
    model_name: str = DEFAULT_MODEL,
    client: QdrantClient | None = None,
) -> List[ScoredPoint]:
    """
    Wyszukuje strony PDF pasujące do zapytania (late interaction scoring).

    Returns:
        Lista ScoredPoint:
            .score      — wynik MAX_SIM (im wyższy, tym lepiej)
            .payload    — {doc_id, file_path, page, total_pages}
    """
    if client is None:
        client = get_qdrant_client()

    query_vec = embed_query(query, model_name)

    results = client.query_points(
        collection_name=COLPALI_COLLECTION,
        query=query_vec,
        limit=top_k,
        with_payload=True,
    ).points

    return results


def scored_points_to_context(points: List[ScoredPoint], extract_text: bool = True) -> str:
    """
    Konwertuje ScoredPoint z kolekcji ColPali na tekst kontekstu dla LLM.
    Opcjonalnie wyciąga tekst OCR z pasujących stron PDF przez PyMuPDF.

    Args:
        points:        Lista ScoredPoint z Qdrant (wynik search())
        extract_text:  Jeśli True, ekstrahuje tekst ze znalezionego PDF

    Returns:
        String z sformatowanym kontekstem dla LLM
    """
    parts = []
    for sp in points:
        p = sp.payload or {}
        doc_id = p.get("doc_id", "unknown")
        page = p.get("page", 0)
        file_path = p.get("file_path", "")
        score = round(sp.score, 3)

        text_content = ""
        if extract_text and file_path and os.path.exists(file_path):
            try:
                doc = fitz.open(file_path)
                text_content = doc[page].get_text().strip()
                doc.close()
            except Exception:
                text_content = ""

        header = f"[{doc_id}, strona {page + 1}, ColPali score {score}]"
        parts.append(f"{header}\n{text_content}" if text_content else header)

    return "\n\n".join(parts)
