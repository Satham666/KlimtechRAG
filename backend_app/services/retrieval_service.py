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

    # Standardowy e5-large retrieval
    try:
        query_embedding = get_text_embedder().run(text=query)
        retriever = get_qdrant_retriever()
        result = retriever.run(query_embedding=query_embedding["embedding"])
        docs = result.get("documents", [])
        sources = [doc.meta.get("source", "unknown") for doc in docs]
        logger.info(
            "[RAG] %d dokumentów: %s",
            len(docs),
            ", ".join(sources),
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
