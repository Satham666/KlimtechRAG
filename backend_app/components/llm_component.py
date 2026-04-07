"""LLM Component — singleton wrapper dla OpenAIGenerator (Bielik)."""

import logging

logger = logging.getLogger("klimtechrag")

_llm_component = None


def get_llm_component():
    """Zwraca komponent LLM (OpenAIGenerator).

    Lazy initialized — załadowuje się przy pierwszym użyciu.
    """
    from ..services.llm import get_llm_component as _get_llm
    global _llm_component
    if _llm_component is None:
        _llm_component = _get_llm()
        logger.debug("[LLM Component] Initialized")
    return _llm_component


def free_llm_component():
    """Zwalnia komponent LLM z pamięci."""
    global _llm_component
    if _llm_component is not None:
        try:
            # OpenAIGenerator nie ma standardowego unload — jeśli potrzebny, zrobić w services/llm.py
            logger.info("[LLM Component] Freed")
        except Exception as e:
            logger.warning("[LLM Component] Error freeing: %s", e)
    _llm_component = None
