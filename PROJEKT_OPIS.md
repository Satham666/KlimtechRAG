# KlimtechRAG — Pełny opis projektu

**Wersja:** v7.3  
**Data:** 2026-03-21  
**Repozytorium:** https://github.com/Satham666/KlimtechRAG  
**Katalog serwera:** `/media/lobo/BACKUP/KlimtechRAG/`  
**Katalog laptopa:** `~/Programy/KlimtechRAG`

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

## 2. Infrastruktura i środowisko

### 2.1 Maszyny

| Rola | Hostname | Katalog główny | Uwagi |
|------|----------|----------------|-------|
| **Serwer** | lobo@hall9000 (192.168.31.70) | `/media/lobo/BACKUP/KlimtechRAG/` | AMD Instinct 16GB, ROCm 7.2, środowisko bash |
| **Laptop** | tamiel@hall8000 | `~/Programy/KlimtechRAG` | Maszyna deweloperska, środowisko bash |

### 2.2 Workflow synchronizacji (Git)

- **Laptop → GitHub:** `git add -A && git commit -m "Sync" -a || true && git push --force`
- **GitHub → Serwer:** `git pull`
- **Zasada:** Kod edytowany ZAWSZE na laptopie, nigdy bezpośrednio na serwerze.

### 2.3 Środowisko Python

- **Venv:** `/media/lobo/BACKUP/KlimtechRAG/venv/` (Python 3.12)
- **Aktywacja (fish shell):** `cd /media/lobo/BACKUP/KlimtechRAG && source venv/bin/activate.fish`
- **Start backendu:** `KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000`
- **Fish shell constraint:** Komendy SSH na serwerze muszą używać `python3 -c "..."` — **nigdy heredoc (`cat << 'EOF'`)**, fish go nie obsługuje.

---

## 3. Architektura systemu

### 3.1 Diagram architektury

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

### 3.2 Data Flow — zapytanie (Query)

```
Pytanie użytkownika
    → [use_rag=false] → Prosto do llama-server → Odpowiedź
    → [use_rag=true]  → Embedding pytania (e5-large, 1024 dim)
                       → Retrieval z Qdrant (top_k=5 chunks)
                       → Prompt Builder (kontekst + historia)
                       → llama.cpp-server (Bielik-11B/4.5B)
                       → Odpowiedź

Opcjonalnie (web_search=true):
    → DuckDuckGo fallback — gdy RAG nie zwraca wyników

WAŻNE: use_rag=False domyślnie (v7.3) — czat idzie prosto do LLM.
       RAG włączany ręcznie przyciskiem globe 🌐 w UI.
```

### 3.3 Data Flow — indeksowanie (Ingestion)

```
Plik wrzucony do Nextcloud RAG_Dane/ lub przez /upload
    → Watchdog (watch_nextcloud.py) wykrywa nowy plik
    → Ekstrakcja tekstu (docling / pdfplumber)
    → Chunking (200 słów z nakładką)

    Rozgałęzienie:
    ├── .txt/.md/.py/.json/.docx → Pipeline A: e5-large (1024 dim) → klimtech_docs
    ├── .pdf (skany/mieszane)    → Pipeline B: ColPali (128 dim multi-vector) → klimtech_colpali
    └── .pdf z obrazami          → Pipeline C: VLM → wzbogacenie → Pipeline A
```

### 3.4 Architektura VRAM — Lazy Loading (v7.3)

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
| Whisper small | ~2 GB | Lazy STT |

---

## 4. Stack technologiczny

### 4.1 Infrastruktura

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
| UI | HTML/JS + Tailwind | `backend_app/static/index.html` |
| Nextcloud AI | integration_openai + assistant | Port 8081 → backend :8000 |
| Automatyzacja | n8n | Port 5678 |
| HTTPS | nginx reverse proxy | self-signed cert |
| Sync | Git → GitHub | laptop → push --force, serwer → pull |

### 4.2 Modele GGUF (`modele_LLM/`)

