"""
backend_app/services/embedder_pool.py

Singleton embedder pool — zarządzanie cyklem życia embedderów.
Ładuje embedder raz, cache'uje w pamięci, zwalnia VRAM na żądanie.

Wzorzec:
    embedder = get_embedder("e5-large")      # Załaduj lub zwróć z cache
    unload_embedder("e5-large")              # Usuń z cache, zwolnij VRAM
    get_embedder("colpali")                  # Inny embedder, niezależny cache
    clear_all_embedders()                    # Emergency cleanup
"""

import logging
import torch
from typing import Dict, Any, Optional

from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.utils import ComponentDevice

from ..config import settings

logger = logging.getLogger("klimtechrag")

# ─────────────────────────────────────────────────────────────────────────────
# CACHE — embedder pool
# ─────────────────────────────────────────────────────────────────────────────

_embedder_cache: Dict[str, Any] = {}

# Mapowanie model_name → HuggingFace model ID
# WAŻNE: musi być spójne z config.py: embedding_model = "intfloat/multilingual-e5-large"
EMBEDDER_MODELS = {
    "e5-large": "intfloat/multilingual-e5-large",  # Multilingual dla dokumentacji PL
    "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    "colpali": "vidore/colpali-v1.3-hf",  # Obsługiwane przez colpali_embedder.py
}


def _get_hf_model_id(model_name: str) -> str:
    """Mapuje internal model name na HuggingFace model ID."""
    return EMBEDDER_MODELS.get(model_name, model_name)


def get_embedder(model_name: str, embedder_type: str = "text") -> Any:
    """
    Zwraca embedder z cache'a lub ładuje nowy.

    Args:
        model_name: Nazwa modelu (e.g. "e5-large", "bge-large-en-v1.5")
        embedder_type: "text" (TextEmbedder) lub "doc" (DocumentEmbedder)

    Returns:
        SentenceTransformersTextEmbedder lub SentenceTransformersDocumentEmbedder

    Uwagi:
        - ColPali jest obsługiwane osobno przez colpali_embedder.py
        - Pool cache'uje na podstawie model_name
        - Lazy loading — loading dopiero przy pierwszym get_embedder()
    """
    # Klucz cache'a
    cache_key = f"{model_name}_{embedder_type}"

    # Zwróć z cache'a jeśli załadowany
    if cache_key in _embedder_cache:
        logger.debug(f"[Pool] Zwracam {cache_key} z cache'a")
        return _embedder_cache[cache_key]

    # Kolpali — obsługiwane osobnie
    if model_name.lower().startswith("vidore/colpali") or model_name == "colpali":
        try:
            from .colpali_embedder import load_model as load_colpali

            hf_id = _get_hf_model_id(model_name)
            logger.info(f"[Pool] Ładuję ColPali: {hf_id}")
            model, processor = load_colpali(hf_id)
            _embedder_cache[cache_key] = {"model": model, "processor": processor}
            logger.info(f"[Pool] ✅ ColPali załadowany")
            return _embedder_cache[cache_key]
        except Exception as e:
            logger.error(f"[Pool] ❌ Błąd ładowania ColPali: {e}")
            raise

    # Sentence Transformers (e5-large, bge-large, itd.)
    try:
        hf_model_id = _get_hf_model_id(model_name)
        embedding_device = ComponentDevice.from_str(settings.embedding_device)

        logger.info(
            f"[Pool] Ładuję {embedder_type} embedder: {hf_model_id} "
            f"na {settings.embedding_device}"
        )

        if embedder_type == "text":
            embedder = SentenceTransformersTextEmbedder(
                model=hf_model_id,
                device=embedding_device,
            )
        else:  # doc
            embedder = SentenceTransformersDocumentEmbedder(
                model=hf_model_id,
                device=embedding_device,
            )

        embedder.warm_up()
        _embedder_cache[cache_key] = embedder
        logger.info(f"[Pool] ✅ {embedder_type} embedder załadowany: {hf_model_id}")
        return embedder

    except Exception as e:
        logger.error(f"[Pool] ❌ Błąd ładowania embeddera {model_name}: {e}")
        raise


def unload_embedder(model_name: str, embedder_type: str = "text") -> None:
    """
    Usuwa embedder z cache'a i zwalnia VRAM.

    Args:
        model_name: Nazwa modelu
        embedder_type: "text" lub "doc"

    Uwagi:
        - Bezpieczne — nie rzuca błędem jeśli model nie załadowany
        - Zawsze czyści torch cache'a
    """
    cache_key = f"{model_name}_{embedder_type}"

    if cache_key in _embedder_cache:
        embedder = _embedder_cache[cache_key]
        logger.info(f"[Pool] Zwalnianie {cache_key} z VRAM...")

        # Kolpali — specjalny unload
        if model_name.lower().startswith("vidore/colpali") or model_name == "colpali":
            try:
                from .colpali_embedder import unload_model as unload_colpali

                unload_colpali()
            except Exception as e:
                logger.warning(f"[Pool] Błąd przy unload ColPali: {e}")
        else:
            # Sentence Transformers
            if hasattr(embedder, "model"):
                del embedder.model
            del embedder

        del _embedder_cache[cache_key]
        logger.info(f"[Pool] ✅ {cache_key} zwolniony")

    # Zawsze czyść GPU
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        logger.debug("[Pool] torch.cuda.empty_cache() wykonany")


def unload_all_embedders() -> None:
    """Emergency cleanup — zwalnia WSZYSTKIE embedder'y."""
    logger.warning("[Pool] Zwalniam WSZYSTKIE embedder'y...")

    for cache_key in list(_embedder_cache.keys()):
        try:
            embedder = _embedder_cache[cache_key]

            # Kolpali check
            if "colpali" in cache_key.lower():
                try:
                    from .colpali_embedder import unload_model as unload_colpali

                    unload_colpali()
                except Exception:
                    pass
            else:
                # Sentence Transformers
                if hasattr(embedder, "model"):
                    del embedder.model
                del embedder

            del _embedder_cache[cache_key]
        except Exception as e:
            logger.warning(f"[Pool] Błąd przy czyszczeniu {cache_key}: {e}")

    _embedder_cache.clear()

    # Cleanup GPU
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    logger.info("[Pool] ✅ VRAM wyczyszczony")


def get_pool_stats() -> Dict[str, Any]:
    """Zwraca info o załadowanych embedder'ach w cache'u."""
    return {
        "cached_embedders": list(_embedder_cache.keys()),
        "count": len(_embedder_cache),
    }
