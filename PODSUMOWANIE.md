# 📚 KlimtechRAG — Podsumowanie Projektu

**Data aktualizacji:** 2026-03-14
**Wersja systemu:** v7.0 (Dual Model Selection)
**Repozytorium:** https://github.com/Satham666/KlimtechRAG
**Katalog serwera:** `/media/lobo/BACKUP/KlimtechRAG/`
**Katalog laptopa:** `~/KlimtechRAG`

---

## 1. Cel projektu

**KlimtechRAG** to lokalny system RAG (Retrieval-Augmented Generation) do pracy z dokumentacją techniczną w języku polskim. Działa w 100% offline — LLM, embedding, OCR i VLM uruchamiane są lokalnie na GPU AMD Instinct 16 GB (ROCm/HIP).

**Główne zastosowania:**
- Odpowiadanie na pytania na podstawie zaindeksowanych dokumentów PDF/DOCX/TXT
- Automatyczne OCR skanów i indeksowanie
- Obsługa dokumentów z obrazkami (tryb VLM / ColPali)
- Baza wiedzy firmowej / technicznej

---

## 2. Architektura systemu (aktualna — v7.0)

```
┌──────────────────────────────────────────────────────────┐
│             PRZEGLĄDARKA  http://192.168.31.70:8000/      │
│         (własny UI — FastAPI routes/ui.py)               │
└───────────────────────────┬──────────────────────────────┘
                            │
        ┌───────────────────▼──────────────────┐
        │     KlimtechRAG Backend FastAPI       │
        │     Port: 8000                        │
        │  - /v1/chat/completions  (RAG czat)   │
        │  - /upload  (wgrywanie plików)        │
        │  - /ingest  (indeksowanie)            │
        │  - /model/switch/{llm|vlm}            │
        │  - /model/list  (lista modeli)        │
        │  - /v1/embeddings                     │
        │  - /files/stats, /files/pending       │
        │  - /rag/debug                         │
        └──────┬───────────────┬────────────────┘
               │               │
   ┌───────────▼───┐   ┌───────▼──────────────┐
   │ llama.cpp     │   │  Qdrant (port 6333)  │
   │ -server       │   │  kolekcje:           │
   │ Port: 8082    │   │  - klimtech_docs     │
   │ LLM lub VLM   │   │    (e5-large, 1024d) │
   │ (przełączalne)│   │  - klimtech_colpali  │
   └───────────────┘   │    (ColPali, 128d)   │
                       └──────────────────────┘
               │
   ┌───────────▼──────────────────────────────┐
   │  Podman kontenery                        │
   │  ✅ qdrant          (port 6333)          │
   │  ✅ nextcloud        (port 8443)         │
   │  ✅ postgres_nextcloud                   │
   │  ✅ n8n             (port 5678)          │
   └──────────────────────────────────────────┘
```

> ⚠️ **Open WebUI usunięte** — zastąpione własnym interfejsem w `routes/ui.py`

---

## 3. Stack technologiczny

| Warstwa | Technologia | Uwagi |
|---------|-------------|-------|
| **System** | Linux Mint / Ubuntu 24 | Serwer + Laptop |
| **Python** | 3.12 (venv `/home/lobo/klimtech_venv`) | — |
| **GPU** | AMD Instinct 16 GB (AMD Radeon Pro VII) | ROCm 7.2, HSA_OVERRIDE_GFX_VERSION=9.0.6 |
| **PyTorch** | 2.5.1+rocm6.2 | ✅ podmieniony z CUDA na ROCm |
| **Backend** | FastAPI + Haystack 2.x | Port 8000 |
| **LLM/VLM** | llama.cpp-server | Port 8082 |
| **Wektory** | Qdrant | Port 6333, Podman |
| **Embedding (tekst)** | intfloat/multilingual-e5-large | dim=1024, HuggingFace |
| **Embedding (PDF)** | ColPali v1.3 (vidore/colpali-v1.3-hf) | dim=128 multi-vector, HuggingFace |
| **Kontenery** | Podman | qdrant, nextcloud, postgres, n8n |
| **UI** | HTML/JS wbudowany w FastAPI | `routes/ui.py` |
| **Sync** | Git → GitHub | laptop → push, serwer → pull |