| Typ | Model | VRAM | Kwantyzacja |
|-----|-------|------|-------------|
| LLM | Bielik-11B-v3.0-Instruct | ~14 GB | Q8_0 |
| LLM | Bielik-4.5B-v3.0-Instruct | ~5 GB | Q8_0 |
| LLM | LFM2-2.6B | ~6 GB | F16 |
| VLM | LFM2.5-VL-1.6B (+mmproj) | ~3.2 GB | BF16 |
| VLM | Qwen2.5-VL-7B-Instruct (+mmproj) | ~4.7 GB | Q4_K_XL |
| Audio | LFM2.5-Audio-1.5B (+mmproj) | ~2.2 GB | F16 |
| Embed (GGUF) | bge-large-en-v1.5 | — | Q8_0 |

### 4.3 Modele HuggingFace

| Model | Typ | Wymiar | Kolekcja Qdrant |
|-------|-----|--------|-----------------|
| `intfloat/multilingual-e5-large` | Embedding tekstu | 1024 | `klimtech_docs` |
| `vidore/colpali-v1.3-hf` | Embedding wizualny (multi-vector) | 128 | `klimtech_colpali` |

---

## 5. Struktura katalogów

```
/media/lobo/BACKUP/KlimtechRAG/
│
├── start_klimtech_v3.py          # Start całego systemu (nginx, qdrant, backend)
├── stop_klimtech.py              # Stop całego systemu
├── start_backend_gpu.py          # Start backend w trybie GPU ingest
├── .env                          # Konfiguracja środowiska
├── .gitignore                    # Git ignore (venv, .env, modele_LLM/)
├── PROJEKT_OPIS.md               # Ten plik — opis projektu
├── postep.md                     # Log postępu — status sesji
├── agents/AGENTS.md              # Instrukcje dla modeli AI (OpenCode)
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
│   │   ├── chat.py               # /v1/chat/completions, /query, /v1/embeddings, /v1/models
│   │   ├── ingest.py             # /upload, /ingest, /ingest_path, /ingest_all, /ingest_pdf_vlm
│   │   ├── admin.py              # /health, /metrics, /documents, /ws/health, /files/*
│   │   ├── model_switch.py       # /model/status, /model/switch/*, /model/list, /model/start, /model/stop
│   │   ├── filesystem.py         # /fs/list, /fs/glob, /fs/read, /fs/grep
│   │   ├── web_search.py         # /web/status, /web/search, /web/fetch, /web/summarize
│   │   ├── gpu_status.py         # /gpu/status (rocm-smi, temp, VRAM, use)
│   │   ├── whisper_stt.py        # /v1/audio/transcriptions (Whisper STT)
│   │   └── ui.py                 # GET / (serwuje static/index.html)
│   │
│   ├── services/
│   │   ├── __init__.py           # Eksport: doc_store, get_text_embedder, get_rag_pipeline...
│   │   ├── qdrant.py             # Klient Qdrant, get_embedding_dimension() (cache)
│   │   ├── embeddings.py         # Lazy: get_text_embedder() / get_doc_embedder()
│   │   ├── rag.py                # Lazy: get_indexing_pipeline() / get_rag_pipeline()
│   │   ├── llm.py                # Standalone OpenAIGenerator (do llama-server)
│   │   ├── model_manager.py      # llama-server lifecycle (start/stop/switch/progress)
│   │   └── colpali_embedder.py   # ColPali multi-vector embedding (Pipeline B)
│   │
│   ├── models/
│   │   └── schemas.py            # Pydantic schemas — use_rag: False domyślnie (v7.3)
│   │
│   ├── utils/
│   │   ├── rate_limit.py         # Rate limiting (token bucket)
│   │   ├── tools.py              # Tool calling helpers
│   │   └── dependencies.py       # API key auth (X-API-Key + Bearer fallback)
│   │
│   ├── scripts/
│   │   ├── watch_nextcloud.py    # Watchdog v3.0 — monitoruje RAG_Dane/*, auto-ingest
│   │   ├── ingest_gpu.py         # Batch GPU ingest (e5-large)
│   │   ├── ingest_colpali.py     # Batch ColPali ingest (Pipeline B)
│   │   └── model_parametr.py     # Obliczanie parametrów llama-server (ctx, cache, ngl)
│   │
│   ├── ingest/
│   │   └── image_handler.py      # Ekstrakcja obrazów z PDF + VLM opisy
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── vlm_prompts.py        # 8 wariantów promptów VLM (DEFAULT..MEDICAL)
│   │
│   └── static/
│       ├── index.html            # Główny UI v7.3 (z JS, GPU Dashboard, czat)
│       └── code.html             # Kopia statyczna UI (bez JS backend)
│
├── data/
│   ├── nextcloud/                # Dane kontenera Nextcloud
│   ├── n8n/                      # Dane kontenera n8n
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
│   └── model_embedding/          # Embedding GGUF: bge-large-en-v1.5, bge-m3
│
├── n8n_workflows/
│   ├── workflow_auto_index.json  # Auto-indeksowanie (Schedule + WebDAV + routing)
│   ├── workflow_chat_webhook.json# Webhook czat → backend
│   └── workflow_vram_manager.json# Zarządzanie VRAM (switch modeli)
│
├── venv/                         # Virtualenv Python 3.12
│
└── llama.cpp/                    # Skompilowany llama.cpp (AMD Instinct ROCm)
    └── build/bin/
        ├── llama-server          # Serwer LLM/VLM
        └── llama-cli             # CLI do VLM opisów obrazów
```

