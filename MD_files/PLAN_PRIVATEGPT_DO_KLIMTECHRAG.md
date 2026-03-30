# Plan wdrożenia wzorców PrivateGPT do KlimtechRAG

**Cel:** Wyodrębnienie najlepszych rozwiązań architektonicznych i funkcjonalnych z PrivateGPT (57k★) i zaadaptowanie ich do KlimtechRAG — bez zmiany frameworka RAG (zostajemy na Haystack, nie LlamaIndex).

**Zasada:** Każdy punkt to osobne, atomowe zadanie. Można wdrażać niezależnie, w dowolnej kolejności.

---

## FAZA 1 — RESTRUKTURYZACJA KODU (architektura Router → Service → Component)

PrivateGPT stosuje czysty podział trójwarstwowy:
- `router.py` — TYLKO FastAPI, walidacja, HTTP
- `service.py` — logika biznesowa, orkiestracja
- `component.py` — konkretne implementacje (LLM, embedding, vector store)

KlimtechRAG ma teraz wszystko w jednym pliku (np. `chat.py` = 500 linii z routingiem, RAG retrievalem, prompt buildingiem i cache).

### 1.1 Wydzielenie warstwy Service z `routes/chat.py`

**Stan obecny:** `routes/chat.py` (500 linii) zawiera:
- routing FastAPI
- cache z TTL
- RAG retrieval (e5-large + ColPali)
- Web Search (DuckDuckGo)
- prompt building (RAG_PROMPT + kontekst + pytanie)
- wywołanie LLM
- tool calling loop

**Plan:**
```
PRZED:
  routes/chat.py (500 linii — wszystko)

PO:
  routes/chat.py         (~80 linii — TYLKO routing, walidacja, HTTP response)
  services/chat_service.py  (~150 linii — orkiestracja: cache → retrieval → prompt → LLM)
  services/retrieval_service.py  (~100 linii — RAG retrieval: e5-large, ColPali, web search)
  services/prompt_service.py     (~50 linii — budowanie promptu z kontekstem)
  services/cache_service.py      (~40 linii — cache z TTL, wydzielony singleton)
```

**Kroki atomowe:**
1. Utwórz `backend_app/services/cache_service.py` — przenieś `_answer_cache`, `get_cached()`, `set_cached()`, `clear_cache()`
2. Utwórz `backend_app/services/retrieval_service.py` — przenieś logikę retrieval (blok `if request.use_rag` + `if request.web_search`)
3. Utwórz `backend_app/services/prompt_service.py` — przenieś `RAG_PROMPT` i budowanie `full_prompt`
4. Utwórz `backend_app/services/chat_service.py` — orkiestracja: cache → retrieval → prompt → LLM → response
5. Refaktoryzuj `routes/chat.py` — zamień ciało endpointów na wywołania `chat_service`
6. Zaktualizuj importy w `services/__init__.py`
7. Test: `curl -sk -X POST https://192.168.31.70:8443/v1/chat/completions -d '{"messages":[{"role":"user","content":"hej"}]}'`

---

### 1.2 Wydzielenie warstwy Service z `routes/ingest.py`

**Stan obecny:** `routes/ingest.py` (767 linii) zawiera:
- routing FastAPI (6 endpointów)
- parsowanie PDF (pdftotext + docling OCR)
- parsowanie DOCX/TXT (mammoth)
- text cleaning
- hash deduplication
- zapis do Nextcloud + occ rescan
- background indexing
- ColPali routing

**Plan:**
```
PRZED:
  routes/ingest.py (767 linii — wszystko)

PO:
  routes/ingest.py            (~120 linii — TYLKO routing, upload handling)
  services/parser_service.py  (~100 linii — ekstrakcja tekstu: PDF, DOCX, TXT, kod)
  services/ingest_service.py  (~120 linii — orkiestracja: parse → chunk → embed → store)
  services/nextcloud_service.py (~60 linii — save_to_nextcloud, rescan_nextcloud)
  services/dedup_service.py   (~30 linii — hash computation, duplicate check)
```

