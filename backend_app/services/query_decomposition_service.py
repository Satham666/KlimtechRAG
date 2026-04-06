import logging
import os
import re
from typing import List, Tuple

from haystack import Document as HaystackDocument

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Query Decomposition Service — rozbijanie zlozonych pytan (B4)
# LLM rozbija pytanie na 2-3 sub-pytania, kazde osobno retrieval, merge.
# ---------------------------------------------------------------------------

QUERY_DECOMPOSITION_ENABLED = os.getenv(
    "KLIMTECH_QUERY_DECOMPOSITION", "false"
).lower() in ("1", "true", "yes")

MAX_SUB_QUERIES = 3

_DECOMPOSITION_PROMPT = """Twoim zadaniem jest rozbicie pytania na 2-3 prostsze pod-pytania.
Kazde pod-pytanie powinno byc niezalezne i mozliwe do odpowiedzi osobno.
Zwroc TYLKO liste pod-pytan, kazde w nowej linii, bez numeracji, bez dodatkowego tekstu.
Jesli pytanie jest proste (jedno aspekt) — zwroc je w jednej linii.

Pytanie: {query}

Pod-pytania:"""


def _should_decompose(query: str) -> bool:
    """Heurystyka — czy pytanie jest zlozone i warto je rozbic."""
    if not QUERY_DECOMPOSITION_ENABLED:
        return False
    indicators = [
        "porownaj", "porownaj", "porownanie",
        "roznica", "roznice", "roznic",
        "vs", "versus", "v",
        "oraz", "a takze", "takze",
        "jaka jest roznica", "co jest lepsze",
        "na tle", "w kontekscie", "w stosunku do",
    ]
    query_lower = query.lower()
    hit_count = sum(1 for w in indicators if w in query_lower)
    return hit_count >= 1 and len(query.split()) >= 5


def _parse_sub_queries(llm_output: str) -> List[str]:
    """Parsuje output LLM na liste sub-pytan."""
    lines = []
    for line in llm_output.strip().split("\n"):
        line = line.strip()
        line = re.sub(r"^[\d\.\-\)\*]+\s*", "", line).strip()
        if line and len(line) >= 3:
            lines.append(line)
    return lines[:MAX_SUB_QUERIES]


def decompose_query(query: str, request_id: str = "-") -> List[str]:
    """Rozbija zlozone pytanie na sub-pytania przez LLM.

    Zwraca liste sub-pytan (1-3). Przy bledzie LLM zwraca [query].
    """
    if not _should_decompose(query):
        return [query]

    try:
        from ..services import get_llm_component

        llm = get_llm_component()
        prompt = _DECOMPOSITION_PROMPT.format(query=query)
        result = llm.run(prompt=prompt)
        raw = result["replies"][0] if result.get("replies") else ""
        sub_queries = _parse_sub_queries(raw)

        if len(sub_queries) < 2:
            logger.debug(
                "[B4] Query nie zostal rozbity (1 sub-query): %s",
                query[:50],
                extra={"request_id": request_id},
            )
            return [query]

        logger.info(
            "[B4] Query decomposed: %d sub-queries: %s",
            len(sub_queries),
            " | ".join(q[:30] for q in sub_queries),
            extra={"request_id": request_id},
        )
        return sub_queries
    except Exception as e:
        logger.warning(
            "[B4] Decomposition error, fallback to original: %s",
            str(e),
            extra={"request_id": request_id},
        )
        return [query]


def retrieve_with_decomposition(
    query: str,
    top_k: int = 5,
    embedding_model: str = "",
    request_id: str = "-",
) -> Tuple[List[HaystackDocument], List[str]]:
    """Retrieval z opcjonalnym query decomposition.

    Jesli B4 enabled i pytanie zlozone:
        1. Rozbij na sub-pytania
        2. Kazde sub-pytanie → retrieve_rag (top_k)
        3. Deduplikacja chunkow po content hash
        4. Zwraca top_k unikalnych
    Inaczej: standardowe retrieve_rag.
    """
    from .retrieval_service import retrieve_rag

    sub_queries = decompose_query(query, request_id=request_id)

    if len(sub_queries) <= 1:
        return retrieve_rag(
            query, top_k=top_k,
            embedding_model=embedding_model,
            request_id=request_id,
        )

    all_docs: List[HaystackDocument] = []
    seen_content: set = set()

    for sq in sub_queries:
        docs, _ = retrieve_rag(
            sq, top_k=top_k * 2,
            embedding_model=embedding_model,
            request_id=request_id,
        )
        for doc in docs:
            content_key = doc.content[:200] if doc.content else ""
            if content_key and content_key not in seen_content:
                seen_content.add(content_key)
                all_docs.append(doc)

    merged = all_docs[:top_k]
    sources = [doc.meta.get("source", "unknown") for doc in merged]
    logger.info(
        "[B4] Decomposed retrieval: %d sub-queries → %d unique docs (from %d total)",
        len(sub_queries), len(merged), len(all_docs),
        extra={"request_id": request_id},
    )
    return merged, sources
