import logging
from typing import List, Optional, Tuple

from haystack import Document as HaystackDocument

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Retrieval Service — RAG (e5/ColPali) + Web Search
# Wydzielony z routes/chat.py (A1a refaktoryzacja)
# ---------------------------------------------------------------------------


def retrieve_rag(
    query: str,
    top_k: int = 5,
    embedding_model: str = "",
    request_id: str = "-",
) -> Tuple[List[HaystackDocument], List[str]]:
    """Pobiera dokumenty z Qdrant (e5-large lub ColPali).

    Zwraca (docs, sources). Przy błędzie zwraca ([], []) z logiem WARNING.
    """
    from ..services import get_text_embedder
    from ..services.qdrant import get_qdrant_retriever

    if embedding_model.lower().startswith("vidore/colpali"):
        try:
            from ..services.colpali_embedder import (
                search as colpali_search,
                scored_points_to_context,
            )

            colpali_results = colpali_search(
                query=query, top_k=top_k, model_name=embedding_model
            )
            if colpali_results:
                context_text = scored_points_to_context(colpali_results)
                sources = [
                    sp.payload.get("doc_id", "unknown")
                    for sp in colpali_results
                    if sp.payload
                ]
                logger.info(
                    "[ColPali] %d stron: %s",
                    len(colpali_results),
                    ", ".join(sources),
                    extra={"request_id": request_id},
                )
                # Opakuj wynik ColPali jako HaystackDocument dla spójności interfejsu
                doc = HaystackDocument(content=context_text, meta={"source": "ColPali"})
                return [doc], sources
        except Exception as e:
            logger.warning(
                "[ColPali] Błąd retrieval: %s", str(e), extra={"request_id": request_id}
            )
        return [], []

    # Standardowy e5-large retrieval z hybrid BM25 merge (B2)
    try:
        from ..config import settings as _settings
        from .hybrid_search_service import hybrid_merge

        query_embedding = get_text_embedder().run(text=query)
        retriever = get_qdrant_retriever()
        # Pobieramy więcej dokumentów (top_k_fetch) przed hybrid merge
        fetch_k = max(top_k * 3, _settings.retrieval_top_k_fetch)
        result = retriever.run(
            query_embedding=query_embedding["embedding"],
            top_k=fetch_k,
        )
        raw_docs = result.get("documents", [])

        # Wyciągnij dense scores (haystack zwraca score w meta lub jako atrybut)
        dense_scores = [
            float(getattr(doc, "score", 0.0) or doc.meta.get("score", 0.0))
            for doc in raw_docs
        ]

        # Hybrid merge: BM25 + dense → top_k*4 (przed rerankiem)
        pre_rerank_k = top_k * 4
        docs_pre = hybrid_merge(raw_docs, dense_scores, query, top_k=pre_rerank_k)

        # B3 Reranking: cross-encoder → final top_k
        from .reranker_service import rerank
        docs = rerank(query, docs_pre, top_k=top_k)

        sources = [doc.meta.get("source", "unknown") for doc in docs]
        logger.info(
            "[RAG] %d dokumentów po hybrid+rerank (fetch=%d, pre_rerank=%d): %s",
            len(docs), len(raw_docs), len(docs_pre), ", ".join(sources),
            extra={"request_id": request_id},
        )
        return docs, sources
    except Exception as e:
        logger.warning(
            "[RAG] Błąd retrieval: %s", str(e), extra={"request_id": request_id}
        )
        return [], []


def retrieve_web(
    query: str,
    max_results: int = 20,
    request_id: str = "-",
) -> Tuple[Optional[HaystackDocument], List[str]]:
    """Pobiera wyniki z DuckDuckGo.

    Zwraca (doc, sources) lub (None, []) przy błędzie/braku wyników.
    """
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            web_results = list(ddgs.text(query, max_results=max_results))

        if not web_results:
            return None, []

        web_snippets = []
        for res in web_results:
            snippet = res.get("body", "")
            url = res.get("href", "")
            title = res.get("title", "")
            if snippet:
                web_snippets.append(f"**{title}**\n{snippet}\nŹródło: {url}")

        web_context = (
            "=== WYNIKI Z INTERNETU ===\n"
            + "\n\n---\n\n".join(web_snippets)
            + "\n=== KONIEC WYNIKÓW ==="
        )
        sources = [res.get("title", "Web") for res in web_results]

        logger.info(
            "[Web Search] %d wyników dla: %s",
            len(web_results),
            query,
            extra={"request_id": request_id},
        )
        return HaystackDocument(content=web_context, meta={"source": "Web Search"}), sources

    except Exception as e:
        logger.warning(
            "[Web Search] Błąd: %s", str(e), extra={"request_id": request_id}
        )
        return None, []
