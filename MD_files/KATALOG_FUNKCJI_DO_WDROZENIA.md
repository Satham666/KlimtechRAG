# Katalog funkcji do wdrożenia w KlimtechRAG

**Źródła:** PrivateGPT, LocalGPT, h2oGPT, RAGFlow, Quivr, Danswer, DocQuery  
**Cel:** Lista konkretnych funkcji do wyboru — każda niezależna, atomowa, z opisem co daje i skąd pochodzi.

---

## LEGENDA PRIORYTETÓW

- 🔴 **Krytyczne** — bezpośrednio poprawia jakość odpowiedzi lub stabilność systemu
- 🟡 **Wartościowe** — poprawia UX, ułatwia rozwój, dodaje nową funkcjonalność
- 🟢 **Nice-to-have** — usprawnienie, ale system działa bez tego
- ⚪ **Na przyszłość** — wymaga dużo pracy lub zmiany architektury

---

## A. ARCHITEKTURA I STRUKTURA KODU

### A1. Podział Router → Service → Component 🔴
**Źródło:** PrivateGPT, Quivr  
**Problem w KlimtechRAG:** `chat.py` (500 linii) i `ingest.py` (767 linii) mieszają routing HTTP z logiką biznesową, budowaniem promptu i obsługą cache.  
**Co wdrożyć:**
- `routes/chat.py` → tylko FastAPI routing (~80 linii)
- `services/chat_service.py` → orkiestracja: cache → retrieval → prompt → LLM
- `services/retrieval_service.py` → RAG retrieval (e5 + ColPali + web)
- `services/ingest_service.py` → orkiestracja ingestu
- `services/parser_service.py` → ekstrakcja tekstu z PDF/DOCX/TXT
- `components/` → singletony z lazy loading (LLM, embedding, Qdrant, Whisper)

**Korzyść:** Łatwiejsze testowanie, debugowanie, wymiana komponentów. Zmiana modelu LLM = zmiana 1 pliku zamiast 5.

---

### A2. Profile konfiguracyjne YAML 🟡
**Źródło:** PrivateGPT (`settings-local.yaml`, `settings-ollama.yaml`)  
**Problem w KlimtechRAG:** Jeden `.env` + hardcoded wartości w `config.py`. Przełączenie trybu (dev/server/ingest) wymaga ręcznej edycji.  
**Co wdrożyć:**
- `settings.yaml` — bazowa konfiguracja
- `settings-server.yaml` — produkcja (GPU, Bielik-11B)
- `settings-ingest.yaml` — tryb ingestowania (GPU embedding, bez LLM)
- `settings-dev.yaml` — laptop (CPU, mały model)
- Env var `KLIMTECH_PROFILES=server` przełącza profil

**Korzyść:** Jedno polecenie zmienia całą konfigurację. Brak ryzyka zapomnienia o jakimś ustawieniu.

---

### A3. Walidacja konfiguracji na starcie 🟡
**Źródło:** PrivateGPT, LocalGPT (`system_health_check.py`)  
**Problem w KlimtechRAG:** Backend startuje i dopiero pada gdy brakuje Qdrant lub katalogu modeli.  
**Co wdrożyć:**
- Funkcja `validate_config()` w `lifespan()` main.py
- Sprawdza: Qdrant dostępny? Katalog modeli istnieje? Porty wolne? .env istnieje?
- Czytelny komunikat błędu zamiast stack trace

**Korzyść:** Natychmiastowa informacja co jest nie tak, zamiast debugowania logów.

---

## B. RETRIEVAL I RAG

### B1. Smart Router — automatyczny wybór RAG vs Direct LLM 🔴
**Źródło:** LocalGPT  
**Problem w KlimtechRAG:** Użytkownik musi ręcznie włączać RAG przyciskiem globe. Zapytanie "hej bielik" z RAG = 78000 tokenów i crash.  
**Co wdrożyć:**
- Lekki klasyfikator (LLM lub heurystyka) decyduje czy pytanie wymaga RAG
- Heurystyka: jeśli pytanie < 20 słów i nie zawiera słów kluczowych dokumentów → Direct LLM
- Jeśli pytanie odwołuje się do dokumentów/danych/raportów → RAG
- Użytkownik nadal może wymusić RAG przyciskiem globe

