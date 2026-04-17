# Analiza błędów — PLAN_WDROZENIA_MASTER.md

**Data analizy:** 2026-04-07  
**Ostatnia aktualizacja:** 2026-04-07 (weryfikacja błędów 9-14 + ELEMENTY NIEZREALIZOWANE)  
**Wersja planu:** 1.0 (2026-03-30)  
**Analizował:** Claude Code (Sonnet 4.6), aktualizacja: GLM-5 (2026-04-07)

---

## PODSUMOWANIE

| Kategoria | Liczba |
|-----------|--------|
| Błędy nazw / ścieżek | 3 |
| ~~Pliki brakujące (plan mówi "utwórz", a ich nie ma)~~ | ~~2~~ → 0 (oba naprawione) |
| Kroki z Sprint 6 już wykonane | 7 |
| Cały Sprint 0–5 praktycznie ukończony (nie zaznaczono w planie) | 31 |
| Nieaktualne rozmiary plików | 4 |
| Nieaktualny harmonogram | 1 |

---

## BŁĘDY NAZW I ŚCIEŻEK

### [BŁĄD_NAZWY] W3 — kolumna `embedding_hash` vs `content_hash`

**Sekcja:** Sprint 0, W3, linia ~67  
**Plan mówi:** `Dodaj kolumnę embedding_hash (SHA256 treści po chunking)`  
**Stan rzeczywisty:** Kolumna w `file_registry.py` nazywa się `content_hash`, nie `embedding_hash`. Kod używa `content_hash` konsekwentnie w `dedup_service.py` i `ingest_service.py`.  
**Powaga:** DROBNY — funkcjonalnie OK, ale plan wprowadza w błąd jeśli ktoś szuka `embedding_hash`.

---

### [BŁĄD_WERSJI] G4 — `version="7.6"` zamiast `"7.7"`

**Sekcja:** Sprint 5, G4, linia ~667  
**Plan mówi:** `app = FastAPI(title="KlimtechRAG API", version="7.6")`  
**Stan rzeczywisty:** `backend_app/main.py:97` — `version="7.7"` (zaktualizowano w Sprint 7l).  
**Powaga:** DROBNY — plan jest przestarzały, kod poprawny.

---

### [BŁĄD_NAZWY] A1b — docelowy rozmiar `routes/chat.py`

**Sekcja:** Sprint 1, A1a, linia ~119  
**Plan mówi:** `routes/chat.py (~80 linii — TYLKO routing, walidacja, HTTP response)`  
**Stan rzeczywisty:** `backend_app/routes/chat.py` ma **277 linii** — refaktoryzacja jest częściowa, logika wciąż częściowo w route zamiast w service.  
**Powaga:** WAŻNY — A1a nie jest w pełni zakończone. `chat.py` 3× większy niż cel.

---

## PLIKI BRAKUJĄCE (plan wymienia, kod nie ma)

### ~~[BRAK_PLIKU] A2 — `settings-ingest.yaml`~~ ✅ NAPRAWIONE

**Sekcja:** Sprint 5, A2, linia ~588  
**Plan mówi:** Utwórz `settings-ingest.yaml` — tryb ingest (GPU embedding, bez LLM)  
**Stan rzeczywisty:** Plik `settings-ingest.yaml` istnieje (35 linii) — profil ingest z GPU embedding, wyłączonym LLM, odpowiednimi limitami.  
**Naprawione:** 2026-04-07

---

### ~~[BRAK_PLIKU] G1 — brakujące pliki testów~~ ✅ CZĘŚCIOWO NAPRAWIONE

