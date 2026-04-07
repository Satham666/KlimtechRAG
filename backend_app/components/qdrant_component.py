"""Qdrant Component — singleton wrapper dla Qdrant retriever i kolekcji."""

import logging

logger = logging.getLogger("klimtechrag")

_qdrant_component = None


def get_qdrant_component():
    """Zwraca komponent Qdrant (vector store retriever).

    Lazy initialized — załadowuje się przy pierwszym użyciu.
    """
    from ..services.qdrant import get_qdrant_retriever as _get_retriever
    global _qdrant_component
    if _qdrant_component is None:
        _qdrant_component = _get_retriever()
        logger.debug("[Qdrant Component] Initialized")
    return _qdrant_component