### Modele GGUF (katalogi)

```
modele_LLM/
├── model_thinking/     ← LLM do czatu
│   ├── Bielik-11B-v3.0-Instruct.Q8_0.gguf   (~14 GB VRAM)
│   ├── Bielik-4.5B-v3.0-Instruct.Q8_0.gguf  (~6 GB VRAM)
│   └── LFM2-2.6B-F16.gguf                   (~3 GB VRAM)
├── model_video/        ← VLM (obrazki)
│   └── LFM2.5-VL-1.6B-F16.gguf
├── model_audio/        ← TTS/STT (do testów)
│   └── vocoder-LFM2.5-Audio-1.5B-F16.gguf
└── model_embedding/    ← Embedding GGUF (alternatywa)
    ├── bge-large-en-v1.5.Q8_0.gguf
    └── Bge-M3-567M-F32.gguf
```

### Modele HuggingFace (pobierane automatycznie)
- `intfloat/multilingual-e5-large` — główny embedding tekstu
- `vidore/colpali-v1.3-hf` — ColPali, embedding wizualny PDF

---

## 4. Historia sesji

### Sesja 1 — Diagnoza (2026-02-20)
- ✅ Naprawiono OCR (`bitmap_area_threshold=0.0`, język PL)
- ✅ `top_k` zwiększone z 3 → 10
- ✅ Skrypty `ingest_pdfCPU.py`, `ingest_pdfGPU.py`
- ✅ Reset Qdrant i `file_registry.db`

### Sesja 2 — Refaktoryzacja (2026-02-20 19:17)
- ✅ Monolit `main.py` (1350 linii) → moduły (89 linii main, -93%)
- ✅ Nowa struktura: `routes/`, `services/`, `models/`, `utils/`, `scripts/`
- ✅ Pydantic Settings + `.env`
- ✅ `/rag/debug`, logi do pliku, PID file dla watchdog

### Sesja 3 — GPU Embedding i VLM (2026-02-21 01:20)
- ✅ GPU embedding: **13× szybszy** (batch: 18s → 1.4s)
- ✅ PDF 20MB (307 chunków): **~70× szybszy** (~15 min → 13s)
- ✅ `ingest_gpu.py`, ekstrakcja obrazów z PDF (PyMuPDF)
- ✅ HNSW threshold naprawiony w `services/qdrant.py`
- ❌ VLM opis obrazów nie działa (brak mmproj)

### Sesja 4 — Własny UI (2026-02-xx)
- ✅ HTML/JS czat wbudowany w FastAPI (`routes/ui.py`)
- ✅ Sidebar z historią sesji, eksport/import JSON
- ✅ Upload drag&drop, przycisk "🧠 Indeksuj pliki w RAG"
- ✅ Toggle VLM/LLM, statystyki, wskaźnik statusu backendu

### Sesja 5 — Model Switch API (2026-02-xx)
- ✅ `routes/model_switch.py` — API przełączania modeli
- ✅ `GET /model/status`, `POST /model/switch/{llm|vlm}`
- ✅ `GET /model/list`, `GET /model/config`

### Sesja 6 — start_klimtech_v3.py (2026-03-xx)
- ✅ Skrypt v7.0 — Dual Model Selection (LLM + VLM przy starcie)
- ✅ Automatyczne zarządzanie VRAM (pkill + czekanie)
- ✅ Konfiguracja zapisywana do `logs/models_config.json`
- ✅ Interaktywne menu terminalu (opcje 1–5, q)
- ✅ `model_parametr.py` — obliczanie parametrów VRAM