**Korzyść:** Czat działa natychmiast dla prostych pytań, RAG włącza się tylko gdy potrzebny. Zero crashy z przekroczonym kontekstem.

---

### B2. Hybrid Search (dense + sparse/BM25) 🔴
**Źródło:** LocalGPT, RAGFlow  
**Problem w KlimtechRAG:** Tylko dense vector search (e5-large). Brak keyword matching — pytanie z dokładną nazwą pliku lub terminem technicznym może nie trafić.  
**Co wdrożyć:**
- BM25 index obok Qdrant vector search
- Hybrid scoring: `final_score = 0.7 * dense_score + 0.3 * bm25_score`
- Konfigurowalny weight w settings.yaml

**Korzyść:** Lepsze wyniki dla zapytań z konkretnymi terminami, nazwami, numerami. Dense search łapie semantykę, BM25 łapie exact match.

---

### B3. Reranking po retrieval 🟡
**Źródło:** LocalGPT (ColBERT reranker), RAGFlow  
**Problem w KlimtechRAG:** Top-5 chunków z Qdrant idzie prosto do promptu. Kolejność oparta tylko na cosine similarity.  
**Co wdrożyć:**
- Po retrieval top-20 → reranker (cross-encoder) → top-5 do promptu
- Model: `BAAI/bge-reranker-base` (lekki, ~400MB) lub ColBERT
- Lazy loading — ładowany tylko gdy RAG aktywny

**Korzyść:** Znacząco lepsza jakość kontekstu w promptu. Reranker rozumie relację pytanie↔dokument lepiej niż cosine similarity.

---

### B4. Query Decomposition — rozbijanie złożonych pytań 🟡
**Źródło:** LocalGPT  
**Problem w KlimtechRAG:** Złożone pytanie ("Porównaj metodologię A z B i oceń skuteczność") idzie jako jedno zapytanie do Qdrant.  
**Co wdrożyć:**
- LLM rozbija pytanie na 2-3 sub-pytania
- Każde sub-pytanie → osobny retrieval → chunki
- Merge wyników → budowanie odpowiedzi z kontekstem ze wszystkich sub-zapytań

**Korzyść:** Lepsze odpowiedzi na złożone, wieloczęściowe pytania.

---

### B5. Answer Verification — weryfikacja odpowiedzi 🟢
**Źródło:** LocalGPT  
**Problem w KlimtechRAG:** Odpowiedź LLM nie jest weryfikowana — może halucynować.  
**Co wdrożyć:**
- Po wygenerowaniu odpowiedzi → drugi pass LLM sprawdza czy odpowiedź jest spójna z kontekstem
- Jeśli niespójna → oznacz jako "niska pewność" w UI
- Opcjonalne — włączane w settings.yaml

**Korzyść:** Zmniejsza ryzyko halucynacji. Użytkownik wie kiedy odpowiedź jest pewna.

---

### B6. Semantic Cache z similarity matching 🟡
**Źródło:** LocalGPT  
**Problem w KlimtechRAG:** Cache w `chat.py` jest prosty dict z exact match na query string. "Co to RAG?" i "Czym jest RAG?" to dwa różne klucze.  
**Co wdrożyć:**
- Cache przechowuje embedding pytania + odpowiedź
- Nowe pytanie → embedding → cosine similarity z cached pytaniami
- Jeśli similarity > 0.92 → zwróć cached odpowiedź
- TTL (1h) jak teraz + limit rozmiaru

**Korzyść:** Cache trafia znacznie częściej. Oszczędność VRAM i czasu — nie trzeba odpytywać LLM dla sparafrazowanych pytań.

