# KlimtechRAG — Opis projektu

**Wersja:** v7.5 (Sesja 14: konsolidacja dokumentacji + naprawy po audycie)
**Data:** 2026-03-25
**Repozytorium:** https://github.com/Satham666/KlimtechRAG
**Katalog serwera:** `/media/lobo/BACKUP/KlimtechRAG/`
**Serwer:** lobo@hall9000 (192.168.31.70) | AMD Instinct 16GB | ROCm 7.2

---

## 1. Cel projektu

Lokalny system RAG (Retrieval-Augmented Generation) do pracy z dokumentacją techniczną w języku polskim. 100% offline — LLM, embedding, OCR i VLM na serwerze z GPU AMD Instinct 16 GB.

Zastosowania: pytania do zaindeksowanych dokumentów (PDF, DOCX, TXT, kod), OCR skanów, VLM opisy obrazów w PDF, web search (DuckDuckGo), tool calling (ls/glob/read/grep), baza wiedzy z suwerennością danych, Nextcloud AI Assistant, n8n auto-indeksowanie.

---

## 2. Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                         UŻYTKOWNICY                             │
│     https://:8443          http://:8081        http://:5678      │
│     KlimtechRAG UI         Nextcloud+AI        n8n workflows    │
└────────┬───────────────────────┬──────────────────┬─────────────┘
         │ Chat/Upload           │ Chat/Summarize    │ Trigger
         ↓                      ↓                   ↓
┌─────────────────────────────────────────────────────────────────┐
│            KlimtechRAG Backend (port 8000) — GATEWAY            │
│  FastAPI + Haystack 2.x                                         │
│  /v1/chat/completions, /v1/models, /v1/embeddings               │
│  /gpu/status, /upload, /ingest, /web/search, /model/start...   │
└────────┬──────────────────┬──────────────────┬──────────────────┘
         ↓                  ↓                  ↓
┌────────────────┐ ┌─────────────────┐ ┌──────────────────────────┐
│ llama.cpp      │ │ Qdrant (6333)   │ │ Nextcloud (8081)         │
│ (port 8082)    │ │ klimtech_docs   │ │ + integration_openai     │
│ Bielik 4.5B/11B│ │ klimtech_colpali│ │ + assistant              │
│ VRAM: 4-14 GB  │ │ + persistent vol│ │ Pod: klimtech_pod        │
└────────────────┘ └─────────────────┘ └──────────────────────────┘
```

### VRAM — Lazy Loading (v7.3+)

Ograniczenie: na GPU zmieści się **jeden duży model** naraz (16 GB).
VRAM na starcie backendu: **14 MB** (lazy loading).

| Model | VRAM | Uruchomienie |
|-------|------|-------------|
| Backend sam | 14 MB | Automatyczny |
| Bielik-11B Q8_0 | ~14 GB | Z panelu UI |
| Bielik-4.5B Q8_0 | ~5 GB | Z panelu UI |
| e5-large (embedding) | ~2.5 GB | Lazy przy "Indeksuj RAG" |
| ColPali v1.3 | ~6-8 GB | On-demand |
| Qwen2.5-VL-7B Q4 | ~4.7 GB | On-demand VLM |
| Whisper small | ~2 GB | Lazy STT |

### Data Flow — Query

```
Pytanie → [use_rag=false] → llama-server → Odpowiedź
        → [use_rag=true]  → Embedding (e5-large CPU) → Qdrant top_k
                           → Prompt Builder → llama-server → Odpowiedź
        → [web_search=true] → DuckDuckGo (max 20 wyników) → kontekst
```

RAG domyślnie OFF. Przyciski UI: `📎 RAG` (use_rag=true), `🌐 RAG+Web` (use_rag+web_search=true).

### Data Flow — Ingestion

```
Plik (upload/watchdog) → Ekstrakcja tekstu → Chunking (200 słów)
  ├── .txt/.md/.py/.docx → e5-large (1024 dim) → klimtech_docs
  ├── .pdf (skany)       → ColPali (128 dim)    → klimtech_colpali
  └── .pdf z obrazami    → VLM opis → e5-large  → klimtech_docs
