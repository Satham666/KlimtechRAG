import logging
import re
from typing import List, Tuple

from haystack import Document as HaystackDocument

from ..config import settings

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Hybrid Search Service — BM25 + dense vector merge
# B2: final_score = (1 - bm25_weight) * dense_score + bm25_weight * bm25_score
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> List[str]:
    """Prosta tokenizacja: małe litery, tylko słowa."""
    return re.findall(r"\b\w+\b", text.lower())


def bm25_score_docs(
    query: str,
    docs: List[HaystackDocument],
) -> List[float]:
    """Oblicza BM25 scores dla listy dokumentów względem query.

    Używa rank_bm25 jeśli dostępne, fallback na TF-IDF uproszczone.
    Zwraca listę scores znormalizowanych do [0, 1].
    """
    if not docs:
        return []

    corpus = [_tokenize(doc.content or "") for doc in docs]
    query_tokens = _tokenize(query)

    try:
        from rank_bm25 import BM25Okapi
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)
    except ImportError:
        # Fallback: uproszczony TF (term frequency overlap)
        scores = []
        for tokens in corpus:
            if not tokens:
                scores.append(0.0)
                continue
            overlap = sum(1 for t in query_tokens if t in set(tokens))
            scores.append(overlap / max(len(query_tokens), 1))

    # Normalizuj do [0, 1]
    max_score = max(scores) if scores else 1.0
    if max_score == 0:
        return [0.0] * len(docs)
    return [float(s) / max_score for s in scores]


def hybrid_merge(
    dense_docs: List[HaystackDocument],
    dense_scores: List[float],
    query: str,
    top_k: int = 5,
    bm25_weight: float | None = None,
) -> List[HaystackDocument]:
    """Łączy dense retrieval z BM25 i zwraca top_k dokumentów po hybrid scoring.

    final_score = (1 - bm25_weight) * dense_score + bm25_weight * bm25_score
    """
    if not dense_docs:
        return []

    w = bm25_weight if bm25_weight is not None else settings.bm25_weight
    bm25_scores = bm25_score_docs(query, dense_docs)

    # Normalizuj dense scores do [0, 1]
    max_dense = max(dense_scores) if dense_scores else 1.0
    if max_dense == 0:
        max_dense = 1.0
    norm_dense = [s / max_dense for s in dense_scores]

    scored: List[Tuple[float, HaystackDocument]] = []
    for doc, ds, bs in zip(dense_docs, norm_dense, bm25_scores):
        final = (1.0 - w) * ds + w * bs
        scored.append((final, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    result = [doc for _, doc in scored[:top_k]]

    logger.debug(
        "[Hybrid] %d → top %d po merge (bm25_weight=%.2f)",
        len(dense_docs), len(result), w,
    )
    return result