---

### B7. Endpoint `/v1/chunks` — Low-level retrieval bez LLM 🟡
**Źródło:** PrivateGPT  
**Problem w KlimtechRAG:** Brak sposobu na sprawdzenie CO retriever zwraca bez generowania odpowiedzi LLM.  
**Co wdrożyć:**
```
POST /v1/chunks
{"text": "pytanie", "limit": 10, "context_filter": {"source": "raport.pdf"}}
→ zwraca chunki z score, source, content (BEZ wysyłania do LLM)
```

**Korzyść:** Debugowanie jakości RAG, budowanie custom pipeline z frontendu, inspekcja kontekstu.

---

## C. PARSOWANIE DOKUMENTÓW

### C1. Layout Analysis — rozpoznawanie struktury dokumentu 🔴
**Źródło:** RAGFlow (DeepDoc)  
**Problem w KlimtechRAG:** `pdftotext -layout` + docling OCR. Brak rozpoznawania struktury — tabela, diagram, nagłówek, stopka traktowane jednakowo.  
**Co wdrożyć:**
- Model layout recognition (np. z RAGFlow DeepDoc lub LayoutLMv3)
- Klasyfikacja regionów strony: tekst, tabela, obraz, nagłówek, stopka
- Tabele → osobny parser (Table Structure Recognition)
- Obrazy → VLM pipeline (już masz vlm_prompts.py)
- Nagłówki/stopki → metadane, nie treść chunku

**Korzyść:** Znacznie lepsza jakość ekstrakcji. Tabela nie jest rozbijana na bezsensowne chunki tekstu. Stopki nie zanieczyszczają kontekstu.

---

### C2. Automatyczna klasyfikacja typu treści dla VLM 🟡
**Źródło:** RAGFlow, DocQuery  
**Problem w KlimtechRAG:** `vlm_prompts.py` ma 8 wariantów (DIAGRAM, CHART, TABLE...) ale `image_handler.py` używa prostej heurystyki (aspect ratio + extension).  
**Co wdrożyć:**
- Klasyfikator obrazu: lekki model CNN lub heurystyka oparta na:
  - Ilość tekstu OCR na obrazie (dużo tekstu → screenshot/table)
  - Proporcje kolorów (mało kolorów → diagram, dużo → zdjęcie)
  - Aspect ratio + rozmiar
- Wynik klasyfikacji → odpowiedni prompt z `vlm_prompts.py`

**Korzyść:** Automatyczny dobór promptu VLM zamiast generic "opisz obraz". Lepsze opisy obrazów w RAG.

---

### C3. Table Structure Recognition (TSR) 🟡
**Źródło:** RAGFlow (DeepDoc)  
**Problem w KlimtechRAG:** Tabele z PDF parsowane jako surowy tekst — tracą strukturę.  
**Co wdrożyć:**
- Rozpoznawanie tabeli → konwersja do Markdown table
- Markdown table przechowywany jako chunk z `type: table` w metadanych
- Opcja: auto-rotacja tabel (RAGFlow wykrywa obrócone tabele w skanach)

**Korzyść:** Pytania o dane z tabel dają precyzyjne odpowiedzi. "Jaka jest cena produktu X?" — LLM widzi strukturę tabeli, nie chaotyczny tekst.

---

### C4. Contextual Enrichment — wzbogacanie chunków kontekstem 🟡
**Źródło:** LocalGPT (inspirowane Anthropic Contextual Retrieval)  
**Problem w KlimtechRAG:** Chunk to 200 słów bez kontekstu. Chunk "Wartość wynosi 45%" nie mówi o czym jest.  
**Co wdrożyć:**
- Przy ingeście: LLM generuje krótki opis kontekstu dla każdego chunku
- Format: `"Ten chunk dotyczy rozdziału 3 dokumentu X, opisuje wyniki badań temperatury..."`
- Opis + chunk przechowywane razem w Qdrant

