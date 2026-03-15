# KlimtechRAG — Podsumowanie Projektu

**Data aktualizacji:** 2026-03-14  
**Wersja systemu:** v7.1 (Web Search + Dual Model)  
**Repozytorium:** https://github.com/Satham666/KlimtechRAG  
**Katalog serwera:** `/media/lobo/BACKUP/KlimtechRAG/`  
**Katalog laptopa:** `~/KlimtechRAG`

---

> **Nowe w v7.1:** Panel Web Search jako druga zakładka w sidebarzie (obok RAG), tryb hybrydowy RAG+Web, podgląd stron, podsumowanie przez LLM.

---

## 1. Cel projektu

**KlimtechRAG** to w pełni lokalny system RAG (Retrieval-Augmented Generation) do pracy z dokumentacją techniczną w języku polskim. Działa w 100% offline — LLM, embedding, OCR i VLM uruchamiane są lokalnie na serwerze Linux z GPU AMD Instinct 16 GB (ROCm/HIP).

### Główne zastosowania

- Odpowiadanie na pytania na podstawie zaindeksowanych dokumentów (PDF, DOCX, TXT, kod)
- Automatyczne OCR skanów i dokumentów graficznych
- Obsługa dokumentów z obrazkami, tabelami i wykresami (tryb VLM / ColPali)
- Wyszukiwanie w internecie jako fallback (DuckDuckGo)
- Tool calling — LLM może wykonywać operacje na plikach (ls, glob, read, grep)
- Baza wiedzy firmowej i technicznej z pełną suwerennością danych

---

## 2. Architektura systemu

### Diagram architektury

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PRZEGLĄDARKA  http://192.168.31.70:8000/              │
│              (HTML/JS UI — static/index.html)                          │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
              ┌───────────────▼──────────────────┐
              │    KlimtechRAG Backend FastAPI   │
              │    Port: 8000                    │
              │  ┌─────────────────────────────┐ │
              │  │ Rate Limiting (60/60s/IP)  │ │
              │  │ API Key Auth (opcjonalne)   │ │
              │  │ Answer Cache (TTL=1h)       │ │
              │  │ Request ID + Logging        │ │
              │  └─────────────────────────────┘ │
              └──────┬────────────────┬──────────────┘
                     │                │
     ┌───────────────┼────────────────┼────────────────┐
     │               │                │                │
┌────▼────┐    ┌─────▼─────┐   ┌────▼─────┐   ┌──────▼──────┐
│  Chat   │    │  Ingest   │   │  Model   │   │   Admin     │
│ Routes  │    │  Routes   │   │  Switch  │   │   Routes    │
│         │    │           │   │  Routes  │   │             │
│/query   │    │/upload    │   │/model/   │   │/health      │
│/v1/chat │    │/ingest    │   │status    │   │/metrics     │
│/v1/embed│    │/ingest_all│   │/model/   │   │/files/stats │
│/rag/dbg │    │/vlm/      │   │switch    │   │/ws/health   │
└────┬─────┘    └─────┬─────┘   └────┬─────┘   └──────┬──────┘
     │                │                │                │
     │     ┌──────────▼────────┐       │                │
     │     │  Qdrant (port 6333)│      │                │
     │     │  Kolekcje:         │      │                │
     │     │  - klimtech_docs   │      │                │
     │     │    (e5-large,      │      │                │
     │     │     1024d, cosine) │      │                │
     │     │  - klimtech_colpali│      │                │
     │     │    (ColPali,       │      │                │
     │     │     128d, MAX_SIM) │      │                │
     │     └────────────────────┘      │                │
     │                               │                │
┌────▼───────────────────────────────▼────────────────▼─────────────────┐
│                    llama.cpp-server (port 8082)                        │
│  ┌─────────────────────┐    ┌─────────────────────────────────────┐  │
│  │ LLM Mode            │    │ VLM Mode                             │  │
│  │ Bielik-11B-v3.0    │    │ Qwen2.5-VL-7B / LFM2.5-VL-1.6B     │  │
│  │ Bielik-4.5B        │    │ (+ mmproj do rozpoznawania obrazów) │  │
│  │ LFM2-2.6B          │    │                                      │  │
│  └─────────────────────┘    └─────────────────────────────────────┘  │
│  Context: 8192 tokens │ GPU layers: 99 │ Quant: Q8_0 / F16           │
└─────────────────────────────────────────────────────────────────────┘
     │
┌────▼──────────────────────────────────────────────────────────────────┐
│                      Podman Kontenery                                 │
│  ┌────────────┐ ┌────────────┐ ┌─────────────┐ ┌──────────────────┐  │
│  │  Qdrant    │ │ Nextcloud  │ │ PostgreSQL  │ │       n8n        │  │
│  │  (6333)    │ │  (8443)    │ │  (5432)     │ │     (5678)       │  │
│  └────────────┘ └────────────┘ └─────────────┘ └──────────────────┘  │
│  Wektorowa DB │ Pliki │ Nextcloud DB │ Automatyzacja workflowów    │
└──────────────────────────────────────────────────────────────────────┘
```

### Data Flow — Ingestion (indeksowanie dokumentów)

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│  Upload  │ ──► │  Ekstrakcja │ ──► │  Chunking   │ ──► │ Embedding   │
│  /upload │     │  tekstu     │     │  (200 słów) │     │ (e5-large/ │
└──────────┘     │  pdftotext  │     │             │     │  ColPali)  │
                 │  Docling    │     └─────────────┘     └──────┬──────┘
                 │  OCR fallback│                            │
                 └──────────────┘                            │
                                                              ▼
                    ┌────────────────────────────────────────────────┐
                    │  Qdrant (klimtech_docs / klimtech_colpali)   │
                    │  + SQLite file_registry.db (status: indexed) │
                    └────────────────────────────────────────────────┘
```

