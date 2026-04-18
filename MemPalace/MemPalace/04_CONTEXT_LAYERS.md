# 04_CONTEXT_LAYERS — System 4 warstw kontekstu (wzorzec MemPalace)

**Zadanie:** Zaimplementuj progresywne ładowanie kontekstu L0-L3
**Czas:** 2 dni
**Zależności:** 02_METADATA_HIERARCHY
**VRAM:** 0 MB (logika backendowa, bez nowych modeli)
**Pliki do utworzenia:** `backend_app/services/context_layers.py`
**Pliki do modyfikacji:** `backend_app/routes/chat.py`

---

## KONTEKST DLA ROBOTNIKA

System 4 warstw minimalizuje tokeny w prompcie startowym, ładując kontekst
progresywnie. Bielik-11B ma ograniczone okno kontekstowe — im mniej tokenów
zużywamy na kontekst, tym więcej zostaje na odpowiedź.

```
L0 (~100 tokenów)  = Stały system prompt po polsku
L1 (~500 tokenów)  = Top-K najważniejszych faktów z Qdrant (pre-ranked)
L2 (~1000 tokenów) = Filtrowane zapytanie wing+room (po detekcji tematu)
L3 (~2000 tokenów) = Pełne wyszukiwanie semantyczne (fallback)
```

Backend FastAPI na porcie 8000, llama-server na 8082.
Kolekcja Qdrant: `klimtech_docs` (dim=1024, e5-large).
Endpoint czatu: `POST /v1/chat/completions` w `routes/chat.py`.
RAG domyślnie OFF (`use_rag=false` w schema).

---

## KROK 1: Utwórz backend_app/services/context_layers.py

