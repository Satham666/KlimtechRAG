# 07_GRAPH_NER — Krawędzie z ekstrakcji encji (opcjonalny)

**Zadanie:** Dodaj krawędzie shared_entity na podstawie NER/regex
**Czas:** 2-3 dni
**Zależności:** 06_GRAPH_API_VIZ
**VRAM:** 0 MB (heurystyka regex) LUB ~5 GB (Bielik-4.5B jako NER)
**Pliki do utworzenia:** `backend_app/services/entity_service.py`, `backend_app/scripts/extract_entities.py`

---

## KONTEKST DLA ROBOTNIKA

Cel: wykryj encje (nazwy przepisów, normy, organizacje) w dokumentach.
Gdy dwa dokumenty wspominają tę samą encję → krawędź shared_entity w grafie.

Trzy strategie (od najprostszej do najcięższej):

**A) Regex (0 VRAM, szybkie, ograniczone)** — wzorce na polskie normy i przepisy
**B) spaCy pl_core_news_lg (~500 MB RAM, CPU)** — NER PER/ORG/LOC
**C) Bielik-4.5B jako NER (~5 GB VRAM)** — najlepsze dla polskiego technicznego

Rekomendacja: zacznij od A), dodaj B) lub C) gdy A) jest niewystarczające.

---

## KROK 1: Regex-based entity extraction (strategia A)

Utwórz `backend_app/services/entity_service.py`:

```python
"""
entity_service.py — Ekstrakcja encji z dokumentów polskich.

Strategia A: regex na znane wzorce (normy, przepisy, organizacje).
Brak zależności ML — czyste string matching.
"""
import re
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger("klimtechrag")

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "file_registry.db"

# Wzorce regex dla polskich dokumentów technicznych/prawnych
ENTITY_PATTERNS = {
    "norma": [
        r"PN-EN\s*[\d\-:]+",           # PN-EN 1992-1-1
        r"PN-ISO\s*[\d\-:]+",          # PN-ISO 9001
        r"PN-B-\d+",                   # PN-B-03264
        r"EN\s+\d{3,5}(?:-\d+)*",      # EN 1090-2
        r"ISO\s+\d{3,5}(?:-\d+)*",     # ISO 14001
        r"Eurokod\s+\d+",              # Eurokod 2
    ],
    "ustawa": [
        r"[Uu]stawa z dnia \d{1,2}\s+\w+\s+\d{4}\s*r?\.\s*[\w\s]+",
        r"Prawo budowlane",
        r"Prawo zamówień publicznych",
        r"Kodeks pracy",
        r"Kodeks cywilny",
        r"RODO",
        r"GDPR",
    ],
    "rozporzadzenie": [
        r"[Rr]ozporządzeni\w+ [Mm]inistra \w+",
        r"Dz\.?\s*U\.?\s*\d{4}[\s,]+(?:nr\s*\d+[\s,]+)?poz\.?\s*\d+",
    ],
    "organizacja": [
        r"GDDKiA",
        r"GUNB",
        r"PIP",
        r"ITB",
        r"PIIB",
        r"UDT",
        r"PKN",
        r"UODO",
    ],
}


def extract_entities(content: str, max_length: int = 5000) -> list:
    """
    Wyciąga encje z tekstu za pomocą regex.

    Args:
        content: treść dokumentu
        max_length: max znaków do przeskanowania

    Returns:
        list[dict]: [{"type": "norma", "value": "PN-EN 1992-1-1"}, ...]
    """
    text = content[:max_length]
    entities = []
    seen = set()

    for entity_type, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = match.strip().upper()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    entities.append({
                        "type": entity_type,
                        "value": normalized,
                    })

    return entities


def _ensure_entity_table(conn: sqlite3.Connection) -> None:
    """Tworzy tabelę document_entities."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_entities (
            source TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_value TEXT NOT NULL,
            PRIMARY KEY (source, entity_type, entity_value)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity_value
        ON document_entities(entity_value)
    """)
    conn.commit()


def store_entities(source: str, entities: list) -> None:
    """Zapisz encje dokumentu do SQLite."""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        _ensure_entity_table(conn)
        for e in entities:
            conn.execute(
                "INSERT OR IGNORE INTO document_entities "
                "(source, entity_type, entity_value) VALUES (?, ?, ?)",
                (source, e["type"], e["value"]),
            )
        conn.commit()
    finally:
        conn.close()


def find_shared_entities() -> list:
    """
    Znajdź pary dokumentów współdzielące encje.

    Returns:
        list[dict]: [{"source_a": ..., "source_b": ...,
                      "shared_entities": [...], "count": N}, ...]
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        _ensure_entity_table(conn)
        rows = conn.execute("""
            SELECT a.source, b.source, a.entity_value, a.entity_type
            FROM document_entities a
            JOIN document_entities b
              ON a.entity_value = b.entity_value
              AND a.entity_type = b.entity_type
              AND a.source < b.source
            ORDER BY a.source, b.source
        """).fetchall()

        pairs = {}
        for src_a, src_b, value, etype in rows:
            key = (src_a, src_b)
            if key not in pairs:
                pairs[key] = {"source_a": src_a, "source_b": src_b,
                              "shared_entities": [], "count": 0}
            pairs[key]["shared_entities"].append(
                {"type": etype, "value": value}
            )
            pairs[key]["count"] += 1

        return list(pairs.values())
    finally:
        conn.close()
```