### Data Flow — Query (odpowiadanie na pytania)

```
┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│ Pytanie  │ ──► │  Embedding   │ ──► │  Retrieval  │ ──► │   Prompt   │
│  użytkow.│     │  (e5-large) │     │  (top_k=10) │     │  Builder   │
└──────────┘     └──────────────┘     └─────────────┘     └──────┬──────┘
                                                                      │
       ┌──────────────────────────────────────────────────────────────┘
       │                    Opcjonalnie:
       │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
       │  │   Cache      │    │ DuckDuckGo  │    │   Tool       │
       │  │  (TTL=1h)    │    │   Fallback  │    │   Calling    │
       │  └──────────────┘    └──────────────┘    └──────────────┘
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    llama.cpp-server (Bielik-11B)                    │
│                    → Odpowiedź z cytatami źródeł                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Stack technologiczny

### 3.1 Infrastruktura

| Warstwa | Technologia | Uwagi |
|---------|-------------|-------|
| **System operacyjny** | Linux Mint / Ubuntu 24 | Serwer + Laptop |
| **Python** | 3.12 (venv `/media/lobo/BACKUP/KlimtechRAG/venv`) | — |
| **GPU** | AMD Instinct 16 GB (AMD Radeon Pro VII) | ROCm 7.2, `HSA_OVERRIDE_GFX_VERSION=9.0.6` |
| **PyTorch** | 2.5.1+rocm6.2 | Wersja z ROCm (nie CUDA) |
| **Backend** | FastAPI + Haystack 2.x | Port 8000 |
| **LLM/VLM** | llama.cpp-server (build z `llama.cpp/`) | Port 8082 |
| **Wektorowa baza** | Qdrant | Port 6333, uruchomiony w Podman |
| **Kontenery** | Podman | qdrant, nextcloud, postgres_nextcloud, n8n |
| **Baza plików** | SQLite | file_registry.db — śledzenie statusu plików |
| **UI** | HTML/JS + Bootstrap | `backend_app/static/index.html` |
| **Sync** | Git → GitHub | laptop → push, serwer → pull |

### 3.2 Modele GGUF (katalog `modele_LLM/`)

#### Modele LLM (model_thinking/)

| Model | Plik | Rozmiar | Kwantyzacja | VRAM |
|-------|------|---------|-------------|------|
| Bielik-11B-v3.0-Instruct | `speakleash_Bielik-11B-v3.0-Instruct-GGUF_Bielik-11B-v3.0-Instruct.Q8_0.gguf` | ~14 GB | Q8_0 | ~14 GB |
| Bielik-4.5B-v3.0-Instruct | `speakleash_Bielik-4.5B-v3.0-Instruct-GGUF_Bielik-4.5B-v3.0-Instruct.Q8_0.gguf` | ~4.7 GB | Q8_0 | ~5 GB |
| LFM2-2.6B | `DevQuasar_LiquidAI.LFM2-2.6B-GGUF_LiquidAI.LFM2-2.6B.f16.gguf` | ~5.2 GB | F16 | ~6 GB |
| LFM2.5-1.2B-Base | `LiquidAI_LFM2.5-1.2B-Base-GGUF_LFM2.5-1.2B-Base-BF16.gguf` | ~2.4 GB | BF16 | ~3 GB |

#### Modele VLM (model_video/)

| Model | Plik GGUF | mmproj | Rozmiar |
|-------|-----------|--------|---------|
| LFM2.5-VL-1.6B | `LiquidAI_LFM2.5-VL-1.6B-GGUF_LFM2.5-VL-1.6B-BF16.gguf` | `LiquidAI_LFM2.5-VL-1.6B-GGUF_mmproj-LFM2.5-VL-1.6b-BF16.gguf` | ~3.2 GB |
| Qwen2.5-VL-7B-Instruct | `unsloth_Qwen2.5-VL-7B-Instruct-GGUF_Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf` | `unsloth_Qwen2.5-VL-7B-Instruct-GGUF_mmproj-BF16.gguf` | ~4.7 GB |
| Qwen2.5-VL-7B-Instruct | `unsloth_Qwen2.5-VL-7B-Instruct-GGUF_Qwen2.5-VL-7B-Instruct-UD-Q6_K_XL.gguf` | (j.w.) | ~6.2 GB |

#### Modele Audio (model_audio/)

| Model | Plik GGUF | mmproj |
|-------|-----------|--------|
| LFM2.5-Audio-1.5B | `LiquidAI_LFM2.5-Audio-1.5B-GGUF_LFM2.5-Audio-1.5B-F16.gguf` | `LiquidAI_LFM2.5-Audio-1.5B-GGUF_mmproj-LFM2.5-Audio-1.5B-F16.gguf` |

#### Modele Embedding GGUF (model_embedding/) — alternatywa dla HuggingFace

| Model | Plik | Wymiar |
|-------|------|--------|
| bge-large-en-v1.5 | `ChristianAzinn_bge-large-en-v1.5-gguf_bge-large-en-v1.5.Q8_0.gguf` | 1024 |
| Bge-M3-567M | `mykor_bge-m3.gguf_Bge-M3-567M-F32.gguf` | 1024 |

#### Rezerwa (puste katalogi)

- `model_medical/` — przewidziany dla domeny medycznej
- `model_financial_analysis/` — przewidziany dla analizy finansowej

### 3.3 Modele HuggingFace (pobierane automatycznie)

| Model | Typ | Wymiar | Kolekcja Qdrant |
|-------|-----|--------|-----------------|
| `intfloat/multilingual-e5-large` | Embedding tekstu | 1024 | `klimtech_docs` |
| `vidore/colpali-v1.3-hf` | Embedding wizualny PDF (multi-vector) | 128 | `klimtech_colpali` |

---

## 4. Struktura plików

### 4.1 Backend (`backend_app/`)

```
backend_app/
├── main.py                      # Entry point FastAPI (89 linii)
├── config.py                    # Pydantic Settings (konfiguracja)
├── file_registry.py             # SQLite — rejestracja plików, deduplicacja
├── monitoring.py                # CPU, RAM, GPU stats (ROCm)
├── fs_tools.py                  # Narzędzia filesystem dla LLM tool calling
│
├── routes/
│   ├── ui.py                   # Serwowanie static/index.html (GET /)
│   ├── chat.py                 # /v1/chat/completions, /query, /v1/embeddings
│   ├── ingest.py               # /upload, /ingest, /ingest_path, /ingest_all
│   ├── admin.py                # /health, /metrics, /files/stats, /files/pending
│   ├── model_switch.py         # /model/status, /model/switch, /model/list
│   └── filesystem.py           # /fs/list, /fs/glob, /fs/read, /fs/grep
│
├── services/
│   ├── qdrant.py               # QdrantDocumentStore singleton (Haystack)
│   ├── embeddings.py            # SentenceTransformersTextEmbedder (e5-large)
│   ├── rag.py                  # Haystack pipelines (indexing + RAG)
│   ├── llm.py                  # LLM wrapper (llama.cpp HTTP client)
│   ├── model_manager.py        # Zarządzanie llama-server (start/stop/switch)
│   └── colpali_embedder.py     # ColPali multi-vector embedder
│
├── models/
│   └── schemas.py              # Pydantic schemas (ChatMessage, QueryRequest, itd.)
│
├── utils/
│   ├── rate_limit.py           # Rate limiting (60 req/60s per IP)
│   ├── tools.py                # LLM tool calling parser + executor
│   └── dependencies.py        # FastAPI deps (require_api_key, get_request_id)
│
├── scripts/
│   ├── watch_nextcloud.py      # Watchdog — monitoruje nowe pliki w Nextcloud
│   ├── ingest_gpu.py           # Batch indeksowanie na GPU
│   ├── ingest_pdfCPU.py       # PDF OCR na CPU (RapidOCR + ONNX)
│   ├── ingest_pdfGPU.py        # PDF OCR na GPU (EasyOCR)
│   ├── ingest_colpali.py       # ColPali CLI (indeksowanie, status, search)
│   ├── ingest_repo.py          # Indeksowanie repozytoriów Git
│   └── model_parametr.py       # Kalkulator parametrów VRAM dla llama-server
│
├── ingest/
│   └── image_handler.py         # Ekstrakcja obrazów z PDF (PyMuPDF)
│
└── static/
    └── index.html              # Główny UI (HTML/JS + Bootstrap)
