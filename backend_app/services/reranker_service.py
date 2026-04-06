import logging
import os
from typing import List

from haystack import Document as HaystackDocument

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Reranker Service — cross-encoder reranking po retrieval
# B3: retrieval top-20 → reranker (BAAI/bge-reranker-base) → top-5
# Lazy loading — model ładowany tylko gdy KLIMTECH_RERANKER_ENABLED=true
# ---------------------------------------------------------------------------

_reranker = None
_RERANKER_MODEL = os.getenv("KLIMTECH_RERANKER_MODEL", "BAAI/bge-reranker-base")
RERANKER_ENABLED = os.getenv("KLIMTECH_RERANKER_ENABLED", "false").lower() == "true"


def _get_reranker():
    """Lazy singleton dla cross-encoder reranker."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info("[Reranker] Ładowanie %s...", _RERANKER_MODEL)
            _reranker = CrossEncoder(_RERANKER_MODEL)
            logger.info("[Reranker] Załadowany: %s", _RERANKER_MODEL)
        except ImportError:
            logger.warning(
                "[Reranker] sentence_transformers niedostępne — reranking wyłączony"
            )
            return None
        except Exception as e:
            logger.error("[Reranker] Błąd ładowania: %s", e)
            return None
    return _reranker


def rerank(
    query: str,
    docs: List[HaystackDocument],
    top_k: int = 5,
) -> List[HaystackDocument]:
    """Rerankuje dokumenty cross-encoderem i zwraca top_k.

    Jeśli reranker niedostępny lub KLIMTECH_RERANKER_ENABLED=false,
    zwraca pierwsze top_k dokumentów bez zmian.
    """
    if not RERANKER_ENABLED or not docs:
        return docs[:top_k]

    reranker = _get_reranker()
    if reranker is None:
        return docs[:top_k]

    try:
        pairs = [(query, doc.content or "") for doc in docs]
        scores = reranker.predict(pairs)
        ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
        result = [doc for _, doc in ranked[:top_k]]
        logger.debug(
            "[Reranker] %d → top %d po rerankingu (model=%s)",
            len(docs), len(result), _RERANKER_MODEL,
        )
        return result
    except Exception as e:
        logger.warning("[Reranker] Błąd rerankingu: %s — zwracam bez rerankingu", e)
        return docs[:top_k]


def unload_reranker() -> None:
    """Zwalnia reranker z pamięci."""
    global _reranker
    if _reranker is not None:
        _reranker = None
        logger.info("[Reranker] Model zwolniony z pamięci")
