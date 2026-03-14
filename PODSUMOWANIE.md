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
- Obsługa dokumentów z obrazkami (tryb VLM)
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
        │  - /v1/embeddings                     │
        │  - /files/stats, /files/pending       │
        │  - /rag/debug                         │
        └──────┬───────────────┬────────────────┘
               │               │
   ┌───────────▼───┐   ┌───────▼──────────────┐
   │ llama.cpp     │   │  Qdrant (port 6333)  │
   │ -server       │   │  kolekcja:           │
   │ Port: 8082    │   │  klimtech_docs       │
   │ LLM lub VLM   │   │  dim: 1024           │
   │ (przełączalne)│   │  5114+ punktów       │
   └───────────────┘   └──────────────────────┘
               │
   ┌───────────▼──────────────────────────────┐
   │  Podman kontenery                        │
   │  ✅ qdrant          (port 6333)          │
   │  ✅ nextcloud        (port 8443)         │
   │  ✅ postgres_nextcloud                   │
   │  ✅ n8n             (port 5678)          │
   └──────────────────────────────────────────┘
```

> ⚠️ **Open WebUI zostało usunięte** z architektury — zastąpione własnym interfejsem w `routes/ui.py`.

---

## 3. Stack technologiczny

| Warstwa | Technologia | Uwagi |
|---------|-------------|-------|
| **System** | Linux Mint / Ubuntu 24 | Serwer + Laptop |
| **Python** | 3.11+ (venv `/home/lobo/klimtech_venv`) | — |
| **GPU** | AMD Instinct 16 GB | ROCm/HIP, HSA_OVERRIDE_GFX_VERSION=9.0.6 |
| **Backend** | FastAPI + Haystack 2.x | Port 8000 |
| **LLM/VLM** | llama.cpp-server | Port 8082 |
| **Wektory** | Qdrant | Port 6333, Podman |
| **Embedding** | intfloat/multilingual-e5-large | dim=1024, HuggingFace |
| **Kontenery** | Podman | qdrant, nextcloud, postgres, n8n |
| **UI** | HTML/JS wbudowany w FastAPI | `routes/ui.py` |
| **Sync** | Git → GitHub | `git push --force` |

### Modele GGUF (katalogi)

```
modele_LLM/
├── model_thinking/     ← LLM do czatu (wybierany przy starcie)
│   ├── Bielik-11B-v3.0-Instruct.Q8_0.gguf   (~14 GB VRAM)
│   ├── Bielik-4.5B-v3.0-Instruct.Q8_0.gguf  (~6 GB VRAM)
│   └── LFM2-2.6B-F16.gguf                   (~3 GB VRAM)
├── model_video/        ← VLM (obrazki, wybierany przy starcie)
│   └── LFM2.5-VL-1.6B-F16.gguf
├── model_audio/        ← TTS/STT (do testów)
│   └── vocoder-LFM2.5-Audio-1.5B-F16.gguf
└── model_embedding/    ← Embedding GGUF (alternatywa)
    ├── bge-large-en-v1.5.Q8_0.gguf
    └── Bge-M3-567M-F32.gguf
