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
embedding_device = ComponentDevice.from_str(EMBEDDING_DEVICE)
logger.info("Embedding device: %s", EMBEDDING_DEVICE)

text_embedder = SentenceTransformersTextEmbedder(
    model=settings.embedding_model, device=embedding_device
)
text_embedder.warm_up()

doc_embedder = SentenceTransformersDocumentEmbedder(
    model=settings.embedding_model, device=embedding_device
)
doc_embedder.warm_up()
