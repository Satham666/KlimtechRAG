# KlimtechRAG — STATUS SESJI (plik wznowienia)

> **Cel tego pliku:** Po wczytaniu tego pliku model AI natychmiast wie co zostało zrobione, co jest do zrobienia i jakie są plany. Aktualizuj po każdej sesji.

**Ostatnia aktualizacja:** 2026-03-23
**Wersja systemu:** v7.4
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

### Sesja 12: Audyt bezpieczeństwa + czyszczenie projektu (2026-03-23, laptop)

#### Audyt bezpieczeństwa (plik: `AUDYT_2026-03-23_22-19-27.md`)
Połączono audyt Haiku 4.5 (2026-03-21) z nowym audytem Sonnet 4.6. 25 znalezisk (5 CRITICAL, 6 HIGH, 7 MEDIUM, 4 LOW, 3 INFO). Naprawiono wszystkie pozycje CRITICAL i HIGH. Postęp zapisany w `POSTEP_AUDYT.md`.

Kluczowe naprawy:
- `utils/dependencies.py` — `secrets.compare_digest` zamiast `==` (timing attack)
- `routes/admin.py` — auth na `/documents DELETE`, `/files/*`, WebSocket `/ws/health`
- `routes/chat.py` — auth na `/v1/embeddings`, `/rag/debug`, `/models`
- `routes/ingest.py` — `resolve_path()` w `/ingest_path` i `/ingest_pdf_vlm`, sanityzacja nazw plików, pre-check Content-Length
- `routes/model_switch.py` — router-level auth, walidacja ścieżki modelu
- `routes/web_search.py` — SSRF: `_assert_public_url()`, `require_api_key` na wszystkich endpointach
- `routes/whisper_stt.py` — limit 100 MB, auth na wszystkich endpointach
- `services/model_manager.py` — FD leak: `open()` → `with open(...)` (2 miejsca)
- `ingest/image_handler.py` — usunięto hardcoded ścieżki, używa `_find_llama_binary()`
- Stworzono `.env` (root projektu) z `KLIMTECH_API_KEY=sk-local`
- `.gitignore` — dodano `*.bak`, `*.backup`, `nohup.out`

#### Czyszczenie projektu
Usunięto pliki `.bak`/`.backup`/`.old` (6 plików). Zarchiwizowano 7 plików `session-*.md` → `MD_files/Archiw/`. Przeniesiono skrypty do `scripts/` (`fix_postgres.sh`, `setup_sudoers_nginx.sh`, `ingest_embed.py`). Przekonwertowano `scripts/plan.txt` → `MD_files/INSTALACJA_NEXTCLOUD.md`. Usunięto `modele_LLM/.env`, `code.html`, `ingest_fix.py`, `backend_app/prompts/apply_changes.sh`, puste katalogi repo_github.

---

### Sesja 13: Filtrowanie tematyczne RAG — Fazy 0–3 (2026-03-23, laptop)

#### Nowy pakiet `backend_app/categories/`
- `definitions.py` — **14 kategorii głównych** z pełną strukturą podkategorii (zgodnie z `DRZEWO_KATEGORII.md`): medicine, law, finance, technology, construction, education, agriculture, society, culture, sport, family, religion, environment, other. Każda kategoria ma: id, names (pl/en/de), path, path_hints, keywords (pl/en/de), subcategories (3 poziomy głębokości).
- `classifier.py` — `classify_document(filepath, content) → str`. Logika: (1) path-based z normalizacją diakrytyków, (2) keyword-based na 3000 znakach treści (PL+EN+DE), (3) fallback "other". Pre-kalkulowane struktury dla wydajności.
- `__init__.py` — eksportuje `CATEGORIES`, `classify_document`, `get_category_ids`, `get_category_name`.

#### Integracja z pipeline'm
- `services/rag.py` — dodano `_build_category_filter()` i `run_rag_pipeline(query, category_filter)`. Filtr Qdrant: `{"field": "meta.category", "operator": "==", "value": category}`.
- `routes/ingest.py` — 3 miejsca (`ingest_file_background`, `/upload`, `/ingest_path`) — każdy dokument dostaje `meta["category"]` z klasyfikatora.
- `routes/chat.py` — endpoint `/query` używa `run_rag_pipeline(query, category_filter)`.
- `models/schemas.py` — `QueryRequest` ma nowe pole `category_filter: str | None = None`.

#### Skrypt Nextcloud
- `scripts/create_nextcloud_folders.py` — tworzy strukturę 300+ folderów w Nextcloud przez `podman exec occ files:mkdir`. Obsługuje `--dry-run`, `--base-path`. Uruchomić na serwerze gdy będzie dostęp.

#### Archiwizacja
- `category_definitions.py` (root) → `MD_files/Archiw/`
- `category_generator.py` (root) → `MD_files/Archiw/`

---

