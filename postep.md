# KlimtechRAG — STATUS SESJI (plik wznowienia)

> **Cel tego pliku:** Po wczytaniu tego pliku model AI natychmiast wie co zostało zrobione, co jest do zrobienia i jakie są plany. Aktualizuj po każdej sesji.

**Ostatnia aktualizacja:** 2026-03-21  
**Wersja systemu:** v7.3  
**Serwer:** 192.168.31.70 | Katalog: `/media/lobo/BACKUP/KlimtechRAG/`  
**GitHub:** https://github.com/Satham666/KlimtechRAG

---

## ⚡ SZYBKI KONTEKST

**Co to jest:** Lokalny system RAG do dokumentacji technicznej po polsku. 100% offline, serwer z GPU AMD Instinct 16 GB (ROCm). Backend FastAPI, LLM przez llama.cpp, Qdrant, Nextcloud, n8n.

**Kluczowe adresy:**
- Backend UI: `https://192.168.31.70:8443`
- Nextcloud: `http://192.168.31.70:8081` (admin / klimtech123)
- n8n: `http://192.168.31.70:5678`
- Backend API: `http://192.168.31.70:8000`

**ZAWSZE przed uruchomieniem .py na serwerze:**
```fish
cd /media/lobo/BACKUP/KlimtechRAG && source venv/bin/activate.fish
```

---

## ✅ CO ZOSTAŁO ZROBIONE

### Sesje 1–8: Fundament systemu
- Architektura FastAPI + Haystack 2.x + Qdrant + llama.cpp (ROCm)
- 3 pipeline'y embeddingu: e5-large (tekst), ColPali (PDF), VLM (obrazy w PDF)
- UI (HTML/JS/Tailwind), model switch, rate limiting, API key auth
- ColPali multi-vector embedding (`vidore/colpali-v1.3-hf`)

### Sesja 9: Web Search (v7.1)
- Panel Web Search (DuckDuckGo), tryb hybrydowy RAG+Web
- Endpointy: `/web/search`, `/web/fetch`, `/web/summarize`

### Sesja 10: Nextcloud AI Integration (v7.2)
- NC apps: `integration_openai` v3.10.1 + `assistant` v2.13.0
- CORS middleware, Bearer auth, endpoint `/models` (bez /v1/)
- 3 workflow JSON dla n8n (auto-index, chat webhook, VRAM manager)
- Whisper STT: `/v1/audio/transcriptions`

### Sesja 11: UI v7.3, Lazy Loading, Naprawy krytyczne
- **gpu_status.py** — endpoint `/gpu/status` (rocm-smi, temp, VRAM, use)
- **Lazy loading VRAM** — embedding i pipeline tworzony dopiero przy użyciu
  - `embeddings.py` → `get_text_embedder()` / `get_doc_embedder()`
  - `qdrant.py` → `get_embedding_dimension()` z cache znanych wymiarów
  - `rag.py` → `get_indexing_pipeline()` / `get_rag_pipeline()`
  - `llm.py` → standalone `OpenAIGenerator` (nie wyciąga z RAG pipeline)
  - **Wynik: VRAM na starcie 14 MB** (było 4.5 GB)
- **use_rag=False domyślnie** — czat nie dławi się kontekstem RAG
- **Fix `_detect_base()`** — preferuje `/media/lobo/BACKUP/` nad `~/KlimtechRAG`
- **Model dropdown działa** — 4 LLM, 5 VLM, 2 Audio, 3 Embedding
- **GPU Dashboard** — live monitoring co 2s
- HTTPS nginx reverse proxy (self-signed cert)
- `index.html` — pełnofunkcyjny UI z czatem, sesjami, upload, web search

### Sekcja 16: VLM Prompts (UKOŃCZONA)
- `backend_app/prompts/__init__.py` — utworzony
- `backend_app/prompts/vlm_prompts.py` — 8 wariantów promptów: DEFAULT, DIAGRAM, CHART, TABLE, PHOTO, SCREENSHOT, TECHNICAL, MEDICAL
- `VLM_PARAMS` dict (max_tokens, temperature, context_length, gpu_layers)
- Funkcje: `get_prompt()`, `get_full_prompt()`, `get_vlm_params()`
- **NIE podpięte jeszcze** do `image_handler.py` (krok 16d/16e)