```

### 4.2 Pliki główne w root projektu

```
KlimtechRAG/
├── .env                         # Konfiguracja (KLIMTECH_*)
├── .gitignore
│
├── start_klimtech_v3.py         # Główny skrypt startowy (v7.0, Dual Model)
├── start_backend_gpu.py         # Backend z GPU embedding (bez LLM)
├── stop_klimtech.py             # Zatrzymanie wszystkich usług
│
├── ingest_embed.py              # Embedding standalone (GGUF via llama.cpp)
├── ingest_fix.py                # Naprawa ingestu (jednorazowe)
│
├── scraper.py                   # Web scraper (GitHub trending)
├── download_readme.py           # Pobieranie README z repozytoriów
├── fork_repos.py                # Zarządzanie forkami
├── github_trending.py           # GitHub trending repos
│
├── PODSUMOWANIE.md              # Ten dokument
├── PODSUMOWANIE_PROJEKTU_KLIMTECHRAG.md  # Rozszerzone podsumowanie
├── notatki.md                   # Robocze notatki
├── DRZEWO.md                    # Dokumentacja drzewa katalogów
├── GIT_KOMENDY.md               # Referencja komend git
│
├── kreuzberg/                   # Zewnętrzne lib (document extraction, Rust)
├── leki/                        # Scraper bazy leków (osobny projekt)
├── llama.cpp/                   # Zbudowane binaria (llama-server, llama-cli)
├── modele_LLM/                  # Modele GGUF (LLM, VLM, Audio, Embedding)
├── data/                        # Runtime data (gitignored)
│
└── venv/                        # Virtual environment Python 3.12
```

### 4.3 Katalog `data/` (runtime, gitignored)

```
data/
├── file_registry.db            # SQLite — śledzenie plików i statusu indeksowania
├── qdrant/                     # Qdrant persistent storage
├── uploads/                    # Lokalne kopie uploadów (backup)
│   ├── pdf_RAG/
│   ├── Doc_RAG/
│   ├── txt_RAG/
│   ├── json_RAG/
│   ├── Audio_RAG/
│   ├── Video_RAG/
│   └── Images_RAG/
├── nextcloud/                  # Nextcloud data volume
│   └── data/admin/files/RAG_Dane/   # Główny katalog dla plików RAG
│       ├── pdf_RAG/
│       ├── Doc_RAG/
│       ├── txt_RAG/
│       ├── json_RAG/
│       ├── Audio_RAG/
│       ├── Video_RAG/
│       └── Images_RAG/
├── nextcloud_db/               # Nextcloud MariaDB/MySQL
├── postgres/                   # PostgreSQL dla n8n
├── n8n/                        # n8n workflows
└── tmp/                        # Pliki tymczasowe
```

---

## 5. Backend — Endpointy API

### 5.1 Chat & RAG (8 endpointów)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/v1/models` | Lista modeli (OpenAI-compatible, dla OWUI) |
| POST | `/v1/embeddings` | Tworzenie embeddingów tekstu (e5-large, 1024d) |
| POST | `/query` | Podstawowy RAG query + cache (TTL=1h) + DuckDuckGo fallback + tool loop |
| POST | `/v1/chat/completions` | OpenAI-compatible chat + RAG (standard lub ColPali) |
| POST | `/chat/completions` | Alias `/v1/chat/completions` |
| POST | `/code_query` | RAG dla kodu (Senior Python Developer prompt) + tool loop |
| GET | `/rag/debug` | Diagnostyka pipeline RAG (status Qdrant, test retrieval, cache stats) |
| GET | `/` | Główny UI HTML |