### Sesja 7 — Wymagania i ColPali (2026-03-13/14)
- ✅ Wygenerowano nowe `PODSUMOWANIE.md`
- ✅ Zdefiniowano wymagania UI (wybór modelu, okienko POSTĘP, menu przyciski)
- ✅ Napisano `backend_app/services/colpali_embedder.py`
- ✅ Napisano `backend_app/scripts/ingest_colpali.py`
- ✅ ColPali dodany do `get_available_models()` w `model_manager.py`
- ✅ Wyczyszczono `.env` (usunięto duplikaty OWUI, BACKEND_API_PORT, KLIMTECH_DATA_PATH)

### Sesja 8 — ROCm + Backend (2026-03-14) ← OBECNA
- ✅ **Podmieniono PyTorch CUDA → ROCm 6.2** (`torch 2.5.1+rocm6.2`)
  - Poprzednio był PyTorch CUDA (Nvidia) — błąd `Found no NVIDIA driver`
  - Komenda: `pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.2 --force-reinstall`
  - GPU działa: `AMD Radeon (TM) Pro VII`, `torch.cuda.is_available() = True`
- ✅ **Zdiagnozowano i uruchomiono backend** po awarii
  - Backend wyłączył się bo `start_klimtech_v3.py` dostał Ctrl+C
  - Backend uruchamiany teraz bezpośrednio: `KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000`
- ✅ **Potwierdzono działanie GPU embeddingu**
  - VRAM: 7.2 GB zajęte podczas indeksowania
  - Temperatura GPU: 85-90°C (normalnie pod obciążeniem)
  - Log `GPU: 0%` to błąd `monitoring.py` (źle parsuje ROCm output) — nie wpływa na działanie
- ✅ **Wyczyszczono `.env`** — usunięto zbędne zmienne
- ✅ **ColPali widoczny w `/model/list`** — `vidore/colpali-v1.3-hf` w liście embeddingów

---

## 5. Aktualna struktura plików

```
/media/lobo/BACKUP/KlimtechRAG/
│
├── .env                              # ✅ Wyczyszczone (bez duplikatów)
├── .gitignore
│
├── start_klimtech_v3.py              # Główny skrypt startowy (v7.0)
├── start_backend_gpu.py              # Indeksowanie GPU (bez LLM)
├── stop_klimtech.py
│
├── backend_app/
│   ├── main.py
│   ├── config.py                     # Pydantic Settings
│   ├── file_registry.py              # SQLite (hash, rozmiar, status)
│   ├── monitoring.py                 # ⚠️ GPU% nie działa dla ROCm
│   │
│   ├── routes/
│   │   ├── chat.py                   # /v1/chat/completions, /v1/embeddings
│   │   ├── ingest.py                 # /upload, /ingest
│   │   ├── admin.py                  # /health, /files/stats, /files/pending
│   │   ├── model_switch.py           # /model/status, /model/switch, /model/list
│   │   └── ui.py                     # Główny UI HTML/JS
│   │
│   ├── services/
│   │   ├── qdrant.py
│   │   ├── embeddings.py             # e5-large (cuda:0 / cpu)
│   │   ├── rag.py
│   │   ├── llm.py
│   │   ├── model_manager.py          # ✅ ColPali dodany do listy embeddingów
│   │   └── colpali_embedder.py       # ✅ NOWY — ColPali multi-vector embedding
│   │
│   └── scripts/
│       ├── watch_nextcloud.py
│       ├── ingest_gpu.py
│       ├── ingest_colpali.py         # ✅ NOWY — masowe indeksowanie PDF przez ColPali
│       └── model_parametr.py
│
├── modele_LLM/
│   ├── model_thinking/               # LLM
│   ├── model_video/                  # VLM
│   ├── model_audio/                  # Audio
│   └── model_embedding/              # Embedding GGUF
│
└── PODSUMOWANIE.md                   ← ten plik
```

---

## 6. ColPali — co to jest i jak używać

### Czym różni się od e5-large