**Korzyść:** Retrieval lepiej trafia — embedding chunku zawiera kontekst dokumentu. Duży skok jakości odpowiedzi.

---

### C5. Late Chunking — chunking po embeddingu 🟢
**Źródło:** LocalGPT (inspirowane Jina AI)  
**Problem w KlimtechRAG:** Chunking → embedding. Każdy chunk traci kontekst sąsiednich fragmentów.  
**Co wdrożyć:**
- Embedding CAŁEGO dokumentu (long-context model)
- Chunking embeddingów po fakcie — zachowuje kontekst
- Wymaga modelu z dużym kontekstem (np. Jina Embeddings v3)

**Korzyść:** Chunki zachowują kontekst dokumentu. Znacznie lepszy retrieval dla dokumentów z long-range dependencies.

**Uwaga:** Wymaga dużo VRAM dla długich dokumentów. Rozważ jako opcjonalny tryb.

---

### C6. Metadata extraction przy ingeście 🟡
**Źródło:** PrivateGPT, Danswer  
**Problem w KlimtechRAG:** Chunk ma tylko `source` i `type`. Brak tytułu, autora, daty, języka.  
**Co wdrożyć:**
- Ekstrakcja z PDF: tytuł, autor, data utworzenia, liczba stron (PyMuPDF metadata)
- Detekcja języka (langdetect lub heurystyka)
- `chunk_index` / `total_chunks` — pozycja chunku w dokumencie
- Wszystko w `payload` Qdrant

**Korzyść:** Filtrowanie retrieval po metadanych (np. "szukaj tylko w dokumentach z 2025"). Lepsza atrybucja źródeł w odpowiedzi.

---

## D. STREAMING I RESPONSYWNOŚĆ

### D1. SSE Streaming odpowiedzi (token-by-token) 🔴
**Źródło:** PrivateGPT, Danswer, LocalGPT  
**Problem w KlimtechRAG:** `stream: bool = False` w schema istnieje, ale streaming NIE jest zaimplementowany. Użytkownik czeka 10-30s na pełną odpowiedź.  
**Co wdrożyć:**
- Endpoint `/v1/chat/completions` z `stream: true`
- Backend: `httpx.AsyncClient` z `stream=True` do llama-server
- Response: Server-Sent Events w formacie OpenAI
- UI: `fetch` z `body.getReader()` renderuje tokeny incrementalnie

**Korzyść:** Odpowiedź widoczna od pierwszego tokenu. UX jak w ChatGPT zamiast czekania na pełną odpowiedź.

---

### D2. Streaming postępu ingestu (per-chunk) 🟢
**Źródło:** RAGFlow, LocalGPT  
**Problem w KlimtechRAG:** Progress panel polluje `/model/progress-log` co 600ms — ale ingest nie raportuje postępu per-chunk.  
**Co wdrożyć:**
- SSE endpoint `/ingest/progress` — raportuje: parsowanie → chunking → embedding → zapis
- Każdy etap z procentem (np. "Embedding chunk 15/45")
- UI: progress bar z dokładnym statusem

**Korzyść:** Użytkownik widzi co się dzieje podczas indeksowania dużego PDF (300 stron).

---

## E. ZARZĄDZANIE DOKUMENTAMI I KOLEKCJAMI

### E1. Endpoint `DELETE /v1/ingest/{doc_id}` — usuwanie z RAG 🟡
**Źródło:** PrivateGPT, Quivr  
**Problem w KlimtechRAG:** `DELETE /documents` wymaga znajomości filtrów Qdrant. Brak prostego "usuń ten dokument ze wszystkimi chunkami".  
**Co wdrożyć:**
```
DELETE /v1/ingest/{doc_id}
→ Usuwa chunki z Qdrant (filter: meta.source == doc_id)
→ Aktualizuje file_registry.db
→ Opcjonalnie: usuwa plik z Nextcloud (?delete_file=true)
```

