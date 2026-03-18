# Plan refaktoryzacji image_handler.py — ZAAKCEPTOWANY

**Data akceptacji:** 2026-03-18  
**Dotyczy:** `backend_app/ingest/image_handler.py`  
**Status:** ✅ Zaakceptowany, do wdrożenia

---

## Punkt 1: Wyciągnięcie promptów z kodu do pliku konfiguracyjnego

**Problem:** Prompt VLM jest hardcoded w `image_handler.py` (linia ~60). Zmiana wymaga edycji kodu i restartu.

**Rozwiązanie:** Nowy plik `backend_app/prompts/vlm_prompts.py` (lub `.yaml`) z zestawem promptów ładowanych przy starcie. Parametr `prompt` w `describe_image_with_vlm()` nadal ma domyślną wartość, ale pobieraną z pliku konfiguracyjnego.

**Pliki:**
- Nowy: `backend_app/prompts/__init__.py`
- Nowy: `backend_app/prompts/vlm_prompts.py`
- Zmiana: `backend_app/ingest/image_handler.py` — import promptów z nowego modułu

---

## Punkt 2: Rozbudowa promptu domyślnego

**Problem:** Obecny prompt obsługuje tylko 3 typy (medyczne, diagramy, wykresy). Brak instrukcji o formacie wyjścia, brak wyciągania tekstu/numerów, brak kontekstu dokumentu.

**Rozwiązanie:** Nowy prompt `DEFAULT` w `vlm_prompts.py` — uniwersalny, szczegółowy, z instrukcjami formatu wyjścia i wyciągania kluczowych informacji.

---

## Punkt 3: Zestaw promptów per typ obrazu

**Problem:** Jeden prompt dla wszystkich typów obrazów to kompromis — nigdy nie jest optymalny.

**Rozwiązanie:** 8 wariantów promptów w `vlm_prompts.py`:

```
vlm_prompts.py:
├── DEFAULT          — uniwersalny, szczegółowy, z formatem wyjścia
├── DIAGRAM          — dla schematów, flowchartów, algorytmów
├── CHART            — dla wykresów (dane, osie, trendy, wartości)
├── TABLE            — dla tabel (zachowaj strukturę, kolumny, wiersze)
├── PHOTO            — dla zdjęć (co widać, kontekst, detale)
├── SCREENSHOT       — dla screenów UI (elementy interfejsu, tekst)
├── TECHNICAL        — dla schematów technicznych (wymiary, części)
└── MEDICAL          — dla obrazów medycznych (anatomia, procedury)
```

Dobór promptu automatyczny na podstawie `image_type` z `ExtractedImage` (pole już istnieje w kodzie).

Każdy prompt zawiera:
- Jasną instrukcję CO opisać
- Format wyjścia (structured, max ~200 słów)
- Instrukcję wyciągania tekstu/numerów z obrazu
- Język odpowiedzi (polski)

---

## Punkt 4: Dynamiczne parametry llama-cli

**Problem:** W `image_handler.py` linie 128-145 mają hardcoded parametry:
```python
cmd = [
    LLAMA_CLI_BIN,
    "-m", VLM_MODEL,
    "--image", image_path,
    "-p", prompt,
    "-n", "512",        # ← hardcoded
    "--temp", "0.1",    # ← hardcoded
    "-ngl", "99",       # ← hardcoded
    "-c", "4096",       # ← hardcoded
    "--no-display",
]
```

Niespójne z `start_klimtech_v3.py`, gdzie parametry są obliczane dynamicznie przez `model_parametr.calculate_params()`.

**Rozwiązanie:**
1. Wywołać `model_parametr.calculate_params(VLM_MODEL)` przy starcie VLM
2. Parametry specyficzne dla VLM (`-n`, `--temp`) przenieść do konfiguracji:
   - `config.py` → nowe pola: `vlm_max_tokens`, `vlm_temperature`, `vlm_context`
   - Lub `vlm_prompts.py` → sekcja `VLM_PARAMS`
3. Zachować sensowne domyślne wartości jako fallback

---

## Podsumowanie zmian

| # | Co | Gdzie | Efekt |
|---|-----|-------|-------|
| 1 | Prompty → plik konfiguracyjny | Nowy `backend_app/prompts/vlm_prompts.py` | Zmiana promptu bez zmiany kodu |
| 2 | Rozbudowa DEFAULT prompt | `vlm_prompts.py` → `DEFAULT` | Lepsze opisy, format, ekstrakcja tekstu |
| 3 | 8 promptów per typ obrazu | `vlm_prompts.py` → 8 wariantów | Auto-dobór promptu do typu obrazu |
| 4 | Dynamiczne parametry llama-cli | `image_handler.py` + `config.py` | Spójność z resztą systemu |

**Pliki do zmiany:**
- `backend_app/ingest/image_handler.py` — refactor (import promptów, dynamiczne params)
- Nowy: `backend_app/prompts/__init__.py`
- Nowy: `backend_app/prompts/vlm_prompts.py`
- `backend_app/config.py` — dodanie VLM params (opcjonalne)

**Pliki BEZ zmian:**
- `start_klimtech_v3.py`
- `model_manager.py`
- `routes/chat.py`
- `routes/ingest.py`
- `static/index.html`

---

*Zaakceptowano: 2026-03-18*