```

---

## 3. Stack technologiczny

| Warstwa | Technologia |
|---------|-------------|
| System | Linux Ubuntu 24 / Mint |
| Python | 3.12 (venv) |
| GPU | AMD Instinct 16 GB, ROCm 7.2, `HSA_OVERRIDE_GFX_VERSION=9.0.6` |
| PyTorch | 2.5.1+rocm6.2 |
| Backend | FastAPI + Haystack 2.x (port 8000) |
| LLM/VLM | llama.cpp-server (port 8082) |
| Wektorowa baza | Qdrant w Podman (port 6333), volume `klimtech_qdrant_data` |
| Kontenery | Podman: qdrant, nextcloud, postgres_nextcloud, n8n |
| UI | HTML/JS + Tailwind (`static/index.html`) |
| Nextcloud AI | integration_openai + assistant (port 8081) |
| Automatyzacja | n8n (port 5678) |
| HTTPS | nginx reverse proxy (self-signed cert) |
| Auth | API key `sk-local` przez `X-API-Key` lub `Authorization: Bearer` |

### Modele GGUF (`modele_LLM/`)

| Typ | Model | VRAM | Kwantyzacja |
|-----|-------|------|-------------|
| LLM | Bielik-11B-v3.0-Instruct | ~14 GB | Q8_0 |
| LLM | Bielik-4.5B-v3.0-Instruct | ~5 GB | Q8_0 |
| LLM | LFM2-2.6B | ~6 GB | F16 |
| VLM | LFM2.5-VL-1.6B (+mmproj) | ~3.2 GB | BF16 |
| VLM | Qwen2.5-VL-7B-Instruct (+mmproj) | ~4.7 GB | Q4_K_XL |
| Audio | LFM2.5-Audio-1.5B (+mmproj) | ~2.2 GB | F16 |

### Modele HuggingFace

| Model | Wymiar | Kolekcja Qdrant |
|-------|--------|-----------------|
| `intfloat/multilingual-e5-large` | 1024 | `klimtech_docs` |
| `vidore/colpali-v1.3-hf` | 128 | `klimtech_colpali` |

---

## 4. Struktura katalogów

```
/media/lobo/BACKUP/KlimtechRAG/
├── start_klimtech_v3.py       # Start systemu (kontenery + backend + nginx)
├── stop_klimtech.py           # Stop systemu
├── .env                       # Konfiguracja środowiskowa
├── CLAUDE.md                  # Instrukcje dla Claude Code
├── agents/AGENTS.md           # Instrukcje dla AI asystentów
│
├── backend_app/
│   ├── main.py                # Entry point FastAPI + CORS + middleware
│   ├── config.py              # Pydantic Settings (z .env)
│   ├── file_registry.py       # SQLite rejestr plików
│   ├── monitoring.py          # CPU/RAM stats
│   ├── fs_tools.py            # Filesystem tools (sandboxed)
│   │
│   ├── routes/
│   │   ├── chat.py            # /v1/chat/completions, /query, /v1/embeddings, /v1/models
│   │   ├── ingest.py          # /upload, /ingest, /ingest_path, /ingest_all
│   │   ├── admin.py           # /health, /metrics, /documents, /ws/health, /files/*
│   │   ├── model_switch.py    # /model/status, /model/list, /model/start, /model/stop
│   │   ├── filesystem.py      # /fs/list, /fs/glob, /fs/read, /fs/grep
│   │   ├── web_search.py      # /web/search, /web/fetch, /web/summarize
│   │   ├── gpu_status.py      # /gpu/status (rocm-smi)
│   │   ├── whisper_stt.py     # /v1/audio/transcriptions
│   │   └── ui.py              # GET / (serwuje index.html)
│   │
│   ├── services/
│   │   ├── qdrant.py          # QdrantDocumentStore + get_qdrant_retriever()
│   │   ├── embeddings.py      # Lazy: get_text_embedder() / get_doc_embedder()
│   │   ├── rag.py             # Lazy: get_indexing_pipeline() / get_rag_pipeline()
│   │   ├── llm.py             # OpenAIGenerator (do llama-server)
│   │   ├── model_manager.py   # llama-server lifecycle (start/stop/switch)
│   │   ├── colpali_embedder.py# ColPali multi-vector
│   │   ├── embedder_pool.py   # Singleton cache embedderów
│   │   └── model_selector.py  # Automatyczny wybór embeddera po rozszerzeniu
│   │
│   ├── categories/
│   │   ├── definitions.py     # 14 kategorii RAG (pl/en/de)
│   │   └── classifier.py      # classify_document() → kategoria
│   │
│   ├── models/schemas.py      # Pydantic: use_rag=False domyślnie
│   ├── utils/                 # rate_limit, tools, dependencies (API key auth)
│   ├── prompts/vlm_prompts.py # 8 wariantów promptów VLM
│   ├── ingest/image_handler.py# Ekstrakcja obrazów z PDF + VLM
│   ├── scripts/               # watch_nextcloud, ingest_gpu, model_parametr
│   └── static/index.html      # UI v7.3
│
├── data/
│   ├── uploads/               # Pliki do indeksowania
│   ├── file_registry.db       # SQLite rejestr
│   └── ssl/                   # Certyfikat + klucz
│
├── modele_LLM/                # (w .gitignore)
├── n8n_workflows/             # 3 workflow JSON
├── venv/                      # Python 3.12 venv
└── llama.cpp/build/bin/       # llama-server, llama-cli (ROCm)
```

---

## 5. Endpointy API

### Chat & RAG
| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/v1/chat/completions` | POST | Główny czat OpenAI-compatible |
| `/v1/models` | GET | Lista modeli |
| `/models` | GET | Lista modeli (Nextcloud compat) |
| `/v1/embeddings` | POST | Generowanie embeddingów |
| `/query` | POST | RAG query z opcjonalnym web fallback |
| `/code_query` | POST | Query z kontekstem kodu |
| `/rag/debug` | GET | Diagnostyka Qdrant |