**Kroki atomowe:**
1. Utwórz `services/parser_service.py` — przenieś `extract_pdf_text()`, `parse_with_docling()`, `read_text_file()`, `clean_text()`
2. Utwórz `services/nextcloud_service.py` — przenieś `save_to_nextcloud()`, `rescan_nextcloud()`, `EXT_TO_DIR`
3. Utwórz `services/dedup_service.py` — przenieś `_hash_bytes()`, logikę deduplikacji
4. Utwórz `services/ingest_service.py` — orkiestracja: parse → pipeline → Qdrant
5. Refaktoryzuj `routes/ingest.py` — endpointy wywołują `ingest_service`
6. Test: upload pliku PDF przez UI, sprawdź `/files/stats`

---

### 1.3 Wydzielenie Component Layer (wzorzec PrivateGPT)

PrivateGPT ma `components/` — każdy component dostarcza konkretną implementację abstrakcji. W KlimtechRAG odpowiednikiem są `services/`, ale mieszają orkiestrację z implementacją.

**Plan:**
```
NOWY KATALOG:
  backend_app/components/
  ├── __init__.py
  ├── llm_component.py        — wrapper na llama-server (OpenAIGenerator)
  ├── embedding_component.py  — wrapper na e5-large (lazy singleton)
  ├── colpali_component.py    — wrapper na ColPali (lazy singleton)
  ├── vectorstore_component.py — wrapper na Qdrant (doc_store + ensure_indexed)
  └── whisper_component.py    — wrapper na Whisper STT (lazy singleton)
```

**Zasada:** Component = singleton z lazy loading + unload(). Service używa Component, nie tworzy go sam.

**Kroki atomowe:**
1. Utwórz `backend_app/components/__init__.py`
2. Przenieś `services/llm.py` → `components/llm_component.py`
3. Przenieś `services/embeddings.py` → `components/embedding_component.py`
4. Przenieś `services/colpali_embedder.py` → `components/colpali_component.py`
5. Przenieś `services/qdrant.py` → `components/vectorstore_component.py`
6. Wyodrębnij Whisper z `routes/whisper_stt.py` → `components/whisper_component.py`
7. Zaktualizuj WSZYSTKIE importy (services, routes)
8. Test: pełny restart backendu, sprawdź `/health`, `/gpu/status`

---

## FAZA 2 — NOWE ENDPOINTY API (wzorce z PrivateGPT)

### 2.1 Endpoint `/v1/chunks` — Low-level contextual retrieval

PrivateGPT ma endpoint do pobierania chunków BEZ generowania odpowiedzi LLM. Przydatne do debugowania RAG, budowania custom pipelines, inspecting kontekstu.

**Plan:**
```python
POST /v1/chunks
{
    "text": "pytanie użytkownika",
    "limit": 10,
    "prev_next_chunks": 1,    # ile sąsiednich chunków dołączyć
    "context_filter": {
        "source": "raport.pdf"  # opcjonalny filtr po źródle
    }
}

Response:
{
    "object": "list",
    "data": [
        {
            "object": "context.chunk",
            "text": "treść chunku...",
            "score": 0.87,
            "document": {
                "source": "raport.pdf",
                "page": 3,
                "chunk_index": 12
            },
            "previous_texts": ["tekst przed..."],
            "next_texts": ["tekst po..."]
        }
    ]
}
```

**Kroki atomowe:**
1. Dodaj schemat `ChunksRequest` i `ChunksResponse` do `models/schemas.py`
2. Utwórz `routes/chunks.py` z endpointem `/v1/chunks`
3. Logika: embed pytanie → retrieval z Qdrant → zwróć chunki z metadanymi (BEZ LLM)
4. Zarejestruj router w `main.py`
5. Dodaj opcjonalny parametr `context_filter` do filtrowania po source
6. Test: `curl -sk -X POST https://...:8443/v1/chunks -d '{"text":"co to RAG","limit":5}'`