### 5.2 Ingest & Upload (6 endpointów)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/upload` | Upload pliku → deduplicacja (SHA-256) → zapis do Nextcloud → background indexing |
| POST | `/ingest` | Legacy: indeksowanie bezpośrednie (bez Nextcloud) |
| POST | `/ingest_path` | Indeksowanie pliku ze ścieżki (dla watchdog/OWUI) |
| POST | `/ingest_all` | Batch indeksowanie wszystkich pending plików |
| POST | `/ingest_pdf_vlm` | Indeksowanie PDF z opisami obrazów przez VLM |
| GET | `/vlm/status` | Status serwera VLM (running/stopped, port) |

### 5.3 Model Management (10 endpointów)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/model/status` | Status serwera LLM/VLM (running, model_type, port) |
| POST | `/model/switch/llm` | Przełączenie na tryb LLM (kill + start, ~20-25s) |
| POST | `/model/switch/vlm` | Przełączenie na tryb VLM (kill + start, ~20-25s) |
| POST | `/model/switch` | Przełączenie przez query param (`?model_type=llm` lub `vlm`) |
| GET | `/model/list` | Lista wszystkich modeli z dysku (LLM, VLM, Audio, Embedding) |
| GET | `/model/config` | Pełna konfiguracja modeli (z `models.yaml` lub equivalent) |
| GET | `/model/ui` | HTML UI do przełączania modeli (z live status polling) |
| POST | `/model/start` | Start llama-server dla wybranego modelu (background thread) |
| GET | `/model/progress-log` | Log postępu ładowania modelu (dla UI polling ~500ms) |
| POST | `/model/stop` | Zatrzymanie serwera LLM/VLM |

### 5.4 Admin & Monitoring (8 endpointów)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/health` | Health check (Qdrant + LLM availability) |
| GET | `/metrics` | Liczniki requestów (ingest, query, code_query) |
| DELETE | `/documents` | Usuwanie dokumentów z Qdrant (filtr: source, doc_id) |
| WS | `/ws/health` | WebSocket continuous health monitoring |
| GET | `/files/stats` | Statystyki: file registry + Qdrant (points, indexed) |
| GET | `/files/list` | Lista plików z rejestru (filtr: extension, status) |
| POST | `/files/sync` | Sync rejestru plików z filesystemem |
| GET | `/files/pending` | Lista plików pending indeksowania |

