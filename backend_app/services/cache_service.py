import logging
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Cache odpowiedzi z TTL i limitem rozmiaru
# Wydzielony z routes/chat.py (A1a refaktoryzacja)
# ---------------------------------------------------------------------------

_answer_cache: Dict[str, Tuple[str, float]] = {}
CACHE_TTL = 3600  # 1 godzina
CACHE_MAX_SIZE = 500


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
    global _answer_cache
    _answer_cache.clear()
    logger.info("Cache odpowiedzi wyczyszczony")


def cache_size() -> int:
    """Zwraca aktualny rozmiar cache."""
    return len(_answer_cache)