```

---

## 4. Historia sesji i co zostało zrobione

### Sesja 1 — Diagnoza (2026-02-20)
- ✅ Wykryto i naprawiono problem z OCR (`bitmap_area_threshold=0.0`, język PL)
- ✅ Zwiększono `top_k` z 3 → 10
- ✅ Stworzono skrypty `ingest_pdfCPU.py`, `ingest_pdfGPU.py`
- ✅ Reset Qdrant i `file_registry.db`

### Sesja 2 — Refaktoryzacja (2026-02-20 19:17)
- ✅ Monolit `main.py` (1350 linii) → moduły (93% redukcja, 89 linii main)
- ✅ Nowa struktura: `routes/`, `services/`, `models/`, `utils/`, `scripts/`
- ✅ Config używa Pydantic Settings (`.env`)
- ✅ Endpoint `/rag/debug`
- ✅ Logi do pliku `logs/backend.log`
- ✅ PID file dla watchdog (eliminacja dubli)

### Sesja 3 — GPU Embedding i VLM (2026-02-21 01:20)
- ✅ GPU embedding: **13× szybszy** (batch: 18s → 1.4s)
- ✅ PDF 20 MB (307 chunków): **~70× szybszy** (~15 min → 13s)
- ✅ `ingest_gpu.py` — masowe indeksowanie na GPU
- ✅ Ekstrakcja obrazów z PDF (PyMuPDF) działa
- ✅ HNSW threshold naprawiony w `services/qdrant.py`
- ❌ VLM opis obrazów nie działa (brak mmproj)

### Sesja 4 — Własny interfejs UI (2026-02-xx)
- ✅ Własny HTML/JS czat wbudowany w FastAPI (`routes/ui.py`)
- ✅ Sidebar z historią sesji (localStorage)
- ✅ Eksport/import rozmów (JSON)
- ✅ Upload drag&drop plików
- ✅ Przycisk "🧠 Indeksuj pliki w RAG"
- ✅ Toggle VLM/LLM w UI
- ✅ Statystyki: Zaindeksowane / Wektory RAG / Do indeksu / Dzisiaj
- ✅ Wskaźnik statusu backendu (dot + tekst)

### Sesja 5 — Model Switch API (2026-02-xx)
- ✅ `routes/model_switch.py` — API do przełączania modeli
- ✅ `GET /model/status` — status serwera LLM/VLM
- ✅ `POST /model/switch/llm` — przełącz na LLM
- ✅ `POST /model/switch/vlm` — przełącz na VLM
- ✅ `GET /model/list` — lista dostępnych modeli
- ✅ `GET /model/config` — aktualna konfiguracja

### Sesja 6 — start_klimtech_v3.py (2026-03-xx)
- ✅ Skrypt v7.0 — Dual Model Selection
- ✅ Dwie listy modeli przy starcie: LLM (model_thinking/) + VLM (model_video/)
- ✅ Wybór trybu startowego: czat (LLM) lub VLM (ingest z obrazkami)
- ✅ Automatyczne zarządzanie VRAM (pkill + czekanie)
- ✅ Konfiguracja zapisywana do `logs/models_config.json`
- ✅ Interaktywne menu w terminalu (opcje 1–5, q)
- ✅ Kontenery: qdrant, nextcloud, postgres_nextcloud, n8n
- ✅ `model_parametr.py` — obliczanie parametrów VRAM dla modelu

### Sesja 7 — Bieżące wymagania (2026-03-14) ← OBECNA
Zdefiniowano nowe wymagania do implementacji:

**1. UI — czat z wyborem modelu:**
- Użytkownik sam wybiera model LLM (lista z model_thinking/)
- Żadnych modeli na sztywno w UI

**2. UI — czysty embedding z wyborem modelu:**
- Użytkownik wybiera model do embeddingu (z listy)
- Upload plików do okienka
- Po wgraniu: lista zaindeksowanych plików z nazwą, hashem i rozmiarem
- Deduplikacja przez SQLite `file_registry.db` (hash + rozmiar)

**3. UI — ikonka "Backend niedostępny":**
- Przenieść ikonkę statusu obok przycisku "Wgraj pliki" (sidebar)

**4. Rezygnacja z Open WebUI:**
- OpenWebUI **usunięte** z `start_klimtech_v3.py` i architektury
- Własny lekki interfejs w `routes/ui.py` jest wystarczający

**5. start_klimtech_v3.py — tylko kontenery + backend:**
- Uruchamia TYLKO: qdrant, nextcloud, postgres_nextcloud, n8n, Backend FastAPI
- **NIE** uruchamia llama.cpp-server automatycznie
- W kolumnie sidebar (pod "Ostatnie pliki") dodać okienko **POSTĘP** wyświetlające logi startu w czasie rzeczywistym (WebSocket lub polling)

**6. Menu operacji pod okienkiem POSTĘP:**
- Przyciski zamiast wpisywania liter
- Opcje: LLM czat / VLM obrazki / Przełącz LLM↔VLM / Status / Zatrzymaj wszystko / Wyjście

---

## 5. Aktualna struktura plików

```
/media/lobo/BACKUP/KlimtechRAG/
│
├── .env                              # Zmienne środowiskowe
├── .gitignore
│
├── start_klimtech_v3.py              # ← GŁÓWNY skrypt startowy (v7.0)
├── start_backend_gpu.py              # Backend z GPU embedding (indeksowanie)
├── stop_klimtech.py                  # Zatrzymanie systemu
├── fix_start.py                      # Naprawa startowych problemów
│
├── backend_app/
│   ├── main.py                       # 89 linii — FastAPI app + middleware
│   ├── config.py                     # Pydantic Settings (.env)
│   ├── file_registry.py              # SQLite — status plików (hash, rozmiar)
│   ├── monitoring.py                 # Metryki GPU/CPU
│   ├── fs_tools.py                   # Narzędzia systemowe
│   │
│   ├── models/
│   │   └── schemas.py                # Pydantic models
│   │
│   ├── routes/
│   │   ├── chat.py                   # /query /v1/chat/completions /rag/debug /v1/models /v1/embeddings
│   │   ├── ingest.py                 # /upload /ingest /ingest_path /ingest_all
│   │   ├── filesystem.py             # /fs/*
│   │   ├── admin.py                  # /health /files/stats /files/pending
│   │   ├── model_switch.py           # /model/status /model/switch/* /model/list
│   │   └── ui.py                     # ← Główny UI (HTML/JS — czat + upload + stats)
│   │
│   ├── services/
│   │   ├── qdrant.py                 # QdrantDocumentStore singleton
│   │   ├── embeddings.py             # Embedder singleton (e5-large)
│   │   ├── rag.py                    # RAG pipeline
│   │   └── llm.py                    # OpenAIGenerator wrapper
│   │
│   ├── ingest/
│   │   └── image_handler.py          # Ekstrakcja + opis obrazów (VLM)
│   │
│   ├── utils/
│   │   ├── rate_limit.py
│   │   ├── tools.py
│   │   └── dependencies.py
│   │
│   └── scripts/
│       ├── watch_nextcloud.py        # Watchdog Nextcloud (PID file)
│       ├── ingest_gpu.py             # Masowe indeksowanie GPU
│       ├── ingest_pdfCPU.py
│       ├── ingest_pdfGPU.py
│       ├── ingest_repo.py            # Indeksowanie repozytoriów Git
│       └── model_parametr.py         # Obliczanie parametrów VRAM
│
├── data/
│   ├── file_registry.db              # SQLite (hash, rozmiar, status)
│   ├── uploads/                      # Backup wgranych plików
│   │   ├── pdf_RAG/ Doc_RAG/ txt_RAG/ json_RAG/
│   │   ├── Audio_RAG/ Video_RAG/ Images_RAG/
│   └── nextcloud/data/admin/files/RAG_Dane/
│
├── logs/
│   ├── backend.log
│   ├── llm_server_stdout.log / stderr.log
│   ├── llm_command.txt
│   ├── models_config.json            # Wybrane modele (llm/vlm/current_type)
│   └── watchdog_stdout.log / stderr.log
│
├── modele_LLM/
│   ├── model_thinking/               # LLM (czat)
│   ├── model_video/                  # VLM (obrazki)
│   ├── model_audio/                  # Audio
│   └── model_embedding/              # Embedding GGUF
│
├── llama.cpp/build/bin/
│   ├── llama-server                  # LLM/VLM server
│   └── llama-cli
│
└── PODSUMOWANIE.md                   ← ten plik
```

---

## 6. Znane problemy

| # | Priorytet | Problem | Status |
|---|-----------|---------|--------|
| 1 | 🔴 | VLM opis obrazów nie działa (brak mmproj) | Nierozwiązane |
| 2 | 🔴 | `ingest_gpu.py` zabija `start_klimtech.py` (konflikt GPU) | Nierozwiązane |
| 3 | 🟡 | `stop_klimtech.py` nie zabija wszystkich procesów | Do naprawy |
| 4 | 🟡 | Backend po ingest_gpu wraca na CPU embedding | Projektowe (VRAM) |
| 5 | 🟢 | `@router.on_event("startup")` deprecated | Nie wpływa na działanie |

---

## 7. Wymagania do implementacji (Sesja 7)

### 7.1 `start_klimtech_v3.py` — zmiany

**Co powinien robić:**
```
1. Uruchom kontenery Podman:
   ✅ qdrant
   ✅ nextcloud
   ✅ postgres_nextcloud
   ✅ n8n