### Ingest
| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/upload` | POST | Upload + zapis do Nextcloud + ingest w tle |
| `/ingest` | POST | Upload + bezpośredni ingest (używany przez UI) |
| `/ingest_path` | POST | Ingest ze ścieżki lokalnej |
| `/ingest_all` | POST | Batch ingest pending plików z registry |

### Model Management
| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/model/status` | GET | Status llama-server |
| `/model/start` | POST | Uruchom model |
| `/model/stop` | POST | Zatrzymaj model |
| `/model/list` | GET | Lista modeli GGUF |

### Monitoring, Web, Filesystem, Audio
| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/gpu/status` | GET | Temperatura, VRAM, GPU use |
| `/health` | GET | Status serwisów |
| `/web/search` | POST | DuckDuckGo (max 20 wyników) |
| `/web/fetch` | POST | Pobranie treści strony |
| `/web/summarize` | POST | Podsumowanie strony przez LLM |
| `/fs/list,glob,read,grep` | POST | Filesystem tools (sandboxed) |
| `/v1/audio/transcriptions` | POST | Whisper STT |

---

## 6. Konfiguracja

### Porty

| Usługa | HTTP | HTTPS (nginx) |
|--------|------|---------------|
| Backend + UI | 8000 | 8443 |
| llama-server | 8082 | — |
| Qdrant | 6333 | 6334 |
| Nextcloud | 8081 | 8444 |
| n8n | 5678 | 5679 |

### Dane dostępowe

| Usługa | Login | Hasło |
|--------|-------|-------|
| Nextcloud | admin | klimtech123 |
| Backend API key | — | sk-local |
| n8n | admin | admin123 |

### .env

```bash
KLIMTECH_BASE_PATH=/media/lobo/BACKUP/KlimtechRAG
KLIMTECH_LLM_BASE_URL=http://localhost:8082/v1
KLIMTECH_LLM_API_KEY=sk-dummy
KLIMTECH_EMBEDDING_MODEL=intfloat/multilingual-e5-large
KLIMTECH_EMBEDDING_DEVICE=cpu
KLIMTECH_QDRANT_URL=http://localhost:6333
KLIMTECH_QDRANT_COLLECTION=klimtech_docs
KLIMTECH_API_KEY=sk-local
```

### Środowisko serwera

```fish
cd /media/lobo/BACKUP/KlimtechRAG && source venv/bin/activate.fish
python3 start_klimtech_v3.py    # start
python3 stop_klimtech.py        # stop
```

---

## 7. Kontenery Podman

| Kontener | Obraz | Volume | Uwagi |
|----------|-------|--------|-------|
| qdrant | qdrant/qdrant:latest | `klimtech_qdrant_data:/qdrant/storage` | Standalone |
| n8n | n8nio/n8n:latest | — | Standalone |
| postgres_nextcloud | postgres:16 | `klimtech_postgres_data:/var/lib/postgresql/data` | W pod klimtech_pod |
| nextcloud | nextcloud:32 | `klimtech_nextcloud_data:/var/www/html/data` | W pod klimtech_pod |

`start_klimtech_v3.py` — tworzy kontenery tylko jeśli nie istnieją, istniejące tylko startuje.

---

## 8. Inteligentna selekcja embeddera

`model_selector.py` automatycznie wybiera embedder na podstawie rozszerzenia pliku:

| Typ | Rozszerzenia | Model | Wymiar |
|-----|-------------|-------|--------|
| VISUAL | .pdf, .png, .jpg, .gif, .bmp, .webp | ColPali | 128 |
| SEMANTIC | .txt, .md, .docx, .csv, .json, .sql | e5-large | 1024 |
| CODE | .py, .js, .ts, .java, .cpp, .go, .rs (27 ext.) | bge-large-en-v1.5 | 1024 |

---

## 9. Kategorie RAG

14 kategorii w `categories/definitions.py`: medicine, law, finance, technology, construction, education, agriculture, society, culture, sport, family, religion, environment, other.

`classify_document(filepath, content)` — path-based + keyword-based (PL/EN/DE) + fallback "other".

Filtr Qdrant: `{"field": "meta.category", "operator": "==", "value": category}`.

---

## 10. Znane problemy

### Otwarte

| # | Priorytet | Problem | Status |
|---|-----------|---------|--------|
| 1 | 🔴 | Nextcloud AI Assistant — HTTP 417 (Expect header) | Do debugowania |
| 2 | 🔴 | VLM opis obrazów — brak mmproj w llama-cli | Nierozwiązane |
| 3 | 🔴 | `ingest_gpu.py` zabija `start_klimtech.py` | Obejście: `start_backend_gpu.py` |
| 4 | 🟡 | Race condition w `embeddings.py` (brak threading lock) | Niezaplikowane |
| 5 | 🟡 | File handle leak w `model_manager.py` (2 miejsca) | Niezaplikowane |
| 6 | 🟡 | ColPali alias "colpali" nie rozwiązywany w `embedder_pool.py` | Niezaplikowane |
| 7 | 🟡 | Deprecated `regex=` w `model_switch.py` (Pydantic v2) | Kosmetyczny |
| 8 | 🟡 | Nextcloud na exFAT — problemy z uprawnieniami PostgreSQL | Planowana migracja serwera |

### Rozwiązane (sesja 14, 2026-03-25)

- Merge conflicts (11 w Python, 2 w MD) — rozwiązane
- Frontend 401 (brak API key) — dodano wrapper `F()` z `X-API-Key`
- DuckDuckGo pusta odpowiedź — zmiana `duckduckgo_search` → `ddgs`
- `admin.py` duplikat parametru `req: Request` — usunięto
- `ChatCompletionResponse` brak pola `sources` — dodano
- Embedding na GPU (OOM) — zmieniono na `KLIMTECH_EMBEDDING_DEVICE=cpu`
- `safe_filename` undefined w `/ingest` — zmieniono na `file.filename`
- Qdrant bez persistent storage — dodano volume `klimtech_qdrant_data`
- `start_klimtech_v3.py` niszczył kontenery przy każdym restarcie — dodano check "pod exists"
- Web search za mało wyników (2-3) — zwiększono do 20

---

## 11. Komendy diagnostyczne

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/models
curl http://localhost:8000/rag/debug
curl http://localhost:8000/files/stats
curl http://localhost:8000/gpu/status
curl http://localhost:8000/web/status
podman ps -a --format "{{.Names}} {{.Status}}"
```

---

## 12. TODO

### Wysoki priorytet
- Re-indeksowanie dokumentów do Qdrant po resecie
- Debug NC Assistant 417 (Expect header middleware)
- Test Whisper STT
- Migracja serwera na Ubuntu z ext4

### Średni priorytet
- UI dropdown z kategoriami + endpoint `GET /categories`
- Podpięcie vlm_prompts do image_handler.py (krok 16d-16e)
- Threading lock w `embeddings.py`

### Niski priorytet
- `stop_klimtech.py` nie zabija wszystkich procesów
- Auto-transkrypcja audio w n8n
- Chunked summarization dla długich dokumentów

---

*Skonsolidowano: 2026-03-25 z plików PROJEKT_OPIS, PODSUMOWANIE, postep, ERRORS, AUDYT*