### 5.5 Filesystem Tools (4 endpointy) — dla LLM Tool Calling

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/fs/list` | Lista katalogów (sandboxed pod fs_root) |
| POST | `/fs/glob` | Wyszukiwanie plików po glob (z limitem) |
| POST | `/fs/read` | Czytanie pliku tekstowego (paginated, max 512KB) |
| POST | `/fs/grep` | Wyszukiwanie w plikach (regex/literal, max 1MB/plik, 200 matchy) |

### 5.6 Web Search (4 endpointy)

| Metoda | Endpoint | Opis |
|--------|----------|------|
| GET | `/web/status` | Status dostępności (duckduckgo, trafilatura) |
| POST | `/web/search` | Wyszukiwanie w internecie (DuckDuckGo, max 5 wyników) |
| POST | `/web/fetch` | Pobieranie treści strony (konwersja HTML→tekst przez trafilatura) |
| POST | `/web/summary` | Podsumowanie strony przez LLM |

---

## 6. Funkcjonalności

### 6.1 RAG Pipeline

#### Ingestion (indeksowanie dokumentów)

1. Upload przez `/upload` lub watchdog Nextcloud
2. Deduplicacja w `file_registry.db` (SHA-256 hash, pliki <10MB)
3. Ekstrakcja tekstu:
   - Pierwszeństwo: `pdftotext` (fast, ~1-2s)
   - Fallback: Docling OCR (slow, ~15min CPU / ~13s GPU)
4. Chunking: 200 słów, 30 słów overlap (Haystack `DocumentSplitter`)
5. Embedding: `multilingual-e5-large` (1024-dim, CUDA lub CPU)
6. Zapis do Qdrant `klimtech_docs`
7. Status w SQLite: `pending` → `indexed` (z chunks_count i timestamp)

#### Query (odpowiadanie na pytania)

1. Embedding zapytania (e5-large)
2. Retrieval top-k=10 z Qdrant
3. Budowa promptu z kontekstem (system prompt PL)
4. Generacja odpowiedzi przez Bielik-11B
5. Zwrot z cytatami źródeł

### 6.2 ColPali — Wizualne Embedding PDF

ColPali (`vidore/colpali-v1.3-hf`) to alternatywny pipeline dla dokumentów wizualnych:

| Cecha | e5-large (tekst) | ColPali (wizualny) |
|-------|------------------|---------------------|
| Wejście | Tekst (chunki) | Obraz strony PDF |
| Wyjście | 1 wektor × 1024d | ~1000 wektorów × 128d |
| Kolekcja Qdrant | `klimtech_docs` | `klimtech_colpali` |
| OCR potrzebny? | Tak | Nie — widzi wizualnie |
| Rozumie tabele/wykresy | Słabo | Tak |
| VRAM | ~2.5 GB | ~6-8 GB |
| Scoring | Cosine similarity | MAX_SIM (late interaction) |

#### Uruchamianie indeksowania ColPali

```bash
# WAŻNE: zatrzymaj LLM przed uruchomieniem (konflikt VRAM)
pkill -f llama-server

# Jeden plik:
python3 -m backend_app.scripts.ingest_colpali --file data/uploads/pdf_RAG/plik.pdf

# Cały katalog:
python3 -m backend_app.scripts.ingest_colpali --dir data/uploads/pdf_RAG

# Status kolekcji:
python3 -m backend_app.scripts.ingest_colpali --status