---

## ❌ NIEROZWIĄZANE PROBLEMY

### Problem 1: Nextcloud AI Assistant nie odpowiada — 🔴 PRIORYTET
**Status:** NIEROZWIĄZANY  
**Objawy:** POST `/check_generation` z kodem HTTP 417 (Expectation Failed).  
**Diagnoza:** Backend działa (curl OK), API key ustawiony, URL poprawny.  
**Możliwe przyczyny:**
1. Header `Expect: 100-continue` wysyłany przez NC — FastAPI go nie obsługuje → 417
2. Sesja/cache przeglądarki
3. Provider w NC admin nie ustawiony dla konkretnego task type

**Do sprawdzenia:**
```fish
podman logs nextcloud 2>&1 | tail -100
# + dodać middleware w main.py usuwający header Expect
```

### Problem 2: Bielik-11B nie mieści się w VRAM — 🟡
**Status:** OBEJŚCIE (Bielik-4.5B)  
**Problem:** ~4.7 GB zajęte przez ROCm runtime.

### Problem 3: VLM opis obrazów — brak mmproj w llama-cli — 🔴
**Status:** NIEROZWIĄZANE  

### Problem 4: ingest_gpu.py zabija start_klimtech.py — 🔴
**Status:** NIEROZWIĄZANE  
**Obejście:** Używaj `start_backend_gpu.py`

### Problem 5: monitoring.py GPU: 0% dla AMD — 🟡 kosmetyczny
**Status:** Rozwiązany przez `gpu_status.py` (rocm-smi)

### Problem 6: Refaktoryzacja image_handler.py — 🟡
**Status:** Prompty gotowe (vlm_prompts.py), ale **nie podpięte** do image_handler.py  
**Kroki 16d-16e** — do wykonania

---

## ⏳ DO ZROBIENIA

### Priorytet WYSOKI

| # | Zadanie | Notatki |
|---|---------|---------|
| A | Debugować NC Assistant 417 | Sprawdź Expect header, logi NC |
| B | Przetestować Whisper STT | `curl -F file=@audio.mp3 .../v1/audio/transcriptions` |
| C | Zmapować Speech-to-text w NC Admin | Po teście B |

### Priorytet ŚREDNI — Sekcja 16d-16e

| # | Zadanie | Plik | Status |
|---|---------|------|--------|
| 16d | Refaktoryzuj `image_handler.py` — import z `vlm_prompts` | `ingest/image_handler.py` | ⏳ |
| 16e | Dynamiczne params llama-cli (zamiast hardcoded) | `ingest/image_handler.py` | ⏳ |

### Priorytet NISKI

| # | Zadanie |
|---|---------|
| L1 | Skrypt `setup_nextcloud_ai.sh` |
| L2 | Heurystyka RAG off dla NC summarize (msg > 2000 znaków) |
| L3 | Chunked summarization dla długich dokumentów |
| L4 | NC `webhook_listeners` — event-driven zamiast pollingu |
| L5 | Auto-transkrypcja audio w n8n (Whisper + e5-large → Qdrant) |
| L6 | Naprawić `stop_klimtech.py` — nie zabija wszystkich procesów |

---

## 📁 MAPA KLUCZOWYCH PLIKÓW