```python
#!/usr/bin/env python3
"""
context_layers.py — Progresywne ładowanie kontekstu RAG (wzorzec MemPalace).

Warstwy:
    L0: Stały system prompt (polski, ~100 tokenów)
    L1: Top-K krytycznych faktów z Qdrant, pre-ranked po ważności
    L2: Filtrowane zapytanie wing+room po detekcji tematu
    L3: Pełne wyszukiwanie semantyczne (bez filtrów)
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger("klimtechrag")

QDRANT_URL = "http://localhost:6333"
COLLECTION = "klimtech_docs"

# ─── L0: System Prompt ────────────────────────────────────────────────

SYSTEM_PROMPT_PL = (
    "Jesteś asystentem KlimtechRAG — polskojęzycznym systemem odpowiadania "
    "na pytania w oparciu o zaindeksowane dokumenty techniczne i prawne. "
    "Odpowiadaj po polsku. Cytuj źródła dokumentów gdy to możliwe. "
    "Jeśli nie masz wystarczających informacji w kontekście, powiedz o tym. "
    "Preferuj informacje z dostarczonych dokumentów nad wiedzą treningową."
)


def get_l0_prompt() -> str:
    """L0: Zwraca stały system prompt (~100 tokenów)."""
    return SYSTEM_PROMPT_PL


# ─── L1: Pre-ranked Top-K Facts ──────────────────────────────────────

def get_l1_facts(top_k: int = 10, max_chars: int = 200) -> str:
    """
    L1: Pobiera najważniejsze fakty z Qdrant, truncowane do max_chars.

    Strategia: scroll po kolekcji z sortowaniem po metadanych ważności.
    Jeśli brak pola 'importance' — bierze losowe top_k punktów.

    Returns:
        str: Sformatowany kontekst L1
    """
    try:
        r = httpx.post(
            QDRANT_URL + "/collections/" + COLLECTION + "/points/scroll",
            json={
                "limit": top_k,
                "with_payload": True,
                "with_vector": False,
            },
            timeout=10,
        )
        data = r.json()
        points = data.get("result", {}).get("points", [])
    except Exception as e:
        logger.warning("L1: Błąd Qdrant scroll: %s", e)
        return ""

    if not points:
        return ""

    # Grupuj po wing, truncuj snippety
    wings = {}
    for p in points:
        payload = p.get("payload", {})
        wing = payload.get("wing", "ogólne")
        content = payload.get("content", "")[:max_chars]
        source = payload.get("source", "?")
        if wing not in wings:
            wings[wing] = []
        wings[wing].append("[" + source + "] " + content)

    lines = ["=== Kluczowe fakty z bazy wiedzy ==="]
    for wing, snippets in wings.items():
        lines.append("-- " + wing + " --")
        for s in snippets[:3]:  # max 3 per wing
            lines.append("  " + s)

    return "\n".join(lines)


# ─── L2: Filtrowane zapytanie wing+room ──────────────────────────────

def detect_wing_from_query(query: str) -> Optional[str]:
    """
    Prosta detekcja tematu (wing) z pytania użytkownika.

    Używa keyword matching na polskich i angielskich słowach kluczowych.
    Zwraca wing ID lub None jeśli nie wykryto.
    """
    query_lower = query.lower()

    wing_keywords = {
        "construction": [
            "budow", "beton", "fundament", "konstrukc", "dach",
            "instalac", "archit", "prawo budowlane", "eurokod",
        ],
        "medicine": [
            "lekar", "pacjent", "leczen", "chorob", "szpital",
            "medyc", "zdrow", "diagno",
        ],
        "it_technology": [
            "program", "software", "kod", "baza danych", "serwer",
            "python", "api", "algorytm",
        ],
        "law": [
            "ustaw", "prawo", "regulac", "przepis", "rodo",
            "rozporz", "kodeks",
        ],
        "electrical": [
            "elektr", "prąd", "napięci", "silnik", "transform",
            "instalacja elektryczna",
        ],
    }

    best_wing = None
    best_score = 0

    for wing, keywords in wing_keywords.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > best_score:
            best_score = score
            best_wing = wing

    return best_wing if best_score > 0 else None


def get_l2_context(query: str, query_embedding: list,
                   top_k: int = 5, max_chars: int = 300) -> str:
    """
    L2: Filtrowane wyszukiwanie w ramach wykrytego wing.

    Args:
        query: pytanie użytkownika (do detekcji wing)
        query_embedding: wektor pytania (dim=1024)
        top_k: ile wyników
        max_chars: max długość snippetu

    Returns:
        str: Sformatowany kontekst L2 lub pusty string
    """
    wing = detect_wing_from_query(query)
    if not wing:
        return ""

    search_body = {
        "vector": query_embedding,
        "limit": top_k,
        "with_payload": True,
        "filter": {
            "must": [
                {"key": "wing", "match": {"value": wing}}
            ]
        },
    }

    try:
        r = httpx.post(
            QDRANT_URL + "/collections/" + COLLECTION + "/points/search",
            json=search_body,
            timeout=10,
        )
        results = r.json().get("result", [])
    except Exception as e:
        logger.warning("L2: Błąd Qdrant search: %s", e)
        return ""

    if not results:
        return ""

    lines = ["=== Dokumenty z domeny: " + wing + " ==="]
    for hit in results:
        payload = hit.get("payload", {})
        score = hit.get("score", 0)
        source = payload.get("source", "?")
        content = payload.get("content", "")[:max_chars]
        lines.append(
            "[" + source + " score=" + str(round(score, 3)) + "] " + content
        )

    return "\n".join(lines)


# ─── L3: Pełne wyszukiwanie semantyczne ──────────────────────────────

def get_l3_context(query_embedding: list, top_k: int = 10,
                   max_chars: int = 500) -> str:
    """
    L3: Pełne wyszukiwanie semantyczne bez filtrów.

    Args:
        query_embedding: wektor pytania (dim=1024)
        top_k: ile wyników
        max_chars: max długość snippetu

    Returns:
        str: Sformatowany kontekst L3
    """
    try:
        r = httpx.post(
            QDRANT_URL + "/collections/" + COLLECTION + "/points/search",
            json={
                "vector": query_embedding,
                "limit": top_k,
                "with_payload": True,
            },
            timeout=10,
        )
        results = r.json().get("result", [])
    except Exception as e:
        logger.warning("L3: Błąd Qdrant search: %s", e)
        return ""

    if not results:
        return ""

    lines = ["=== Wyniki wyszukiwania semantycznego ==="]
    for hit in results:
        payload = hit.get("payload", {})
        score = hit.get("score", 0)
        source = payload.get("source", "?")
        content = payload.get("content", "")[:max_chars]
        lines.append(
            "[" + source + " score=" + str(round(score, 3)) + "] " + content
        )

    return "\n".join(lines)


# ─── Orkiestrator warstw ──────────────────────────────────────────────

def build_progressive_context(query: str,
                              query_embedding: list,
                              use_l1: bool = True,
                              use_l2: bool = True,
                              max_total_chars: int = 4000) -> dict:
    """
    Buduje kontekst progresywnie L0 → L1 → L2 → L3.

    Zatrzymuje się gdy zebrano wystarczająco dużo kontekstu
    lub przekroczono max_total_chars.

    Returns:
        dict: {
            "system_prompt": str,  # L0
            "context": str,        # L1 + L2 + L3 (połączone)
            "layers_used": list,   # np. ["L0", "L1", "L2"]
        }
    """
    system_prompt = get_l0_prompt()
    context_parts = []
    layers_used = ["L0"]
    current_chars = 0

    # L1: Pre-ranked facts
    if use_l1:
        l1 = get_l1_facts(top_k=10, max_chars=200)
        if l1:
            context_parts.append(l1)
            current_chars += len(l1)
            layers_used.append("L1")

    # L2: Filtrowane po wing
    if use_l2 and current_chars < max_total_chars:
        l2 = get_l2_context(
            query, query_embedding,
            top_k=5,
            max_chars=300,
        )
        if l2:
            context_parts.append(l2)
            current_chars += len(l2)
            layers_used.append("L2")

    # L3: Pełne semantyczne (zawsze jako fallback)
    if current_chars < max_total_chars:
        remaining_chars = max_total_chars - current_chars
        l3 = get_l3_context(
            query_embedding,
            top_k=10,
            max_chars=min(500, remaining_chars // 10),
        )
        if l3:
            context_parts.append(l3)
            layers_used.append("L3")

    context = "\n\n".join(context_parts)

    logger.info(
        "Context layers: %s, total chars: %d",
        "+".join(layers_used), len(context),
    )

    return {
        "system_prompt": system_prompt,
        "context": context,
        "layers_used": layers_used,
    }
```

