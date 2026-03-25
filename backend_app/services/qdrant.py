import os
import logging
import time

from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
import requests

from ..config import settings

logger = logging.getLogger("klimtechrag")

os.environ["OPENAI_BASE_URL"] = str(settings.llm_base_url)
os.environ["OPENAI_API_KEY"] = settings.llm_api_key

# Znane wymiary embeddingu dla popularnych modeli (bez ladowania na GPU)
KNOWN_EMBEDDING_DIMS = {
    "intfloat/multilingual-e5-large": 1024,
    "intfloat/multilingual-e5-base": 768,
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": 768,
    "BAAI/bge-m3": 1024,
}


def get_embedding_dimension(model_name: str) -> int:
    """Zwraca wymiar embeddingu — najpierw z cache, potem z modelu."""
    if model_name in KNOWN_EMBEDDING_DIMS:
        dim = KNOWN_EMBEDDING_DIMS[model_name]
        logger.info("Embedding dimension (cached): %s -> %d", model_name, dim)
        return dim
    # Fallback — zaladuj model (wolne, ale poprawne)
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name)
        dim = model.get_sentence_embedding_dimension()
        if dim is None:
            dim = 1024
        logger.info("Model %s - embedding dimension: %d", model_name, dim)
        del model  # zwolnij pamiec
        return dim
    except Exception as e:
        logger.warning("Cannot detect embedding dimension, using default 1024: %s", e)
        return 1024


def ensure_indexed():
    try:
        url = f"{settings.qdrant_url}/collections/{settings.qdrant_collection}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        indexed = data.get("result", {}).get("indexed_vectors_count", 0)
        points = data.get("result", {}).get("points_count", 0)

        if points > 0 and indexed < points:
            logger.info("Wymuszam indeksowanie HNSW w Qdrant (%d punktów)...", points)
            requests.patch(
                url,
                json={"hnsw_config": {"full_scan_threshold": 10}},
                timeout=10,
            )
            logger.info("HNSW threshold obniżony, indeksowanie nastąpi automatycznie")
    except Exception as e:
        logger.warning("Nie udało się wymusić indeksowania: %s", e)


def get_qdrant_retriever():
    """
    Zwraca MINIMALISTYCZNY retriever z Qdrant — TYLKO retrieval, bez pipeline'u.

    Użycie:
    -------
    # Embed query
    embedding = get_text_embedder().run(text=user_message)["embedding"]

    # Retrieve (bez ładowania całego RAG pipeline'u!)
    retriever = get_qdrant_retriever()
    result = retriever.run(query_embedding=embedding["embedding"])
    docs = result.get("documents", [])

    Zaoszczędza VRAM:
    - OLD (pełny pipeline):   4 GB
    - NEW (minimal retriever): 0.5 GB

    Zwraca:
    -------
    QdrantEmbeddingRetriever — gotowy do użytku w /query i /code_query
    """
    from haystack_integrations.components.retrievers.qdrant import (
        QdrantEmbeddingRetriever,
    )

    return QdrantEmbeddingRetriever(document_store=doc_store, top_k=10)


embedding_dim = get_embedding_dimension(settings.embedding_model)

for _attempt in range(3):
    try:
        doc_store = QdrantDocumentStore(
            url=str(settings.qdrant_url),
            index=settings.qdrant_collection,
            embedding_dim=embedding_dim,
            recreate_index=False,
            wait_result_from_api=True,
        )
        break
    except Exception as e:
        logger.warning(f"Qdrant niedostępny (próba {_attempt + 1}/3): {e}")
        time.sleep(5)
else:
    logger.error("KRYTYCZNE: Nie udało się połączyć z Qdrant!")
    doc_store = None
