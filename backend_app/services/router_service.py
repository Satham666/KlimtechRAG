import re
from typing import Optional

# ---------------------------------------------------------------------------
# Router Service — automatyczny wybór RAG vs Direct LLM
# B1: heurystyka zapobiega ładowaniu embeddingu dla prostych pytań
# ---------------------------------------------------------------------------

# Słowa kluczowe sugerujące że pytanie wymaga kontekstu z dokumentów
_RAG_KEYWORDS = {
    # Polskie
    "dokument", "dokumenty", "dokumentacja", "raport", "raporty",
    "specyfikacja", "specyfikacje", "norma", "normy", "procedura", "procedury",
    "instrukcja", "instrukcje", "protokół", "protokoły", "umowa", "umowy",
    "kontrakt", "kontrakty", "certyfikat", "certyfikaty", "regulamin",
    "załącznik", "załączniki", "plik", "pliki", "dane", "baza",
    "klimtech", "projekt", "projekty", "standard", "standardy",
    "wytyczne", "przepis", "przepisy", "wymagania", "wymaganie",
    "parametr", "parametry", "tabela", "tabele", "wykres", "wykresy",
    "schemat", "schematy", "rysunek", "rysunki", "zawiera", "zawierają",
    "według", "zgodnie", "mówi", "stwierdza", "opisuje", "opisuje",
    # Angielskie
    "document", "documents", "report", "reports", "specification",
    "specifications", "standard", "standards", "procedure", "procedures",
    "manual", "manuals", "contract", "contracts", "file", "files",
    "according", "states", "describes", "contains",
}

# Wzorce pytań które ZAWSZE idą przez RAG
_RAG_PATTERNS = [
    r"co (mówi|zawiera|opisuje|stwierdza)",
    r"(znajd[źz]|wyszukaj|pokaż|wyświetl).*(w|ze?|z)",
    r"(jaki|jaka|jakie|jakich).*(dokument|raport|specyf|norma|procedur)",
    r"(ile|kiedy|gdzie|kto).*(dokument|raport|specyf|norma|procedur)",
    r"(według|zgodnie z|na podstawie)",
    r"(przeczytaj|przeanalizuj|sprawdź).*(plik|dokument|raport)",
]

# Wzorce pytań ZAWSZE Direct LLM (small talk, pytania ogólne)
_DIRECT_PATTERNS = [
    r"^(hej|cześć|siema|hello|hi|hey|witaj|dobry|dzień dobry|dobry wieczór)[\s!?]*$",
    r"^(co słychać|jak się masz|jak leci|what'?s up)[\s!?]*$",
    r"^(dziękuję|dzięki|thx|thanks|ok|okej|rozumiem|jasne|super|świetnie)[\s!?]*$",
    r"^(1\+1|2\+2|\d+[\+\-\*\/]\d+)[\s=?]*$",  # proste działania
]

# Próg długości — pytania krótsze niż N słów bez słów kluczowych → Direct
_MIN_WORDS_FOR_AUTO_RAG = 8


def should_use_rag(query: str, user_forced: Optional[bool] = None) -> bool:
    """Decyduje czy pytanie wymaga kontekstu RAG.

    Kolejność decyzji:
    1. Jeśli użytkownik wymusił RAG przyciskiem (use_rag=True) → zawsze RAG
    2. Jeśli pasuje do _DIRECT_PATTERNS → zawsze Direct LLM
    3. Jeśli pasuje do _RAG_PATTERNS → zawsze RAG
    4. Jeśli zawiera słowo kluczowe z _RAG_KEYWORDS → RAG
    5. Jeśli pytanie >= _MIN_WORDS_FOR_AUTO_RAG słów → RAG (może potrzebuje kontekstu)
    6. Domyślnie → Direct LLM (krótkie pytanie bez słów kluczowych)
    """
    if user_forced is not None:
        return user_forced

    q = query.strip().lower()

    # 2. Direct patterns — small talk, proste pytania
    for pattern in _DIRECT_PATTERNS:
        if re.match(pattern, q, re.IGNORECASE):
            return False

    # 3. RAG patterns — jawne odwołania do dokumentów
    for pattern in _RAG_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return True

    # 4. Słowa kluczowe RAG
    words = set(re.findall(r"\b\w+\b", q))
    if words & _RAG_KEYWORDS:
        return True

    # 5. Długie pytanie — prawdopodobnie potrzebuje kontekstu
    if len(q.split()) >= _MIN_WORDS_FOR_AUTO_RAG:
        return True

    # 6. Krótkie pytanie bez sygnałów → Direct LLM
    return False


def classify_query(query: str) -> str:
    """Zwraca etykietę decyzji routera dla celów logowania/debugowania."""
    q = query.strip().lower()
    for pattern in _DIRECT_PATTERNS:
        if re.match(pattern, q, re.IGNORECASE):
            return "direct_pattern"
    for pattern in _RAG_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return "rag_pattern"
    words = set(re.findall(r"\b\w+\b", q))
    if words & _RAG_KEYWORDS:
        return "rag_keyword"
    if len(q.split()) >= _MIN_WORDS_FOR_AUTO_RAG:
        return "rag_length"
    return "direct_short"