---

### 2.2 Endpoint `/v1/ingest` — ustandaryzowany ingest z metadanymi

PrivateGPT ma czysty endpoint ingestion zwracający `doc_id` i status. KlimtechRAG ma `/upload` (multipart) i `/ingest_path` (JSON) — ale bez spójnego API response.

**Plan:** Ustandaryzować response format dla WSZYSTKICH endpointów ingest:
```python
Response (jednolity dla /upload, /ingest_path, /ingest_all):
{
    "object": "ingest.result",
    "data": [
        {
            "doc_id": "sha256_abc123",
            "source": "raport.pdf",
            "status": "indexed",       # indexed | skipped | error | duplicate
            "chunks_count": 45,
            "embedding_model": "intfloat/multilingual-e5-large",
            "collection": "klimtech_docs",
            "indexed_at": "2026-03-21T14:30:00Z"
        }
    ]
}
```

**Kroki atomowe:**
1. Dodaj `IngestResponse` schema do `models/schemas.py`
2. Refaktoryzuj return statements w `/upload`, `/ingest_path`, `/ingest_all`, `/ingest_pdf_vlm`
3. Dodaj `doc_id` (SHA256 hash) do każdego response
4. Test: upload pliku, sprawdź czy response ma nowy format

---

### 2.3 Endpoint `/v1/ingest/list` — lista zaindeksowanych dokumentów

PrivateGPT ma endpoint do listowania zaindeksowanych dokumentów z metadanymi. KlimtechRAG ma `/files/list` ale zwraca surowe dane z SQLite.

**Plan:**
```python
GET /v1/ingest/list?status=indexed&source=raport.pdf

Response:
{
    "object": "list",
    "data": [
        {
            "doc_id": "sha256_abc123",
            "source": "raport.pdf",
            "status": "indexed",
            "chunks_count": 45,
            "size_bytes": 1234567,
            "embedding_model": "intfloat/multilingual-e5-large",
            "indexed_at": "2026-03-21T14:30:00Z"
        }
    ]
}
```

**Kroki atomowe:**
1. Dodaj endpoint `GET /v1/ingest/list` do nowego pliku `routes/ingest_list.py` lub do `routes/admin.py`
2. Logika: query `file_registry.db` → format OpenAI-style response
3. Test

---

### 2.4 Endpoint `DELETE /v1/ingest/{doc_id}` — usuwanie dokumentu z RAG

PrivateGPT pozwala usunąć zaindeksowany dokument. KlimtechRAG ma `DELETE /documents` ale wymaga znajomości filtrów Qdrant.

**Plan:**
```python
DELETE /v1/ingest/{doc_id}

# Usuwa:
# 1. Chunki z Qdrant (filtry po meta.source = doc_id)
# 2. Rekord z file_registry.db
# 3. Opcjonalnie: plik z Nextcloud
```

**Kroki atomowe:**
1. Dodaj endpoint `DELETE /v1/ingest/{doc_id}` do `routes/admin.py`
2. Implementuj usuwanie z Qdrant (filter po `meta.source`)
3. Implementuj usuwanie z file_registry
4. Parametr opcjonalny `?delete_file=true` — usuwa plik źródłowy
5. Test

---

## FAZA 3 — SYSTEM KONFIGURACJI (profile YAML)

### 3.1 Profile konfiguracyjne YAML (zamiast jednego .env)

PrivateGPT ma `settings-{profile}.yaml` — można szybko przełączyć konfigurację. KlimtechRAG ma tylko `.env` + hardcoded wartości w `config.py`.

**Plan:**
```
NOWE PLIKI:
  settings.yaml              — bazowa konfiguracja (zawsze ładowana)
  settings-local.yaml        — tryb dev na laptopie (CPU embedding, mały model)
  settings-server.yaml       — tryb produkcyjny na serwerze (GPU, Bielik-11B)
  settings-ingest.yaml       — tryb ingestowania (GPU embedding, bez LLM)
```

