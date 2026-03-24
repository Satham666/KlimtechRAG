import logging
from typing import Optional

from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator

from ..config import settings
from .qdrant import doc_store

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# LAZY LOADING — pipeline tworzony dopiero gdy potrzebny
# ---------------------------------------------------------------------------
_indexing_pipeline = None
_rag_pipeline = None


def _build_category_filter(category: Optional[str]) -> Optional[dict]:
    """
    Buduje filtr Haystack dla Qdrant na podstawie ID kategorii.

    Args:
        category: ID kategorii np. "medicine", "law" lub None (brak filtra)

    Returns:
        Słownik filtra Haystack lub None.

    Example:
        >>> _build_category_filter("medicine")
        {"field": "meta.category", "operator": "==", "value": "medicine"}
    """
    if not category or category == "other":
        return None
    return {"field": "meta.category", "operator": "==", "value": category}


def get_indexing_pipeline():
    """Zwraca indexing pipeline (lazy load — laduje embedding przy pierwszym uzyciu)."""
    global _indexing_pipeline
    if _indexing_pipeline is None:
        from .embeddings import get_doc_embedder
        logger.info("Tworzenie indexing pipeline...")
        _indexing_pipeline = Pipeline()
        _indexing_pipeline.add_component(
            "splitter", DocumentSplitter(split_by="word", split_length=200, split_overlap=30)
        )
        _indexing_pipeline.add_component("embedder", get_doc_embedder())
        _indexing_pipeline.add_component(
            "writer", DocumentWriter(document_store=doc_store, policy=DuplicatePolicy.OVERWRITE)
        )
        _indexing_pipeline.connect("splitter", "embedder")
        _indexing_pipeline.connect("embedder", "writer")
        logger.info("Indexing pipeline gotowy")
    return _indexing_pipeline


def get_rag_pipeline():
    """Zwraca RAG pipeline (lazy load — laduje embedding przy pierwszym uzyciu)."""
    global _rag_pipeline
    if _rag_pipeline is None:
        from .embeddings import get_text_embedder
        logger.info("Tworzenie RAG pipeline...")
        _rag_pipeline = Pipeline()
        _rag_pipeline.add_component("embedder", get_text_embedder())
        _rag_pipeline.add_component(
            "retriever", QdrantEmbeddingRetriever(document_store=doc_store, top_k=5)
        )
        _rag_pipeline.add_component(
            "prompt_builder",
            PromptBuilder(
                template="Given these documents:\n{% for doc in documents %}\n{{ doc.content }}\n{% endfor %}\n\nAnswer: {{query}}",
                required_variables=["documents", "query"],
            ),
        )
        _rag_pipeline.add_component(
            "llm", OpenAIGenerator(model=settings.llm_model_name or "klimtech-bielik")
        )
        _rag_pipeline.connect("embedder", "retriever")
        _rag_pipeline.connect("retriever", "prompt_builder.documents")
        _rag_pipeline.connect("prompt_builder", "llm")
        logger.info("RAG pipeline gotowy")
    return _rag_pipeline


def run_rag_pipeline(query: str, category_filter: Optional[str] = None) -> dict:
    """
    Uruchamia RAG pipeline z opcjonalnym filtrowaniem po kategorii.

    Args:
        query:           Zapytanie użytkownika.
        category_filter: ID kategorii do filtrowania (np. "medicine") lub None.

    Returns:
        Wynik pipeline (dict z kluczem "llm").
    """
    pipeline = get_rag_pipeline()
    filters = _build_category_filter(category_filter)

    run_input: dict = {
        "embedder": {"text": query},
        "prompt_builder": {"query": query},
    }
    if filters:
        run_input["retriever"] = {"filters": filters}
        logger.info("RAG query z filtrem kategorii: %s", category_filter)

    return pipeline.run(run_input)
