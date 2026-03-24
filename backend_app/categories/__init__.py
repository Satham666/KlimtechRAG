"""
Pakiet kategorii dokumentów RAG.

Eksportuje:
    - CATEGORIES: dict {id: definition} — wszystkie 14 kategorii
    - classify_document(filepath, content) -> str — klasyfikator
    - get_category_ids() -> List[str] — lista ID kategorii
    - get_category_name(category_id, lang) -> str — nazwa lokalizowana
"""

from .definitions import CATEGORIES, get_category_ids, get_category_name
from .classifier import classify_document

__all__ = [
    "CATEGORIES",
    "classify_document",
    "get_category_ids",
    "get_category_name",
]