### Sekcja 16: VLM Prompts (UKOŃCZONA) - DODANE DO DOKUMENTACJI
- `backend_app/prompts/__init__.py` — utworzony
- `backend_app/prompts/vlm_prompts.py` — 8 wariantów promptów: DEFAULT, DIAGRAM, CHART, TABLE, PHOTO, SCREENSHOT, TECHNICAL, MEDICAL
- `VLM_PARAMS` dict (max_tokens, temperature, context_length, gpu_layers)
- Funkcje: `get_prompt()`, `get_full_prompt()`, `get_vlm_params()`
- **DODANO** sekcję do PROJEKT_OPIS.md (sekcja 10: VLM Prompts)
- **DODANO** opis model_manager.py (sekcja 11: Zarządzanie modelami)
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

### Problem 5: monitoring.py GPU: 0% dla AMD — ✅ ROZWIĄZANY
**Status:** Rozwiązany przez `gpu_status.py` (rocm-smi)

### Problem 6: Refaktoryzacja image_handler.py — 🟡
**Status:** Prompty gotowe (vlm_prompts.py), ale **nie podpięte** do image_handler.py  
**Kroki 16d-16e** — do wykonania

---

## ⏳ DO ZROBIENIA

### Priorytet WYSOKI — wymaga serwera

| # | Zadanie | Notatki |
|---|---------|---------|
| A | Uruchomić `create_nextcloud_folders.py` | `python3 scripts/create_nextcloud_folders.py --dry-run` → potem bez --dry-run |
| B | Debugować NC Assistant 417 | Sprawdź Expect header, logi NC |
| C | Przetestować Whisper STT | `curl -F file=@audio.mp3 .../v1/audio/transcriptions` |
| D | Sprawdzić czy `.env` na serwerze ma `KLIMTECH_API_KEY=sk-local` | `/media/lobo/BACKUP/KlimtechRAG/.env` |

### Priorytet ŚREDNI

| # | Zadanie | Plik | Status |
|---|---------|------|--------|
| M1 | UI — dropdown z kategoriami w czacie | `static/index.html` + `GET /categories` endpoint | ⏳ |
| M2 | Endpoint `GET /categories` dla UI | `routes/chat.py` lub nowy router | ⏳ |
| M3 | Sekcja 16d — podpięcie vlm_prompts do image_handler.py | `ingest/image_handler.py` | ⏳ |
| M4 | Rozważyć web search enhancement z kategoriami | `routes/web_search.py` | ⏳ |

### Priorytet NISKI

| # | Zadanie |
|---|---------|
| L1 | Skrypt `setup_nextcloud_ai.sh` |
| L2 | Heurystyka RAG off dla NC summarize (msg > 2000 znaków) |
| L3 | Chunked summarization dla długich dokumentów |
| L4 | NC `webhook_listeners` — event-driven zamiast pollingu |
| L5 | Auto-transkrypcja audio w n8n (Whisper + e5-large → Qdrant) |
| L6 | Naprawić `stop_klimtech.py` — nie zabija wszystkich procesów |
| L7 | Usunąć `start_backend_gpu.py` jeśli nie używany |

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
| `backend_app/prompts/vlm_prompts.py` | 8 wariantów promptów VLM + VLM_PARAMS |
| `backend_app/services/model_manager.py` | Lifecycle llama-server, przełączanie LLM↔VLM |
| `backend_app/categories/definitions.py` | 14 kategorii RAG (pl/en/de keywords + struktura folderów) |
| `backend_app/categories/classifier.py` | `classify_document(filepath, content)` → path/keyword/fallback |
| `scripts/create_nextcloud_folders.py` | Tworzy 300+ folderów w Nextcloud (podman exec occ) |
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

2. **Rekomendowana kolejność pracy (po uzyskaniu dostępu do serwera):**
   1. `python3 scripts/create_nextcloud_folders.py --dry-run` → sprawdź, potem uruchom
   2. Wrzuć testowy plik PDF do `/DOKUMENTY_RAG/medycyna/` w Nextcloud → sprawdź czy `meta.category == "medicine"`
   3. Test `/query` z `category_filter: "medicine"` — czy filtrowanie działa w Qdrant
   4. Debugowanie NC Asystenta 417 (Expect header)
   5. Test Whisper STT

3. **Filtrowanie kategorii — jak przetestować:**
```bash
curl -s -X POST http://localhost:8000/query \
  -H "X-API-Key: sk-local" -H "Content-Type: application/json" \
  -d '{"query": "co to zawał serca", "category_filter": "medicine"}'
```

4. **Przy debugowaniu NC Asystenta:** Prawdopodobna przyczyna to header `Expect: 100-continue` — middleware w `main.py` usuwający ten header powinno rozwiązać problem.

5. **Pliki TYLKO NA LAPTOPIE (nie zsynchronizowane z serwerem):** Wszystkie zmiany z sesji 12 i 13 — wymagają `git push` + `git pull` na serwerze.

---

*Ostatnia aktualizacja: 2026-03-23*
