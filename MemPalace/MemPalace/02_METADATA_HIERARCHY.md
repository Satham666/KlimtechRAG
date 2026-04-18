# 02_METADATA_HIERARCHY — Hierarchia metadanych wing/room/hall w Qdrant

**Zadanie:** Dodaj pola wing, room, hall do payloadów obu kolekcji Qdrant
**Czas:** 2 dni
**Zależności:** 01_ROBOTNIK_SETUP
**VRAM:** 0 MB (modyfikacja pipeline'u, bez ładowania modeli)
**Pliki do modyfikacji:** `backend_app/routes/ingest.py`, `backend_app/categories/definitions.py`, `backend_app/categories/classifier.py`

---

## KONTEKST DLA ROBOTNIKA

Projekt KlimtechRAG ma 14 kategorii w `backend_app/categories/definitions.py`.
Funkcja `classify_document()` w `classifier.py` przypisuje kategorię do dokumentu.
Chunki w Qdrant mają payload: `source`, `type`, `category`, `chunk_idx`.
Celem jest rozszerzenie payloadu o 3 nowe pola: `wing`, `room`, `hall`.

**Mapowanie na polską dokumentację techniczno-prawną:**

```
wing    = domena tematyczna (= istniejące top-level categories)
          Przykłady: "medicine", "construction", "it_technology", "law"

room    = podkategoria / konkretny temat w domenie
          Przykłady: "medicine.diseases.cardiology", "law.regulations.rodo"

hall    = typ dokumentu (niezależny od domeny)
          Wartości: "ustawa", "rozporządzenie", "instrukcja", "raport",
                    "specyfikacja", "manual", "norma", "procedura", "inny"
```

---

## KROK 1: Rozszerz classifier.py o detekcję hall (typ dokumentu)

Dodaj nową funkcję do `backend_app/categories/classifier.py`:

```python
def classify_document_type(filepath: str = "", content: str = "") -> str:
    """
    Klasyfikuje typ dokumentu na podstawie ścieżki i treści.

    Returns:
        str: Jeden z: "ustawa", "rozporządzenie", "instrukcja",
             "raport", "specyfikacja", "manual", "norma",
             "procedura", "inny"
    """
    text_lower = (filepath + " " + content[:2000]).lower()

    # Wykrywanie po wzorcach tekstowych (polskie dokumenty prawne)
    patterns = {
        "ustawa": [
            "ustawa z dnia", "dz.u.", "dziennik ustaw",
            "art.", "artykuł", "ustawy z dnia",
        ],
        "rozporządzenie": [
            "rozporządzenie ministra", "rozporządzenie rady",
            "rozporządzenie prezesa", "rozporządzenie parlamentu",
        ],
        "norma": [
            "pn-en", "pn-iso", "iso ", "norma ", "en ",
            "eurokod", "eurocode",
        ],
        "specyfikacja": [
            "specyfikacja techniczna", "stwiorb", "sst ",
            "specyfikacja istotnych", "opis przedmiotu zamówienia",
        ],
        "instrukcja": [
            "instrukcja ", "instruction", "anleitung",
            "obsługi", "użytkowania", "montażu",
        ],
        "manual": [
            "manual", "podręcznik", "handbuch", "handbook",
        ],
        "raport": [
            "raport", "report", "bericht", "sprawozdanie",
            "protokół", "wyniki badań",
        ],
        "procedura": [
            "procedura", "procedure", "verfahren",
            "proces ", "workflow",
        ],
    }

    scores = {}
    for doc_type, keywords in patterns.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[doc_type] = score

    if scores:
        return max(scores, key=scores.get)
    return "inny"
```

**Wymagania:**
- Funkcja musi być czysta (bez efektów ubocznych)
- Type hints na argumentach i return
- Docstring po polsku
- NIE importuj żadnych nowych bibliotek — tylko string matching

**Test:** Wywołaj ręcznie:
```python
from backend_app.categories.classifier import classify_document_type
assert classify_document_type(content="Ustawa z dnia 7 lipca 1994 r. Prawo budowlane") == "ustawa"
assert classify_document_type(content="Instrukcja obsługi kotła gazowego") == "instrukcja"
assert classify_document_type(content="PN-EN 1992-1-1 Eurokod 2") == "norma"
assert classify_document_type(filepath="random_file.txt", content="lorem ipsum") == "inny"
```

---

## KROK 2: Rozszerz classify_document() o wing i room

W istniejącej funkcji `classify_document()` w `classifier.py`,
zmień return type z `str` na `dict`:

```python
def classify_document_full(filepath: str = "", content: str = "") -> dict:
    """
    Pełna klasyfikacja dokumentu: wing, room, hall.

    Returns:
        dict z kluczami:
            wing (str): top-level category id (np. "construction")
            room (str): subcategory id (np. "construction.design.architecture")
            hall (str): typ dokumentu (np. "ustawa")
    """
    # Użyj istniejącej classify_document() do uzyskania category
    category = classify_document(filepath=filepath, content=content)

    # Wing = top-level id (część przed pierwszą kropką)
    wing = category.split(".")[0] if "." in category else category

    # Room = pełna ścieżka subcategory (= category)
    room = category

    # Hall = typ dokumentu
    hall = classify_document_type(filepath=filepath, content=content)

    return {"wing": wing, "room": room, "hall": hall}
```

**WAŻNE:** NIE modyfikuj istniejącej `classify_document()` — dodaj NOWĄ
funkcję `classify_document_full()` obok niej. Stara musi dalej działać.

**Test:**
```python
from backend_app.categories.classifier import classify_document_full
result = classify_document_full(
    filepath="/budownictwo/normy/PN-EN-1992.pdf",
    content="Eurokod 2 Projektowanie konstrukcji z betonu"
)
assert result["wing"] == "construction"
assert "construction" in result["room"]
assert result["hall"] == "norma"
```

---

## KROK 3: Rozszerz payload w ingest.py

W pliku `backend_app/routes/ingest.py`, znajdź funkcję `_background_ingest()`
(lub `ingest_single_file()`). Znajdź miejsce, gdzie tworzony jest `Document`:

```python
# PRZED (istniejący kod):
category = classify_document(filepath=file_path, content=markdown_text)
docs = [
    Document(content=markdown_text, meta={
        "source": filename,
        "type": suffix,
        "category": category,
    })
]

# PO (nowy kod):
from ..categories.classifier import classify_document_full

classification = classify_document_full(filepath=file_path, content=markdown_text)
docs = [
    Document(content=markdown_text, meta={
        "source": filename,
        "type": suffix,
        "category": classification["room"],  # zachowaj kompatybilność
        "wing": classification["wing"],
        "room": classification["room"],
        "hall": classification["hall"],
    })
]
```

**WAŻNE:**
- Zachowaj pole `category` dla kompatybilności wstecznej
- NIE usuwaj żadnych istniejących pól z meta
- Import `classify_document_full` dodaj na górze pliku

**Test:** Po zaindeksowaniu dokumentu testowego, sprawdź payload w Qdrant:
```bash
curl -s http://localhost:6333/collections/klimtech_docs/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 1, "with_payload": true}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
p = data['result']['points'][0]['payload']
print('wing:', p.get('wing', 'BRAK'))
print('room:', p.get('room', 'BRAK'))
print('hall:', p.get('hall', 'BRAK'))
"
```
**Oczekiwany wynik:** Trzy pola z wartościami (nie BRAK).

---

## KROK 4: Migracja istniejących punktów (batch update payloadów)

Istniejące ~5114 punktów w klimtech_docs nie mają pól wing/room/hall.
Utwórz skrypt migracyjny `backend_app/scripts/migrate_metadata.py`:

```python
#!/usr/bin/env python3
"""
migrate_metadata.py — Dodaje wing/room/hall do istniejących punktów w Qdrant.

Iteruje przez wszystkie punkty, klasyfikuje na podstawie source/content,
i aktualizuje payload przez set_payload.

Użycie:
    python3 -m backend_app.scripts.migrate_metadata --dry-run
    python3 -m backend_app.scripts.migrate_metadata --apply
"""
import argparse
import logging
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend_app.categories.classifier import classify_document_full

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate")

QDRANT_URL = "http://localhost:6333"
COLLECTION = "klimtech_docs"
BATCH_SIZE = 100


def migrate(dry_run: bool = True):
    """Migruj istniejące punkty — dodaj wing/room/hall."""
    offset = None
    total = 0
    updated = 0

    while True:
        body = {"limit": BATCH_SIZE, "with_payload": True, "with_vector": False}
        if offset is not None:
            body["offset"] = offset

        r = httpx.post(
            QDRANT_URL + "/collections/" + COLLECTION + "/points/scroll",
            json=body,
            timeout=30,
        )
        data = r.json()
        points = data["result"]["points"]
        next_offset = data["result"].get("next_page_offset")

        if not points:
            break

        for point in points:
            total += 1
            payload = point["payload"]

            # Pomiń jeśli już ma wing
            if payload.get("wing"):
                continue

            source = payload.get("source", "")
            content = payload.get("content", "")[:2000]

            classification = classify_document_full(
                filepath=source,
                content=content,
            )

            if dry_run:
                logger.info(
                    "DRY-RUN: %s → wing=%s room=%s hall=%s",
                    source[:40], classification["wing"],
                    classification["room"], classification["hall"],
                )
            else:
                httpx.post(
                    QDRANT_URL + "/collections/" + COLLECTION + "/points/payload",
                    json={
                        "payload": {
                            "wing": classification["wing"],
                            "room": classification["room"],
                            "hall": classification["hall"],
                        },
                        "points": [point["id"]],
                    },
                    timeout=10,
                )
            updated += 1

        if next_offset is None:
            break
        offset = next_offset

    logger.info("Gotowe: %d/%d punktów %s",
                updated, total,
                "DO AKTUALIZACJI" if dry_run else "ZAKTUALIZOWANYCH")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    migrate(dry_run=not args.apply)
```

**Test (dry-run):**
```bash
python3 -m backend_app.scripts.migrate_metadata --dry-run
```
**Oczekiwany wynik:** Lista punktów z proponowanymi wing/room/hall, bez modyfikacji.

**Aplikacja (po weryfikacji dry-run):**
```bash
python3 -m backend_app.scripts.migrate_metadata --apply
```

---

## KROK 5: Dodaj indeks payloadów w Qdrant

Utwórz indeksy na nowych polach dla szybkiego filtrowania:

```bash
# Indeks na wing
curl -X PUT "http://localhost:6333/collections/klimtech_docs/index" \
  -H "Content-Type: application/json" \
  -d '{"field_name": "wing", "field_schema": "keyword"}'

# Indeks na room
curl -X PUT "http://localhost:6333/collections/klimtech_docs/index" \
  -H "Content-Type: application/json" \
  -d '{"field_name": "room", "field_schema": "keyword"}'

# Indeks na hall
curl -X PUT "http://localhost:6333/collections/klimtech_docs/index" \
  -H "Content-Type: application/json" \
  -d '{"field_name": "hall", "field_schema": "keyword"}'
```

**Test:**
```bash
curl -s http://localhost:6333/collections/klimtech_docs \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
idx = data['result']['payload_schema']
for field in ['wing', 'room', 'hall']:
    print(field, ':', 'INDEXED' if field in idx else 'BRAK')
"
```

---

## RAPORTOWANIE

| Krok | Status | Uwagi |
|------|--------|-------|
| 1. classify_document_type() | PASS/FAIL | testy asercji |
| 2. classify_document_full() | PASS/FAIL | testy asercji |
| 3. Payload w ingest.py | PASS/FAIL | nowe punkty mają wing/room/hall |
| 4. Migracja (dry-run) | PASS/FAIL | ile punktów do aktualizacji |
| 4b. Migracja (apply) | PASS/FAIL | ile zaktualizowano |
| 5. Indeksy Qdrant | PASS/FAIL | 3 indeksy INDEXED |
