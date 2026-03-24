# POSTĘP AUDYTU — KlimtechRAG
**Audyt na podstawie:** AUDYT_2026-03-23_22-19-27.md
**Start:** 2026-03-23

---

## PRIORITY 1 — NATYCHMIASTOWE

| # | Problem | Status | Uwagi |
|---|---------|--------|-------|
| P1.1 | KLIMTECH_API_KEY w .env | ✅ Gotowe | Utworzono .env z KLIMTECH_API_KEY=sk-local |
| P1.2 | secrets.compare_digest w dependencies.py | ✅ Gotowe | |
| P1.3 | Auth na DELETE /documents i POST /files/sync | ✅ Gotowe | Objęto też /files/stats, /files/list, /files/pending, /ws/health |
| P1.4 | resolve_path() w /ingest_path | ✅ Gotowe | Naprawiono też /ingest_pdf_vlm |
| P1.5 | Auth na /model/start, /model/stop, /model/switch | ✅ Gotowe | Router-level Depends + walidacja model_path |

## PRIORITY 2 — WAŻNE

| # | Problem | Status |
|---|---------|--------|
| P2.1 | SSRF — blokada adresów prywatnych /web/fetch | ✅ Gotowe | _assert_public_url() w /fetch i /summarize |
| P2.2 | Auth na /web/* | ✅ Gotowe | Depends(require_api_key) na wszystkich + Field limits |
| P2.3 | Auth na /whisper/* + size limit | ✅ Gotowe | Depends + 100MB limit przed zapisem do temp |
| P2.4 | Auth na /v1/embeddings i /rag/debug | ✅ Gotowe | |
| P2.5 | Auth na /v1/models i /models | ✅ Gotowe | |

## PRIORITY 3 — REKOMENDOWANE

| # | Problem | Status |
|---|---------|--------|
| P3.1 | settings singleton w web_search.py | ✅ Gotowe | Zrobione razem z P2.1/P2.2 |
| P3.2 | await get_request_id w web_search.py | ✅ Gotowe | Wszystkie 3 wywołania poprawione |
| P3.3 | Size check przed read() w /upload | ✅ Gotowe | Content-Length check + istniejący check po read() |
| P3.4 | FD leak — context manager w model_manager.py | ✅ Gotowe | Oba miejsca naprawione |
| P3.5 | rate_limit_store cleanup | ✅ Gotowe | Usuwanie stale entries po 2x window |
| P3.6 | Field limits w WebSearchRequest/WebFetchRequest | ✅ Gotowe | Zrobione razem z P2.2 |

## PRIORITY 4 — NISKA PILNOŚĆ

| # | Problem | Status |
|---|---------|--------|
| P4.1 | Usunąć .bak/.backup/nohup.out z repo | ✅ Gotowe | 6 plików usuniętych + wpisy w .gitignore |
| P4.2 | Hardcoded paths w image_handler.py | ✅ Gotowe | _find_llama_binary() oparty na settings.base_path |
| P4.3 | Sanityzacja filename przy upload | ✅ Gotowe | re.sub na basename przed zapisem |
| P4.4 | Ujednolicić error handling subprocess | ✅ Gotowe | logger.warning zamiast silent pass w extract_pdf_text |

---

## DZIENNIK ZMIAN

### 2026-03-23 — P1.1 ✅
**Plik:** `.env` (nowy)
**Zmiana:** Utworzono `.env` z `KLIMTECH_API_KEY=sk-local`. Plik jest w `.gitignore`.
**Efekt:** `settings.api_key` nie będzie już `None` → `require_api_key()` zacznie sprawdzać klucz.
**UWAGA:** Na serwerze produkcyjnym (`/media/lobo/BACKUP/KlimtechRAG/.env`) należy zweryfikować że ten plik istnieje z tym samym kluczem.

### 2026-03-23 — P1.2 ✅
**Plik:** `backend_app/utils/dependencies.py:16`
**Zmiana:** `key != settings.api_key` → `not secrets.compare_digest(key or "", settings.api_key)`
**Efekt:** Porównanie API key jest teraz constant-time — eliminuje timing attack.

### 2026-03-23 — P1.3 ✅
**Plik:** `backend_app/routes/admin.py`
**Zmiany:**
- `DELETE /documents` — dodano `require_api_key(req)`
- `GET /files/stats` — dodano `require_api_key(req)`
- `GET /files/list` — dodano `require_api_key(req)`
- `POST /files/sync` — dodano `require_api_key(req)`
- `GET /files/pending` — dodano `require_api_key(req)`
- `WS /ws/health` — dodano ręczny check `secrets.compare_digest` przed `ws.accept()`
- `GET /health` i `GET /metrics` — pozostają publiczne (monitoring)
**Efekt:** Baza RAG i filesystem nie są już dostępne bez API key.

### 2026-03-23 — P1.4 ✅
**Plik:** `backend_app/routes/ingest.py:510` i `ingest.py:780`
**Zmiana:** Dodano `resolve_path(settings.base_path, body.path)` przed `os.path.exists()` w:
- `/ingest_path` (linia 510)
- `/ingest_pdf_vlm` (linia 780) — dodatkowy endpoint z tym samym problemem
**Efekt:** Ścieżki spoza `base_path` zwracają HTTP 403 zamiast czytać dowolny plik z serwera.

### 2026-03-23 — P1.5 ✅
**Plik:** `backend_app/routes/model_switch.py:33`
**Zmiany:**
- Router otrzymał `dependencies=[Depends(require_api_key)]` — obejmuje WSZYSTKIE endpointy `/model/*`
- `/model/start`: dodano walidację `model_path` — ścieżki spoza `BASE_DIR` zwracają HTTP 403
**Efekt:** Przełączanie/start/stop modelu wymaga API key; path traversal przez model_path zablokowany.

### 2026-03-23 — P2.1 + P2.2 + P3.6 ✅
**Plik:** `backend_app/routes/web_search.py`
**Zmiany:**
- Dodano `_assert_public_url()` — blokuje IP prywatne/loopback/link-local przed fetchem
- `settings = Settings()` → `from ..config import settings` (singleton)
- Wszystkie endpointy: `Depends(require_api_key)` na `/search`, `/fetch`, `/summarize`, `/status`
- `WebSearchRequest.num_results`: `Field(5, ge=1, le=20)`
- `WebFetchRequest.max_length`: `Field(50000, ge=1, le=500_000)`
- `WebSummarizeRequest.max_chars`: `Field(4000, ge=1, le=50_000)`
- `_assert_public_url()` wywołane w `/fetch` i `/summarize`
**Efekt:** SSRF zablokowany; endpointy wymagają auth; limity Pydantic egzekwowane.

### 2026-03-23 — P2.3 ✅
**Plik:** `backend_app/routes/whisper_stt.py`
**Zmiany:**
- `/v1/audio/transcriptions`: `dependencies=[Depends(require_api_key)]` + size check 100MB przed zapisem
- `/whisper/models`: `dependencies=[Depends(require_api_key)]`
- `/whisper/status`: `dependencies=[Depends(require_api_key)]`
**Efekt:** Transkrypcja wymaga auth; duże pliki audio odrzucane przed zajęciem zasobów GPU.

### 2026-03-23 — P2.4 + P2.5 ✅
**Plik:** `backend_app/routes/chat.py`
**Zmiany:**
- `/v1/embeddings`: dodano `Depends(require_api_key)`
- `/rag/debug`: dodano `Depends(require_api_key)`
- `/models` i `/v1/models`: dodano `Depends(require_api_key)`
**Efekt:** Embeddingi, debug RAG i lista modeli wymagają auth.

### 2026-03-23 — P3.1 + P3.2 ✅
**Plik:** `backend_app/routes/web_search.py`
**P3.1:** `settings = Settings()` usunięte — moduł używa teraz importowanego singletona z config.py.
**P3.2:** Trzy wywołania `get_request_id(req)` poprawione na `await get_request_id(req)` (linie 102, 158, 256).
**Efekt:** Konfiguracja spójna z resztą aplikacji; request_id w logach web_search poprawny.

### 2026-03-23 — P3.3 ✅
**Plik:** `backend_app/routes/ingest.py:329`
**Zmiana:** Dodano wczesny check `Content-Length` nagłówka przed `await file.read()`.
Istniejący check po read() pozostawiony jako drugi poziom ochrony.
**Efekt:** Żądania z dużymi plikami odrzucane bez ładowania do RAM.

### 2026-03-23 — P3.4 ✅
**Plik:** `backend_app/services/model_manager.py:243` i `model_manager.py:564`
**Zmiana:** `open()` bez context managera → `with open(...) as log_out, open(...) as log_err:` w obu miejscach.
**Efekt:** File descriptory zamykane zawsze po starcie Popen, eliminując FD leak przy cyklicznym start/stop.

### 2026-03-23 — P3.5 ✅
**Plik:** `backend_app/utils/rate_limit.py:25`
**Zmiana:** Po każdym wywołaniu `apply_rate_limit()` czyszczone są wpisy klientów,
których ostatni request był ponad `2 * window` temu.
**Efekt:** Dict nie rośnie bezterminowo przy dużej liczbie unikalnych IP.

### 2026-03-23 — P4.1 ✅
**Usunięte pliki:**
- `backend_app/config.py.bak`
- `backend_app/routes/chat.py.bak`
- `backend_app/scripts/watch_nextcloud.py.bak`
- `backend_app/static/index.html.backup`
- `backend_app/nohup.out`
- `start_klimtech_v3.py.backup`
**Dodano do `.gitignore`:** `*.bak`, `*.backup`, `nohup.out`

### 2026-03-23 — P4.2 ✅
**Plik:** `backend_app/ingest/image_handler.py:44-45`
**Zmiana:** Hardcoded `os.path.expanduser("~/KlimtechRAG/...")` zastąpione
funkcją `_find_llama_binary()` która przeszukuje lokalizacje oparte na `settings.base_path`.
**Efekt:** Binarki llama znajdowane poprawnie niezależnie od katalogu bazowego serwera.

### 2026-03-23 — P4.3 ✅
**Plik:** `backend_app/routes/ingest.py` (endpoint `/upload`)
**Zmiana:** `file.filename` → `safe_filename = re.sub(r"[^\w\-_\.]", "_", os.path.basename(file.filename))`
przed jakimkolwiek użyciem nazwy. Plik zapisywany pod `safe_filename`.
**Efekt:** Znaki specjalne, spacje i sekwencje path traversal w nazwie pliku są neutralizowane.

### 2026-03-23 — P4.4 ✅
**Plik:** `backend_app/routes/ingest.py:135` (funkcja `extract_pdf_text`)
**Zmiana:** `except Exception: pass` → oddzielne `except subprocess.TimeoutExpired` i `except Exception`
z `logger.warning()` w obu przypadkach.
**Efekt:** Timeouty pdftotext są widoczne w logach zamiast cichego fallbacku.

---

## PODSUMOWANIE KOŃCOWE

**Data zakończenia:** 2026-03-23
**Wynik weryfikacji składni:** ✅ 10/10 plików bez błędów

### Wszystkie 20 punktów planu zakończone:
- **Priority 1 (5/5):** ✅ Wszystkie CRITICAL naprawione
- **Priority 2 (5/5):** ✅ Wszystkie HIGH naprawione
- **Priority 3 (6/6):** ✅ Wszystkie MEDIUM naprawione (P3.1 przy P2.1, P3.6 przy P2.2)
- **Priority 4 (4/4):** ✅ Wszystkie LOW naprawione

### Pliki zmodyfikowane:
| Plik | Zmiany |
|------|--------|
| `.env` (nowy) | KLIMTECH_API_KEY=sk-local |
| `.gitignore` | *.bak, *.backup, nohup.out |
| `backend_app/utils/dependencies.py` | secrets.compare_digest |
| `backend_app/utils/rate_limit.py` | stale entry cleanup |
| `backend_app/routes/admin.py` | auth na 5 endpointach + WS |
| `backend_app/routes/ingest.py` | resolve_path, size check, filename sanitize, logging |
| `backend_app/routes/model_switch.py` | router-level auth, model_path validation |
| `backend_app/routes/web_search.py` | auth, SSRF block, Field limits, singleton, await |
| `backend_app/routes/whisper_stt.py` | auth, 100MB size limit |
| `backend_app/routes/chat.py` | auth na 4 endpointach |
| `backend_app/services/model_manager.py` | FD leak fix (2 miejsca) |
| `backend_app/ingest/image_handler.py` | _find_llama_binary() |

### Pliki usunięte (6):
`config.py.bak`, `routes/chat.py.bak`, `scripts/watch_nextcloud.py.bak`,
`static/index.html.backup`, `nohup.out`, `start_klimtech_v3.py.backup`

### Następny krok:
`git pull` na serwerze + weryfikacja że `/media/lobo/BACKUP/KlimtechRAG/.env` zawiera `KLIMTECH_API_KEY=sk-local`.