# Test wyszukiwania:
python3 -m backend_app.scripts.ingest_colpali --search "szukana fraza"
```

### 6.3 File Registry (SQLite)

`file_registry.py` śledzi wszystkie pliki przeznaczone do indeksowania:

- **Deduplicacja:** SHA-256 hash (pliki <10MB), sprawdzenie `SELECT path FROM files WHERE content_hash = ?`
- **Statusy:** `pending` → `indexed` → `error`
- **Kolumny:** id, path, filename, extension, directory, size_bytes, mtime, content_hash, indexed_at, chunks_count, status, error_message
- **Indeksy:** status, extension, directory
- **14 katalogów:** 2 base × 7 subdir (Audio_RAG, Doc_RAG, Images_RAG, json_RAG, pdf_RAG, txt_RAG, Video_RAG)

### 6.4 Cache Odpowiedzi

Implementacja w `routes/chat.py`:

| Parametr | Wartość |
|----------|---------|
| Typ | In-memory dict (`_answer_cache: Dict[str, Tuple[str, float]]`) |
| TTL | 3600 sekund (1 godzina) |
| Max rozmiar | 500 wpisów |
| Eviction | Oldest-first (po timestamp) |
| Zakres | Tylko endpoint `/query` (nie `/v1/chat/completions`) |

### 6.5 DuckDuckGo Web Search (backend)

- **Endpoint:** `/query` (tylko ten ma fallback)
- **Biblioteka:** `duckduckgo_search.DDGS`
- **Max wyników:** 2
- **Mechanizm:** Jeśli RAG nie zwróci wystarczających dokumentów, wyszukuje w internecie i dodaje jako synthetic document z `meta={"source": "Web Search"}`
- **Błędy:** Cichnie logowane, system kontynuuje z lokalnymi dokumentami

### 6.6 Web Search UI (nowe — zakładka w sidebarze)

Od wersji v7.1: Panel Web Search jako osobna zakładka w sidebarze obok RAG.

- **Lokalizacja:** Sidebar → zakładka "🌐 Web Search" (druga zakładka obok "📚 RAG")
- **Silnik:** DuckDuckGo (biblioteka `duckduckgo_search.DDGS`)
- **Funkcje:**
  - Wyszukiwanie w internecie z wynikami ( tytuł, URL, snippet)
  - Podgląd strony (fetch HTML → tekst przez `trafilatura`)
  - Dodaj do RAG — pobranie treści i dodanie jako kontekst
  - Podsumowanie strony przez LLM
  - Historia wyszukiwań (localStorage, max 20 wpisów)
  - Tryb hybrydowy RAG+Web — ikona 🌐 w input bar aktywuje wyszukiwanie web razem z RAG
- **Endpointy:**
  - `POST /web/search` — wyszukiwanie
  - `POST /web/fetch` — pobieranie strony
  - `POST /web/summarize` — podsumowanie przez LLM
  - `GET /web/status` — status dostępności

### 6.7 LLM Tool Calling

`utils/tools.py` — LLM może wykonywać operacje na plikach:

| Tool | Argumenty | Opis | Limity |
|------|-----------|------|--------|
| `ls` | `path` | Lista katalogów (`ls -la`) | 5s timeout |
| `glob` | `pattern`, `limit` | Glob search (rekursywny) | max 200 wyników |
| `read` | `path`, `offset`, `limit` | Czytanie pliku (z numerami linii) | max 512 KB |
| `grep` | `path`, `query`, `regex`, `case_insensitive`, `file_glob` | Wyszukiwanie w plikach | max 1 MB/plik, 200 matchy |

**Bezpieczeństwo:** Wszystkie ścieżki sandboxowane pod `fs_root` (base_path projektu). Ścieżki wychodzące poza root zwracają `FsSecurityError`.

**Parsowanie:** LLM musi zwrócić JSON `{"tool": "nazwa", "args": {...}}`. System sprawdza czy tekst zaczyna się od `{` i kończy na `}`.

**Pętla:** Maksymalnie 3 iteracje (tool → result → re-prompt LLM).

### 6.8 Model Switch (LLM/VLM Hot-Swap)

`services/model_manager.py`:

- **Port:** 8082
- **Lifecycle:** `stop_llm_server()` → czekaj 5s (VRAM release) → `start_llm_server()` → aktualizuj config
- **llama-server params:** `-ngl 99` (all layers), `-c 8192` (context), `--host 0.0.0.0 --port 8082`
- **VLM:** automatyczne wykrywanie plików `*mmproj*` i dodanie `--mmproj`
- **AMD GPU:** hardcoded env vars: `HIP_VISIBLE_DEVICES=0`, `GPU_MAX_ALLOC_PERCENT=100`, `HSA_OVERRIDE_GFX_VERSION=9.0.6`
- **Config persistence:** `logs/models_config.json` (model_type, model_paths, timestamp)
- **Progress logging:** `logs/llm_progress.log` (background thread, front-end polling przez `/model/progress-log`)

### 6.9 Rate Limiting

`utils/rate_limit.py`:

| Parametr | Wartość |
|----------|---------|
| Algorytm | Sliding window (timestamp-based) |
| Okno | 60 sekund |
| Max requestów | 60 (1 req/s sustained) |
| Identyfikacja | Client IP (`request.client.host`) |
| Storage | In-memory dict (tracony po restarcie servera) |

**Endpointy z rate limiting:** `/query`, `/v1/chat/completions`, `/code_query`

### 6.10 API Key Authentication

`utils/dependencies.py` — `require_api_key()`:

- Odczytuje z nagłówka `X-API-Key`
- Porównuje z `settings.api_key`
- Jeśli `settings.api_key = None` (dev mode) — brak autoryzacji
- Brak klucza = `401 Unauthorized`

---

## 7. Konfiguracja

### 7.1 Zmienne środowiskowe (config.py)

Wszystkie zmienne mają prefix `KLIMTECH_` (np. `KLIMTECH_QDRANT_URL`). Wartości domyślne:

| Kategoria | Zmienna | Domyślna wartość |
|-----------|---------|------------------|
| **Ścieżki** | `base_path` | Auto-detect (env / ~/KlimtechRAG / /media/lobo/BACKUP/KlimtechRAG) |
| | `data_path` | `{base_path}/data` |
| | `upload_base` | `{base_path}/data/uploads` |
| | `nextcloud_base` | `{base_path}/data/nextcloud/data/admin/files/RAG_Dane` |
| | `file_registry_db` | `{base_path}/data/file_registry.db` |
| **Nextcloud** | `nextcloud_container` | `"nextcloud"` |
| | `nextcloud_user` | `"admin"` |
| **LLM** | `llm_base_url` | `http://localhost:8082/v1` |
| | `llm_api_key` | `"sk-dummy"` |
| | `llm_model_name` | `""` (auto-detect) |
| **Embedding** | `embedding_model` | `"intfloat/multilingual-e5-large"` |
| | `embedding_device` | Z env `KLIMTECH_EMBEDDING_DEVICE`, domyślnie `"cpu"` |
| **Qdrant** | `qdrant_url` | `http://localhost:6333` |
| | `qdrant_collection` | `"klimtech_docs"` |
| **Bezpieczeństwo** | `api_key` | `None` (auth disabled w dev) |
| | `rate_limit_window_seconds` | `60` |
| | `rate_limit_max_requests` | `60` |
| **Filesystem Tools** | `fs_root` | `{base_path}` |
| | `fs_max_file_bytes_read` | `524288` (512 KB) |
| | `fs_max_file_bytes_grep` | `1048576` (1 MB) |
| | `fs_max_matches_grep` | `200` |
| **Pliki** | `max_file_size_bytes` | `209715200` (200 MB) |
| **Logging** | `log_level` | `"INFO"` (z env `LOG_LEVEL`) |
| | `log_json` | `false` |

### 7.2 Plik `.env` — przykładowa konfiguracja

```bash
KLIMTECH_BASE_PATH=/media/lobo/BACKUP/KlimtechRAG
KLIMTECH_UPLOAD_BASE=/media/lobo/BACKUP/KlimtechRAG/data/uploads
KLIMTECH_NEXTCLOUD_BASE=/media/lobo/BACKUP/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane
KLIMTECH_FILE_REGISTRY_DB=/media/lobo/BACKUP/KlimtechRAG/data/file_registry.db

KLIMTECH_LLM_BASE_URL=http://localhost:8082/v1
KLIMTECH_LLM_API_KEY=sk-dummy

KLIMTECH_EMBEDDING_MODEL=intfloat/multilingual-e5-large
KLIMTECH_EMBEDDING_DEVICE=cuda:0

KLIMTECH_QDRANT_URL=http://localhost:6333
KLIMTECH_QDRANT_COLLECTION=klimtech_docs

BACKEND_PORT=8000
LLAMA_API_PORT=8082

# Opcjonalnie — API key auth (zakomentowane = brak auth):
# KLIMTECH_API_KEY=your-secret-key-here
```

