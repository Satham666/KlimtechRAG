# KlimtechRAG — Podsumowanie Projektu

**Data aktualizacji:** 2026-03-16  
**Wersja systemu:** v7.2 (Web Search + Dual Model + Nextcloud AI)  
**Repozytorium:** https://github.com/Satham666/KlimtechRAG  
**Katalog serwera:** `/media/lobo/BACKUP/KlimtechRAG/`  
**Katalog laptopa:** `~/KlimtechRAG`

---

> **Nowe w v7.2:** Integracja Nextcloud AI Assistant (integration_openai → KlimtechRAG backend), workflow n8n (auto-indeksowanie + zarządzanie VRAM), dostosowanie `/v1/chat/completions` pod Nextcloud.  
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
- **Czat AI w Nextcloud** — Nextcloud Assistant podpięty do lokalnego backendu (NOWE v7.2)
- **Automatyczne indeksowanie z Nextcloud** — n8n workflow z zarządzaniem VRAM (NOWE v7.2)

---

## 2. Architektura systemu

### Diagram architektury (v7.2 — z Nextcloud AI)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UŻYTKOWNICY                                      │
│         ↓                    ↓                    ↓                       │
│  http://..:8000              http://..:8081        http://..:5678         │
│  (KlimtechRAG UI)           (Nextcloud + AI)     (n8n workflows)         │
└──────────┬──────────────────────────┬───────────────────────┬────────────┘
           │                          │                       │
           │ Chat / Upload            │ Chat / Summarize      │ Trigger
           ↓                          ↓                       ↓
┌────────────────────────────────────────────────────────────────────────────┐
│              KlimtechRAG Backend (port 8000) — GATEWAY                     │
│  FastAPI                                                                    │
│  ├── /v1/chat/completions  ← OWUI + Nextcloud Assistant + n8n              │
│  ├── /v1/models            ← OWUI + Nextcloud (lista modeli)               │
│  ├── /v1/embeddings        ← OWUI RAG (Wariant C)                         │
│  ├── /upload, /ingest_path ← upload plików                                 │
│  ├── /web/search,fetch,summarize ← Web Search panel                        │
│  ├── /rag/debug            ← diagnostyka                                   │
│  └── Watchdog (Nextcloud)  ← automatyczne indeksowanie                     │
└──────────┬─────────────────────┬──────────────────┬────────────────────────┘
           │                     │                  │
           ↓                     ↓                  ↓
┌──────────────────┐  ┌─────────────────┐  ┌──────────────────────────────────┐
│ llama.cpp-server │  │ Qdrant (6333)   │  │ Nextcloud (8081)                 │
│ (port 8082)      │  │ klimtech_docs   │  │ + integration_openai (app)       │
│ Bielik-11B Q8_0  │  │ 5114+ punktów   │  │ + assistant (app)                │
│ ~14GB VRAM       │  │ klimtech_colpali│  │ → Service URL: http://..:8000    │
└──────────────────┘  └─────────────────┘  └──────────────────────────────────┘
```

### Data Flow — Nextcloud AI Assistant (NOWE v7.2)

```
Nextcloud Assistant (przeglądarka na :8081)
       │
       │  POST /v1/chat/completions (OpenAI-compatible)
       │  Authorization: Bearer sk-local
       ↓
KlimtechRAG Backend (:8000)
       │
       ├── RAG retrieval (Qdrant) ──► kontekst z dokumentów
       │
       └── Forward do llama.cpp-server (:8082) ──► odpowiedź Bielik-11B
```

### Data Flow — Ingestion (indeksowanie dokumentów)

```
Upload/Watchdog ──► Ekstrakcja tekstu ──► Chunking (200 słów) ──► Embedding (e5-large)
       ──► Qdrant (klimtech_docs) + SQLite file_registry.db
```

### Data Flow — Query (odpowiadanie na pytania)

```
Pytanie ──► Embedding ──► Retrieval (top_k=10) ──► Prompt Builder ──► llama.cpp (Bielik-11B)
       + opcjonalnie: Cache (TTL=1h), DuckDuckGo fallback, Tool Calling
