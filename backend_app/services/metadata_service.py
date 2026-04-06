import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Metadata Service — ekstrakcja metadanych przy ingeście
# C6: title, author, page_count, language, chunk_index, indexed_at
# ---------------------------------------------------------------------------

# Prosta heurystyka detekcji języka bez zewnętrznych zależności
_PL_STOPWORDS = frozenset([
    "i", "w", "z", "na", "do", "nie", "to", "że", "się", "jest",
    "jak", "co", "ale", "już", "czy", "po", "tak", "go", "jego",
    "jej", "ich", "być", "przez", "oraz", "przy", "który", "która",
])
_EN_STOPWORDS = frozenset([
    "the", "and", "of", "to", "a", "in", "is", "it", "you", "that",
    "he", "was", "for", "on", "are", "as", "with", "his", "they",
    "be", "at", "one", "have", "this", "from", "or", "had", "by",
])


def detect_language(text: str) -> str:
    """Detekcja języka na podstawie stopwords (pl/en/unknown).

    Heurystyka — bez zewnętrznych bibliotek. Dla ~95% dokumentów pl/en wystarczająca.
    """
    words = set(text.lower().split()[:200])
    pl_hits = len(words & _PL_STOPWORDS)
    en_hits = len(words & _EN_STOPWORDS)
    if pl_hits == 0 and en_hits == 0:
        return "unknown"
    return "pl" if pl_hits >= en_hits else "en"


def extract_pdf_metadata(file_path: str) -> Dict[str, Any]:
    """Wyciąga metadane z pliku PDF przez PyMuPDF (fitz).

    Zwraca dict z title, author, page_count lub pusty dict przy błędzie.
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        meta = doc.metadata or {}
        page_count = doc.page_count
        doc.close()

        return {
            "title": meta.get("title") or "",
            "author": meta.get("author") or "",
            "page_count": page_count,
        }
    except ImportError:
        logger.debug("[Metadata] PyMuPDF niedostępne — brak metadanych PDF")
        return {}
    except Exception as e:
        logger.warning("[Metadata] Błąd odczytu PDF metadata: %s", e)
        return {}


def extract_docx_metadata(file_path: str) -> Dict[str, Any]:
    """Wyciąga metadane z pliku DOCX przez python-docx.

    Zwraca dict z title, author lub pusty dict przy błędzie.
    """
    try:
        from docx import Document  # python-docx

        doc = Document(file_path)
        props = doc.core_properties
        return {
            "title": props.title or "",
            "author": props.author or "",
        }
    except ImportError:
        logger.debug("[Metadata] python-docx niedostępne — brak metadanych DOCX")
        return {}
    except Exception as e:
        logger.warning("[Metadata] Błąd odczytu DOCX metadata: %s", e)
        return {}


def build_chunk_meta(
    source: str,
    chunk_index: int,
    total_chunks: int,
    text: str,
    file_path: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Buduje pełny słownik meta dla chunku dokumentu.

    Łączy: source, chunk_index, total_chunks, language, indexed_at
    oraz opcjonalne metadane z pliku (title, author, page_count).
    """
    meta: Dict[str, Any] = {
        "source": source,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "language": detect_language(text),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }

    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            meta.update(extract_pdf_metadata(file_path))
        elif ext in (".docx", ".doc"):
            meta.update(extract_docx_metadata(file_path))

    if extra:
        meta.update(extra)

    # Usuń puste stringi aby nie zaśmiecać payloadu Qdrant
    return {k: v for k, v in meta.items() if v != ""}
