"""ColPali Component — singleton wrapper dla vidore/colpali (visual retrieval)."""

import logging

logger = logging.getLogger("klimtechrag")

_colpali_component = None


def get_colpali_component():
    """Zwraca komponent ColPali (visual PDF retrieval).

    Lazy initialized — załadowuje się przy pierwszym użyciu.
    """
    from ..services.embedder_pool import get_embedder
    global _colpali_component
    if _colpali_component is None:
        _colpali_component = get_embedder("colpali")
        logger.debug("[ColPali Component] Initialized")
    return _colpali_component


def free_colpali_component():
    """Zwalnia komponent ColPali z VRAM."""
    from ..services.embedder_pool import unload_embedder
    global _colpali_component
    if _colpali_component is not None:
        try:
            unload_embedder("colpali")
            logger.info("[ColPali Component] Freed")
        except Exception as e:
            logger.warning("[ColPali Component] Error freeing: %s", e)
    _colpali_component = None