2. Uruchom Backend FastAPI (port 8000)
3. NIE uruchamia llama.cpp-server automatycznie
4. Wyświetla w okienku POSTĘP (sidebar UI) logi startu
```

**Co wyświetlać w okienku POSTĘP (sidebar → pod "Ostatnie pliki"):**
```
a) KlimtechRAG v7.0 — Dual Model Selection
b) 📚 ZNALEZIONE MODELE (wg katalogów)
c) 📦 LISTA 1: MODELE LLM DO CZATU (model_thinking/)
d) 📷 LISTA 2: MODELE VLM - VISION (model_video/)
e) 🚀 URUCHAMIANIE LLM (CZAT) SERVER
f) ANALIZA ZASOBÓW VRAM
g) 🔍 Test kontekstu 98304 tokenów
h) 📋 WYBRANE PARAMETRY
i) ⏳ Czekam 15s...  →  ✅ LLM (Czat) Server działa (PID: ...)
j) 🚀 Uruchamianie: Backend FastAPI...
k) ⏳ Czekam 5s...  →  ✅ Backend FastAPI działa
```

### 7.2 Menu operacji (pod okienkiem POSTĘP)

```
📋 MENU OPERACJI
[1] 💬 Przełącz na LLM (czat)
[2] 📷 Przełącz na VLM (obrazki)
[3] 🔄 Przełącz model LLM ↔ VLM
[4] 📊 Status systemu
[5] 🛑 Zatrzymaj wszystko
[q] ❌ Wyjście
```
Każda opcja → przycisk HTML (nie wpisywanie liter).

### 7.3 UI — czat

- Dropdown z listą modeli LLM (z `model_thinking/`)
- Użytkownik wybiera model i klika "Załaduj" → backend `/model/switch/llm`
- Brak modelu na sztywno w kodzie

### 7.4 UI — embedding

- Dropdown z listą modeli embeddingowych (z `model_embedding/` + HuggingFace)
- Upload plików → po wgraniu wyświetlana lista:
  - Nazwa pliku
  - Hash MD5/SHA256
  - Rozmiar (KB/MB)
  - Status (nowy / już zaindeksowany)
- Deduplikacja przez `file_registry.db` (hash + rozmiar)

### 7.5 UI — ikonka statusu backendu

- Przenieść ikonkę (dot + "Backend niedostępny") bezpośrednio obok przycisku "Wgraj pliki"
- Aktualizacja co 10s (polling `/health`)

---

## 8. Komendy operacyjne

### Sync z GitHub (laptop → serwer)
```bash
# Laptop (wysyłanie):
git add -A && git commit -m "Sync" -a || true && git push --force

