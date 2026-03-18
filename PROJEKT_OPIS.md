# KlimtechRAG — Pełny opis projektu

⚠️ WAŻNE: Komendy z "sudo" są ZAWSZE wyświetlane dla użytkownika do ręcznego wykonania w osobnym terminalu. Model AI nie może wykonywać komend z sudo (brak hasła).

**Wersja:** v7.5  
**Data:** 2026-03-19 (noc)  
**Repozytorium:** https://github.com/Satham666/KlimtechRAG  
**Katalog serwera:** `/media/lobo/BACKUP/KlimtechRAG/`  

⚠️ UWAGA: Katalog `/home/lobo/KlimtechRAG/` został USUNIĘTY (2026-03-18)!
Teraz istnieje TYLKO `/media/lobo/BACKUP/KlimtechRAG/`

---

## 1. Cel i przeznaczenie

**KlimtechRAG** to w pełni lokalny system RAG (Retrieval-Augmented Generation) do pracy z dokumentacją techniczną w języku polskim. Działa w 100% offline — LLM, embedding, OCR i VLM uruchamiane są lokalnie na serwerze Linux z GPU AMD Instinct 16 GB (ROCm/HIP).

### Główne zastosowania

- Odpowiadanie na pytania na podstawie zaindeksowanych dokumentów (PDF, DOCX, TXT, kod źródłowy)
- Automatyczne OCR skanów i dokumentów graficznych
- Obsługa dokumentów z obrazkami, tabelami i wykresami (tryb VLM / ColPali)
- Wyszukiwanie w internecie jako fallback (DuckDuckGo)
- Tool calling — LLM może wykonywać operacje na plikach (ls, glob, read, grep)
- Firmowa baza wiedzy technicznej z pełną suwerennością danych
- Czat AI w Nextcloud — Nextcloud Assistant podpięty do lokalnego backendu
- Automatyczne indeksowanie plików z Nextcloud — workflow n8n z zarządzaniem VRAM

---

## 2. Architektura systemu

### 2.1 Diagram architektury

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UŻYTKOWNICY                                     │
│          ↓                        ↓                      ↓                   │
│  https://:8443               http://:8081           http://:5678             │
│  KlimtechRAG UI              Nextcloud + AI         n8n workflows            │
│  (New UI + GPU Dashboard)    (+ Assistant)          (+ VRAM Management)      │
└────────────┬──────────────────────┬──────────────────────┬────────────────── ┘
             │                      │                      │
             │ Chat / Upload        │ Chat / Summarize     │ Trigger
             ↓                      ↓                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│               KlimtechRAG Backend (port 8000) — GATEWAY                      │
│  FastAPI                                                                      │
│  ├── /v1/chat/completions  ← UI + Nextcloud Assistant + n8n                 │
│  ├── /v1/models            ← UI + Nextcloud (lista modeli)                  │
│  ├── /gpu/status           ← GPU Dashboard (temp, VRAM, use)                │
│  ├── /v1/embeddings        ← RAG embedding                                  │
│  ├── /upload, /ingest_path ← upload plików                                  │
│  ├── /web/search, /fetch, /summarize ← Web Search panel                    │
│  ├── /v1/audio/transcriptions ← Whisper STT                                │
│  ├── /model/start, /stop, /switch ← zarządzanie VRAM                       │
│  └── /rag/debug            ← diagnostyka                                    │
└────────────┬────────────────────┬──────────────────┬────────────────────────┘
             │                    │                  │
             ↓                    ↓                  ↓
┌────────────────────┐  ┌─────────────────┐  ┌────────────────────────────────┐
│  llama.cpp-server  │  │  Qdrant (6333)  │  │  Nextcloud (8081)              │
│  (port 8082)       │  │  klimtech_docs  │  │  + integration_openai (app)    │
│  Bielik-4.5B/11B   │  │  10k+ punktów  │  │  + assistant (app)             │
│  VRAM: 4-14 GB     │  │  klimtech_colpali│  │  → Service URL: :8000         │
└────────────────────┘  └─────────────────┘  └────────────────────────────────┘
```

### 2.2 Data Flow — zapytanie (Query)

```
Pytanie użytkownika
    → Embedding pytania (e5-large, 1024 dim)
    → Retrieval z Qdrant (top_k=10 chunks)
    → Prompt Builder (kontekst + historia)
    → llama.cpp-server (Bielik-11B/4.5B)
    → Odpowiedź