---

## 8. Wydajność i metryki

### 8.1 Porównanie CPU vs GPU

| Operacja | CPU | GPU | Przyspieszenie |
|----------|-----|-----|----------------|
| Embedding batch | ~18s | ~1.4s | **13×** |
| PDF 20MB (307 chunków) | ~15 min | ~13s | **~70×** |
| Retrieval (top_k=10) | <100ms | — | — |
| LLM generation (Bielik-11B) | — | ~15 tok/s | — |

### 8.2 Stan bazy danych

| Metryka | Wartość |
|---------|---------|
| Zaindeksowane chunki | 5114+ |
| Rozmiar kolekcji Qdrant | ~1.2 GB |
| Kolekcja tekstowa | `klimtech_docs` (e5-large, 1024d, cosine) |
| Kolekcja wizualna | `klimtech_colpali` (ColPali, 128d, MAX_SIM) |

### 8.3 Limity systemowe

| Limit | Wartość |
|-------|---------|
| Max rozmiar uploadu | 200 MB |
| Max rozmiar pliku do read (tool) | 512 KB |
| Max rozmiar pliku do grep (tool) | 1 MB |
| Max matchy grep | 200 |
| Max rozmiar pliku do hash | 10 MB |
| Rozmiar cache (odpowiedzi) | 500 wpisów |
| TTL cache | 3600s (1h) |
| Rate limit | 60 req/60s per IP |
| LLM context length | 8192 tokenów |
| GPU layers offloaded | 99 (all) |

### 8.4 VRAM

| Komponent | Zużycie |
|-----------|---------|
| LLM Bielik-11B Q8_0 | ~14 GB |
| LLM Bielik-4.5B Q8_0 | ~5 GB |
| Embedding e5-large | ~2.5 GB |
| ColPali | ~6-8 GB |
| **Razem (GPU 16GB)** | Tylko jeden naraz: LLM LUB Embedding/ColPali |

---

## 9. Historia sesji

### Sesja 1 — Diagnoza (2026-02-20)
- Naprawiono OCR (`bitmap_area_threshold=0.0`, język PL)
- `top_k` zwiększone z 3 → 10
- Skrypty `ingest_pdfCPU.py`, `ingest_pdfGPU.py`
- Reset Qdrant i `file_registry.db`

### Sesja 2 — Refaktoryzacja (2026-02-20 19:17)
- Monolit `main.py` (1350 linii) → moduły (89 linii main, -93%)
- Nowa struktura: `routes/`, `services/`, `models/`, `utils/`, `scripts/`
- Pydantic Settings + `.env`
- `/rag/debug`, logi do pliku, PID file dla watchdog

### Sesja 3 — GPU Embedding i VLM (2026-02-21 01:20)
- GPU embedding: **13× szybszy** (batch: 18s → 1.4s)
- PDF 20MB (307 chunków): **~70× szybszy** (~15 min → 13s)
- `ingest_gpu.py`, ekstrakcja obrazów z PDF (PyMuPDF)
- HNSW threshold naprawiony w `services/qdrant.py`
- VLM opis obrazów nie działa (brak mmproj)

### Sesja 4 — Własny UI (2026-02-xx)
- HTML/JS czat wbudowany w FastAPI (`routes/ui.py` → `static/index.html`)
- Sidebar z historią sesji, eksport/import JSON
- Upload drag&drop, przycisk "Indeksuj pliki w RAG"
- Toggle VLM/LLM, statystyki, wskaźnik statusu backendu

### Sesja 5 — Model Switch API (2026-02-xx)
- `routes/model_switch.py` — API przełączania modeli
- `GET /model/status`, `POST /model/switch/{llm|vlm}`
- `GET /model/list`, `GET /model/config`

### Sesja 6 — start_klimtech_v3.py (2026-03-xx)
- Skrypt v7.0 — Dual Model Selection (LLM + VLM przy starcie)
- Automatyczne zarządzanie VRAM (pkill + czekanie)
- Konfiguracja zapisywana do `logs/models_config.json`
- Interaktywne menu terminalu (opcje 1–5, q)
- `model_parametr.py` — obliczanie parametrów VRAM

### Sesja 7 — Wymagania i ColPali (2026-03-13/14)
- Wygenerowano nowe `PODSUMOWANIE.md`
- Zdefiniowano wymagania UI (wybór modelu, okienko POSTĘP, menu przyciski)
- Napisano `backend_app/services/colpali_embedder.py`
- Napisano `backend_app/scripts/ingest_colpali.py`
- ColPali dodany do `get_available_models()` w `model_manager.py`
- Wyczyszczono `.env` (usunięto duplikaty OWUI, BACKEND_API_PORT, KLIMTECH_DATA_PATH)

### Sesja 8 — ROCm + Backend (2026-03-14)
- **Podmieniono PyTorch CUDA → ROCm 6.2** (`torch 2.5.1+rocm6.2`)
- **Zdiagnozowano i uruchomiono backend** po awarii
- **Potwierdzono działanie GPU embeddingu** (VRAM: 7.2 GB, temp: 85-90°C)
- **Wyczyszczono `.env`**
- **ColPali widoczny w `/model/list`**