---

## KROK 2: Podepnij w routes/chat.py

W endpoincie `/v1/chat/completions`, gdy `use_rag=True`:

```python
from ..services.context_layers import build_progressive_context
from ..services.embeddings import get_text_embedder

# Embed pytanie
embedding_result = get_text_embedder().run(text=user_message)
query_embedding = embedding_result["embedding"]

# Progresywny kontekst
ctx = build_progressive_context(
    query=user_message,
    query_embedding=query_embedding,
    use_l1=True,
    use_l2=True,
    max_total_chars=4000,
)

# Buduj messages dla llama-server
messages = [
    {"role": "system", "content": ctx["system_prompt"]},
]
if ctx["context"]:
    messages.append({
        "role": "system",
        "content": "Kontekst z bazy wiedzy:\n" + ctx["context"],
    })
# Dodaj historię konwersacji i pytanie użytkownika
messages.extend(original_messages)
```

**WAŻNE:**
- NIE usuwaj istniejącego kodu RAG — dodaj jako alternatywną ścieżkę
- Parametr w .env: `KLIMTECH_PROGRESSIVE_CONTEXT=true` (domyślnie false)
- Gdy false → stary pipeline RAG, gdy true → nowy 4-warstwowy

---

## KROK 3: Endpoint diagnostyczny

Dodaj endpoint do sprawdzania co zwraca każda warstwa:

```python
# W routes/chat.py lub routes/admin.py:

@router.get("/v1/context/debug")
async def debug_context_layers(
    query: str = "Jakie są wymagania Prawa budowlanego?",
    req: Request = None,
):
    """Debugowanie warstw kontekstu — pokazuje co zwraca każda warstwa."""
    require_api_key(req)
    from ..services.context_layers import (
        get_l0_prompt, get_l1_facts, detect_wing_from_query,
    )

    wing = detect_wing_from_query(query)

    return {
        "query": query,
        "detected_wing": wing,
        "l0_length": len(get_l0_prompt()),
        "l1_preview": get_l1_facts(top_k=3, max_chars=100),
    }
```

**Test:**
```bash
curl -sk "http://localhost:8000/v1/context/debug?query=normy%20budowlane" \
  -H "Authorization: Bearer sk-local" | python3 -m json.tool
```

---

## RAPORTOWANIE

| Krok | Status | Uwagi |
|------|--------|-------|
| 1. context_layers.py | PASS/FAIL | import bez błędów |
| 2. Integracja chat.py | PASS/FAIL | env var działa |
| 3. Debug endpoint | PASS/FAIL | zwraca wing + preview |
