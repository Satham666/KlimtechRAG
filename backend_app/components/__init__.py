"""
Components — singleton wrappers dla GPU modeli i pipeline'ów.

Każdy komponent:
- Leniwi initialized (load on first use)
- Thread-safe (single instance per process)
- Unloadowalny (free_component) do zwolnienia VRAM
"""

from .llm_component import get_llm_component, free_llm_component
from .embedding_component import get_embedding_component, free_embedding_component
from .colpali_component import get_colpali_component, free_colpali_component
from .qdrant_component import get_qdrant_component
from .whisper_component import get_whisper_component, free_whisper_component

__all__ = [
    "get_llm_component",
    "free_llm_component",
    "get_embedding_component",
    "free_embedding_component",
    "get_colpali_component",
    "free_colpali_component",
    "get_qdrant_component",
    "get_whisper_component",
    "free_whisper_component",
]