**Sekcja:** Sprint 5, G1, linia ~613  
**Plan wymienia:**
```
tests/conftest.py
tests/test_health.py
tests/test_chat.py
tests/test_ingest.py
tests/test_chunks.py
```
**Stan rzeczywisty (2026-04-07):**
- ✅ `tests/conftest.py` — istnieje (32 linie, wspólne fixtures: app, client, api_key, auth_headers, bad_headers)
- ❌ `tests/test_health.py` — brak (ale health testowany w `test_admin.py`)
- ✅ `tests/test_chat.py` — istnieje (59 linii, testy models, chat/completions, rag/debug)
- ✅ `tests/test_ingest.py` — istnieje (62 linie, testy upload, ingest_path, files/stats, progress)
- ✅ `tests/test_chunks.py` — istnieje (51 linii, testy /v1/chunks z auth, limit, context_filter)

**Naprawione:** conftest.py, test_chat.py, test_ingest.py, test_chunks.py dodane. Brakuje test_health.py (trivialne — health testowany w test_admin.py).

---

## ROZMIARY PLIKÓW — NIEAKTUALNE

### [PRZESTARZAŁE] A1 — rozmiary plików przed refaktoryzacją

**Sekcja:** Sprint 1, A1, linia ~110  
**Plan mówi:** `chat.py (500 linii)` i `ingest.py (767 linii)` jako punkt startowy.  
**Stan rzeczywisty:** `chat.py` = 277 linii, `ingest.py` = 548 linii. Refaktoryzacja A1a i A1b już częściowo wykonana.  
**Powaga:** INFO — dane historyczne, nie błąd krytyczny.

### [PRZESTARZAŁE] Docelowa struktura — rozmiary po refaktoryzacji

**Sekcja:** Docelowa struktura katalogów, linia ~914  
**Plan mówi:** `chat.py (~80 linii)` i `ingest.py (~120 linii)` jako cel.  
**Stan rzeczywisty:** `chat.py` = 277 linii, `ingest.py` = 548 linii. Cel nie osiągnięty — refaktoryzacja A1a/A1b niekompletna.  
**Powaga:** WAŻNY — jeśli ktoś czyta plan jako "stan docelowy osiągnięty", jest to mylące.

---

## KROKI Z SPRINT 6 JUŻ WYKONANE

Plan umieszcza poniższe funkcje w Sprint 6 (tydzień 11+, 🟢), ale wszystkie są już zaimplementowane:

### [KROK_WYKONANY] D2 — Streaming postępu ingestu

**Plan:** Sprint 6, linia ~731 — `SSE endpoint /ingest/progress`  
**Stan rzeczywisty:** Zaimplementowane:
- `backend_app/services/progress_service.py` — `stream_progress()`, SSE generator
- `backend_app/routes/ingest.py:444` — `GET /ingest/progress/{task_id}`

---

### ~~[KROK_WYKONANY] F4 — Session-aware chat z persistent history~~ ✅ ZGODNO Z PLANEM

**Sekcja:** Sprint 6, linia ~742 — sessions table w SQLite, GET/POST /sessions  
**Stan rzeczywisty:** Zaimplementowane w całości — `backend_app/routes/sessions.py` z pełnym CRUD, wiadomościami, eksportem, importem, wyszukiwaniem, bulk-delete, export-all, cleanup-old i więcej.  
**Plan master:** Oznaczony ✅ DONE (linia 740).

---

### ~~[KROK_WYKONANY] H2 — Watcher zintegrowany z backendem~~ ✅ ZGODNO Z PLANEM

**Sekcja:** Sprint 6, linia ~754  
**Stan rzeczywisty:** `backend_app/services/watcher_service.py` istnieje. `GET /v1/watcher/status` w `admin.py:503`.  
**Plan master:** Oznaczony ✅ DONE (linia 750).

---

### ~~[KROK_WYKONANY] W2 — MCP Compatibility~~ ✅ ZGODNO Z PLANEM

**Sekcja:** Sprint 6, linia ~766  
**Stan rzeczywisty:** `backend_app/routes/mcp.py` istnieje. `GET /mcp` zwraca endpoint, protokół, listę narzędzi.  
**Plan master:** Oznaczony ✅ DONE (linia 761).

---

### ~~[KROK_WYKONANY] W5 — Batch Processing~~ ✅ ZGODNO Z PLANEM