Opcjonalnie:
    → Cache (TTL=1h) — pominięcie embeddingu
    → DuckDuckGo fallback — gdy RAG nie zwraca wyników
    → Tool Calling — LLM wykonuje ls/glob/read/grep
```

### 2.3 Data Flow — indeksowanie (Ingestion)

```
Plik wrzucony do Nextcloud RAG_Dane/
    → Watchdog (watch_nextcloud.py) wykrywa nowy plik
    → Ekstrakcja tekstu (docling / pdfplumber)
    → Chunking (200 słów z nakładką)

    Rozgałęzienie:
    ├── .txt/.md/.py/.json/.docx → Pipeline A: e5-large (1024 dim) → klimtech_docs
    ├── .pdf (skany/mieszane)    → Pipeline B: ColPali (128 dim multi-vector) → klimtech_colpali
    └── .pdf z obrazami          → Pipeline C: VLM (Qwen2.5-VL / LFM2.5-VL) → wzbogacenie → Pipeline A
```

### 2.4 Data Flow — Nextcloud AI Assistant

```
Nextcloud Assistant (przeglądarka na :8081)
    → POST /v1/chat/completions (OpenAI-compatible)
    → Authorization: Bearer sk-local
    → KlimtechRAG Backend (:8000)
    → RAG retrieval (Qdrant) → kontekst z dokumentów
    → Forward do llama.cpp-server (:8082)
    → Odpowiedź Bielik-11B → z powrotem do Nextcloud
