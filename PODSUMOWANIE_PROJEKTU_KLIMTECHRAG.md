# 📚 KlimtechRAG - Kompleksowe Podsumowanie Projektu

**Data aktualizacji:** 2026-03-13  
**Wersja:** 2.0 (po refaktoryzacji i migracji do Open WebUI)  
**Repozytorium:** https://github.com/Satham666/KlimtechRAG

---

## 📋 Spis treści

1. [Przegląd projektu](#1-przegląd-projektu)
2. [Architektura systemu](#2-architektura-systemu)
3. [Stack technologiczny](#3-stack-technologiczny)
4. [Historia rozwoju](#4-historia-rozwoju)
5. [Aktualna struktura plików](#5-aktualna-struktura-plików)
6. [Kluczowe komponenty](#6-kluczowe-komponenty)
7. [Workflow i pipeline](#7-workflow-i-pipeline)
8. [Znane problemy i rozwiązania](#8-znane-problemy-i-rozwiązania)
9. [Plany rozwoju](#9-plany-rozwoju)
10. [Komendy operacyjne](#10-komendy-operacyjne)

---

## 1. Przegląd projektu

### 1.1 Cel projektu

**KlimtechRAG** to zaawansowany system Retrieval-Augmented Generation (RAG) zaprojektowany do przetwarzania i indeksowania dokumentacji technicznej w języku polskim. System umożliwia inteligentne odpowiadanie na pytania użytkowników poprzez wyszukiwanie relevantnego kontekstu z bazy wiedzy i generowanie odpowiedzi przez lokalny model językowy.

### 1.2 Kluczowe cechy

- ✅ **Pełna lokalizacja** - działa w 100% offline (LLM, embedding, OCR, VLM)
- ✅ **Wsparcie dla języka polskiego** - model Bielik-11B-v3.0, polski OCR
- ✅ **Multimodalność** - PDF (tekst + OCR), obrazy (VLM), audio (Whisper), video
- ✅ **GPU acceleration** - AMD Instinct 16GB (ROCm/HIP)
- ✅ **Integracja z Nextcloud** - automatyczne monitorowanie i indeksowanie
- ✅ **Open WebUI** - profesjonalny interfejs użytkownika
- ✅ **Skalowalność** - Qdrant jako baza wektorowa

### 1.3 Use cases

1. **Dokumentacja techniczna** - manualne, specyfikacje, normy
2. **Baza wiedzy firmowej** - procedury, regulaminy, instrukcje
3. **Archiwizacja** - automatyczne OCR skanów i indeksowanie
4. **Q&A system** - odpowiadanie na pytania oparte na dokumentach
5. **Code search** - indeksowanie repozytoriów kodu

---

## 2. Architektura systemu

### 2.1 Schemat architektury (aktualna - Wariant C)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UŻYTKOWNIK                                       │
│                            ↓                                              │
│                   http://localhost:3000                                  │
└─────────────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      OPEN WEBUI (port 3000/8080)                         │
│  - Interfejs użytkownika                                                 │
│  - Zarządzanie konwersacjami                                             │
│  - Upload dokumentów                                                     │
│  - OWUI Function (File Router)                                           │
└────────────┬────────────────────────────────┬───────────────────────────┘
             │                                │
             │ Chat                           │ Upload
             ↓                                ↓
┌──────────────────────────┐    ┌──────────────────────────────────────┐
│  llama.cpp-server         │    │  KlimtechRAG Backend (port 8000)     │
│  (port 8082)              │    │  - FastAPI                            │
│  ┌────────────────────┐   │    │  - /v1/embeddings                     │
│  │ Bielik-11B-v3.0    │   │    │  - /upload, /ingest_path              │
│  │ Q5_K_M (~14GB VRAM)│   │    │  - /rag/debug                         │
│  └────────────────────┘   │    │  - Watchdog (Nextcloud)               │
└──────────────────────────┘    └─────────────┬────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ↓                         ↓                         ↓
        ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐
        │  Qdrant (port 6333) │  │ Nextcloud (8443)    │  │  n8n (5678)      │
        │  ┌───────────────┐  │  │  RAG_Dane/          │  │  Automatyzacje   │
        │  │klimtech_docs  │  │  │  - pdf_RAG/         │  │                  │
        │  │5114+ punktów  │  │  │  - Doc_RAG/         │  │                  │
        │  │dim: 1024      │  │  │  - txt_RAG/         │  │                  │
        │  └───────────────┘  │  │  - Images_RAG/      │  │                  │
        └─────────────────────┘  └─────────────────────┘  └──────────────────┘
```

### 2.2 Flow danych

#### Upload i indeksowanie:
```
1. Użytkownik → OWUI → dołącza plik do czatu
2. OWUI Function → pobiera plik z OWUI API
3. Function → POST /upload do KlimtechRAG
4. Backend → zapis do Nextcloud/RAG_Dane/{subdir}/
5. Backend → BackgroundTask → ekstrakcja tekstu (pdftotext/OCR)
6. Backend → chunking (1500 chars, overlap 150)
7. Backend → embedding (e5-large, CPU lub GPU)
8. Backend → zapis do Qdrant (klimtech_docs)
9. Nextcloud → rescan (podman exec occ files:scan)
```

#### Zapytanie (RAG):
```
1. Użytkownik → OWUI → zadaje pytanie
2. OWUI → POST /v1/chat/completions → KlimtechRAG
3. Backend → embedding pytania (e5-large)
4. Backend → retrieval z Qdrant (top_k=10)
5. Backend → formatowanie kontekstu
6. Backend → POST /v1/chat/completions → llama.cpp-server
7. llama.cpp → generowanie odpowiedzi (Bielik-11B)
8. Backend → odpowiedź z cytatami → OWUI → użytkownik
```

---

## 3. Stack technologiczny

### 3.1 Środowisko

| Komponent | Wersja/Szczegóły |
|-----------|------------------|
| **System** | Linux Mint / Ubuntu 24 |
| **Python** | 3.11+ (venv) |
| **GPU** | AMD Instinct 16GB (1x, docelowo 2x 32GB) |
| **ROCm/HIP** | HIP_VISIBLE_DEVICES kontrola GPU |
| **Kontenery** | Podman (Qdrant, Nextcloud, n8n) |

### 3.2 Backend

| Biblioteka | Cel | Uwagi |
|------------|-----|-------|
| **FastAPI** | Web framework | async endpoints |
| **Haystack 2.x** | RAG framework | Pipeline, retrievers |
| **Qdrant-Haystack** | Integration | QdrantDocumentStore |
| **SentenceTransformers** | Embeddings | e5-large |
| **llama-cpp-python** | LLM wrapper | Opcjonalny, serwer osobno |

### 3.3 Modele AI

| Typ | Model | Rozmiar | VRAM | Cel |
|-----|-------|---------|------|-----|
| **LLM** | Bielik-11B-v3.0-Instruct.Q5_K_M.gguf | ~7GB | ~14GB | Chat, generowanie |
| **Embedding** | intfloat/multilingual-e5-large | 1.3GB | ~2.5GB GPU / CPU | Wektory (dim 1024) |
| **VLM** | LFM2.5-VL-1.6B-F16.gguf | 2.3GB | - | Opis obrazów (⚠️ nie działa) |
| **Whisper** | (planowany) | - | - | Audio → tekst |

### 3.4 Narzędzia przetwarzania

| Narzędzie | Cel | Wydajność |
|-----------|-----|-----------|
| **pdftotext** (Poppler) | PDF z warstwą tekstową | ~1-2s |
| **Docling + RapidOCR** | PDF bez tekstu (skany) | CPU: ~15min/20MB |
| **EasyOCR** | OCR na GPU | GPU: ~13s/20MB (70x szybciej) |
| **PyMuPDF** | Ekstrakcja obrazów z PDF | - |
| **llama-cli** | VLM inference | - |

### 3.5 Bazy danych

| Typ | Technologia | Lokalizacja |
|-----|-------------|-------------|
| **Wektory** | Qdrant 1.x | Podman, port 6333 |
| **File registry** | SQLite | data/file_registry.db |
| **Open WebUI** | SQLite/Postgres | data/open-webui/webui.db |

---

## 4. Historia rozwoju

### 4.1 Sesja 1 - Diagnoza (2026-02-20)

**Problemy zidentyfikowane:**
- ❌ PDF z warstwą tekstową przetwarzany przez wolny OCR zamiast pdftotext
- ❌ Qdrant zawierał puste chunki (spacje, artefakty tabel)
- ❌ Model nie widział dokumentów w bazie (problem RAG)
- ❌ Watchdog - błędy typów (LSP errors)

**Wykonane działania:**
- ✅ Dodano wykrywanie OCR: `bitmap_area_threshold=0.0`, język polski
- ✅ Zwiększono `top_k` z 3 → 10
- ✅ Stworzone skrypty: `ingest_pdfCPU.py`, `ingest_pdfGPU.py`
- ✅ Skasowano kolekcję Qdrant i file_registry.db (reset)

### 4.2 Sesja 2 - Refaktoryzacja (2026-02-20 19:17)

**🎯 Główne osiągnięcie: Monolit → Modularność**

| Przed | Po | Redukcja |
|-------|-----|----------|
| `main.py`: 1350 linii | `main.py`: 89 linii | **93%** |
| 1 plik | 20+ modułów | - |

**Nowa struktura:**
```
backend_app/
├── main.py (89 linii - tylko app + middleware)
├── routes/ (chat, ingest, filesystem, admin, ui)
├── services/ (qdrant, embeddings, rag, llm)
├── models/ (schemas.py - Pydantic)
├── utils/ (rate_limit, dependencies)
└── scripts/ (watch_nextcloud, ingest_gpu)
```

**Naprawy kluczowe:**
- ✅ Usunięto duplikat kodu w `monitoring.py`
- ✅ Config używa `settings` zamiast sztywnych ścieżek
- ✅ `llm_model_name: str = ""` (pusty - klient wybiera model)
- ✅ Import `HTTPException` w `admin.py`
- ✅ Logi do pliku: `logs/backend.log`
- ✅ Endpoint `/rag/debug` do diagnostyki

**Problemy nierozwiązane:**
- 🔴 HNSW nie indeksuje się automatycznie (`indexed_vectors_count: 0`)
- 🟡 Watchdog - wiele instancji po restarcie
- 🟡 RAG nie działa po restarcie (model halucynuje)

### 4.3 Sesja 3 - GPU Embedding i VLM (2026-02-21 01:20)

**🚀 GPU Acceleration - główny sukces:**

| Operacja | CPU | GPU | Przyspieszenie |
|----------|-----|-----|----------------|
| Embedding batch | ~18s | ~1.4s | **13x** |
| PDF 20MB (307 chunków) | ~15 min | ~13s | **~70x** |

**VRAM usage:**
- LLM (Bielik-11B): ~14GB (93% z 16GB)
- Embedding (e5-large): ~2.5GB
- **Konflikt:** Nie mieszczą się jednocześnie → embedding na CPU przy normalnej pracy

**Nowe pliki:**
- ✅ `start_backend_gpu.sh` - backend z GPU embedding
- ✅ `backend_app/scripts/ingest_gpu.py` - masowe indeksowanie GPU
- ✅ `backend_app/utils/dependencies.py` - wspólne funkcje
- ✅ `backend_app/ingest/image_handler.py` - ekstrakcja + opis VLM
- ✅ `clean_text()` - czyszczenie chunków z białych znaków
- ✅ `clear_cache()` - czyszczenie cache po indeksowaniu

**VLM - status: ⚠️ Częściowo działa**
- ✅ Ekstrakcja obrazów z PDF (PyMuPDF) - działa
- ❌ Opis obrazów przez VLM - `llama-cli --image` nie działa
- ❌ VLM server nie startuje (brak mmproj?)

**Znane błędy:**
- 🔴 `ingest_gpu.py` zabija `start_klimtech.py` (konflikt procesów)
- 🔴 Backend po restarcie wraca na CPU embedding
- 🟡 `stop_klimtech.py` nie zabija wszystkich procesów

---

## 5. Aktualna struktura plików

### 5.1 Katalog główny

```
/media/lobo/BACKUP/KlimtechRAG/
│
├── .env                              # Zmienne środowiskowe
├── .gitignore
│
├── start_klimtech.py                 # Główny skrypt startowy
├── stop_klimtech.py                  # Zatrzymanie systemu
├── start_backend_gpu.sh              # Backend z GPU embedding
├── fix_start.py                      # Naprawa startowych problemów
│
├── backend_app/                      # Aplikacja FastAPI (refaktoryzacja)
│   ├── main.py                       # 89 linii - tylko routing
│   ├── config.py                     # Konfiguracja (Pydantic Settings)
│   ├── file_registry.py              # SQLite - status plików
│   ├── monitoring.py                 # Metryki GPU/CPU
│   ├── fs_tools.py                   # Narzędzia systemowe
│   │
│   ├── models/
│   │   └── schemas.py                # Pydantic models
│   │
│   ├── routes/
│   │   ├── chat.py                   # /query, /v1/chat/completions, /rag/debug
│   │   ├── ingest.py                 # /upload, /ingest_path, /ingest_all
│   │   ├── filesystem.py             # /fs/* endpoints
│   │   ├── admin.py                  # /health, /files/stats
│   │   └── ui.py                     # HTML UI
│   │
│   ├── services/
│   │   ├── qdrant.py                 # QdrantDocumentStore singleton
│   │   ├── embeddings.py             # Embedder singleton
│   │   ├── rag.py                    # RAG pipeline
│   │   └── llm.py                    # OpenAIGenerator wrapper
│   │
│   ├── ingest/
│   │   ├── __init__.py
│   │   └── image_handler.py          # Ekstrakcja + opis obrazów (VLM)
│   │
│   ├── utils/
│   │   ├── rate_limit.py
│   │   ├── tools.py
│   │   └── dependencies.py           # require_api_key, get_request_id
│   │
│   └── scripts/
│       ├── watch_nextcloud.py        # Obserwator Nextcloud + PID file
│       ├── ingest_gpu.py             # Indeksowanie na GPU
│       ├── ingest_pdfCPU.py          # OCR na CPU
│       └── ingest_repo.py            # Indeksowanie repozytoriów Git
│
├── data/
│   ├── file_registry.db              # SQLite - status plików
│   ├── qdrant/                       # Baza wektorowa (Podman volume)
│   ├── uploads/                      # Backup plików
│   │   ├── pdf_RAG/
│   │   ├── Doc_RAG/
│   │   ├── txt_RAG/
│   │   ├── json_RAG/
│   │   ├── Audio_RAG/
│   │   ├── Video_RAG/
│   │   └── Images_RAG/
│   ├── nextcloud/                    # Nextcloud data (Podman volume)
│   │   └── data/admin/files/RAG_Dane/
│   │       ├── pdf_RAG/
│   │       ├── Doc_RAG/
│   │       └── ...
│   └── open-webui/                   # Open WebUI data (nowe)
│       ├── webui.db
│       └── uploads/
│
├── logs/                             # Logi systemowe
│   ├── backend.log
│   ├── backend_stdout.log
│   ├── watchdog.log
│   ├── watchdog_stdout.log
│   └── llm_command.txt               # Zapisana komenda LLM
│
├── modele_LLM/                       # Modele GGUF
│   ├── Bielik-11B-v3.0-Instruct.Q5_K_M.gguf
│   ├── LFM2.5-VL-1.6B-F16.gguf       # VLM
│   └── AudioLLM/
│
├── llama.cpp/                        # llama.cpp build
│   └── build/bin/
│       ├── llama-server              # LLM server
│       └── llama-cli                 # VLM/Whisper
│
├── venv/                             # Python virtual environment
│
└── programy_mint/                    # Skrypty pomocnicze dla Linux Mint
```

### 5.2 Dokumentacja (pliki .md)

```
├── DRZEWO.md                         # Struktura projektu
├── GIT_KOMENDY.md                    # Komendy Git
├── PODSUMOWANIE_SESJI_2026-02-20_nr_1.md
├── PODSUMOWANIE_2026-02-20_19-17_nr_2.md
├── PODSUMOWANIE_2026-02-21_01-20.md
├── PLAN_MIGRACJI_OpenWebUI_2026-02-21.md
├── PLAN_OPEN_WEBUI_QDRANT_RAG.md
├── WDROZENIE.md                      # Instrukcja wdrożenia OWUI
└── notatki.md
```

---

## 6. Kluczowe komponenty

### 6.1 Config.py - Konfiguracja

**Lokalizacja:** `backend_app/config.py`

Kluczowe zmienne (Pydantic Settings, czytane z `.env`):

```python
class Settings(BaseSettings):
    # Ścieżki
    base_path: str = "/media/lobo/BACKUP/KlimtechRAG"
    data_path: str = f"{base_path}/data"
    upload_base: str = f"{data_path}/uploads"
    nextcloud_base: str = f"{data_path}/nextcloud/data/admin/files/RAG_Dane"
    file_registry_db: str = f"{data_path}/file_registry.db"
    
    # LLM
    llm_base_url: str = "http://localhost:8082/v1"
    llm_api_key: str = "sk-dummy"
    llm_model_name: str = ""  # PUSTY - klient wybiera!
    
    # Embedding
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_device: str = "cpu"  # lub "cuda:0"
    
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "klimtech_docs"
```

### 6.2 Services - Singletony

**6.2.1 Qdrant (`services/qdrant.py`)**

```python
from qdrant_haystack import QdrantDocumentStore

doc_store = QdrantDocumentStore(
    url=settings.qdrant_url,
    index=settings.qdrant_collection,
    embedding_dim=1024,
    recreate_index=False,
    hnsw_config={
        "m": 16,
        "ef_construct": 100,
        "full_scan_threshold": 10  # Buduj HNSW dla >10 punktów
    }
)

def ensure_indexed():
    """Wymusza budowę HNSW jeśli indexed_vectors_count < points_count"""
    # PATCH zamiast POST - naprawione w sesji 3
    requests.patch(
        f"{settings.qdrant_url}/collections/{settings.qdrant_collection}",
        json={"hnsw_config": {"full_scan_threshold": 10}},
        timeout=10
    )
```

**6.2.2 Embedder (`services/embeddings.py`)**

```python
from haystack.components.embedders import SentenceTransformersTextEmbedder

text_embedder = SentenceTransformersTextEmbedder(
    model=settings.embedding_model,
    device=settings.embedding_device  # "cpu" lub "cuda:0"
)
text_embedder.warm_up()  # Tylko raz przy starcie!
```

**6.2.3 RAG Pipeline (`services/rag.py`)**

```python
from haystack import Pipeline
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

rag_pipeline = Pipeline()
rag_pipeline.add_component("embedder", text_embedder)
rag_pipeline.add_component(
    "retriever",
    QdrantEmbeddingRetriever(document_store=doc_store, top_k=10)
)
rag_pipeline.connect("embedder.embedding", "retriever.query_embedding")
```

### 6.3 Watchdog - Nextcloud monitoring

**Lokalizacja:** `backend_app/scripts/watch_nextcloud.py`

**Ulepszenia (sesja 2-3):**
- ✅ PID file `/tmp/klimtech_watchdog.pid` - zapobiega duplikatom
- ✅ Logi do `logs/watchdog.log`
- ✅ Używa `settings.nextcloud_base`, `settings.upload_base`
- ✅ Sprawdza czy już działa przed startem

**Workflow:**
```
Nextcloud: nowy plik w RAG_Dane/pdf_RAG/
    ↓
Watchdog wykrywa (FileSystemEventHandler)
    ↓
Kopiuje do data/uploads/pdf_RAG/
    ↓
Wywołuje POST /ingest_path
    ↓
Backend: ekstrakcja → chunking → embedding → Qdrant
```

### 6.4 Ingest - Przetwarzanie plików

**6.4.1 Inteligentny PDF handler (`routes/ingest.py`)**

```python
def extract_pdf_text(file_path: str) -> str:
    """
    1. Próbuje pdftotext (szybkie, ~1-2s)
    2. Jeśli puste → Docling OCR (wolne, ~15min CPU / 13s GPU)
    """
    result = subprocess.run(
        ["pdftotext", file_path, "-"],
        capture_output=True,
        text=True,
        timeout=30
    )
    text = result.stdout.strip()
    
    if len(text) > 100:
        return text  # Sukces - PDF ma warstwę tekstową
    else:
        # Fallback: OCR
        return parse_with_docling(file_path)
```

**6.4.2 GPU Ingest (`scripts/ingest_gpu.py`)**

Niezależny skrypt do masowego indeksowania z GPU:

```bash
# Zatrzymaj LLM (zwalnia VRAM)
pkill llama-server

# Uruchom backend z GPU embedding
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python -m backend_app.main &

# Zaindeksuj wszystkie pending
curl -X POST "http://localhost:8000/ingest_all?limit=50"
```

**Konflikt:** Zabija `start_klimtech.py` - trzeba restartować system po zakończeniu.

**6.4.3 VLM Image Handler (`ingest/image_handler.py`)**

Status: ⚠️ Częściowo działa

```python
def extract_images_from_pdf(pdf_path: str) -> List[ImageMetadata]:
    """Ekstrakcja obrazów z PDF - DZIAŁA"""
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        for img_index, img in enumerate(page.get_images()):
            # ... ekstrakcja do bytes ...
            
def describe_image_with_vlm(image_bytes: bytes) -> str:
    """Opis obrazu przez VLM - NIE DZIAŁA"""
    # llama-cli --image problem z flagami/mmproj
    pass
```

---

## 7. Workflow i pipeline

### 7.1 Start systemu (`start_klimtech.py`)

**Workflow:**
```
1. Wybór modelu GGUF z listy (menu interaktywne)
2. Uruchomienie llama-server (LLM) → port 8082
3. Uruchomienie kontenerów Podman:
   - Qdrant → port 6333
   - Nextcloud → port 8443
   - n8n → port 5678
4. Uruchomienie backendu FastAPI → port 8000
   - Środowisko: KLIMTECH_EMBEDDING_DEVICE=cpu
5. Uruchomienie watchdog → PID file
6. (Opcjonalnie) Uruchomienie Open WebUI → port 3000
```

**Zapisywane logi:**
- `logs/llm_server_stdout.log`
- `logs/llm_server_stderr.log`
- `logs/backend_stdout.log`
- `logs/backend.log` (aplikacyjny)
- `logs/watchdog.log`
- `logs/llm_command.txt` (komenda LLM dla debugowania)

### 7.2 Upload pliku (przez OWUI)

**Wariant C - docelowy (z WDROZENIE.md):**

```
Użytkownik → OWUI → dołącza plik (spinacz)
    ↓
OWUI Function (File Router)
    ↓
GET OWUI /files/{id}/content (pobranie pliku)
    ↓
POST KlimtechRAG /upload (multipart/form-data)
    ↓
Backend zapisuje → Nextcloud/RAG_Dane/{subdir}/
    ↓
podman exec nextcloud php occ files:scan (rescan)
    ↓
BackgroundTask → /ingest_path
    ↓
Ekstrakcja tekstu (pdftotext lub OCR)
    ↓
Chunking (1500 chars, overlap 150)
    ↓
Embedding (e5-large, CPU)
    ↓
Zapis do Qdrant (klimtech_docs)
    ↓
clear_cache() - czyszczenie cache RAG
```

### 7.3 RAG Query

**Endpoint:** `POST /v1/chat/completions`

```python
# 1. Embedding pytania
question_embedding = text_embedder.run(text=user_query)["embedding"]

# 2. Retrieval z Qdrant (top_k=10)
docs = rag_pipeline.run({
    "embedder": {"text": user_query}
})["retriever"]["documents"]

# 3. Formatowanie kontekstu
context = "\n\n".join([
    f"[Dokument {i+1}]\n{doc.content}"
    for i, doc in enumerate(docs[:5])
])

# 4. Prompt z kontekstem
system_prompt = f"""Jesteś asystentem AI. Odpowiadaj na podstawie kontekstu:

{context}

Pytanie: {user_query}"""

# 5. Generowanie przez LLM
response = llm_generator.run(
    prompt=system_prompt,
    generation_kwargs={"max_tokens": 2048}
)

return response["replies"][0]
```

### 7.4 Diagnostyka (`/rag/debug`)

**Endpoint do testowania RAG:**

```bash
curl -s "http://localhost:8000/rag/debug?query=klimatyzacja" | python3 -m json.tool
```

**Odpowiedź:**
```json
{
  "qdrant_points": 5114,
  "qdrant_indexed": 5114,
  "retrieved_docs": 10,
  "sample": "Klimatyzacja przemysłowa to system...",
  "embedding_device": "cpu",
  "embedding_model": "intfloat/multilingual-e5-large"
}
```

---

## 8. Znane problemy i rozwiązania

### 8.1 🔴 Krytyczne

#### Problem 1: HNSW nie indeksuje się automatycznie

**Objawy:**
```bash
curl -s http://localhost:6333/collections/klimtech_docs | grep indexed
# "indexed_vectors_count": 0  # Powinno być = points_count
```

**Przyczyna:** `full_scan_threshold: 10000` - Qdrant nie buduje HNSW dla małych kolekcji.

**Rozwiązanie (manualne):**
```bash
# Obniż threshold
curl -X PATCH "http://localhost:6333/collections/klimtech_docs" \
  -H "Content-Type: application/json" \
  -d '{"hnsw_config": {"full_scan_threshold": 10}}'

# W sesji 3 naprawiono - teraz PATCH zamiast POST
```

**Status:** ✅ Naprawione w `services/qdrant.py` (sesja 3)

#### Problem 2: `ingest_gpu.py` zabija `start_klimtech.py`

**Objawy:** Po uruchomieniu `ingest_gpu.py`, proces `start_klimtech.py` się kończy ("Wszystkie procesy zakończone").

**Przyczyna:** Konflikt procesów zarządzających tym samym zasobem (GPU/backend).

**Obejście:**
- Używać `start_backend_gpu.sh` osobno
- Lub nie uruchamiać `ingest_gpu.py` gdy `start_klimtech.py` działa

**Status:** 🔴 Nierozwiązane

#### Problem 3: VLM nie działa

**Objawy:** 
- Ekstrakcja obrazów działa ✅
- Opis obrazów przez VLM nie działa ❌

**Przyczyny:**
- `llama-cli --image` flaga `--no-display` nie istnieje
- Model VLM może wymagać mmproj (brak w folderze)

**Do naprawy:**
1. Sprawdzić czy VLM model ma wbudowany mmproj
2. Pobrać mmproj jeśli potrzebny
3. Przetestować `llama-cli --image` ręcznie

**Status:** 🔴 Nierozwiązane

### 8.2 🟡 Średnie

#### Problem 4: `stop_klimtech.py` nie zabija wszystkich procesów

**Objawy:** Po `stop_klimtech.py` backend i watchdog mogą dalej działać.

**Rozwiązanie ręczne:**
```bash
pkill -f "uvicorn backend_app" 2>/dev/null
fuser -k 8000/tcp 2>/dev/null
sleep 2
ss -tlnp | grep 8000 || echo "Port 8000 wolny"
```

**Status:** 🟡 Do naprawy

#### Problem 5: Wiele instancji watchdog

**Objawy:**
```bash
ps aux | grep watch_nextcloud
# lobo  70693 ... watch_nextcloud.py
# lobo  71945 ... watch_nextcloud.py
# lobo  74396 ... watch_nextcloud.py
```

**Rozwiązanie:**
```bash
pkill -f watch_nextcloud
```

**Status:** ✅ Naprawione - dodano PID file (sesja 2)

#### Problem 6: Backend po `ingest_gpu.py` wraca na CPU

**Objawy:** Po zakończeniu indeksowania GPU i przywróceniu LLM, embedding wraca na CPU.

**Przyczyna:** `start_klimtech.py` uruchamia backend z `KLIMTECH_EMBEDDING_DEVICE=cpu`.

**Rozwiązanie:** Zmienić w `start_klimtech.py` na `cuda:0` jeśli LLM nie używa całego VRAM.

**Status:** 🟡 Projektowe (konflikt VRAM)

### 8.3 🟢 Niskie

#### Problem 7: `@router.on_event("startup")` deprecated

**Lokalizacja:** `routes/admin.py`

**Rozwiązanie:** Przenieść do `lifespan` w `main.py`.

**Status:** 🟢 Do poprawy (nie wpływa na działanie)

---

## 9. Plany rozwoju

### 9.1 Warianty migracji do Open WebUI

Szczegóły w: `PLAN_MIGRACJI_OpenWebUI_2026-02-21.md`

#### **Wariant A - OWUI jako frontend** ⭐ ZALECANE (Faza 1)

- Open WebUI jako UI
- KlimtechRAG backend niezmieniony (RAG tutaj)
- Zero zmian w backendzie, nie tracisz 5114 chunków
- ✅ **Zaimplementowane** - patrz `WDROZENIE.md`

#### **Wariant B - OWUI jako pełny RAG**

- OWUI używa natywnego Qdrant RAG
- Nowa kolekcja `open-webui`
- ⚠️ Trzeba re-indeksować wszystkie dokumenty
- ⚠️ VRAM conflict (LLM + OWUI embedding)

#### **Wariant C - Hybrydowy** (Docelowy)

- OWUI używa KlimtechRAG jako serwera embeddingów
- Wspólna kolekcja `klimtech_docs`
- Endpoint `/v1/embeddings` w KlimtechRAG
- ✅ **Planowana implementacja** - patrz `WDROZENIE.md`

### 9.2 Roadmap funkcji

**Q1 2026:**
- [ ] Naprawić VLM (mmproj, llama-cli --image)
- [ ] Dodać Whisper dla audio (przez faster-whisper)
- [ ] Ekstrakcja klatek z video + opis przez VLM
- [ ] Naprawić `stop_klimtech.py` (kill all processes)
- [ ] Dodać `lifespan` w `main.py`

**Q2 2026:**
- [ ] Druga karta AMD Instinct 32GB
  - LLM na karcie 0 (32GB)
  - Embedding na karcie 1 (32GB - równoległy GPU)
- [ ] Równoległe działanie LLM + VLM (porty 8082 + 8083)
- [ ] MCP Server dla Open WebUI
- [ ] Web Search integration (SearXNG)

**Q3 2026:**
- [ ] Migracja do Wariantu C (OWUI + wspólna kolekcja)
- [ ] Postgres zamiast SQLite dla Open WebUI
- [ ] TTS/STT lokalne (piper, faster-whisper)
- [ ] n8n workflows dla automatyzacji

### 9.3 Optymalizacje

**Embedding:**
- Batch processing dla wielu PDF naraz
- Caching embeddingów często używanych fraz
- Kwantyzacja modelu e5-large (INT8) dla szybszego CPU

**Qdrant:**
- Replikacja kolekcji (backup)
- Snapshoty automatyczne
- Migracja do sharded collection (>100k dokumentów)

**LLM:**
- Test Bielik-11B Q8 (wyższa jakość)
- Test Bielik-7B Q4 (szybszy, mniejszy VRAM)
- Speculative decoding dla przyspieszenia

---

## 10. Komendy operacyjne

### 10.1 Codzienne uruchamianie

```bash
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate

# Start systemu
python start_klimtech.py

# Open WebUI (jeśli osobno)
podman start open-webui

# Logi na żywo
tail -f logs/backend.log
tail -f logs/watchdog.log
```

### 10.2 Diagnostyka

**Health checks:**
```bash
# Backend
curl -s http://localhost:8000/health | python3 -m json.tool

# LLM
curl -s http://localhost:8082/v1/models | python3 -m json.tool

# Qdrant
curl -s http://localhost:6333/collections/klimtech_docs | python3 -m json.tool

# RAG debug
curl -s "http://localhost:8000/rag/debug?query=test" | python3 -m json.tool
```

**File registry:**
```bash
# Stats
curl -s http://localhost:8000/files/stats | python3 -m json.tool

# Pending files
curl -s http://localhost:8000/files/pending | python3 -m json.tool
```

**Qdrant komendy:**
```bash
# Liczba punktów
curl -s http://localhost:6333/collections/klimtech_docs | \
  python3 -m json.tool | grep -E "points_count|indexed_vectors"

# Podgląd dokumentów
curl -s -X POST "http://localhost:6333/collections/klimtech_docs/points/scroll" \
  -H "Content-Type: application/json" \
  -d '{"limit": 3, "with_payload": true}' | python3 -m json.tool
```

### 10.3 Indeksowanie

**Ręczne (CPU):**
```bash
# Zaindeksuj wszystkie pending (limit 5)
curl -X POST "http://localhost:8000/ingest_all?limit=5"

# Konkretny plik
curl -X POST "http://localhost:8000/ingest_path" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/file.pdf"}'
```

**Masowe (GPU):**
```bash
# 1. Zatrzymaj LLM (zwalnia VRAM)
pkill llama-server

# 2. Uruchom backend z GPU
./start_backend_gpu.sh

# 3. Indeksuj
curl -X POST "http://localhost:8000/ingest_all?limit=50"

# 4. Sprawdź postęp
curl -s http://localhost:8000/files/stats | python3 -m json.tool

# 5. Wróć do normalnego trybu
pkill -f backend_app.main
python start_klimtech.py
```

### 10.4 Nextcloud

```bash
# Rescan plików
podman exec nextcloud php occ files:scan --path=/admin/files/RAG_Dane

# Lista plików
podman exec nextcloud php occ files:list admin --path=RAG_Dane
```

### 10.5 Zatrzymanie systemu

```bash
python stop_klimtech.py

# Jeśli procesy dalej działają (bug):
pkill -f "uvicorn backend_app"
pkill -f watch_nextcloud
pkill llama-server
fuser -k 8000/tcp
fuser -k 8082/tcp

# Sprawdź porty
ss -tlnp | grep -E "8000|8082|6333|8443"
```

### 10.6 Backup i restore

**Qdrant snapshot:**
```bash
# Utwórz snapshot
curl -X POST "http://localhost:6333/collections/klimtech_docs/snapshots"

# Lista snapshotów
curl "http://localhost:6333/collections/klimtech_docs/snapshots"

# Restore (wymaga zatrzymania Qdrant)
```

**SQLite backup:**
```bash
# File registry
cp data/file_registry.db data/file_registry.db.backup

# Open WebUI
cp data/open-webui/webui.db data/open-webui/webui.db.backup
```

---

## 📊 Metryki projektu

**Kod:**
- Pliki Python: ~95
- Linie kodu (backend_app): ~3500 (po refaktoryzacji z 1350 w main.py)
- Testy: 0 (TODO)

**Baza:**
- Dokumenty w Qdrant: 5114+ chunków
- Rozmiar kolekcji: ~1.2GB (wektory + metadata)
- Czas indexowania (CPU): ~15min/20MB PDF
- Czas indexowania (GPU): ~13s/20MB PDF

**Performance:**
- Embedding CPU: ~18s/batch
- Embedding GPU: ~1.4s/batch (70x szybciej)
- Retrieval (top_k=10): <100ms
- Generation (Bielik-11B): ~15 tokens/s

---

## 📚 Dodatkowe zasoby

**Dokumenty projektu:**
- `DRZEWO.md` - Struktura katalogów
- `GIT_KOMENDY.md` - Komendy Git
- `WDROZENIE.md` - Instrukcja wdrożenia Open WebUI
- `PLAN_MIGRACJI_OpenWebUI_2026-02-21.md` - Plan migracji
- `PLAN_OPEN_WEBUI_QDRANT_RAG.md` - Pełna migracja

**Repozytoria zależności:**
- llama.cpp: https://github.com/ggerganov/llama.cpp
- Haystack: https://github.com/deepset-ai/haystack
- Qdrant: https://github.com/qdrant/qdrant
- Open WebUI: https://github.com/open-webui/open-webui

**Modele:**
- Bielik-11B: https://huggingface.co/speakleash/bielik-11b-v3.0-instruct
- e5-large: https://huggingface.co/intfloat/multilingual-e5-large

---

## 👥 Kontakt i rozwój

**Repozytorium:** https://github.com/Satham666/KlimtechRAG  
**Licencja:** (do określenia)  
**Status:** Active development  
**Ostatnia aktualizacja:** 2026-03-13

---

*Dokument wygenerowany automatycznie na podstawie analizy projektu, historii commitów i dokumentacji sesji.*