| | e5-large | ColPali |
|---|---|---|
| **Wejście** | tekst (chunki) | obraz strony PDF |
| **Wyjście** | 1 wektor × 1024 dim | ~1000 wektorów × 128 dim |
| **Kolekcja Qdrant** | `klimtech_docs` | `klimtech_colpali` |
| **OCR potrzebny?** | ✅ tak | ❌ nie — widzi wizualnie |
| **Tabele/wykresy** | ❌ słabo | ✅ rozumie układ strony |
| **VRAM** | ~2.5 GB | ~6-8 GB |
| **Scoring** | cosine similarity | MAX_SIM (late interaction) |

### Uruchamianie indeksowania ColPali

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

---

## 7. Znane problemy

| # | Priorytet | Problem | Status |
|---|-----------|---------|--------|
| 1 | 🔴 | VLM opis obrazów nie działa (brak mmproj) | Nierozwiązane |
| 2 | 🔴 | `ingest_gpu.py` zabija `start_klimtech.py` (konflikt GPU) | Nierozwiązane |
| 3 | 🟡 | `monitoring.py` zwraca `GPU: 0%` dla AMD ROCm | Kosmetyczny |
| 4 | 🟡 | `stop_klimtech.py` nie zabija wszystkich procesów | Do naprawy |
| 5 | 🟢 | `@router.on_event("startup")` deprecated | Nie wpływa na działanie |

---

## 8. Komendy operacyjne

### Sync kodu
```bash
# Laptop → GitHub:
git add -A && git commit -m "Sync" -a || true && git push --force

# Serwer ← GitHub:
git config pull.rebase false && git pull
```

### Uruchomienie backendu
```bash
source /home/lobo/klimtech_venv/bin/activate
cd /media/lobo/BACKUP/KlimtechRAG
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000
```

### Sprawdzenie GPU
```bash
python3 -c "import torch; print(torch.__version__); print('GPU:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
# Oczekiwany wynik: 2.5.1+rocm6.2 / GPU: True / AMD Radeon (TM) Pro VII
```

### Reinstalacja PyTorch ROCm (jeśli potrzeba)
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/rocm6.2 --force-reinstall --break-system-packages
```

### Diagnostyka
```bash
curl http://192.168.31.70:8000/health
curl http://192.168.31.70:8000/model/list | python3 -m json.tool
curl http://192.168.31.70:8000/rag/debug | python3 -m json.tool
rocm-smi
nvtop
```

---

## 9. Endpointy backendu

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/` | GET | Główny UI |
| `/v1/chat/completions` | POST | RAG czat |
| `/v1/embeddings` | POST | Embedding (OpenAI-compatible) |
| `/v1/models` | GET | Lista modeli |
| `/upload` | POST | Wgraj plik |
| `/ingest` | POST | Indeksuj plik |
| `/ingest_all` | POST | Indeksuj wszystkie pending |
| `/model/status` | GET | Status LLM/VLM serwera |
| `/model/switch/llm` | POST | Przełącz na LLM |
| `/model/switch/vlm` | POST | Przełącz na VLM |
| `/model/list` | GET | Lista wszystkich modeli (+ ColPali) |
| `/model/config` | GET | Aktualna konfiguracja |
| `/files/stats` | GET | Statystyki plików/wektorów |
| `/files/pending` | GET | Pliki oczekujące |
| `/health` | GET | Status systemu |
| `/rag/debug` | GET | Debug RAG pipeline |

---

## 10. Adresy sieciowe

```
🔧 API Backend:    http://192.168.31.70:8000
📦 Qdrant:         http://192.168.31.70:6333
☁️  Nextcloud:      http://192.168.31.70:8443
🔗 n8n:            http://192.168.31.70:5678
🤖 LLM/VLM:        http://192.168.31.70:8082  (po załadowaniu modelu)
```

---

*Ostatnia aktualizacja: 2026-03-14 — Sesja 8 (ROCm fix, ColPali)*