**Korzyść:** Zarządzanie bazą wiedzy z UI — usuwanie nieaktualnych dokumentów bez SQLki.

---

### E2. Endpoint `/v1/ingest/list` z metadanymi 🟡
**Źródło:** PrivateGPT, Danswer  
**Problem w KlimtechRAG:** `/files/list` zwraca surowe dane z SQLite.  
**Co wdrożyć:**
- Standaryzowany response w formacie OpenAI-like
- Filtrowanie: status, extension, source, data
- Metadane: doc_id, chunks_count, embedding_model, collection, indexed_at

**Korzyść:** Czysty endpoint do budowania panelu zarządzania dokumentami w UI.

---

### E3. Multi-collection management w API 🟢
**Źródło:** Quivr  
**Problem w KlimtechRAG:** Dwie kolekcje (`klimtech_docs`, `klimtech_colpali`) zarządzane ręcznie. Brak API do tworzenia/usuwania kolekcji.  
**Co wdrożyć:**
- `POST /collections` — utwórz nową kolekcję z parametrami (dim, distance, multi_vector)
- `GET /collections` — lista kolekcji z stats
- `DELETE /collections/{name}` — usuń kolekcję
- W `/v1/chat/completions` — parametr `collection` do wyboru źródła

**Korzyść:** Możliwość tworzenia tematycznych baz wiedzy (np. "medyczne", "techniczne", "HR") i przeszukiwania wybranej.

---

## F. UI I UX

### F1. Streaming w czacie (token-by-token rendering) 🔴
**Źródło:** Danswer, LocalGPT  
**Zależność:** Wymaga D1 (SSE streaming w backendzie)  
**Co wdrożyć:**
- `send()` w `index.html` używa `fetch` z `body.getReader()` dla streaming
- Tokeny renderowane incrementalnie w bańce czatu
- Animacja typing oparta na realnych tokenach

**Korzyść:** Natychmiastowy feedback zamiast 30s czekania.

---

### F2. Podgląd źródeł w odpowiedzi czatu 🟡
**Źródło:** PrivateGPT, Danswer, LocalGPT  
**Problem w KlimtechRAG:** Backend zwraca `sources` w response ale UI ich nie wyświetla.  
**Co wdrożyć:**
- Pod odpowiedzią AI → klikalna lista źródeł (nazwa pliku, strona, score)
- Kliknięcie źródła → podgląd chunku (wywołanie `/v1/chunks`)
- Ikona 📎 z liczbą źródeł

**Korzyść:** Użytkownik wie SKĄD pochodzi odpowiedź. Może zweryfikować. Buduje zaufanie do systemu.

---

### F3. Panel zarządzania dokumentami RAG 🟡
**Źródło:** PrivateGPT (Gradio), LocalGPT, Quivr  
**Problem w KlimtechRAG:** "Ostatnie pliki" pokazuje listę, ale brak zarządzania.  
**Co wdrożyć:**
- Nowa karta w sidebar: "Dokumenty RAG"
- Tabela: source, chunks, status, data, rozmiar, embedding model
- Przycisk "Usuń z RAG" → `DELETE /v1/ingest/{doc_id}`
- Przycisk "Re-indeksuj" → `POST /ingest_path`
- Filtrowanie po statusie

**Korzyść:** Pełne zarządzanie bazą wiedzy bez terminala.

---

### F4. Session-aware chat z persistent history 🟢
**Źródło:** LocalGPT, Danswer  
**Problem w KlimtechRAG:** Historia w `localStorage` — znika po wyczyszczeniu przeglądarki. Brak kontekstu rozmowy w kolejnych wiadomościach.  
**Co wdrożyć:**
- Backend: `sessions` table w SQLite (session_id, messages JSON, created_at)
- Endpoint: `GET/POST /sessions`, `GET /sessions/{id}/messages`
- Chat wysyła historię rozmowy (ostatnie N wiadomości) w request

