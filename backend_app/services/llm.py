from haystack.components.generators import OpenAIGenerator
from ..config import settings

_llm_component = None


def get_llm_component():
    """Zwraca komponent LLM (OpenAIGenerator) — bez ladowania embeddingu."""
    global _llm_component
    if _llm_component is None:
        _llm_component = OpenAIGenerator(
            model=settings.llm_model_name or "klimtech-bielik"
        )
    return _llm_component
