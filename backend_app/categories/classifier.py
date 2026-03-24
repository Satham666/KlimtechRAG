"""
Klasyfikator dokumentów RAG — przypisuje kategorię tematyczną.

Logika klasyfikacji (priorytet malejący):
    1. Path-based   — jeśli ścieżka pliku zawiera nazwę kategorii (deterministyczna)
    2. Keyword-based — zliczanie dopasowań słów kluczowych w treści dokumentu
    3. Fallback      — "other"

Użycie:
    from backend_app.categories.classifier import classify_document

    category = classify_document("/nextcloud/medycyna/kardiologia.pdf", content)
    # → "medicine"
"""

import logging
import os
import re
from typing import Optional

from .definitions import CATEGORIES, get_all_keywords, get_path_hints

logger = logging.getLogger("klimtechrag")

# Pre-kalkulowane dane dla wydajności (obliczane raz przy imporcie)
_PATH_HINTS: dict[str, list[str]] = get_path_hints()
_KEYWORDS_PL: dict[str, list[str]] = get_all_keywords("pl")
_KEYWORDS_EN: dict[str, list[str]] = get_all_keywords("en")
_KEYWORDS_DE: dict[str, list[str]] = get_all_keywords("de")

# Minimalna liczba dopasowań słów kluczowych, żeby uznać klasyfikację za pewną
_MIN_KEYWORD_MATCHES = 2


def classify_document(filepath: str = "", content: str = "") -> str:
    """
    Klasyfikuje dokument do jednej z 14 kategorii głównych.

    Args:
        filepath: Ścieżka do pliku (może być pusta). Używana do path-based detection.
        content:  Treść dokumentu (może być pusta). Używana do keyword matching.

    Returns:
        ID kategorii, np. "medicine", "law", "finance", ... lub "other".

    Example:
        >>> classify_document("/dane/medycyna/kardiologia.pdf", "")
        "medicine"
        >>> classify_document("", "The patient was diagnosed with heart disease")
        "medicine"
        >>> classify_document("unknown.pdf", "zupełnie niezwiązana treść xyz abc")
        "other"
    """
    # 1. Path-based (najsilniejszy sygnał — deterministyczny)
    if filepath:
        category = _classify_by_path(filepath)
        if category:
            logger.debug("Klasyfikacja path-based: %s → %s", filepath, category)
            return category

    # 2. Keyword-based na treści dokumentu
    if content:
        category = _classify_by_keywords(content)
        if category:
            logger.debug("Klasyfikacja keyword-based: %s → %s",
                         os.path.basename(filepath) or "(no file)", category)
            return category

    logger.debug("Brak klasyfikacji dla: %s → other",
                 os.path.basename(filepath) or "(no file)")
    return "other"


def _classify_by_path(filepath: str) -> Optional[str]:
    """
    Próbuje ustalić kategorię na podstawie ścieżki pliku.

    Normalizuje ścieżkę (małe litery, usuwa znaki specjalne) i szuka
    hint'ów każdej kategorii.

    Returns:
        ID kategorii lub None jeśli brak dopasowania.
    """
    # Normalizuj ścieżkę: małe litery, zamień separatory na spacje
    normalized = filepath.lower().replace("\\", "/").replace("_", " ")
    # Usuń polskie znaki dla porównania (ą→a, ę→e, itd.)
    normalized = _strip_diacritics(normalized)

    for category_id, hints in _PATH_HINTS.items():
        for hint in hints:
            hint_normalized = _strip_diacritics(hint.lower().replace("_", " "))
            if hint_normalized in normalized:
                return category_id

    return None


def _classify_by_keywords(content: str) -> Optional[str]:
    """
    Klasyfikuje dokument na podstawie zliczania słów kluczowych w treści.

    Sprawdza keywords PL, EN i DE. Wynik to kategoria z najwyższą
    łączną liczbą dopasowań powyżej progu _MIN_KEYWORD_MATCHES.

    Returns:
        ID kategorii lub None jeśli brak pewnej klasyfikacji.
    """
    # Analizuj tylko pierwsze 3000 znaków dla wydajności
    sample = content[:3000].lower()
    sample = _strip_diacritics(sample)

    scores: dict[str, int] = {}

    for category_id in _PATH_HINTS:  # iteruj tylko po kategoriach (nie "other")
        score = 0
        for keyword_list in [
            _KEYWORDS_PL.get(category_id, []),
            _KEYWORDS_EN.get(category_id, []),
            _KEYWORDS_DE.get(category_id, []),
        ]:
            for kw in keyword_list:
                kw_norm = _strip_diacritics(kw.lower())
                # Sprawdź czy słowo kluczowe występuje jako osobne słowo
                if re.search(r'\b' + re.escape(kw_norm) + r'\b', sample):
                    score += 1

        if score >= _MIN_KEYWORD_MATCHES:
            scores[category_id] = score

    if not scores:
        return None

    best = max(scores, key=lambda k: scores[k])
    logger.debug("Keyword scores: %s → best: %s (%d)",
                 {k: v for k, v in sorted(scores.items(), key=lambda x: -x[1])[:3]},
                 best, scores[best])
    return best


def _strip_diacritics(text: str) -> str:
    """
    Upraszcza polskie/niemieckie znaki diakrytyczne do ASCII.
    Pozwala porównywać "medycyna" z "medycyna" i "Medizin" z "medizin".
    """
    replacements = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        "ä": "a", "ö": "o", "ü": "u", "ß": "ss",
        "á": "a", "é": "e", "í": "i", "ú": "u", "ý": "y",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def get_available_categories() -> dict[str, str]:
    """
    Zwraca słownik {id: nazwa_pl} dla wszystkich kategorii (dla UI/dropdown).

    Returns:
        np. {"medicine": "Medycyna", "law": "Prawo", ...}
    """
    return {
        cat_id: cat["names"]["pl"]
        for cat_id, cat in CATEGORIES.items()
    }