**Korzyść:** Historia przetrwa wyczyszczenie przeglądarki. LLM ma kontekst rozmowy — lepsze follow-up pytania.

---

## G. TESTY I DEVOPS

### G1. Struktura testów z mockami 🟡
**Źródło:** PrivateGPT (`tests/`), LocalGPT  
**Problem w KlimtechRAG:** Zero testów.  
**Co wdrożyć:**
```
tests/
├── conftest.py          — fixtures (TestClient, mock Qdrant, mock LLM)
├── test_health.py       — smoke tests
├── test_chat.py         — chat z mock LLM
├── test_ingest.py       — ingest z mock Qdrant
├── test_chunks.py       — /v1/chunks
├── test_security.py     — auth, rate limiting, path traversal
```

**Korzyść:** Każda zmiana kodu jest testowalna. Regresja wykrywana natychmiast.

---

### G2. Makefile z komendami 🟢
**Źródło:** PrivateGPT, LocalGPT  
**Co wdrożyć:**
```makefile
run:      python3 -m backend_app.main
test:     python3 -m pytest tests/ -v
check:    bash scripts/check_project.sh
lint:     python3 -m ruff check backend_app/
start:    python3 start_klimtech_v3.py
stop:     python3 stop_klimtech.py
health:   curl -sk https://192.168.31.70:8443/health
```

---

### G3. System health check (diagnostyka) 🟡
**Źródło:** LocalGPT (`system_health_check.py`)  
**Problem w KlimtechRAG:** `check_project.sh` sprawdza składnię ale nie runtime.  
**Co wdrożyć:**
- Skrypt sprawdzający: Python version, venv, porty, Qdrant, llama-server, Nextcloud, GPU
- Kolorowy output: ✅ OK / ❌ FAIL / ⚠️ WARN
- Uruchamiany przed startem systemu

**Korzyść:** Natychmiastowa diagnoza "co nie działa" — zamiast debugowania logów.

---

### G4. Swagger/OpenAPI z pełnymi opisami 🟢
**Źródło:** PrivateGPT  
**Problem w KlimtechRAG:** FastAPI `/docs` istnieje, ale bez opisów endpointów.  
**Co wdrożyć:**
- `summary`, `description`, `tags`, `responses` na KAŻDYM endpoint
- Przykładowe request/response body
- `app = FastAPI(title="KlimtechRAG API", description="...", version="7.4")`

---

## H. BEZPIECZEŃSTWO I STABILNOŚĆ

### H1. Standaryzacja response format (OpenAI-compatible) 🟡
**Źródło:** PrivateGPT, Danswer  
**Problem w KlimtechRAG:** Każdy endpoint zwraca inny format. `/upload`, `/ingest_path`, `/ingest_all` — różne klucze.  
**Co wdrożyć:**
- Jednolity format dla WSZYSTKICH endpointów ingest
- Format zgodny z OpenAI API standard
- `object`, `data`, `model`, `usage` w każdym response

**Korzyść:** Łatwiejsza integracja z Nextcloud, n8n, dowolnym klientem OpenAI-compatible.

---

### H2. Watcher zintegrowany z backendem 🟢
**Źródło:** PrivateGPT (document folder watch)  
**Problem w KlimtechRAG:** `watch_nextcloud.py` to osobny proces — musi być uruchamiany ręcznie.  
**Co wdrożyć:**
- Ustawienie `watcher.enabled: true` w settings.yaml
- W `lifespan()` uruchom watcher jako asyncio background task
- Nie wymaga osobnego procesu

**Korzyść:** Jedna komenda `python3 start_klimtech_v3.py` startuje WSZYSTKO.

---

## MACIERZ: CO SKĄD WZIĄĆ