---

## KROK 2: Skrypt ekstrakcji i budowania krawędzi

Utwórz `backend_app/scripts/extract_entities.py`:

```python
#!/usr/bin/env python3
"""
extract_entities.py — Wyciąga encje z dokumentów w Qdrant i buduje krawędzie.

Użycie:
    python3 -m backend_app.scripts.extract_entities --dry-run
    python3 -m backend_app.scripts.extract_entities --apply
"""
import argparse
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend_app.services.entity_service import (
    extract_entities, store_entities, find_shared_entities,
)
from backend_app.services.graph_service import add_edge

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("extract_entities")

QDRANT_URL = "http://localhost:6333"
COLLECTION = "klimtech_docs"


def extract_all(dry_run: bool = True) -> None:
    """Iteruj przez dokumenty, wyciągnij encje, buduj krawędzie."""
    offset = None
    doc_entities = {}

    # Faza 1: ekstrakcja encji
    while True:
        body = {"limit": 100, "with_payload": True, "with_vector": False}
        if offset is not None:
            body["offset"] = offset

        r = httpx.post(
            QDRANT_URL + "/collections/" + COLLECTION + "/points/scroll",
            json=body, timeout=30,
        )
        data = r.json()
        points = data["result"]["points"]
        next_offset = data["result"].get("next_page_offset")

        for p in points:
            payload = p["payload"]
            source = payload.get("source", "")
            content = payload.get("content", "")

            if source and source not in doc_entities:
                entities = extract_entities(content)
                doc_entities[source] = entities

                if entities:
                    logger.info(
                        "%s: %d encji (%s)",
                        source[:30],
                        len(entities),
                        ", ".join(e["value"][:20] for e in entities[:3]),
                    )

                    if not dry_run:
                        store_entities(source, entities)

        if next_offset is None:
            break
        offset = next_offset

    logger.info("Encje wyciągnięte z %d dokumentów", len(doc_entities))

    # Faza 2: budowanie krawędzi
    if not dry_run:
        pairs = find_shared_entities()
        for pair in pairs:
            weight = min(pair["count"] / 5.0, 1.0)
            add_edge(
                pair["source_a"], pair["source_b"],
                "shared_entity", weight=round(weight, 3),
            )
        logger.info("Utworzono %d krawędzi shared_entity", len(pairs))
    else:
        logger.info("DRY-RUN: pomiń budowanie krawędzi")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    extract_all(dry_run=not args.apply)
```

**Test:**
```bash
python3 -m backend_app.scripts.extract_entities --dry-run
```

---

## KROK 3: Podepnij ekstrakcję w pipeline ingestion

W `backend_app/routes/ingest.py`, w `_background_ingest()`, po indeksowaniu:

```python
from ..services.entity_service import extract_entities, store_entities

entities = extract_entities(markdown_text)
if entities:
    store_entities(filename, entities)
    logger.info("[BG] %s: %d encji wyciągniętych", filename, len(entities))
```

---

## KROK 4 (OPCJONALNY): Bielik-4.5B jako NER

Gdy regex nie wystarcza, użyj Bielika do ekstrakcji encji.
Wymaga: zatrzymania głównego LLM, uruchomienia Bielika na 8083.

Prompt dla Bielika:
```
Wylistuj wszystkie nazwy własne z poniższego tekstu.
Kategorie: NORMA, USTAWA, ORGANIZACJA, OSOBA, MIEJSCE.
Format: TYP: wartość (jedno na linię).
Tekst:
{chunk_content}
```

**UWAGA na VRAM:** Ten krok uruchamia Bielika-4.5B (~5 GB).
Nie uruchamiaj jednocześnie z głównym LLM ani z embeddingami!

---

## RAPORTOWANIE

| Krok | Status | Uwagi |
|------|--------|-------|
| 1. entity_service.py | PASS/FAIL | import + regex test |
| 2. extract_entities --dry-run | PASS/FAIL | ile encji znaleziono |
| 2b. extract_entities --apply | PASS/FAIL | ile krawędzi |
| 3. Ingest hook | PASS/FAIL | nowe docs mają encje |
| 4. Bielik NER (opcja) | PASS/FAIL/SKIP | jakość vs regex |