# Serwer (pobieranie):
git pull
```

### Uruchomienie systemu
```bash
cd /media/lobo/BACKUP/KlimtechRAG
python3 start_klimtech_v3.py
```

### Zatrzymanie
```bash
python3 stop_klimtech.py
# lub ręcznie:
pkill -f "uvicorn backend_app"
pkill -f "llama-server"
fuser -k 8000/tcp 2>/dev/null
fuser -k 8082/tcp 2>/dev/null
```

### Indeksowanie GPU (bez LLM)
```bash
python3 start_backend_gpu.py
# Po zakończeniu CTRL+C → wraca do start_klimtech_v3.py
```

### Diagnostyka RAG
```bash
curl http://192.168.31.70:8000/rag/debug | python3 -m json.tool
curl http://192.168.31.70:6333/collections/klimtech_docs
```

### Przełączanie modeli (API)
```bash
curl -X POST http://192.168.31.70:8000/model/switch/llm
curl -X POST http://192.168.31.70:8000/model/switch/vlm
curl http://192.168.31.70:8000/model/status
curl http://192.168.31.70:8000/model/list
```

---

## 9. Endpointy backendu

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/` | GET | Główny UI (czat) |
| `/v1/chat/completions` | POST | RAG czat (OpenAI-compatible) |
| `/v1/embeddings` | POST | Embedding (OpenAI-compatible) |
| `/v1/models` | GET | Lista modeli |
| `/upload` | POST | Wgraj plik |
| `/ingest` | POST | Indeksuj wgrany plik |
| `/ingest_path` | POST | Indeksuj z ścieżki |
| `/ingest_all` | POST | Indeksuj wszystkie pending |
| `/model/status` | GET | Status LLM/VLM serwera |
| `/model/switch/llm` | POST | Przełącz na LLM |
| `/model/switch/vlm` | POST | Przełącz na VLM |
| `/model/list` | GET | Lista modeli GGUF |
| `/model/config` | GET | Aktualna konfiguracja |
| `/files/stats` | GET | Statystyki plików/wektorów |
| `/files/pending` | GET | Pliki oczekujące na indeksowanie |
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

*Plik wygenerowany automatycznie na podstawie przeglądu repozytorium i historii sesji.*
*Następna aktualizacja: po implementacji wymagań Sesji 7.*