**Przykład settings.yaml:**
```yaml
server:
  host: 0.0.0.0
  port: 8000

llm:
  backend: llamacpp           # llamacpp | disabled
  base_url: http://localhost:8082/v1
  model_name: klimtech-bielik
  default_model_path: modele_LLM/model_thinking/speakleash_Bielik-4.5B...gguf

embedding:
  backend: huggingface        # huggingface | llamacpp | disabled
  model: intfloat/multilingual-e5-large
  device: cuda:0              # cuda:0 | cpu
  dimension: 1024

vectorstore:
  backend: qdrant
  url: http://localhost:6333
  collection: klimtech_docs

colpali:
  model: vidore/colpali-v1.3-hf
  collection: klimtech_colpali
  batch_size: 4

rag:
  enabled: false              # domyślnie OFF (v7.3)
  top_k: 5
  chunk_size: 200
  chunk_overlap: 30

ui:
  enabled: true

whisper:
  model_size: small
  device: cuda
```

**Kroki atomowe:**
1. Utwórz `settings.yaml` z bazową konfiguracją
2. Utwórz `settings-server.yaml` z nadpisaniami dla serwera
3. Zmodyfikuj `config.py` — dodaj ładowanie YAML z merge (YAML nadpisuje .env)
4. Dodaj env var `KLIMTECH_PROFILES` (np. `KLIMTECH_PROFILES=server`)
5. Zachowaj kompatybilność wsteczną z `.env` (YAML ma priorytet)
6. Test: uruchom z `KLIMTECH_PROFILES=server python3 -m backend_app.main`

---

### 3.2 Walidacja konfiguracji na starcie

PrivateGPT waliduje konfigurację przed startem serwera. KlimtechRAG startuje i dopiero pada gdy brakuje czegoś.

**Plan:** Dodaj sprawdzanie na etapie `lifespan()` w `main.py`:

**Kroki atomowe:**
1. Dodaj funkcję `validate_config()` w `config.py`
2. Sprawdź: czy Qdrant jest dostępny, czy katalog modeli istnieje, czy porty nie są zajęte
3. Wywołaj w `lifespan()` — jeśli fail, wypisz czytelny błąd i zakończ
4. Test: odpal backend bez Qdrant, sprawdź czy komunikat jest czytelny

---

## FAZA 4 — STREAMING RESPONSES

### 4.1 SSE streaming w `/v1/chat/completions`

PrivateGPT wspiera `stream: true` z token-by-token streaming. KlimtechRAG ma `stream: bool = False` w schema ale NIE implementuje streaming.

**Plan:**
```python
# Gdy stream=true:
POST /v1/chat/completions
{"messages": [...], "stream": true}

# Response: Server-Sent Events
data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":"Cz"},"index":0}]}
data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"delta":{"content":"eść"},"index":0}]}
data: [DONE]
```

**Kroki atomowe:**
1. Dodaj `StreamingResponse` import do `routes/chat.py`
2. Zmodyfikuj `openai_chat_completions()` — branch na `request.stream`
3. Dla streaming: użyj `httpx.AsyncClient` z `stream=True` do llama-server
4. Przekazuj chunki jako SSE events w formacie OpenAI
5. Zaktualizuj UI (`index.html`) — obsługa `EventSource` lub `fetch` z `reader`
6. Test: `curl -sk -N -X POST .../v1/chat/completions -d '{"messages":[...],"stream":true}'`

---

## FAZA 5 — ULEPSZENIA INGESTION PIPELINE

### 5.1 Metadata extraction przy ingeście

PrivateGPT automatycznie wyciąga metadane z dokumentów (tytuł, autor, data, język). KlimtechRAG zapisuje tylko `source` i `type`.