---

## 10. Znane problemy

| # | Priorytet | Problem | Status |
|---|-----------|---------|--------|
| 1 | 🔴 | VLM opis obrazów nie działa (brak mmproj dla niektórych modeli) | Nierozwiązane |
| 2 | 🔴 | `ingest_gpu.py` zabija `start_klimtech.py` (konflikt GPU/proces) | Nierozwiązane |
| 3 | 🟡 | `monitoring.py` zwraca `GPU: 0%` dla AMD ROCm (źle parsuje output) | Kosmetyczny |
| 4 | 🟡 | `stop_klimtech.py` nie zabija wszystkich procesów | Do naprawy |
| 5 | 🟢 | `@router.on_event("startup")` deprecated w FastAPI | Nie wpływa na działanie |

---

## 11. Komendy operacyjne

### 11.1 Aktywacja środowiska wirtualnego (WYMAGANE!)

```bash
# ZAWSZE najpierw aktywuj venv
source /media/lobo/BACKUP/KlimtechRAG/venv/bin/activate

# Po aktywacji Twój prompt powinien się zmienić na:
(venv) lobo@host:/media/lobo/BACKUP/KlimtechRAG$

# Teraz możesz:
# - Instalować pakiety: pip3 install nazwa-pakietu
# - Uruchamiać Python: python3 script.py
# - Uruchamiać backend: python3 -m uvicorn ...
```

### 11.2 Sync kodu

```bash
# Laptop → GitHub:
git add -A && git commit -m "Sync" -a || true && git push --force

# Serwer ← GitHub:
git config pull.rebase false && git pull
```

### 11.3 Uruchomienie backendu

```bash
# 1. Aktywuj venv
source /media/lobo/BACKUP/KlimtechRAG/venv/bin/activate

# 2. Uruchom backend
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000
```

### 11.4 Sprawdzenie GPU

```bash
python3 -c "import torch; print(torch.__version__); print('GPU:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
# Oczekiwany wynik: 2.5.1+rocm6.2 / GPU: True / AMD Radeon (TM) Pro VII
```

### 11.5 Reinstalacja PyTorch ROCm (jeśli potrzeba)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.2 --force-reinstall --break-system-packages
```

### 11.6 Diagnostyka

```bash
# Health check
curl http://192.168.31.70:8000/health

# Lista modeli
curl http://192.168.31.70:8000/model/list | python3 -m json.tool

# Debug RAG
curl http://192.168.31.70:8000/rag/debug | python3 -m json.tool

# Statystyki plików
curl http://192.168.31.70:8000/files/stats | python3 -m json.tool

# Pliki pending
curl http://192.168.31.70:8000/files/pending | python3 -m json.tool

# GPU monitoring
rocm-smi
nvtop
```

### 11.7 Indeksowanie ColPali

```bash
# UWAGA: najpierw zatrzymaj LLM (konflikt VRAM)
pkill -f llama-server

# Indeksuj plik
python3 -m backend_app.scripts.ingest_colpali --file data/uploads/pdf_RAG/plik.pdf

# Indeksuj katalog
python3 -m backend_app.scripts.ingest_colpali --dir data/uploads/pdf_RAG

# Status
python3 -m backend_app.scripts.ingest_colpali --status

# Szukaj
python3 -m backend_app.scripts.ingest_colpali --search "fraza"
```

---

## 12. Adresy sieciowe

| Usługa | Adres |
|--------|-------|
| 🔧 API Backend | http://192.168.31.70:8000 |
| 📦 Qdrant (wektory) | http://192.168.31.70:6333 |
| ☁️ Nextcloud | http://192.168.31.70:8443 |
| 🔗 n8n (automation) | http://192.168.31.70:5678 |
| 🤖 LLM/VLM (llama-server) | http://192.168.31.70:8082 (po załadowaniu modelu) |

---

## 13. Dodatek: Szybki start

### Uruchomienie pełnego systemu

```bash
cd /media/lobo/BACKUP/KlimtechRAG

# 1. Uruchom Qdrant (jeśli nie działa)
podman run -d --name qdrant -p 6333:6333 -v $(pwd)/data/qdrant:/qdrant/storage qdrant/qdrant

# 2. Aktywuj venv
source venv/bin/activate

# 3. Uruchom backend
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000 &

# 4. Poczekaj i uruchom LLM (opcjonalnie)
# Można to zrobić przez UI: http://192.168.31.70:8000/model/ui
```

### Upload i indeksowanie dokumentu

```bash
# Przez API:
curl -X POST -F "file=@dokument.pdf" http://192.168.31.70:8000/upload

# Przez UI:
# Otwórz http://192.168.31.70:8000 → przeciągnij plik → kliknij "Indeksuj"
```

### Zadawanie pytań

```bash
# Przez API:
curl -X POST http://192.168.31.70:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Co zawiera dokumentacja?"}'

# Przez UI:
# Otwórz http://192.168.31.70:8000 → wpisz pytanie w czacie
```

---

*Ostatnia aktualizacja: 2026-03-14 — v7.1: Web Search (zakładka w sidebarzie, tryb hybrydowy RAG+Web, podgląd, podsumowanie LLM)*