| Plik | Rola |
|------|------|
| `backend_app/main.py` | Entry point: FastAPI, lifespan, CORS, routery |
| `backend_app/config.py` | Pydantic Settings (czyta z .env), `_detect_base()` |
| `backend_app/routes/chat.py` | `/v1/chat/completions`, `/v1/models`, `/v1/embeddings` |
| `backend_app/routes/ingest.py` | Upload, indeksowanie plików, Nextcloud save |
| `backend_app/routes/model_switch.py` | Start/stop/switch llama-server, progress log |
| `backend_app/routes/gpu_status.py` | GPU metrics (rocm-smi) |
| `backend_app/routes/whisper_stt.py` | Whisper STT endpoint |
| `backend_app/services/model_manager.py` | Lifecycle llama-server, `_detect_base()` |
| `backend_app/services/embeddings.py` | **Lazy loading** e5-large |
| `backend_app/services/rag.py` | **Lazy loading** pipeline RAG |
| `backend_app/services/llm.py` | **Standalone** OpenAIGenerator |
| `backend_app/services/colpali_embedder.py` | ColPali multi-vector |
| `backend_app/models/schemas.py` | Pydantic: **use_rag=False** domyślnie |
| `backend_app/prompts/vlm_prompts.py` | 8 wariantów promptów VLM |
| `backend_app/ingest/image_handler.py` | VLM opisy obrazów (prompty hardcoded → do refaktoru) |
| `backend_app/static/index.html` | UI v7.3 (czat, GPU dashboard, upload) |
| `start_klimtech_v3.py` | Start systemu (nginx + kontenery + backend) |
| `stop_klimtech.py` | Stop systemu |

---

## 🔧 WAŻNE SZCZEGÓŁY TECHNICZNE

### Lazy loading — krytyczna zmiana v7.3
**NIE COFAĆ** do eager loading. Kluczowe pliki:
- `embeddings.py`: `get_text_embedder()` / `get_doc_embedder()` — singleton z `_text_embedder = None`
- `qdrant.py`: `KNOWN_EMBEDDING_DIMS` dict — wymiar z cache, bez ładowania modelu
- `rag.py`: `get_indexing_pipeline()` / `get_rag_pipeline()` — pipeline tworzony lazy
- `llm.py`: standalone `OpenAIGenerator` — nie importuje z rag.py

### use_rag=False — krytyczna zmiana v7.3
- `schemas.py` linia 19: `use_rag: bool = False`
- UI: `index.html` linia ~1001: `if(webMode){ requestBody.web_search = true; requestBody.use_rag = true; }`
- Bez RAG czat idzie prosto do llama-server (39 tokenów, nie 78000+)

### Kontenery Podman
```fish
podman ps                          # lista
podman start qdrant nextcloud postgres_nextcloud n8n
```

### nginx HTTPS
```fish
sudo nginx                         # start
sudo nginx -s stop                 # stop
# Konfiguracja: /etc/nginx/sites-available/klimtech
```

---

## 📋 STAN TESTÓW

| Test | Status |
|------|--------|
| Backend health (`/health`) | ✅ OK |
| Lista modeli (`/v1/models`) | ✅ OK |
| Chat bez RAG (`use_rag: false`) | ✅ OK |
| Chat z RAG (`use_rag: true`) | ⚠️ Wymaga embedding na GPU (konflikt z LLM) |
| HTTPS backend (`:8443`) | ✅ OK |
| GPU status (`/gpu/status`) | ✅ OK |
| Model dropdown w UI | ✅ OK (4 LLM, 5 VLM, 2 Audio, 3 Embed) |
| NC AI Assistant | ❌ 417 |
| Whisper STT | ⏳ NIE TESTOWANY |
| n8n auto-index | ⏳ NIE TESTOWANY |
| ColPali PDF ingest | ⏳ NIE TESTOWANY (end-to-end) |

---

## 🗒️ NOTATKI DLA NASTĘPNEJ SESJI

1. **Pierwsze co zrobić:**
```fish
cd /media/lobo/BACKUP/KlimtechRAG && source venv/bin/activate.fish
python3 start_klimtech_v3.py
curl -k https://192.168.31.70:8443/health
```

2. **Rekomendowana kolejność pracy:**
   1. Debugowanie NC Asystenta (417) — najważniejszy nierozwiązany problem
   2. Test Whisper STT
   3. Sekcja 16d-16e (podpięcie vlm_prompts do image_handler.py)

3. **Przy debugowaniu NC Asystenta:** Prawdopodobna przyczyna to header `Expect: 100-continue` — middleware w `main.py` usuwający ten header powinno rozwiązać problem.

---

*Ostatnia aktualizacja: 2026-03-21*
