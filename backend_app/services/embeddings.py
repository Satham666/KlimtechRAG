import os
import logging

from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.utils import ComponentDevice

from ..config import settings

logger = logging.getLogger("klimtechrag")

EMBEDDING_DEVICE = os.getenv("KLIMTECH_EMBEDDING_DEVICE", settings.embedding_device)

# ---------------------------------------------------------------------------
# LAZY LOADING — embedding ladowany dopiero gdy uzytkownik kliknie "Indeksuj"
# ---------------------------------------------------------------------------
_text_embedder = None
_doc_embedder = None


def get_text_embedder():
    """Zwraca text embedder (lazy load)."""
    global _text_embedder
    if _text_embedder is None:
        logger.info("Ladowanie text embedder: %s na %s", settings.embedding_model, EMBEDDING_DEVICE)
        embedding_device = ComponentDevice.from_str(EMBEDDING_DEVICE)
        _text_embedder = SentenceTransformersTextEmbedder(
            model=settings.embedding_model, device=embedding_device
        )
        _text_embedder.warm_up()
        logger.info("Text embedder zaladowany")
    return _text_embedder


def get_doc_embedder():
    """Zwraca document embedder (lazy load)."""
    global _doc_embedder
    if _doc_embedder is None:
        logger.info("Ladowanie doc embedder: %s na %s", settings.embedding_model, EMBEDDING_DEVICE)
        embedding_device = ComponentDevice.from_str(EMBEDDING_DEVICE)
        _doc_embedder = SentenceTransformersDocumentEmbedder(
            model=settings.embedding_model, device=embedding_device
        )
        _doc_embedder.warm_up()
        logger.info("Doc embedder zaladowany")
    return _doc_embedder


def unload_embedders():
    """Zwalnia embedder z pamieci GPU."""
    global _text_embedder, _doc_embedder
    _text_embedder = None
    _doc_embedder = None
    logger.info("Embeddery zwolnione z pamieci")


# Backward compatibility — inne pliki importuja text_embedder / doc_embedder
# Zamiast obiektow dajemy property-like dostep przez funkcje powyzej
# Jesli ktos importowal bezposrednio, musi przejsc na get_text_embedder() / get_doc_embedder()