**Plan:** Rozszerzyć metadane w chunkach Qdrant:
```python
metadata = {
    "source": "raport.pdf",
    "type": ".pdf",
    "title": "Raport kwartalny Q3",     # z pierwszej strony/nagłówka
    "page_count": 45,
    "file_size_bytes": 1234567,
    "language": "pl",                     # detekcja języka
    "created_at": "2026-01-15",           # z metadanych PDF
    "chunk_index": 12,
    "total_chunks": 45,
    "indexed_at": "2026-03-21T14:30:00Z"
}
```

**Kroki atomowe:**
1. Dodaj `services/metadata_service.py` — ekstrakcja metadanych z PDF (PyMuPDF), DOCX (mammoth)
2. Dodaj detekcję języka (biblioteka `langdetect` lub heurystyka polska/angielska)
3. Rozszerz `Document.meta` przy tworzeniu chunków w `ingest_service.py`
4. Test: zaindeksuj PDF, sprawdź `/rag/debug` czy metadane są w payload

---

### 5.2 Document watch (folder monitoring z retry)

PrivateGPT ma wbudowany folder watcher. KlimtechRAG ma `watch_nextcloud.py` jako osobny skrypt — ale musi być uruchamiany ręcznie.

**Plan:** Zintegruj watcher jako opcjonalny moduł backendu (nie osobny proces):

**Kroki atomowe:**
1. Dodaj ustawienie `watcher.enabled: true` w `settings.yaml`
2. W `lifespan()` uruchom watcher jako background task (asyncio)
3. Watcher monitoruje `nextcloud_base` i `upload_base`
4. Nowe pliki → kolejka → `ingest_service.ingest_file()`
5. Zachowaj `watch_nextcloud.py` jako fallback (standalone script)
6. Test: wrzuć plik do Nextcloud, sprawdź czy zaindeksowany bez uruchamiania watchdoga

---

## FAZA 6 — ULEPSZENIA UI

### 6.1 Streaming w czacie (token-by-token)

Po wdrożeniu Fazy 4 (SSE streaming), zaktualizuj UI:

**Kroki atomowe:**
1. Zmień `send()` w `index.html` — gdy odpowiedź, użyj `fetch` z `body.getReader()`
2. Renderuj tokeny incrementalnie w bańce czatu (zamiast czekać na pełną odpowiedź)
3. Dodaj animację "typing" na bazie realnych tokenów
4. Test: wyślij pytanie, obserwuj czy odpowiedź pojawia się token-by-token

---

### 6.2 Panel zarządzania dokumentami

PrivateGPT w Gradio ma panel z listą zaindeksowanych dokumentów, usuwaniem, re-ingestem.

**Kroki atomowe:**
1. Dodaj nową kartę w sidebar UI: "Dokumenty RAG"
2. Lista dokumentów z `/v1/ingest/list` — source, chunks, status, data
3. Przycisk "Usuń" → `DELETE /v1/ingest/{doc_id}`
4. Przycisk "Re-indeksuj" → `POST /ingest_path`
5. Filtrowanie po statusie (indexed / error / pending)
6. Test: wyświetl listę, usuń dokument, sprawdź `/files/stats`

---

### 6.3 Podgląd źródeł w odpowiedzi czatu

PrivateGPT pokazuje z których dokumentów pochodzi odpowiedź. KlimtechRAG ma `sources` w response ale UI ich nie wyświetla.

**Kroki atomowe:**
1. Backend: zwróć `sources` w response `ChatCompletionResponse` (już jest, ale puste gdy RAG off)
2. UI: po odpowiedzi AI, jeśli `sources` nie jest puste — wyświetl listę źródeł pod odpowiedzią
3. Klikalne źródło → pokazuje chunk z kontekstem (wywołanie `/v1/chunks`)
4. Test: włącz RAG (globe), zadaj pytanie, sprawdź czy źródła się wyświetlają

---

## FAZA 7 — TESTY I JAKOŚĆ KODU

### 7.1 Struktura testów (wzorzec PrivateGPT)

