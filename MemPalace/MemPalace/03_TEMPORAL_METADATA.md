# 03_TEMPORAL_METADATA — Metadane temporalne valid_from/valid_to

**Zadanie:** Dodaj pola valid_from i valid_to do payloadów Qdrant
**Czas:** 1 dzień
**Zależności:** 02_METADATA_HIERARCHY
**VRAM:** 0 MB
**Pliki do modyfikacji:** `backend_app/categories/classifier.py`, `backend_app/routes/ingest.py`, `backend_app/services/qdrant.py`

---

## KONTEKST DLA ROBOTNIKA

Dokumenty prawne i regulacyjne mają daty obowiązywania. Ustawa może obowiązywać
od 1 stycznia 2020 i być uchylona 1 lipca 2025. Normy PN-EN mają daty wydania.
Raporty mają daty sporządzenia. Te daty pozwalają na filtrowanie:
"pokaż tylko przepisy obowiązujące DZISIAJ" lub "co obowiązywało w 2023?"

Pola w payload Qdrant:
- `valid_from`: str w formacie ISO "YYYY-MM-DD" lub null
- `valid_to`: str w formacie ISO "YYYY-MM-DD" lub null (null = nadal obowiązuje)

---

## KROK 1: Ekstrakcja dat z treści dokumentu

Dodaj do `backend_app/categories/classifier.py`:

```python
import re
from typing import Optional


def extract_temporal_dates(filepath: str = "",
                           content: str = "") -> dict:
    """
    Wyciąga daty obowiązywania z treści dokumentu.

    Szuka wzorców:
    - "ustawa z dnia DD MMMM YYYY"
    - "z dnia DD.MM.YYYY"
    - "obowiązuje od DD.MM.YYYY"
    - "traci moc DD.MM.YYYY" / "uchylony DD.MM.YYYY"
    - daty w metadanych PDF (jeśli dostępne w content)

    Returns:
        dict: {"valid_from": "YYYY-MM-DD" | None,
               "valid_to": "YYYY-MM-DD" | None}
    """
    text = (filepath + " " + content[:5000]).lower()

    polish_months = {
        "stycznia": "01", "lutego": "02", "marca": "03",
        "kwietnia": "04", "maja": "05", "czerwca": "06",
        "lipca": "07", "sierpnia": "08", "września": "09",
        "października": "10", "listopada": "11", "grudnia": "12",
    }

    valid_from = None
    valid_to = None

    # Wzorzec: "z dnia DD miesiąca YYYY"
    for month_name, month_num in polish_months.items():
        pattern = r"z dnia (\d{1,2})\s+" + month_name + r"\s+(\d{4})"
        match = re.search(pattern, text)
        if match:
            day = match.group(1).zfill(2)
            year = match.group(2)
            valid_from = year + "-" + month_num + "-" + day
            break

    # Wzorzec: "z dnia DD.MM.YYYY"
    if not valid_from:
        match = re.search(r"z dnia (\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).zfill(2)
            year = match.group(3)
            valid_from = year + "-" + month + "-" + day

    # Wzorzec: "obowiązuje od DD.MM.YYYY"
    if not valid_from:
        match = re.search(
            r"obowi[aą]zuje od (\d{1,2})\.(\d{1,2})\.(\d{4})", text
        )
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).zfill(2)
            year = match.group(3)
            valid_from = year + "-" + month + "-" + day

    # Wzorzec: "traci moc" / "uchylony" / "obowiązuje do"
    for prefix in ["traci moc", "uchylon", "obowi.zuje do"]:
        match = re.search(
            prefix + r"[^\d]*(\d{1,2})\.(\d{1,2})\.(\d{4})", text
        )
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).zfill(2)
            year = match.group(3)
            valid_to = year + "-" + month + "-" + day
            break

    return {"valid_from": valid_from, "valid_to": valid_to}
```