---

## 6. Endpointy API (40+ endpointów)

### 6.1 Chat & RAG

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/v1/chat/completions` | POST | Główny czat OpenAI-compatible (RAG opcjonalny) |
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
| `/health` | GET | Status serwisów (backend, qdrant) |
| `/metrics` | GET | CPU, RAM, czas działania |

### 6.3 Ingest (indeksowanie)

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/upload` | POST | Upload pliku + auto-ingest + zapis do Nextcloud |
| `/ingest` | POST | Ingest z treścią tekstu (legacy) |
| `/ingest_path` | POST | Ingest ze ścieżki lokalnej (używany przez n8n) |
| `/ingest_all` | POST | Batch ingest z file_registry |
| `/ingest_pdf_vlm` | POST | Ingest PDF z VLM opisami obrazów |

### 6.4 Model Management

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/model/status` | GET | Status llama-server (running/stopped) |
| `/model/start` | POST | Uruchom model (z parametrami) |
| `/model/stop` | POST | Zatrzymaj model (zwolnij VRAM) |
| `/model/list` | GET | Lista dostępnych modeli GGUF |
| `/model/progress-log` | GET | Linie postępu ładowania modelu |

### 6.5 Web Search, Filesystem, Audio

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/web/search` | POST | DuckDuckGo search |
| `/web/fetch` | POST | Pobieranie treści strony |
| `/web/summarize` | POST | Podsumowanie strony przez LLM |
| `/fs/list`, `/fs/glob`, `/fs/read`, `/fs/grep` | POST | Filesystem tools (sandboxed) |
| `/v1/audio/transcriptions` | POST | Whisper STT (OpenAI-compatible) |

---

## 7. Konfiguracja

### 7.1 Porty systemowe

| Usługa | HTTP | HTTPS (nginx) |
|--------|------|---------------|
| Backend FastAPI + UI | 8000 | 8443 |
| llama.cpp-server | 8082 | — |
| Qdrant | 6333 | 6334 |
| Nextcloud + AI | 8081 | 8444 |
| n8n | 5678 | 5679 |

### 7.2 Dane dostępowe

| Usługa | URL | Login | Hasło |
|--------|-----|-------|-------|
| Nextcloud | http://192.168.31.70:8081 | admin | klimtech123 |
| Backend UI | https://192.168.31.70:8443 | — | sk-local (API key) |
| n8n | http://192.168.31.70:5678 | admin | admin123 |

### 7.3 Plik `.env`

```bash
KLIMTECH_BASE_PATH=/media/lobo/BACKUP/KlimtechRAG
KLIMTECH_LLM_BASE_URL=http://localhost:8082/v1
KLIMTECH_LLM_API_KEY=sk-dummy
KLIMTECH_EMBEDDING_MODEL=intfloat/multilingual-e5-large
KLIMTECH_QDRANT_URL=http://localhost:6333
KLIMTECH_QDRANT_COLLECTION=klimtech_docs
```