**Sekcja:** Sprint 6, linia ~793  
**Stan rzeczywisty:** `backend_app/services/batch_service.py` istnieje z kolejką priorytetową, retry logic, batch embeddingiem. Endpointy: `/v1/batch/stats`, `/v1/batch/enqueue`, `/v1/batch/clear`, `/v1/batch/history`.  
**Plan master:** Oznaczony ✅ DONE (linia 783).

---

### ~~[KROK_WYKONANY] B5 — Answer Verification~~ ✅ ZGODNO Z PLANEM

**Sekcja:** Sprint 6, linia ~704 (🟢)  
**Stan rzeczywisty:** `backend_app/services/verification_service.py` istnieje. Flaga `KLIMTECH_ANSWER_VERIFICATION=false` (domyślnie wyłączone, zgodnie z planem).  
**Plan master:** Oznaczony ✅ DONE (linia 704).

---

### ~~[KROK_WYKONANY] C5 — Late Chunking~~ ❌ NIE ZAIMPLEMENTOWANY

**Sekcja:** Sprint 6, linia ~717 (🟢) — "wymaga dużo VRAM, rozważ jako opcjonalny"  
**Stan rzeczywisty (zweryfikowano 2026-04-07):** C5 Late Chunking **NIE jest zaimplementowany**. Zero odniesień do "late chunking", "jina", "LATE_CHUNK" w całym `backend_app/`. Aktualny pipeline ingest używa tradycyjnego `parse → chunk → embed` (e5-large). ColPali istnieje ale to osobna funkcja (visual late interaction), nie Late Chunking (Jina).
**Powaga:** Nie blokuje działania. Funkcja oznaczona jako 🟢 (nice-to-have). Wymaga modelu Jina Embeddings v3 i dodatkowej logiki w pipeline.

---

## SPRINT 0–5 UKOŃCZONE — NIEOZNACZONE W PLANIE

Wszystkie funkcje z Sprint 0–5 są zaimplementowane, ale plan nie zawiera żadnych oznaczeń ✅ przy ukończonych elementach. Poniżej lista z potwierdzeniem istnienia kodu:

| Funkcja | Plik | Status |
|---------|------|--------|
| W3 Vector Cache | `file_registry.py` (content_hash) + `ingest_service.py` | ✅ DONE |
| A3 validate_config() | `config.py:184` | ✅ DONE |
| A1a chat_service | `services/chat_service.py` | ✅ DONE (częściowe — chat.py za duże) |
| A1b ingest refactor | `services/ingest_service.py`, `parser_service.py`, `dedup_service.py`, `nextcloud_service.py` | ✅ DONE (częściowe — ingest.py za duże) |
| D1 SSE Streaming | `services/streaming_service.py` + `routes/chat.py` | ✅ DONE |
| F1 Streaming UI | `static/index.html` | ✅ DONE |
| B1 Smart Router | `services/router_service.py` | ✅ DONE |
| B2 Hybrid Search | `services/hybrid_search_service.py` | ✅ DONE |
| B3 Reranking | `services/reranker_service.py` | ✅ DONE |
| C1 Layout Analysis | `services/layout_service.py` | ✅ DONE |
| C6 Metadata | `services/metadata_service.py` | ✅ DONE |
| C4 Enrichment | `services/enrichment_service.py` | ✅ DONE |
| B7 /v1/chunks | `routes/chunks.py` | ✅ DONE |
| E1 DELETE /v1/ingest | `routes/admin.py:201` | ✅ DONE |
| E2 /v1/ingest/list | `routes/admin.py:266` | ✅ DONE |
| H1 IngestResponse | `models/schemas.py:119` | ✅ DONE |
| B6 Semantic Cache | `services/cache_service.py` + `chat_service.py:78` | ✅ DONE |
| B4 Query Decomposition | `services/query_decomposition_service.py` | ✅ DONE |
| C2 Klasyfikacja VLM | `ingest/image_handler.py:83` (classify_image_type) | ✅ DONE |
| C3 Table Structure | `services/table_service.py` | ✅ DONE |
| W1 Workspaces | `routes/workspaces.py` | ✅ DONE |
| E3 Multi-collection | `routes/collections.py` | ✅ DONE |
| A2 Profile YAML | `settings.yaml`, `settings-server.yaml`, `settings-dev.yaml` + `config.py:236` | ✅ DONE (brak settings-ingest.yaml) |
| G1 Testy | `tests/test_admin.py`, `test_api.py`, `test_config.py`, `test_security.py`, `test_sessions.py` | ⚠️ CZĘŚCIOWE (brak conftest.py, test_chat, test_ingest, test_chunks) |
| G3 health_check.py | `scripts/health_check.py` | ✅ DONE |
| G2 Makefile | `Makefile` | ✅ DONE |
| G4 Swagger/OpenAPI | `main.py:96` + tagi w admin.py, sessions.py, chat.py | ✅ DONE |