**Test:**
```python
from backend_app.categories.classifier import extract_temporal_dates

r1 = extract_temporal_dates(content="Ustawa z dnia 7 lipca 1994 r. Prawo budowlane")
assert r1["valid_from"] == "1994-07-07"
assert r1["valid_to"] is None

r2 = extract_temporal_dates(content="Rozporządzenie z dnia 12.03.2020 traci moc 01.01.2025")
assert r2["valid_from"] == "2020-03-12"
assert r2["valid_to"] == "2025-01-01"

r3 = extract_temporal_dates(content="Zwykły tekst bez dat")
assert r3["valid_from"] is None
assert r3["valid_to"] is None
```

---

## KROK 2: Podepnij w ingest.py

W `_background_ingest()`, po linii z `classify_document_full()`, dodaj:

```python
from ..categories.classifier import extract_temporal_dates

temporal = extract_temporal_dates(filepath=file_path, content=markdown_text)

# W meta dokumentu dodaj:
docs = [
    Document(content=markdown_text, meta={
        "source": filename,
        "type": suffix,
        "category": classification["room"],
        "wing": classification["wing"],
        "room": classification["room"],
        "hall": classification["hall"],
        "valid_from": temporal["valid_from"],  # może być None
        "valid_to": temporal["valid_to"],      # może być None
    })
]
```

**WAŻNE:** Qdrant akceptuje wartości null w payload — nie filtruj None.

---

## KROK 3: Dodaj filtrowanie temporalne do retrievalu

W `backend_app/services/qdrant.py` lub tam gdzie budujesz query do Qdrant,
dodaj opcjonalny filtr temporalny. Utwórz helper:

```python
def build_temporal_filter(as_of_date: str = "") -> list:
    """
    Buduje filtr Qdrant: dokumenty obowiązujące na daną datę.

    Args:
        as_of_date: data w formacie "YYYY-MM-DD". Puste = brak filtra.

    Returns:
        list: warunki must do filtra Qdrant (pusta lista = brak filtra)
    """
    if not as_of_date:
        return []

    conditions = [
        # valid_from <= as_of_date LUB valid_from jest null
        {
            "should": [
                {"key": "valid_from", "range": {"lte": as_of_date}},
                {"is_null": {"key": "valid_from"}},
            ]
        },
        # valid_to >= as_of_date LUB valid_to jest null (nadal obowiązuje)
        {
            "should": [
                {"key": "valid_to", "range": {"gte": as_of_date}},
                {"is_null": {"key": "valid_to"}},
            ]
        },
    ]
    return conditions
```

**Uwaga:** Składnia filtrów Qdrant dla range na stringach ISO działa
leksykograficznie — format "YYYY-MM-DD" jest poprawny do porównań.

---

## KROK 4: Indeksy na polach temporalnych

```bash
curl -X PUT "http://localhost:6333/collections/klimtech_docs/index" \
  -H "Content-Type: application/json" \
  -d '{"field_name": "valid_from", "field_schema": "keyword"}'

curl -X PUT "http://localhost:6333/collections/klimtech_docs/index" \
  -H "Content-Type: application/json" \
  -d '{"field_name": "valid_to", "field_schema": "keyword"}'
```

---

## KROK 5: Migracja istniejących punktów

Rozszerz `migrate_metadata.py` z kroku 02 o temporalne pola:

W pętli po punktach, po `classify_document_full()`, dodaj:

```python
temporal = extract_temporal_dates(filepath=source, content=content)
# Dodaj do payload update:
payload_update = {
    "wing": classification["wing"],
    "room": classification["room"],
    "hall": classification["hall"],
    "valid_from": temporal["valid_from"],
    "valid_to": temporal["valid_to"],
}
```

---

## RAPORTOWANIE

| Krok | Status | Uwagi |
|------|--------|-------|
| 1. extract_temporal_dates() | PASS/FAIL | 3 asercje |
| 2. Payload w ingest.py | PASS/FAIL | nowe punkty mają valid_from/to |
| 3. build_temporal_filter() | PASS/FAIL | generuje poprawny JSON |
| 4. Indeksy Qdrant | PASS/FAIL | 2 indeksy |
| 5. Migracja | PASS/FAIL | ile punktów z datami |