```

---

## 3. Stack technologiczny

### 3.1 Infrastruktura

| Warstwa | Technologia | Uwagi |
|---------|-------------|-------|
| System | Linux Mint / Ubuntu 24 | Serwer + Laptop |
| Python | 3.12 (venv) | venv w `/media/lobo/BACKUP/KlimtechRAG/venv/` |
| GPU | AMD Instinct 16 GB | ROCm 7.2, `HSA_OVERRIDE_GFX_VERSION=9.0.6` |
| PyTorch | 2.5.1+rocm6.2 | ROCm build |
| Backend | FastAPI + Haystack 2.x | Port 8000 |
| LLM/VLM runner | llama.cpp-server | Port 8082, skompilowany pod AMD |
| Wektorowa baza | Qdrant (Podman) | Port 6333 |
| Kontenery | Podman | qdrant, nextcloud, postgres_nextcloud, n8n |
| UI | HTML/JS + Tailwind | `backend_app/static/index.html` (alias code.html) |
| Nextcloud AI | integration_openai + assistant | Port 8081 → backend :8000 |
| Automatyzacja | n8n | Port 5678 |
| HTTPS | nginx reverse proxy | self-signed cert |
| Sync | Git → GitHub | laptop → push, serwer → pull |

### 3.2 Modele GGUF (`modele_LLM/`)

| Typ | Model | VRAM | Kwantyzacja | Plik |
|-----|-------|------|-------------|------|
| LLM | Bielik-11B-v3.0-Instruct | ~14 GB | Q8_0 | `model_thinking/speakleash_Bielik-11B-v3.0-Instruct-GGUF_*.gguf` |
| LLM | Bielik-4.5B-v3.0-Instruct | ~5 GB | Q8_0 | `model_thinking/speakleash_Bielik-4.5B-v3.0-Instruct-GGUF_*.gguf` |
| LLM | LFM2-2.6B | ~6 GB | F16 | — |
| VLM | LFM2.5-VL-1.6B (+mmproj) | ~3.2 GB | BF16 | `model_video/LiquidAI_LFM2.5-VL-1.6B-GGUF_*.gguf` |
| VLM | Qwen2.5-VL-7B-Instruct (+mmproj) | ~4.7 GB | Q4_K_XL | `model_video/unsloth_Qwen2.5-VL-7B-Instruct-GGUF_*.gguf` |
| Audio | LFM2.5-Audio-1.5B (+mmproj) | ~2.2 GB | F16 | `model_audio/` |
| Embed (GGUF) | bge-large-en-v1.5 | — | Q8_0 | — |

### 3.3 Modele HuggingFace

| Model | Typ | Wymiar | Kolekcja Qdrant | Pipeline |
|-------|-----|--------|-----------------|---------|
| `intfloat/multilingual-e5-large` | Embedding tekstu | 1024 | `klimtech_docs` | A |
| `vidore/colpali-v1.3-hf` | Embedding wizualny (multi-vector) | 128 | `klimtech_colpali` | B |

---

## 4. Architektura VRAM (v7.3 — Lazy Loading)

**Kluczowe ograniczenie:** na GPU zmieści się tylko **jeden duży model** naraz (16 GB GPU).

**v7.3 ZMIANA:** Lazy loading — VRAM na starcie backendu to tylko **14 MB**!

| Stan / Model | VRAM | Uruchomienie |
|-------------|------|--------------|
| Backend sam (v7.3) | **14 MB** | Automatyczny |
| Bielik-11B Q8_0 | ~14 GB | Ręcznie przez UI dropdown |
| Bielik-4.5B Q8_0 | ~4.8 GB | Ręcznie przez UI dropdown |
| e5-large (embedding tekstu) | ~2.5 GB | Lazy — dopiero przy "Indeksuj RAG" |
| ColPali v1.3 (embedding dokumentów) | ~6-8 GB | On-demand |
| Qwen2.5-VL-7B Q4 | ~4.7 GB | On-demand VLM |
| LFM2.5-VL-1.6B | ~3.2 GB | On-demand VLM |
| Whisper small | ~2 GB | Lazy STT |
| Whisper medium | ~5 GB | Wymaga /model/stop |

**Strategia:** Użytkownik wybiera model z dropdown. Przełączanie przez `/model/stop` → `/model/start`.

---

## 5. Struktura katalogów (drzewo plików)

```
/media/lobo/BACKUP/KlimtechRAG/
│
├── start_klimtech_v3.py          # Start całego systemu (nginx, qdrant, backend)
├── stop_klimtech.py              # Stop całego systemu
├── start_backend_gpu.py          # Start backend w trybie GPU ingest
├── model_parametr.py             # Obliczanie parametrów llama-server (ctx, cache, ngl)
├── .env                          # Konfiguracja środowiska
├── .gitignore                    # Git ignore (venv, .env, modele_LLM/, .ruff_cache/)
│
├── backend_app/                  # Główny pakiet Python
│   ├── main.py                   # Entry point FastAPI + lifespan + CORS + routery
│   ├── config.py                 # Pydantic Settings (z .env)
│   ├── file_registry.py          # SQLite — rejestracja zaindeksowanych plików
│   ├── monitoring.py             # CPU, RAM, GPU stats (rocm-smi)
│   ├── fs_tools.py               # Filesystem tools (sandboxed)
│   │
│   ├── routes/
│   │   ├── __init__.py           # Eksport routerów
│   │   ├── chat.py               # /v1/chat/completions, /query, /v1/embeddings, /v1/models, /models
│   │   ├── ingest.py             # /upload, /ingest, /ingest_path, /ingest_all, /ingest_pdf_vlm
│   │   ├── admin.py              # /health, /metrics, /documents, /ws/health, /files/*
│   │   ├── model_switch.py       # /model/status, /model/switch/*, /model/list, /model/start, /model/stop
│   │   ├── filesystem.py         # /fs/list, /fs/glob, /fs/read, /fs/grep
│   │   ├── web_search.py         # /web/status, /web/search, /web/fetch, /web/summarize
│   │   ├── gpu_status.py         # /gpu/status (rocm-smi, temp, VRAM, use) — v7.3
│   │   ├── whisper_stt.py        # /v1/audio/transcriptions (Whisper STT)
│   │   └── ui.py                 # GET / (HTML UI)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── qdrant.py             # Klient Qdrant, get_embedding_dimension() (cache)
│   │   ├── embeddings.py         # Lazy: get_text_embedder() / get_doc_embedder()
│   │   ├── rag.py                # Lazy: get_indexing_pipeline() / get_rag_pipeline()
│   │   ├── llm.py                # Standalone OpenAIGenerator (do llama-server)
│   │   ├── model_manager.py      # llama-server lifecycle (start/stop/switch/progress)
│   │   └── colpali_embedder.py   # ColPali multi-vector embedding (Pipeline B)
│   │
│   ├── models/
│   │   └── schemas.py            # Pydantic schemas (ChatRequest, IngestRequest, ...)
│   │                             # use_rag: False domyślnie (v7.3)
│   │
│   ├── utils/
│   │   ├── rate_limit.py         # Rate limiting (token bucket)
│   │   ├── tools.py              # Tool calling helpers
│   │   └── dependencies.py       # API key auth (X-API-Key + Bearer fallback)
│   │
│   ├── scripts/
│   │   ├── watch_nextcloud.py    # Watchdog v3.0 — monitoruje RAG_Dane/*, auto-ingest
│   │   ├── ingest_gpu.py         # Batch GPU ingest (e5-large)
│   │   └── ingest_colpali.py     # Batch ColPali ingest (Pipeline B)
│   │
│   ├── ingest/
│   │   └── image_handler.py      # Ekstrakcja obrazów z PDF + VLM opisy
│   │                             # UWAGA: hardcoded params — do refaktoryzacji (Sekcja 16)
│   │
│   ├── prompts/                  # ✅ UTWORZONE (Sekcja 16 v7.3)
│   │   ├── __init__.py           # ✅ DONE
│   │   └── vlm_prompts.py        # ✅ DONE (8 wariantów promptów VLM)
│   │
│   └── static/
│       └── index.html            # Główny UI (zawartość code.html + v7.3 GPU Dashboard)
│
├── data/
│   ├── nextcloud/                # Dane kontenera Nextcloud (wolumen Podman)
│   │   └── config/config.php     # allow_local_remote_servers: true
│   ├── n8n/                      # Dane kontenera n8n (wolumen Podman)
│   ├── uploads/                  # Tymczasowe uploady backendu
│   │   └── pdf_RAG/              # PDF do ColPali ingest
│   ├── file_registry.db          # SQLite — rejestr zaindeksowanych plików
│   └── ssl/
│       ├── klimtech.crt          # Certyfikat self-signed
│       └── klimtech.key          # Klucz prywatny
│
├── modele_LLM/                   # (w .gitignore — tylko na serwerze)
│   ├── model_thinking/           # LLM: Bielik-11B, Bielik-4.5B, LFM2-2.6B
│   ├── model_video/              # VLM: LFM2.5-VL-1.6B, Qwen2.5-VL-7B
│   ├── model_audio/              # Audio: LFM2.5-Audio-1.5B
│   └── model_embed/              # Embedding GGUF: bge-large-en-v1.5
│
├── n8n_workflows/                # Workflow JSON do importu w n8n
│   ├── workflow_auto_index.json  # Auto-indeksowanie (Schedule + WebDAV + routing)
│   ├── workflow_chat_webhook.json# Webhook czat → backend
│   └── workflow_vram_manager.json# Zarządzanie VRAM (switch modeli)
│
├── scripts/
│   └── setup_nextcloud_ai.sh     # ⏳ Planowany skrypt konfiguracji NC
│
├── venv/                         # Virtualenv Python 3.12 (przeniesiony z /home/lobo/)
│
├── llama.cpp/                    # Skompilowany llama.cpp (AMD Instinct ROCm)
│   └── build/bin/
│       ├── llama-server          # Serwer LLM/VLM
│       └── llama-cli             # CLI do VLM opisów obrazów
│
├── NextcloudAI.md                # Plan wdrożenia sekcji 11-13 (Nextcloud + n8n)
├── PODSUMOWANIE.md               # Główna dokumentacja projektu (aktualizowana)
└── postep.md                     # Log postępu wdrożenia (ten plik)
```

---

## 6. Endpointy API (40 endpointów)

### 6.1 Chat & RAG

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/v1/chat/completions` | POST | Główny czat OpenAI-compatible (RAG + LLM) |
| `/v1/models` | GET | Lista modeli (Nextcloud + OWUI compatible) |
| `/models` | GET | Lista modeli bez /v1/ (Nextcloud compat) |
| `/v1/embeddings` | POST | Generowanie embeddingów tekstu |
| `/query` | POST | Zapytanie RAG z opcjonalnym web fallback |
| `/code_query` | POST | Zapytanie z kontekstem kodu |
| `/rag/debug` | GET | Diagnostyka kolekcji Qdrant |
| `/` | GET | HTML UI |

