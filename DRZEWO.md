# Drzewo katalogów KlimtechRAG

*Wygenerowano: 2026-02-20*

---

## Struktura główna

```
~/KlimtechRAG/
├── .env                    # Konfiguracja środowiskowa
├── start_klimtech.py       # Uruchomienie wszystkich usług
├── stop_klimtech.py        # Zatrzymanie wszystkich usług
├── backend_app/            # Główna aplikacja FastAPI
├── data/                   # Dane (Qdrant, uploads, Nextcloud, PostgreSQL)
├── llama.cpp/              # llama.cpp binaries (pominięte w drzewie)
└── venv/                   # Środowisko wirtualne Python (pominięte w drzewie)
```

---

## backend_app/ - Aplikacja FastAPI

```
backend_app/
├── main.py                 # Entry point, FastAPI app, middleware (~89 linii)
├── config.py               # Centralna konfiguracja (Settings, ścieżki)
├── file_registry.py        # Rejestr plików do indeksowania (SQLite)
├── monitoring.py           # Statystyki systemu (CPU, RAM, GPU AMD)
├── fs_tools.py             # Narzędzia filesystem (ls, glob, grep, read)
│
├── models/
│   ├── __init__.py
│   └── schemas.py          # Pydantic models (ChatMessage, Request, Response)
│
├── routes/
│   ├── __init__.py
│   ├── chat.py             # /query, /code_query, /v1/chat/completions
│   ├── ingest.py           # /ingest, /upload, /ingest_path, /ingest_all
│   ├── filesystem.py       # /fs/list, /fs/glob, /fs/read, /fs/grep
│   ├── admin.py            # /health, /metrics, /documents, /files/*
│   └── ui.py               # /, /chat (interfejs HTML)
│
├── services/
│   ├── __init__.py
│   ├── qdrant.py           # Singleton QdrantDocumentStore
│   ├── embeddings.py       # Singleton embedder (SentenceTransformers)
│   ├── rag.py              # RAG pipeline + indexing pipeline
│   └── llm.py              # OpenAIGenerator wrapper
│
├── utils/
│   ├── __init__.py
│   ├── rate_limit.py       # Rate limiting per client IP
│   └── tools.py            # Tool calling (ls, glob, grep, read dla LLM)
│
└── scripts/
    ├── ingest_pdfCPU.py    # OCR na CPU (RapidOCR + onnxruntime)
    ├── ingest_pdfGPU.py    # OCR na GPU (EasyOCR) + podział strony + resume
    ├── ingest_repo.py      # Indeksowanie repozytoriów git
    ├── model_parametr.py   # Parametry modelu LLM
    └── watch_nextcloud.py  # Watchdog do automatycznego indeksowania
```

---

## data/ - Dane

```
data/
├── file_registry.db        # Baza SQLite z rejestrem plików
├── qdrant/                 # Baza wektorowa Qdrant
│   ├── collections/
│   └── raft_state.json
├── uploads/                # Pliki wrzucone przez API
│   ├── Audio_RAG/
│   ├── Doc_RAG/
│   ├── Images_RAG/
│   ├── json_RAG/
│   ├── pdf_RAG/
│   ├── txt_RAG/
│   └── Video_RAG/
├── nextcloud/              # Instancja Nextcloud
├── nextcloud_db/           # Baza Nextcloud (MariaDB/MySQL)
├── postgres/               # PostgreSQL dla n8n
├── n8n/                    # Automatyzacja n8n
└── tmp/
```

---

## Opis plików .py

### Główny katalog

| Plik | Opis |
|------|------|
| `start_klimtech.py` | Uruchamia Qdrant, n8n, Nextcloud, PostgreSQL, llama.cpp-server, backend |
| `stop_klimtech.py` | Zatrzymuje wszystkie usługi |

### backend_app/main.py
Entry point aplikacji FastAPI. Rejestruje routery, middleware (request ID, logging), exception handler.

### backend_app/config.py
Centralna konfiguracja przez pydantic-settings. Zmienne środowiskowe z prefiksem `KLIMTECH_`.
- URL Qdrant, LLM
- Ścieżki: `base_path`, `upload_base`, `nextcloud_base`, `file_registry_db`
- Limity: rate limiting, rozmiar plików

### backend_app/routes/chat.py
- `/query` - zapytanie RAG + web search (DuckDuckGo)
- `/code_query` - zapytanie do analizy kodu
- `/v1/chat/completions` - endpoint kompatybilny z OpenAI API

### backend_app/routes/ingest.py
- `/ingest` - upload pliku do indeksowania
- `/upload` - upload pliku do katalogu RAG (automatyczny podział wg rozszerzenia)
- `/ingest_path` - indeksowanie pliku ze ścieżki
- `/ingest_all` - indeksowanie wszystkich pending files

### backend_app/services/rag.py
- `indexing_pipeline` - splitter → embedder → writer
- `rag_pipeline` - embedder → retriever → prompt_builder → llm

### backend_app/scripts/watch_nextcloud.py
Watchdog monitorujący katalogi RAG_Dane w Nextcloud i uploads. Automatycznie rejestruje nowe pliki do indeksowania.

---

## Zależności

```
start_klimtech.py
    │
    ├── llama.cpp-server (port 8082)
    │       └── model GGUF (Bielik lub inny)
    │
    ├── Qdrant (port 6333)
    │
    ├── PostgreSQL (port 5432)
    │
    ├── n8n (port 5678)
    │
    ├── Nextcloud (port 8080)
    │
    └── backend_app/main.py (port 8000)
            ├── services/qdrant.py → Qdrant
            ├── services/llm.py → llama.cpp-server
            └── services/embeddings.py → SentenceTransformers
```

---

## Szybkie komendy

```bash
# Uruchomienie
source venv/bin/activate.fish
python start_klimtech.py

# Zatrzymanie
python stop_klimtech.py

# Test importu backend
cd ~/KlimtechRAG && source venv/bin/activate
python -c "from backend_app.main import app; print('OK')"

# Sprawdzenie Qdrant
curl http://localhost:6333/collections/klimtech_docs

# Health check backend
curl http://localhost:8000/health
```