---

## NIEAKTUALNY HARMONOGRAM

**Sekcja:** Podsumowanie — Harmonogram, linia ~820  
**Plan mówi:** Sprint 0 = tydzień 0, Sprint 5 = tydzień 9–10, Sprint 6 = tydzień 11+  
**Stan rzeczywisty:** Praktycznie cały Sprint 0–5 ukończony PLUS większość Sprint 6 (D2, F4, H2, W2, W5, B5). Harmonogram całkowicie nieaktualny.  
**Powaga:** INFO — plan był realistycznym szacunkiem, realizacja poszła szybciej dzięki iteracyjnemu procesowi z lokalnymi modelami.

---

## ELEMENTY PLANU NIE ZREALIZOWANE (rzeczywiście pozostałe)

| Element | Powód | Priorytet | Status 2026-04-07 |
|---------|-------|-----------|-------------------|
| A1a/A1b dokończenie | `chat.py` = 277 linii (cel: ~80), `ingest_service.py` = 249 linii (cel: ~120) | 🟡 | ⚠️ CZĘŚCIOWO (ingest_service znacznie zmniejszony z 548→249) |
| A1c Components layer | `backend_app/components/` nie istnieje | 🟢 Sprint 6 | ❌ NIE ZROBIONE |
| ~~`settings-ingest.yaml`~~ | ~~Brak profilu dla trybu ingest~~ | 🟢 | ✅ NAPRAWIONE |
| ~~`tests/conftest.py`~~ | ~~Brak wspólnych fixtures~~ | 🟡 | ✅ NAPRAWIONE |
| ~~`tests/test_chat.py`~~ | ~~Brak testów czatu~~ | 🟡 | ✅ NAPRAWIONE |
| ~~`tests/test_ingest.py`~~ | ~~Brak testów ingestu~~ | 🟡 | ✅ NAPRAWIONE |
| ~~`tests/test_chunks.py`~~ | ~~Brak testów /v1/chunks~~ | 🟢 | ✅ NAPRAWIONE |
| C5 Late Chunking | Nie zaimplementowane (zero odniesień do Jina/late chunking w kodzie) | 🟢 | ❌ NIE ZROBIONE |
| W4 Chat Widget | ~~`klimtech-widget.js` nie istnieje~~ → ISTNIEJE (130 linii) | 🟢 Sprint 6 | ✅ NAPRAWIONE |
| W6 Agent Builder | Nie wdrożone | ⚪ Sprint 6 | ❌ NIE ZROBIONE |
| W1 krok 5 — `workspace_id` w `file_registry.db` | Kolumna workspace_id nie istnieje w file_registry | 🟡 | ❌ NIE ZROBIONE |
| F2 — kliknięcie źródła → podgląd chunku | Brak obsługi kliknięcia w UI | 🟢 | ❌ NIE ZROBIONE |

---

*Analiza oparta na odczycie kodu z 2026-04-07. Stan kodu może być nowszy niż plan (v1.0 z 2026-03-30).*
*Aktualizacja 2026-04-07: Zweryfikowano błędy 9-14, naprawiono status 7 elementów NIEZREALIZOWANYCH.*