### 6.2 GPU & Monitoring

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/gpu/status` | GET | Temperatura, VRAM used/total, GPU utilization |
| `/health` | GET | Status serwisów (backend, qdrant, nextcloud, n8n) |
| `/metrics` | GET | CPU, RAM, czas działania |
| `/ws/health` | WS | WebSocket health stream |

### 6.3 Ingest (indeksowanie)

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/upload` | POST | Upload pliku + auto-ingest |
| `/ingest` | POST | Ingest z treścią tekstu |
| `/ingest_path` | POST | Ingest ze ścieżki lokalnej (używany przez n8n) |
| `/ingest_all` | POST | Batch ingest całego katalogu |
| `/ingest_pdf_vlm` | POST | Ingest PDF z VLM opisami obrazów |
| `/vlm/status` | GET | Status VLM ingest |

### 6.4 Model Management

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/model/status` | GET | Status llama-server (running/stopped) |
| `/model/start` | POST | Uruchom model (z parametrami) |
| `/model/stop` | POST | Zatrzymaj model (zwolnij VRAM) |
| `/model/switch/*` | POST | Przełącz na inny model |
| `/model/list` | GET | Lista dostępnych modeli GGUF |
| `/model/progress-log` | GET | SSE stream postępu ładowania modelu |

### 6.5 Web Search

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/web/status` | GET | Status DuckDuckGo |
| `/web/search` | POST | Wyszukiwanie w internecie |
| `/web/fetch` | POST | Pobieranie treści strony |
| `/web/summarize` | POST | Podsumowanie strony przez LLM |

### 6.6 Filesystem Tools

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/fs/list` | POST | Lista plików (sandboxed pod fs_root) |
| `/fs/glob` | POST | Glob pattern matching |
| `/fs/read` | POST | Odczyt pliku |
| `/fs/grep` | POST | Grep w plikach |

### 6.7 Audio (Whisper)

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/v1/audio/transcriptions` | POST | Transkrypcja audio (OpenAI-compatible, Whisper) |

---

## 7. Konfiguracja

### 7.1 Plik `.env`

```bash
KLIMTECH_BASE_PATH=/media/lobo/BACKUP/KlimtechRAG
KLIMTECH_LLM_BASE_URL=http://localhost:8082/v1
KLIMTECH_LLM_API_KEY=sk-dummy
KLIMTECH_EMBEDDING_MODEL=intfloat/multilingual-e5-large
KLIMTECH_QDRANT_URL=http://localhost:6333
KLIMTECH_QDRANT_COLLECTION=klimtech_docs
BACKEND_PORT=8000
LLAMA_API_PORT=8082
```

### 7.2 Porty systemowe

| Usługa | HTTP | HTTPS (nginx) |
|--------|------|---------------|
| Backend FastAPI + UI | 8000 | 8443 |
| llama.cpp-server | 8082 | — |
| Qdrant | 6333 | 6334 |
| Nextcloud + AI | 8081 | 8444 |
| n8n | 5678 | 5679 |

### 7.3 Dane dostępowe

| Usługa | URL | Login | Hasło |
|--------|-----|-------|-------|
| Nextcloud | http://192.168.31.70:8081 | admin | klimtech123 |
| Backend UI | https://192.168.31.70:8443 | — | sk-local (API key) |
| n8n | http://192.168.31.70:5678 | admin | admin123 |

### 7.4 Konfiguracja Nextcloud (Admin → Artificial Intelligence)

| Pole | Wartość |
|------|---------|
| Service URL | `http://192.168.31.70:8000` (**BEZ `/v1/`**) |
| API Key | `sk-local` |
| Model | `klimtech-bielik` |

### 7.5 Kontener Nextcloud — krytyczne ustawienia

```bash
# Musi być ustawione — bez tego NC blokuje prywatne IP
podman exec -u www-data nextcloud php occ config:system:set \
  allow_local_remote_servers --value=true --type=boolean

# HTTPS proxy config
podman exec nextcloud php occ config:system:set overwriteprotocol --value="https"
podman exec nextcloud php occ config:system:set overwritehost --value="192.168.31.70:8444"
```

---

## 8. Workflow n8n

### Workflow 1: Auto-indeksowanie plików

Plik: `n8n_workflows/workflow_auto_index.json`

```
Schedule (co 5 min)
  → WebDAV PROPFIND na /RAG_Dane/
  → Porównaj z poprzednim skanem (Static Data)
  → IF nowe pliki:
      → POST /model/stop (zwolnij VRAM)
      → Wait 10s
      → Loop przez nowe pliki:
          → IF .pdf → ColPali ingest (/ingest_path + X-Embedding-Model: vidore/colpali)
          → ELSE   → Standard ingest (/ingest_path, e5-large CPU)
      → POST /model/start (Bielik-11B)
      → Wait 20s → GET /health
```

### Workflow 2: Czat webhook

Plik: `n8n_workflows/workflow_chat_webhook.json`

```
Webhook POST /chat
  → POST /v1/chat/completions
  → Respond to Webhook
```

### Workflow 3: VRAM management

Plik: `n8n_workflows/workflow_vram_manager.json`

```
Webhook /vram-task (z polem task_type)
  → Switch:
      "rag_chat"      → Start Bielik-11B
      "rag_chat_mini" → Start Bielik-4.5B
      "index_text"    → Stop LLM → Ingest (e5-large CPU) → Start LLM
      "index_pdf"     → Stop LLM → Ingest ColPali (GPU) → Start LLM
      "vlm_ingest"    → Stop LLM → Start VLM → Ingest → Stop VLM → Start LLM
```

---

## 9. Trzy pipeline'y embeddingu

| Pipeline | Model | VRAM | Kolekcja | Typy plików |
|----------|-------|------|---------|-------------|
| **A: Tekst** | `intfloat/multilingual-e5-large` (1024 dim) | ~2.5 GB (GPU/CPU) | `klimtech_docs` | .txt, .md, .py, .json, .docx, PDF z warstwą tekstową |
| **B: ColPali** | `vidore/colpali-v1.3-hf` (128 dim multi-vector) | ~6-8 GB | `klimtech_colpali` | PDF skany, dokumenty mieszane (tekst+grafika+tabele) |
| **C: VLM wzbogacanie** | Qwen2.5-VL-7B / LFM2.5-VL-1.6B | ~4.7 / ~3.2 GB | — (wzbogaca → Pipeline A) | PDF z osadzonymi obrazami |

**Routing (automatyczny w n8n):**
- `.pdf` → Pipeline B (ColPali) — ~95% plików to skany
- `.txt`, `.md`, `.py`, `.json`, `.docx` → Pipeline A (e5-large)

---

## 10. UI (v7.3 — code.html)

Nowy interfejs użytkownika dostępny na `https://192.168.31.70:8443`:

- **GPU Dashboard** — temperatura, VRAM used/total, GPU utilization (aktualizacja co 2s)
- **Header health check** — status Qdrant, Nextcloud, PostgreSQL, n8n (real-time)
- **Model Selection** — dropdown 4 LLM + 5 VLM + 2 Audio + 3 Embedding; Uruchom/Zatrzymaj
- **Upload & Ingest** — drag & drop z progress barem, wybór modelu embeddingu
- **Czat** — sesje, historia, export/import JSON, tryb RAG (globe 🌐)
- **Web Search** — DuckDuckGo + podgląd stron + podsumowanie LLM
- **Terminal POSTĘP** — logi z postępem operacji w czasie rzeczywistym
- **RAG domyślnie OFF** — czat idzie prosto do llama-server (bez dławienia RAG)
- **RAG włączany ręcznie** — kliknięcie globe 🌐 w input bar → `use_rag: true`

---

## 11. Komendy operacyjne

### Krytyczne: aktywacja środowiska

**Przed uruchomieniem JAKIEGOKOLWIEK pliku `.py`:**

```fish
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate.fish
```

### Start / Stop systemu

```fish
# Start całego systemu (nginx + kontenery + backend)
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate.fish
python3 start_klimtech_v3.py

# Stop całego systemu
python3 stop_klimtech.py
```

### Uruchamianie konkretnych komponentów

```fish
# Watchdog (monitorowanie plików Nextcloud)
python3 -m backend_app.scripts.watch_nextcloud

# ColPali ingest
python3 -m backend_app.scripts.ingest_colpali --dir data/uploads/pdf_RAG

# GPU ingest (batch e5-large)
python3 start_backend_gpu.py

# Obliczanie parametrów modelu
python3 -m backend_app.scripts.model_parametr <ścieżka_do_modelu.gguf>
```

### Git sync (laptop → serwer)

```fish
# Na laptopie
git add -A && git commit -m "Sync" && git push --force

# Na serwerze
git pull
```

### Diagnostyka

```fish
curl http://192.168.31.70:8000/health
curl http://192.168.31.70:8000/v1/models
curl http://192.168.31.70:8000/rag/debug
curl -k https://192.168.31.70:8443/health     # HTTPS (self-signed)
```

### Nextcloud occ

```fish
# Lista zainstalowanych aplikacji
podman exec -u www-data nextcloud php occ app:list --enabled

# Sprawdzenie ustawień systemowych
podman exec -u www-data nextcloud php occ config:system:get allow_local_remote_servers
```

---

## 12. Znane problemy i ograniczenia

| # | Priorytet | Problem | Status | Obejście |
|---|-----------|---------|--------|----------|
| 1 | 🔴 | VLM opis obrazów — brak mmproj w llama-cli | Nierozwiązane | — |
| 2 | 🔴 | `ingest_gpu.py` zabija `start_klimtech.py` | Nierozwiązane | Używaj `start_backend_gpu.py` |
| 3 | 🔴 | Nextcloud AI Assistant nie odpowiada (kod 417) | ✅ ROZWIĄZANE v7.5 | Named Volume (ext4) |

### Problem 3: Nextcloud AI Assistant 417 — ROZWIĄZANIE (v7.5)

**Root cause (v7.4):** Próbowano mapować Nextcloud na exFAT - NIE DZIAŁAŁO!
- exFAT ignoruje UID/GID Unix
- www-data (UID 33) nie może pisać do katalogu owned przez "lobo" (UID 1000)
- chmod 777 NIE POMAGA na exFAT
- Mapowanie /var/www/html na exFAT powodowało brak plików Nextcloud (version.php missing)
- Entrypoint NC nie instaluje plików gdy katalog nie jest pusty

**Rozwiązanie v7.5: Named Volume dla WSZYSTKIEGO**

| Component | Location | Filesystem |
|-----------|---------|-----------|
| Pod `klimtech_pod` | Wspólna sieć localhost | - |
| PostgreSQL | W Pod, named volume `klimtech_postgres_data` | ext4 |
| Nextcloud Data | W Pod, named volume `klimtech_nextcloud_data` | ext4 |
| **Brak mapowania na exFAT** | - | - |

**Architektura kontenerów v7.5:**
```
Pod 'klimtech_pod' (wspólna sieć localhost)
├── nextcloud (port 8081)
└── postgres_nextcloud (localhost:5432)

Kontenery standalone:
├── qdrant (6333)
└── n8n (5678)
```

**KOMENDY URUCHOMIENIA (2026-03-19):**
```bash
# 1. Usuń starą konfigurację
podman stop nextcloud postgres_nextcloud
podman rm nextcloud postgres_nextcloud
podman pod rm -f klimtech_pod
rm -rf /media/lobo/BACKUP/KlimtechRAG/data/nextcloud

# 2. Stwórz Pod
podman pod create --name klimtech_pod -p 8081:80

# 3. PostgreSQL
podman run -d --name postgres_nextcloud --pod klimtech_pod --restart always \
    -e POSTGRES_DB=nextcloud -e POSTGRES_USER=nextcloud -e POSTGRES_PASSWORD=klimtech123 \
    -v klimtech_postgres_data:/var/lib/postgresql/data docker.io/library/postgres:16

# 4. Nextcloud (Named Volume, NIE exFAT!)
podman volume create klimtech_nextcloud_data
podman run -d --name nextcloud --pod klimtech_pod --restart always \
    -e POSTGRES_HOST="localhost" -e POSTGRES_DB=nextcloud \
    -e POSTGRES_USER=nextcloud -e POSTGRES_PASSWORD=klimtech123 \
    -e NEXTCLOUD_TRUSTED_DOMAINS="192.168.31.70 localhost" \
    -e NEXTCLOUD_ADMIN_USER="admin" -e NEXTCLOUD_ADMIN_PASSWORD="klimtech123" \
    -v klimtech_nextcloud_data:/var/www/html/data docker.io/library/nextcloud:32

# 5. Konfiguracja (~45s po starcie)
podman exec -u www-data nextcloud php occ app:install integration_openai
podman exec -u www-data nextcloud php occ app:install assistant
podman exec -u www-data nextcloud php occ config:system:set check_data_directory_permissions --value=false --type=boolean
podman exec -u www-data nextcloud php occ config:system:set filelocking.enabled --value=false --type=boolean
podman exec -u www-data nextcloud php occ config:system:set allow_local_remote_servers --value=true --type=boolean
podman exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value="https"
podman exec -u www-data nextcloud php occ config:system:set overwritehost --value="192.168.31.70:8444"
```

**Login Nextcloud:** `admin` / `klimtech123`

---

## 13. Historia wersji

| Wersja | Sesja | Zmiany |
|--------|-------|--------|
| v7.0 | 7-8 | ColPali, ROCm fix |
| v7.1 | 9 | Web Search panel (zakładka sidebar) |
| v7.2 | 10 | Nextcloud AI Integration, n8n workflows |
| v7.3 | 11 | New UI (code.html), GPU Dashboard, lazy loading (VRAM 14MB), RAG domyślnie OFF |
| v7.4 | 12 | Hybrid Storage (PostgreSQL on ext4) + Podman Pod architecture (NIEDZIAŁAŁO!) |
| v7.5 | 13 | Nextcloud Fix - Named Volume (ext4) zamiast exFAT |

---

## 14. Planowane zmiany

### Refaktoryzacja VLM Prompts (`backend_app/ingest/image_handler.py`) — ✅ WYKONANE v7.3

| # | Co | Gdzie | Status |
|---|-----|-------|--------|
| 16a | Utwórz katalog `backend_app/prompts/` | — | ✅ DONE |
| 16b | Utwórz `prompts/__init__.py` | — | ✅ DONE |
| 16c | Utwórz `prompts/vlm_prompts.py` z 8 wariantami | — | ✅ DONE |
| 16d | Refaktoryzuj `image_handler.py` — import promptów | `image_handler.py` | ✅ DONE |
| 16e | Refaktoryzuj `image_handler.py` — dynamiczne params | `image_handler.py` | ✅ DONE |

**8 wariantów promptów VLM:** DEFAULT, DIAGRAM, CHART, TABLE, PHOTO, SCREENSHOT, TECHNICAL, MEDICAL

### Inne planowane (niski priorytet)

- Skrypt `scripts/setup_nextcloud_ai.sh` — jednorazowa konfiguracja NC
- Heurystyka RAG off dla summarize (jeśli wiadomość > 2000 znaków)
- Chunked summarization dla długich dokumentów
- Nextcloud `webhook_listeners` — event-driven zamiast pollingu
- Auto-transkrypcja audio w n8n (Whisper + e5-large → Qdrant)

---

*Wygenerowano: 2026-03-19*
