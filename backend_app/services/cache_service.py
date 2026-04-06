import logging
import os
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Cache odpowiedzi z TTL i limitem rozmiaru
# Wydzielony z routes/chat.py (A1a refaktoryzacja)
# B6: Semantic Cache — cosine similarity matching
# ---------------------------------------------------------------------------

_answer_cache: Dict[str, Tuple[str, float]] = {}
CACHE_TTL = 3600
CACHE_MAX_SIZE = 500

SEMANTIC_CACHE_ENABLED = os.getenv("KLIMTECH_SEMANTIC_CACHE", "false").lower() in ("1", "true", "yes")
SEMANTIC_CACHE_THRESHOLD = float(os.getenv("KLIMTECH_CACHE_SIMILARITY_THRESHOLD", "0.92"))
SEMANTIC_CACHE_MAX = int(os.getenv("KLIMTECH_CACHE_SEMANTIC_MAX", "100"))

_semantic_entries: List[dict] = []


def get_cached(query: str) -> Optional[str]:
    """Zwraca cached odpowiedź jeśli istnieje i nie wygasła."""
    if query in _answer_cache:
        answer, ts = _answer_cache[query]
        if time.time() - ts < CACHE_TTL:
            return answer
        del _answer_cache[query]
    return None


def set_cached(query: str, answer: str) -> None:
    """Zapisuje odpowiedź do cache z aktualnym timestampem."""
    if len(_answer_cache) >= CACHE_MAX_SIZE:
        oldest = min(_answer_cache, key=lambda k: _answer_cache[k][1])
        del _answer_cache[oldest]
    _answer_cache[query] = (answer, time.time())


def clear_cache() -> None:
    """Czyści cały cache odpowiedzi."""
    global _answer_cache, _semantic_entries
    _answer_cache.clear()
    _semantic_entries.clear()
    logger.info("Cache odpowiedzi wyczyszczony")


def cache_size() -> int:
    """Zwraca aktualny rozmiaru cache."""
    return len(_answer_cache)


# ---------------------------------------------------------------------------
# B6: Semantic Cache — cosine similarity matching
# ---------------------------------------------------------------------------


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity między dwoma wektorami."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _embed_for_cache(text: str) -> Optional[np.ndarray]:
    """Embedding dla cache — używa text_embedder jeśli dostępny."""
    try:
        from ..services import get_text_embedder

        result = get_text_embedder().run(text=text)
        emb = result.get("embedding")
        if emb:
            return np.array(emb, dtype=np.float32)
    except Exception as e:
        logger.debug("[SemanticCache] Embedding error: %s", e)
    return None


def get_semantic_cached(query: str) -> Optional[str]:
    """Zwraca cached odpowiedź jeśli cosine similarity > threshold.

    Zwraca None gdy semantic cache disabled, brak embeddingu,
    lub żadne wejście nie przekracza progu.
    """
    if not SEMANTIC_CACHE_ENABLED or not _semantic_entries:
        return None

    query_emb = _embed_for_cache(query)
    if query_emb is None:
        return None

    best_score = -1.0
    best_answer = None
    now = time.time()

    for entry in _semantic_entries:
        if now - entry["ts"] >= CACHE_TTL:
            continue
        sim = _cosine_similarity(query_emb, entry["embedding"])
        if sim > best_score:
            best_score = sim
            best_answer = entry["answer"]

    if best_score >= SEMANTIC_CACHE_THRESHOLD and best_answer:
        logger.info(
            "[SemanticCache] HIT (score=%.3f, threshold=%.3f)",
            best_score, SEMANTIC_CACHE_THRESHOLD,
        )
        return best_answer

    return None


def set_semantic_cached(query: str, answer: str) -> None:
    """Zapisuje embedding + odpowiedź do semantic cache.

    FIFO eviction gdy limit osiągnięty.
    """
    if not SEMANTIC_CACHE_ENABLED:
        return

    query_emb = _embed_for_cache(query)
    if query_emb is None:
        return

    if len(_semantic_entries) >= SEMANTIC_CACHE_MAX:
        _semantic_entries.pop(0)

    _semantic_entries.append({
        "embedding": query_emb,
        "answer": answer,
        "ts": time.time(),
    })


def semantic_cache_size() -> int:
    """Zwraca rozmiaru semantic cache."""
    return len(_semantic_entries)