| # | Funkcja | PrivateGPT | LocalGPT | h2oGPT | RAGFlow | Quivr | Danswer | DocQuery | Priorytet |
|---|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| A1 | Router→Service→Component | ✅ | | | | ✅ | | | 🔴 |
| A2 | Profile YAML | ✅ | | | | | | | 🟡 |
| A3 | Walidacja config na starcie | ✅ | ✅ | | | | | | 🟡 |
| B1 | Smart Router (RAG vs Direct) | | ✅ | ✅ | | | | | 🔴 |
| B2 | Hybrid Search (dense+BM25) | | ✅ | | ✅ | | | | 🔴 |
| B3 | Reranking | | ✅ | | ✅ | | | | 🟡 |
| B4 | Query Decomposition | | ✅ | | | | | | 🟡 |
| B5 | Answer Verification | | ✅ | | | | | | 🟢 |
| B6 | Semantic Cache | | ✅ | | | | | | 🟡 |
| B7 | Endpoint /v1/chunks | ✅ | | | | | ✅ | | 🟡 |
| C1 | Layout Analysis | | | | ✅ | | | ✅ | 🔴 |
| C2 | Klasyfikacja obrazów dla VLM | | | | ✅ | | | ✅ | 🟡 |
| C3 | Table Structure Recognition | | | | ✅ | | | | 🟡 |
| C4 | Contextual Enrichment | | ✅ | | | | | | 🟡 |
| C5 | Late Chunking | | ✅ | | | | | | 🟢 |
| C6 | Metadata extraction | ✅ | | | | | ✅ | | 🟡 |
| D1 | SSE Streaming | ✅ | ✅ | ✅ | | | ✅ | | 🔴 |
| D2 | Streaming postępu ingestu | | ✅ | | ✅ | | | | 🟢 |
| E1 | DELETE /v1/ingest/{doc_id} | ✅ | | | | ✅ | | | 🟡 |
| E2 | /v1/ingest/list + metadane | ✅ | | | | | ✅ | | 🟡 |
| E3 | Multi-collection management | | | | | ✅ | | | 🟢 |
| F1 | Streaming w UI | | ✅ | | | | ✅ | | 🔴 |
| F2 | Podgląd źródeł | ✅ | ✅ | | | | ✅ | | 🟡 |
| F3 | Panel dokumentów RAG | ✅ | ✅ | | | ✅ | | | 🟡 |
| F4 | Session history backend | | ✅ | | | | ✅ | | 🟢 |
| G1 | Testy z mockami | ✅ | | | | | | | 🟡 |
| G2 | Makefile | ✅ | | | | | | | 🟢 |
| G3 | System health check | | ✅ | | | | | | 🟡 |
| G4 | Swagger docs | ✅ | | | | | | | 🟢 |
| H1 | Standaryzacja response | ✅ | | | | | ✅ | | 🟡 |
| H2 | Watcher w backendzie | ✅ | | | | | | | 🟢 |

---

## SUGEROWANA KOLEJNOŚĆ WDRAŻANIA

### Sprint 1 — Fundamenty (krytyczne)
1. **D1** — SSE Streaming (backend)
2. **F1** — Streaming w UI
3. **B1** — Smart Router (RAG vs Direct LLM)
4. **A1** — Restrukturyzacja chat.py i ingest.py

### Sprint 2 — Jakość RAG
5. **B2** — Hybrid Search (dense + BM25)
6. **C1** — Layout Analysis dla PDF
7. **B3** — Reranking po retrieval
8. **C6** — Metadata extraction

### Sprint 3 — UX i zarządzanie
9. **B7** — Endpoint /v1/chunks
10. **E1** — DELETE /v1/ingest/{doc_id}
11. **F2** — Podgląd źródeł w czacie
12. **F3** — Panel zarządzania dokumentami

### Sprint 4 — Zaawansowane
13. **B6** — Semantic Cache
14. **C4** — Contextual Enrichment
15. **B4** — Query Decomposition
16. **C3** — Table Structure Recognition

### Sprint 5 — DevOps i stabilność
17. **G1** — Testy
18. **A2** — Profile YAML
19. **G3** — System health check
20. **A3** — Walidacja config

---

*Utworzono: 2026-03-28*
