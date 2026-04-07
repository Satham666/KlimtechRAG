"""Whisper Component — singleton wrapper dla Speech-to-Text (Whisper small)."""

import logging

logger = logging.getLogger("klimtechrag")

_whisper_component = None


def get_whisper_component():
    """Zwraca komponent Whisper (STT).

    Lazy initialized — załadowuje się przy pierwszym użyciu.
    """
    from ..services.whisper_service import get_whisper_model as _get_whisper
    global _whisper_component
    if _whisper_component is None:
        try:
            _whisper_component = _get_whisper()
            logger.debug("[Whisper Component] Initialized")
        except ImportError:
            logger.warning("[Whisper Component] Service not available")
            _whisper_component = None
    return _whisper_component


def free_whisper_component():
    """Zwalnia komponent Whisper."""
    global _whisper_component
    if _whisper_component is not None:
        try:
            # Whisper zwykle zwolnia się w torch.cuda.empty_cache()
            logger.info("[Whisper Component] Freed")
        except Exception as e:
            logger.warning("[Whisper Component] Error freeing: %s", e)
    _whisper_component = None