---

## 8. UI (v7.3)

Interfejs użytkownika dostępny na `https://192.168.31.70:8443`:

- **GPU Dashboard** — temperatura, VRAM used/total, GPU utilization (aktualizacja co 2s)
- **Header health check** — status Qdrant, Nextcloud, PostgreSQL, n8n
- **Model Selection** — dropdown z listą modeli GGUF; Uruchom/Zatrzymaj
- **Upload & Ingest** — drag & drop z progress barem, SHA256 deduplication
- **Czat** — sesje w localStorage, historia, export/import JSON
- **Web Search** — DuckDuckGo + podgląd stron + podsumowanie LLM
- **Terminal POSTĘP** — logi z postępem operacji w czasie rzeczywistym (polling 600ms)
- **RAG domyślnie OFF** — czat idzie prosto do llama-server
- **RAG włączany ręcznie** — kliknięcie globe 🌐 → `use_rag: true` + `web_search: true`

---

## 9. Trzy pipeline'y embeddingu

| Pipeline | Model | VRAM | Kolekcja | Typy plików |
|----------|-------|------|---------|-------------|
| **A: Tekst** | `intfloat/multilingual-e5-large` (1024 dim) | ~2.5 GB | `klimtech_docs` | .txt, .md, .py, .json, .docx, PDF tekstowe |
| **B: ColPali** | `vidore/colpali-v1.3-hf` (128 dim multi-vector) | ~6-8 GB | `klimtech_colpali` | PDF skany, dokumenty mieszane |
| **C: VLM wzbogacanie** | Qwen2.5-VL-7B / LFM2.5-VL-1.6B | ~4.7 / ~3.2 GB | → Pipeline A | PDF z osadzonymi obrazami |

---

## 10. Komendy operacyjne

### Start / Stop systemu

```fish
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate.fish
python3 start_klimtech_v3.py    # Start
python3 stop_klimtech.py        # Stop
```

### Git sync

```bash
# Na laptopie
git add -A && git commit -m "Sync" -a || true && git push --force

# Na serwerze
git pull
```

### Diagnostyka

```bash
curl -k https://192.168.31.70:8443/health
curl -k https://192.168.31.70:8443/v1/models
curl -k https://192.168.31.70:8443/rag/debug
curl -k https://192.168.31.70:8443/gpu/status
```

---

## 11. Kluczowe decyzje architektoniczne

1. **Lazy loading VRAM** — embedding i pipeline RAG ładowane dopiero przy pierwszym użyciu, nie na starcie backendu. VRAM start: 14 MB zamiast 4.5 GB.
2. **use_rag=False domyślnie** — czat nie dławi się kontekstem RAG. Użytkownik włącza RAG gdy potrzebuje.
3. **Standalone LLM component** — `llm.py` tworzy własny `OpenAIGenerator`, nie wyciąga go z RAG pipeline.
4. **_detect_base() priorytet** — preferuje `/media/lobo/BACKUP/KlimtechRAG` (tam są modele GGUF) nad `~/KlimtechRAG` (stary repo bez modeli).
5. **ColPali oddzielna kolekcja** — `klimtech_colpali` (dim=128, MAX_SIM) osobno od `klimtech_docs` (dim=1024).
6. **JavaScript w Python strings** — template literals (backticks) w JS embedded w Python powodują błędy — zawsze concatenation (+) i var zamiast const/let.

---

## 12. Znane ograniczenia techniczne

- **GPU: 1 duży model naraz** — 16GB VRAM wymusza sekwencyjne używanie LLM/embedding/ColPali
- **ColPali: ~6-8GB VRAM** — wymaga zatrzymania LLM (`pkill -f llama-server`)
- **Fish shell SSH** — heredoc nie działa, używaj `python3 -c "..."`
- **monitoring.py GPU: 0%** — kosmetyczny problem z AMD ROCm, VRAM i temp działają OK
- **qdrant_indexed: 0** — HNSW index wymaga wymuszenia (ensure_indexed())

---

*Wygenerowano: 2026-03-21*
