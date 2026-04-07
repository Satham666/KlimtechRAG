"""Embedding Component — singleton wrapper dla e5-large / bge-large."""

import logging

logger = logging.getLogger("klimtechrag")

_embedding_component = None


def get_embedding_component():
    """Zwraca komponent embeddings (text embedder).

    Lazy initialized — załadowuje się przy pierwszym użyciu.
    """
    from ..services.embeddings import get_text_embedder as _get_embedder
    global _embedding_component
    if _embedding_component is None:
        _embedding_component = _get_embedder()
        logger.debug("[Embedding Component] Initialized")
    return _embedding_component


def free_embedding_component():
    """Zwalnia komponent embeddings."""
    from ..services.embedder_pool import unload_embedder
    global _embedding_component
    if _embedding_component is not None:
        try:
            unload_embedder("e5-large")
            unload_embedder("bge-large")
            logger.info("[Embedding Component] Freed")
        except Exception as e:
            logger.warning("[Embedding Component] Error freeing: %s", e)
    _embedding_component = None