PrivateGPT ma `tests/` z helperami i `make test`. KlimtechRAG nie ma testów.

**Plan:**
```
NOWY KATALOG:
  tests/
  ├── conftest.py              — fixtures (test client, mock Qdrant, mock LLM)
  ├── test_health.py           — test /health, /gpu/status
  ├── test_chat.py             — test /v1/chat/completions (z mock LLM)
  ├── test_ingest.py           — test /upload, /ingest_path (z mock Qdrant)
  ├── test_chunks.py           — test /v1/chunks
  ├── test_models.py           — test /v1/models, /model/list
  └── test_security.py         — test auth, rate limiting, path traversal
```

**Kroki atomowe:**
1. Zainstaluj `pytest`, `httpx` w venv
2. Utwórz `tests/conftest.py` z `TestClient(app)` i mockami
3. Utwórz `tests/test_health.py` — podstawowe testy smoke
4. Utwórz `tests/test_security.py` — auth bypass, path traversal
5. Dodaj `scripts/check_project.sh` z uruchomieniem testów
6. Dodaj `Makefile` z `make test`, `make check`

---

### 7.2 Makefile (wzorzec PrivateGPT)

PrivateGPT ma `Makefile` z komendami `make run`, `make test`, `make check`.

**Plan:**
```makefile
# Makefile
.PHONY: run test check lint start stop

run:
	cd /media/lobo/BACKUP/KlimtechRAG && \
	KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m backend_app.main

test:
	python3 -m pytest tests/ -v

check:
	bash scripts/check_project.sh

lint:
	python3 -m ruff check backend_app/

start:
	python3 start_klimtech_v3.py

stop:
	python3 stop_klimtech.py
```

**Kroki atomowe:**
1. Utwórz `Makefile` w root projektu
2. Test: `make check`, `make lint`

---

## FAZA 8 — SWAGGER / OpenAPI DOCS

### 8.1 Automatyczna dokumentacja API

PrivateGPT ma pełną dokumentację API przez Swagger UI. KlimtechRAG ma domyślny FastAPI `/docs` ale bez opisów.

**Kroki atomowe:**
1. Dodaj `description`, `summary`, `tags` do KAŻDEGO endpointu w routes/
2. Dodaj `responses` z przykładami do kluczowych endpointów
3. Dodaj globalny opis API w `main.py`: `app = FastAPI(title="KlimtechRAG API", description="...", version="7.3")`
4. Dodaj custom Swagger UI na `/docs` (już działa domyślnie)
5. Test: otwórz `https://192.168.31.70:8443/docs`

---

## PODSUMOWANIE — KOLEJNOŚĆ WDRAŻANIA

| Priorytet | Faza | Opis | Trudność | Ryzyko |
|-----------|------|------|----------|--------|
| 🔴 1 | 1.1 | Wydzielenie chat_service z chat.py | Średnia | Niskie |
| 🔴 2 | 1.2 | Wydzielenie ingest_service z ingest.py | Średnia | Niskie |
| 🟡 3 | 2.1 | Endpoint `/v1/chunks` | Niska | Brak |
| 🟡 4 | 3.1 | Profile YAML | Średnia | Niskie |
| 🟡 5 | 4.1 | Streaming SSE | Średnia | Niskie |
| 🟢 6 | 2.2 | Standaryzacja ingest response | Niska | Brak |
| 🟢 7 | 2.3 | Endpoint `/v1/ingest/list` | Niska | Brak |
| 🟢 8 | 2.4 | Endpoint `DELETE /v1/ingest/{doc_id}` | Niska | Niskie |
| 🟢 9 | 1.3 | Component layer | Wysoka | Średnie |
| 🟢 10 | 5.1 | Metadata extraction | Niska | Brak |
| 🟢 11 | 6.1-6.3 | UI streaming + źródła + panel dokumentów | Średnia | Niskie |
| 🟢 12 | 7.1-7.2 | Testy + Makefile | Średnia | Brak |
| 🟢 13 | 8.1 | Swagger docs | Niska | Brak |
| ⚪ 14 | 3.2 | Walidacja konfiguracji | Niska | Brak |
| ⚪ 15 | 5.2 | Watcher w backendzie | Średnia | Średnie |