```

---

## 3. Stack technologiczny

### 3.1 Infrastruktura

| Warstwa | Technologia | Uwagi |
|---------|-------------|-------|
| **System** | Linux Mint / Ubuntu 24 | Serwer + Laptop |
| **Python** | 3.12 (venv) | — |
| **GPU** | AMD Instinct 16 GB | ROCm 7.2, `HSA_OVERRIDE_GFX_VERSION=9.0.6` |
| **PyTorch** | 2.5.1+rocm6.2 | — |
| **Backend** | FastAPI + Haystack 2.x | Port 8000 |
| **LLM/VLM** | llama.cpp-server | Port 8082 |
| **Wektorowa baza** | Qdrant (Podman) | Port 6333 |
| **Kontenery** | Podman | qdrant, nextcloud, postgres_nextcloud, n8n |
| **UI** | HTML/JS + Bootstrap | `backend_app/static/index.html` |
| **Nextcloud AI** | integration_openai + assistant | Port 8081 → backend :8000 (NOWE) |
| **Automatyzacja** | n8n | Port 5678 (NOWE) |
| **Sync** | Git → GitHub | laptop → push, serwer → pull |

### 3.2 Modele GGUF (`modele_LLM/`)

| Typ | Model | VRAM | Kwantyzacja |
|-----|-------|------|-------------|
| LLM | Bielik-11B-v3.0-Instruct | ~14 GB | Q8_0 |
| LLM | Bielik-4.5B-v3.0-Instruct | ~5 GB | Q8_0 |
| LLM | LFM2-2.6B | ~6 GB | F16 |
| VLM | LFM2.5-VL-1.6B (+mmproj) | ~3.2 GB | BF16 |
| VLM | Qwen2.5-VL-7B-Instruct (+mmproj) | ~4.7 GB | Q4_K_XL |
| Audio | LFM2.5-Audio-1.5B (+mmproj) | — | F16 |
| Embed | bge-large-en-v1.5 | — | Q8_0 |

### 3.3 Modele HuggingFace

| Model | Typ | Wymiar | Kolekcja |
|-------|-----|--------|----------|
| `intfloat/multilingual-e5-large` | Embedding tekstu | 1024 | `klimtech_docs` |
| `vidore/colpali-v1.3-hf` | Embedding wizualny | 128 | `klimtech_colpali` |

---

## 4. Struktura plików

### 4.1 Backend (`backend_app/`)

```
backend_app/
├── main.py                 # Entry point FastAPI
├── config.py               # Pydantic Settings
├── file_registry.py        # SQLite — rejestracja plików
├── monitoring.py            # CPU, RAM, GPU stats
├── fs_tools.py             # Filesystem tools
├── routes/
│   ├── chat.py             # /v1/chat/completions, /query, /v1/embeddings, /v1/models
│   ├── ingest.py           # /upload, /ingest, /ingest_path, /ingest_all
│   ├── admin.py            # /health, /metrics, /files/*
│   ├── model_switch.py     # /model/status, /model/switch, /model/list
│   ├── filesystem.py       # /fs/list, /fs/glob, /fs/read, /fs/grep
│   ├── web_search.py       # /web/search, /web/fetch, /web/summarize
│   └── ui.py               # GET / (HTML UI)
├── services/
│   ├── qdrant.py, embeddings.py, rag.py, llm.py
│   ├── model_manager.py    # llama-server lifecycle
│   └── colpali_embedder.py # ColPali multi-vector
├── models/schemas.py       # Pydantic schemas
├── utils/                  # rate_limit, tools, dependencies
├── scripts/                # watch_nextcloud, ingest_gpu, ingest_colpali
├── ingest/image_handler.py # Ekstrakcja obrazów z PDF
└── static/index.html       # Główny UI
```

---

## 5. Endpointy API (40 endpointów)

| Grupa | Endpointy | Opis |
|-------|-----------|------|
| Chat & RAG (8) | `/v1/models`, `/v1/embeddings`, `/v1/chat/completions`, `/query`, `/code_query`, `/rag/debug`, `/` | Główne AI |
| Ingest (6) | `/upload`, `/ingest`, `/ingest_path`, `/ingest_all`, `/ingest_pdf_vlm`, `/vlm/status` | Indeksowanie |
| Model (10) | `/model/status`, `/model/switch/*`, `/model/list`, `/model/start`, `/model/stop` itd. | Zarządzanie LLM |
| Admin (8) | `/health`, `/metrics`, `/documents`, `/ws/health`, `/files/*` | Monitoring |
| Filesystem (4) | `/fs/list`, `/fs/glob`, `/fs/read`, `/fs/grep` | Tool calling |
| Web Search (4) | `/web/status`, `/web/search`, `/web/fetch`, `/web/summarize` | Web (v7.1) |

---

## 6. Funkcjonalności

### 6.1–6.4 RAG, ColPali, File Registry, Cache

Bez zmian — patrz poprzednie wersje PODSUMOWANIE.

### 6.5 DuckDuckGo Web Search

- `/query` — automatyczny fallback
- `/v1/chat/completions` — gdy `web_search: true` (tryb hybrydowy)

### 6.6 Web Search UI (zakładka w sidebarze, v7.1)

Zakładka "🌐 Web Search" obok "📚 RAG", podgląd stron, podsumowanie LLM, historia, ikona 🌐 w input bar.

### 6.7 LLM Tool Calling

ls, glob, read, grep — sandboxed pod `fs_root`, max 3 iteracje.

### 6.8 Model Switch, 6.9 Rate Limiting, 6.10 API Key Auth

Bez zmian.

---

## 7. Konfiguracja (.env)

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

---

## 8. Wydajność

| Operacja | CPU | GPU | Przysp. |
|----------|-----|-----|---------|
| Embedding batch | ~18s | ~1.4s | 13× |
| PDF 20MB | ~15 min | ~13s | ~70× |

VRAM: Bielik-11B ~14GB, e5-large ~2.5GB, ColPali ~6-8GB — tylko jeden naraz na 16GB.

---

## 9. Historia sesji

- Sesja 1–3: Diagnoza, refaktoryzacja, GPU embedding
- Sesja 4–6: UI, Model Switch, start_klimtech_v3
- Sesja 7–8: ColPali, ROCm, v7.0
- Sesja 9: Web Search (v7.1)
- **Sesja 10: Nextcloud AI Integration (v7.2)** ⭐

---

## 10. Znane problemy

| # | Priorytet | Problem | Status |
|---|-----------|---------|--------|
| 1 | 🔴 | VLM opis obrazów (brak mmproj) | Nierozwiązane |
| 2 | 🔴 | `ingest_gpu.py` zabija `start_klimtech.py` | Nierozwiązane |
| 3 | 🟡 | `monitoring.py` GPU: 0% dla AMD | Kosmetyczny |
| 4 | 🟡 | `stop_klimtech.py` nie zabija wszystkich | Do naprawy |
| 5 | 🟢 | `on_event("startup")` deprecated | Nie wpływa |

---

## 11. Integracja Nextcloud AI Assistant ⭐ NOWE v7.2

### 11.1 Instalacja aplikacji

```bash
sudo -u www-data php /var/www/nextcloud/occ app:install integration_openai
sudo -u www-data php /var/www/nextcloud/occ app:install assistant
```

### 11.2 KRYTYCZNE — config.php

```php
'allow_local_remote_servers' => true,
```

**Bez tego Nextcloud blokuje połączenia do prywatnych IP (192.168.x.x).**

### 11.3 Konfiguracja (Admin → Artificial Intelligence)

| Pole | Wartość | UWAGA |
|------|---------|-------|
| Service URL | `http://192.168.31.70:8000` | BEZ `/v1/` na końcu! |
| API Key | `sk-local` lub pusty | Backend akceptuje dowolny |
| Service Name | `KlimtechRAG Bielik-11b` | Opcjonalne |
| Model | `klimtech-bielik` | Z dropdown `/v1/models` |

### 11.4 Mapowanie zadań

Ustaw "OpenAI and LocalAI integration" jako provider dla: Free prompt, Summarize, Generate headline, Reformulate, Context Write, Extract topics.

Nie obsługiwane: Speech-to-text, Image generation.

### 11.5 Jak to działa

KlimtechRAG backend jest **jedynym gateway**. Nextcloud wysyła standardowe OpenAI requests → backend robi RAG (Qdrant) → forward do llama.cpp → zwraca odpowiedź.

### 11.6 Format `/v1/models`

```json
{"object":"list","data":[{"id":"klimtech-bielik","object":"model","created":1700000000,"owned_by":"klimtechrag"}]}
```

### 11.7 Testy

```bash
curl http://192.168.31.70:8000/v1/models
curl -X POST http://192.168.31.70:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{"model":"klimtech-bielik","messages":[{"role":"user","content":"Co to jest RAG?"}]}'
```

### 11.8 Znane pułapki

| Problem | Rozwiązanie |
|---------|-------------|
| Dropdown modeli pusty | Sprawdź `/v1/models` |
| Connection refused | Dodaj `allow_local_remote_servers => true` |
| Podwójne `/v1/v1/` | Usuń `/v1/` z Service URL |
| Timeout przy summarize | Zwiększ PHP timeout |
| Default `gpt-3.5-turbo` | Ręcznie wybierz model w admin |

---

## 12. Workflow n8n — automatyzacja ⭐ NOWE v7.2

### 12.1 Credentials Nextcloud w n8n

- WebDAV URL: `http://192.168.31.70:8081/remote.php/webdav`
- User + **hasło aplikacji** (nie główne hasło!)

### 12.2 Workflow: Auto-indeksowanie

```
Schedule (5 min) → Nextcloud List /RAG_Dane/ → Code: porównaj z poprzednim skanem
  → IF nowe pliki: Stop LLM → Wait 10s → Download + Upload do /ingest → Start LLM → Verify health
```

### 12.3 Workflow: Czat webhook

```
Webhook POST /chat → HTTP POST http://..:8000/v1/chat/completions → Respond to Webhook
```

### 12.4 Zarządzanie VRAM

Opcjonalny management API (port 9000) do stop/start llama-server przez n8n — VRAM jest zwalniany tylko po pełnym killu procesu.

### 12.5 Nextcloud Webhooks (opcja)

`webhook_listeners` app (NC30+) → `NodeCreatedEvent` → trigger n8n workflow.

---

## 13. Dostosowanie `/v1/chat/completions` pod Nextcloud ⭐ NOWE v7.2

### 13.1 Co Nextcloud wysyła

- System message zawsze pierwszy
- User message z treścią (lub dokumentem przy summarize)
- Header `Authorization: Bearer {key}`
- Background tasks: bez `stream`
- Chat with AI: ostatnie 10 tur

### 13.2 Routing w backendzie

- `use_rag: true` (default) → każde zapytanie z Nextcloud przechodzi przez RAG
- `web_search: false` (default) → Nextcloud nie włącza web search
- ColPali routing: nagłówek `X-Embedding-Model`

### 13.3 Kompatybilność llama.cpp-server

Flaga `--alias "Bielik-11b"` → czysta nazwa w `/v1/models` (zamiast ścieżki GGUF).

---

## 14. Komendy operacyjne

```bash
# Aktywacja venv
source /media/lobo/BACKUP/KlimtechRAG/venv/bin/activate

# Sync: laptop → GitHub → serwer
git add -A && git commit -m "Sync" -a || true && git push --force  # laptop
git pull                                                            # serwer

# Diagnostyka
curl http://192.168.31.70:8000/health
curl http://192.168.31.70:8000/v1/models
curl http://192.168.31.70:8000/rag/debug
curl http://192.168.31.70:8000/web/status

# ColPali
pkill -f llama-server
python3 -m backend_app.scripts.ingest_colpali --dir data/uploads/pdf_RAG
```

---

## 15. Adresy sieciowe

| Usługa | Adres |
|--------|-------|
| 🔧 API Backend | http://192.168.31.70:8000 |
| 📦 Qdrant | http://192.168.31.70:6333 |
| ☁️ Nextcloud + AI | http://192.168.31.70:8081 |
| 🔗 n8n | http://192.168.31.70:5678 |
| 🤖 LLM/VLM | http://192.168.31.70:8082 |

---

## Znane problemy (2026-03-16)

### 1. Nextcloud AI Assistant nie odpowiada
- **Status:** ❌ NIEROZWIĄZANY
- **Objawy:** Ciągłe zapytania POST /check_generation z kodem 417
- **Diagnoza:** Backend działa, curl działa, ale Asystent NC nie odbiera odpowiedzi
- **Do wypróbowania:** Wyczyścić cache przeglądarki, tryb incognito

### 2. VRAM - Bielik-11B
- **Status:** ⚠️ OBEJŚCIE
- **Problem:** ~4.7GB VRAM zajęte, Bielik-11B nie mieści się
- **Rozwiązanie:** Używamy Bielik-4.5B (~5GB VRAM)

---

*Ostatnia aktualizacja: 2026-03-16 — v7.2: Integracja Nextcloud AI, porty zaktualizowane (8443→8081), problemy z Assistant*