---

## DOCELOWA STRUKTURA KATALOGÓW (po wszystkich fazach)

```
backend_app/
├── main.py                    # Entry point (bez zmian)
├── config.py                  # + ładowanie YAML profiles
│
├── components/                # NOWE — implementacje (singleton, lazy)
│   ├── __init__.py
│   ├── llm_component.py       # ← z services/llm.py
│   ├── embedding_component.py # ← z services/embeddings.py
│   ├── colpali_component.py   # ← z services/colpali_embedder.py
│   ├── vectorstore_component.py # ← z services/qdrant.py
│   └── whisper_component.py   # ← z routes/whisper_stt.py (model part)
│
├── services/                  # ROZSZERZONE — logika biznesowa
│   ├── __init__.py
│   ├── chat_service.py        # NOWE — orkiestracja czatu
│   ├── retrieval_service.py   # NOWE — RAG retrieval (e5 + ColPali + web)
│   ├── prompt_service.py      # NOWE — budowanie promptów
│   ├── cache_service.py       # NOWE — cache z TTL
│   ├── ingest_service.py      # NOWE — orkiestracja ingestu
│   ├── parser_service.py      # NOWE — ekstrakcja tekstu
│   ├── nextcloud_service.py   # NOWE — integracja Nextcloud
│   ├── dedup_service.py       # NOWE — deduplikacja plików
│   ├── metadata_service.py    # NOWE — ekstrakcja metadanych
│   ├── model_manager.py       # (bez zmian)
│   └── rag.py                 # (uproszczony — używa components)
│
├── routes/                    # UPROSZCZONE — tylko HTTP layer
│   ├── __init__.py
│   ├── chat.py                # ~80 linii (było 500)
│   ├── ingest.py              # ~120 linii (było 767)
│   ├── chunks.py              # NOWE — /v1/chunks
│   ├── admin.py               # + /v1/ingest/list, DELETE /v1/ingest/{id}
│   ├── model_switch.py        # (bez zmian)
│   ├── filesystem.py          # (bez zmian)
│   ├── web_search.py          # (bez zmian)
│   ├── gpu_status.py          # (bez zmian)
│   ├── whisper_stt.py         # (uproszczony — model w component)
│   └── ui.py                  # (bez zmian)
│
├── models/
│   └── schemas.py             # + ChunksRequest, IngestResponse, itp.
│
├── prompts/                   # (bez zmian)
├── ingest/                    # (bez zmian)
├── utils/                     # (bez zmian)
├── scripts/                   # (bez zmian)
└── static/                    # + streaming, panel dokumentów, źródła
│
├── settings.yaml              # NOWE — bazowa konfiguracja
├── settings-server.yaml       # NOWE — profil serwer
├── settings-ingest.yaml       # NOWE — profil ingest
├── Makefile                   # NOWE
└── tests/                     # NOWE
```

---

## CZEGO NIE KOPIUJEMY Z PrivateGPT

| Element | Powód |
|---------|-------|
| LlamaIndex | KlimtechRAG używa Haystack — zmiana frameworka to miesiące pracy |
| Poetry | KlimtechRAG używa pip/venv — Poetry dodaje złożoność bez korzyści |
| Gradio UI | Custom UI jest lepsze (GPU dashboard, model switch, progress panel) |
| Ollama integration | KlimtechRAG używa llama.cpp bezpośrednio — mniej overhead |
| Multi-user auth (JWT) | Sieć lokalna, single-user — API key wystarczy |
| SDKs (Python/TypeScript) | Overkill dla lokalnego systemu |

---

*Plan stworzony: 2026-03-28*
