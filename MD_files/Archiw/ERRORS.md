# KlimtechRAG — Raport błędów (2026-03-22)

**Audyt:** Pełna analiza 42 plików .py
**Znalezione błędy:** 25 (3 CRITICAL, 10 HIGH, 8 MEDIUM, 4 LOW)

---

## CRITICAL (3)

### C1. config.py:173 — NameError: `logging` nie zaimportowany

**Plik:** `backend_app/config.py:173`

**Problem:** Funkcja `get_logger()` wywołuje `logging.getLogger(name)`, ale `logging` nie jest zaimportowany na poziomie modułu. Import `import logging` istnieje tylko wewnątrz `setup_logging()` (linia 131) — to zmienna lokalna tej funkcji, niedostępna globalnie.

**Ryzyko:** `NameError: name 'logging' is not defined` — crash przy każdym wywołaniu `get_logger()`.

**Fix:**
```python
# backend_app/config.py — DODAJ na początku pliku (np. linia 2):
import logging
```

---

### C2. whisper_stt.py:41 — Parametr `model` nadpisany przez obiekt Whisper

**Plik:** `backend_app/routes/whisper_stt.py:41`

**Problem:** Parametr `model: str = Form("whisper-1")` (linia 21) jest nadpisywany przez `model = get_whisper_model()` (linia 41), który zwraca obiekt modelu Whisper. Od linii 41 zmienna `model` to obiekt, nie string. Parametr Form() jest martwy — zawsze ładowany "small".

**Ryzyko:** Użytkownik nie może wybrać innego rozmiaru modelu Whisper.

**Fix:**
```python
# backend_app/routes/whisper_stt.py — linia 41:
# BYŁO:
model = get_whisper_model()
result = model.transcribe(...)

# MA BYĆ:
whisper_model = get_whisper_model()
result = whisper_model.transcribe(
    tmp_path,
    language=language,
    prompt=prompt,
    fp16=True,
)
```

---

### C3. web_search.py:87,143,243 — async `get_request_id()` bez await

**Plik:** `backend_app/routes/web_search.py:87,143,243`

**Problem:** `get_request_id` jest zdefiniowany jako `async def` (w `utils/dependencies.py:20`), ale w web_search.py wywoływany bez `await`. Zwraca obiekt coroutine zamiast stringa.

**Ryzyko:** Logi zawierają `<coroutine object get_request_id at 0x...>` zamiast request ID. Memory leak (coroutine nigdy nie zakończona).

**Fix:**
```python
# backend_app/routes/web_search.py — WSZYSTKIE 3 wystąpienia:
# BYŁO (linie 87, 143, 243):
request_id = get_request_id(req)

# MA BYĆ:
request_id = await get_request_id(req)
```

---

## HIGH — Złe ścieżki (5 plików, 11 wystąpień)

### H1. image_handler.py:44-45 — LLAMA_SERVER_BIN i LLAMA_CLI_BIN

**Plik:** `backend_app/ingest/image_handler.py:44-45`

**Problem:**
```python
LLAMA_SERVER_BIN = os.path.expanduser("~/KlimtechRAG/llama.cpp/build/bin/llama-server")
LLAMA_CLI_BIN = os.path.expanduser("~/KlimtechRAG/llama.cpp/build/bin/llama-cli")
```
Rozwijają się do `/home/lobo/KlimtechRAG/...` — złe. Projekt jest w `/media/lobo/BACKUP/KlimtechRAG/`.

**Ryzyko:** VLM opis obrazów nie zadziała — binarki nie zostaną znalezione.

**Fix:**
```python
# backend_app/ingest/image_handler.py — linie 44-45:
# BYŁO:
LLAMA_SERVER_BIN = os.path.expanduser("~/KlimtechRAG/llama.cpp/build/bin/llama-server")
LLAMA_CLI_BIN = os.path.expanduser("~/KlimtechRAG/llama.cpp/build/bin/llama-cli")

# MA BYĆ:
from ..config import settings
_BASE = settings.base_path
LLAMA_SERVER_BIN = os.path.join(_BASE, "llama.cpp", "build", "bin", "llama-server")
LLAMA_CLI_BIN = os.path.join(_BASE, "llama.cpp", "build", "bin", "llama-cli")
```

Dodatkowo linia 29 w `_find_vlm_model()` ma fallback do `Path.home() / "KlimtechRAG"`:
```python
# Linia 29 — BYŁO:
str(Path.home() / "KlimtechRAG")

# MA BYĆ:
settings.base_path
```

---

### H2. ingest_gpu.py:22,26 — LLAMA_DIR i BASE_DIR

**Plik:** `backend_app/scripts/ingest_gpu.py:22,26`

**Problem:**
```python
LLAMA_DIR = os.path.expanduser("~/KlimtechRAG/llama.cpp")
BASE_DIR = os.path.expanduser("~/KlimtechRAG")
```

**Fix:**
```python
BASE_DIR = "/media/lobo/BACKUP/KlimtechRAG"
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
```

---

### H3. ingest_pdfCPU.py:8,21 — sys.path i PDF_DIR

**Plik:** `backend_app/scripts/ingest_pdfCPU.py:8,21`

**Problem:**
```python
sys.path.insert(0, os.path.expanduser("~/KlimtechRAG"))           # linia 8
PDF_DIR = "/home/lobo/KlimtechRAG/data/uploads/pdf_RAG"           # linia 21
```

**Fix:**
```python
sys.path.insert(0, "/media/lobo/BACKUP/KlimtechRAG")              # linia 8
PDF_DIR = "/media/lobo/BACKUP/KlimtechRAG/data/uploads/pdf_RAG"   # linia 21
```

---

### H4. ingest_pdfGPU.py:9,23-25 — sys.path, PDF_DIR, PAGES_DIR, PROGRESS_FILE

**Plik:** `backend_app/scripts/ingest_pdfGPU.py:9,23-25`

**Problem:**
```python
sys.path.insert(0, os.path.expanduser("~/KlimtechRAG"))                         # linia 9
PDF_DIR = "/home/lobo/KlimtechRAG/data/uploads/pdf_RAG"                         # linia 23
PAGES_DIR = "/home/lobo/KlimtechRAG/data/uploads/pdf_pages"                     # linia 24
PROGRESS_FILE = "/home/lobo/KlimtechRAG/data/uploads/pdf_progress.json"         # linia 25
```

**Fix:**
```python
sys.path.insert(0, "/media/lobo/BACKUP/KlimtechRAG")                            # linia 9
PDF_DIR = "/media/lobo/BACKUP/KlimtechRAG/data/uploads/pdf_RAG"                 # linia 23
PAGES_DIR = "/media/lobo/BACKUP/KlimtechRAG/data/uploads/pdf_pages"             # linia 24
PROGRESS_FILE = "/media/lobo/BACKUP/KlimtechRAG/data/uploads/pdf_progress.json" # linia 25
```

---

### H5. ingest_repo.py:74 — target_folder

**Plik:** `backend_app/scripts/ingest_repo.py:74`

**Problem:**
```python
target_folder = "/home/lobo/KlimtechRAG/git_sync/zizzania"
```

**Fix:**
```python
target_folder = "/media/lobo/BACKUP/KlimtechRAG/git_sync/zizzania"
```

---

## HIGH — Bezpieczeństwo

### H6. admin.py:57 — DELETE /documents bez auth

**Plik:** `backend_app/routes/admin.py:57`

**Problem:** Endpoint `DELETE /documents` nie wywołuje `require_api_key()`. Każdy w sieci może usuwać dokumenty z Qdrant.

**Fix:**
```python
# backend_app/routes/admin.py — linia 57-61:
@router.delete("/documents")
async def delete_documents(
    req: Request,                         # DODAJ
    source: Optional[str] = None,
    doc_id: Optional[str] = None,
):
    require_api_key(req)                  # DODAJ
```

Wymaga dodania importu na górze pliku (jeśli nie ma):
```python
from ..utils.dependencies import require_api_key
```

---

### H7. model_switch.py — Wszystkie endpointy bez auth

**Plik:** `backend_app/routes/model_switch.py`

**Problem:** Żaden endpoint w model_switch.py nie wywołuje `require_api_key()`. Endpointy pozwalają zatrzymać/uruchomić/zmienić model LLM. `POST /model/start` przyjmuje dowolny `model_path`.

**Fix:** Dodać do KAŻDEGO endpointu POST/DELETE:
```python
from ..utils.dependencies import require_api_key

# W każdym POST/DELETE endpoint dodaj parametr req: Request i wywołanie:
require_api_key(req)
```

Dotyczy endpointów:
- `POST /model/switch/llm`
- `POST /model/switch/vlm`
- `POST /model/switch`
- `POST /model/start`
- `POST /model/stop`

GET endpointy (`/model/status`, `/model/list`) mogą pozostać bez auth (read-only).

---

### H8. ingest.py:510 — /ingest_path bez walidacji ścieżki

**Plik:** `backend_app/routes/ingest.py:510-511`

**Problem:** `file_path` z body JSON przekazywany bez sprawdzenia czy jest pod dozwolonym katalogiem. Atakujący z API key może zaindeksować `/etc/shadow` do Qdrant.

**Ryzyko:** Path traversal — odczyt dowolnego pliku na serwerze przez RAG.

**Fix:**
```python
# backend_app/routes/ingest.py — po linii 510, DODAJ:
file_path = body.path
# Walidacja ścieżki — musi być pod dozwolonym katalogiem
from pathlib import Path
allowed_base = Path(settings.base_path).resolve()
target = Path(file_path).resolve()
if not str(target).startswith(str(allowed_base)):
    raise HTTPException(status_code=403, detail="Path outside allowed directory")

if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
```

---

### H9. embedder_pool.py:73-77 — ColPali alias nie rozwiązywany

**Plik:** `backend_app/services/embedder_pool.py:73-77`

**Problem:** Gdy `model_name == "colpali"`, wywołuje `load_colpali("colpali")`. Ale HuggingFace nie zna `"colpali"` — poprawny ID to `"vidore/colpali-v1.3-hf"`. Mapowanie `EMBEDDER_MODELS` (linia 39) jest pomijane dla ścieżki ColPali.

**Ryzyko:** `from_pretrained("colpali")` FAIL — model nie zostanie załadowany.

**Fix:**
```python
# backend_app/services/embedder_pool.py — linia 73-76:
# BYŁO:
if model_name.lower().startswith("vidore/colpali") or model_name == "colpali":
    try:
        from .colpali_embedder import load_model as load_colpali
        logger.info(f"[Pool] Ładuję ColPali: {model_name}")
        model, processor = load_colpali(model_name)

# MA BYĆ:
if model_name.lower().startswith("vidore/colpali") or model_name == "colpali":
    try:
        from .colpali_embedder import load_model as load_colpali
        hf_id = _get_hf_model_id(model_name)  # "colpali" → "vidore/colpali-v1.3-hf"
        logger.info(f"[Pool] Ładuję ColPali: {hf_id}")
        model, processor = load_colpali(hf_id)
```

---

### H10. qdrant.py:96 — Crash przy imporcie gdy Qdrant niedostępny

**Plik:** `backend_app/services/qdrant.py:96`

**Problem:** `QdrantDocumentStore(...)` wykonuje się na poziomie modułu (import time). Jeśli kontener Qdrant nie zdążył wystartować, rzuca wyjątek i cała aplikacja crashuje.

**Ryzyko:** Backend nie wstanie jeśli Qdrant startuje wolniej.

**Fix:**
```python
# backend_app/services/qdrant.py — zamień linie 94-104:
# BYŁO:
embedding_dim = get_embedding_dimension(settings.embedding_model)
doc_store = QdrantDocumentStore(...)
time.sleep(1)
ensure_indexed()

# MA BYĆ:
embedding_dim = get_embedding_dimension(settings.embedding_model)

doc_store = None

def get_doc_store():
    """Lazy init QdrantDocumentStore z retry."""
    global doc_store
    if doc_store is not None:
        return doc_store

    import time as _time
    for attempt in range(3):
        try:
            doc_store = QdrantDocumentStore(
                url=str(settings.qdrant_url),
                index=settings.qdrant_collection,
                embedding_dim=embedding_dim,
                recreate_index=False,
                wait_result_from_api=True,
            )
            _time.sleep(1)
            ensure_indexed()
            return doc_store
        except Exception as e:
            logger.warning(f"Qdrant niedostępny (próba {attempt+1}/3): {e}")
            _time.sleep(5)

    raise RuntimeError("Nie udało się połączyć z Qdrant po 3 próbach")
```

**UWAGA:** Ta zmiana wymaga aktualizacji WSZYSTKICH miejsc importujących `doc_store`:
- `backend_app/services/__init__.py` — zmień `from .qdrant import doc_store` na `from .qdrant import get_doc_store`
- `backend_app/routes/chat.py` — zamień `doc_store` na `get_doc_store()`
- `backend_app/routes/admin.py` — zamień `doc_store` na `get_doc_store()`
- `backend_app/services/rag.py` — zamień `doc_store` na `get_doc_store()`

To jest inwazyjny refaktor. Alternatywny prosty fix:
```python
# Opakuj w try/except z retry (mniej inwazyjne):
for _attempt in range(3):
    try:
        doc_store = QdrantDocumentStore(
            url=str(settings.qdrant_url),
            index=settings.qdrant_collection,
            embedding_dim=embedding_dim,
            recreate_index=False,
            wait_result_from_api=True,
        )
        break
    except Exception as e:
        logger.warning(f"Qdrant niedostępny (próba {_attempt+1}/3): {e}")
        time.sleep(5)
else:
    logger.error("KRYTYCZNE: Nie udało się połączyć z Qdrant!")
    doc_store = None
```

---

## MEDIUM (8)

### M1. web_search.py:37,44 — Settings() zamiast settings (singleton)

**Plik:** `backend_app/routes/web_search.py:37,44`

**Problem:** Importuje `Settings` (klasę) i tworzy nową instancję `settings = Settings()` zamiast użyć singletona z `config.py`.

**Fix:**
```python
# BYŁO (linia 37):
from ..config import Settings

# MA BYĆ:
from ..config import settings

# USUŃ linię 44:
# settings = Settings()  ← USUŃ
```

---

### M2. web_search.py — Endpointy POST bez auth (SSRF)

**Plik:** `backend_app/routes/web_search.py`

**Problem:** `/web/search`, `/web/fetch`, `/web/summarize` nie wywołują `require_api_key()`. `/web/fetch` to de facto SSRF proxy — pobiera dowolny URL z perspektywy serwera.

**Fix:** Dodać do każdego POST endpointu:
```python
from ..utils.dependencies import require_api_key

# W każdym POST handler:
require_api_key(req)
```

---

### M3. chat.py:112 — POST /v1/embeddings bez auth

**Plik:** `backend_app/routes/chat.py:112-113`

**Problem:** Endpoint `/v1/embeddings` nie wywołuje `require_api_key()`. Pozwala na nieautoryzowane generowanie embeddingów (zużycie GPU).

**Fix:**
```python
@router.post("/v1/embeddings")
async def create_embeddings(body: dict, req: Request):
    require_api_key(req)  # DODAJ
```

---

### M4. rate_limit.py:12 — request.client może być None

**Plik:** `backend_app/utils/rate_limit.py:12`

**Problem:** `request.client.host` — `request.client` może być `None` za reverse proxy.

**Fix:**
```python
# BYŁO:
return request.client.host or "unknown"

# MA BYĆ:
return (request.client.host if request.client else None) or "unknown"
```

---

### M5. dependencies.py:16 — Timing attack na API key

**Plik:** `backend_app/utils/dependencies.py:16`

**Problem:** `if key != settings.api_key` — porównanie stringów z short-circuit. Umożliwia timing attack do odgadnięcia API key znak po znaku.

**Fix:**
```python
# DODAJ import na górze pliku:
import hmac

# BYŁO (linia 16):
if key != settings.api_key:

# MA BYĆ:
if not hmac.compare_digest(key, settings.api_key):
```

---

### M6. model_manager.py:243-244, 567-568 — File handle leak

**Plik:** `backend_app/services/model_manager.py:243-244` i `567-568`

**Problem:** `open()` na plikach logów bez `with` — file handles przekazane do Popen nigdy nie zamykane. Każdy restart modelu = +2 otwarte file descriptory.

**Fix (linie 243-244):** Zamknij po Popen jeśli proces nie potrzebuje ich w parent:
```python
# BYŁO:
log_stdout = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
log_stderr = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")

proc = subprocess.Popen(
    llama_cmd, ..., stdout=log_stdout, stderr=log_stderr, ...
)

# MA BYĆ (po Popen zamknij handles — Popen już zduplikował file descriptory):
log_stdout = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
log_stderr = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")

try:
    proc = subprocess.Popen(
        llama_cmd, ..., stdout=log_stdout, stderr=log_stderr, ...
    )
finally:
    log_stdout.close()
    log_stderr.close()
```

Identyczny fix dla linii 567-568.

---

### M7. fs_tools.py:79 — Błędny flag `truncated`

**Plik:** `backend_app/fs_tools.py:79`

**Problem:** `"truncated": len(matches) > limit` porównuje surowe `matches` (przed filtrowaniem) z limitem. Powinno porównywać `safe_matches`.

**Fix:**
```python
# BYŁO:
"truncated": len(matches) > limit,

# MA BYĆ:
"truncated": len(safe_matches) >= limit,
```

---

### M8. embeddings.py:23-48 — Race condition na lazy globals

**Plik:** `backend_app/services/embeddings.py:23-48`

**Problem:** `get_text_embedder()` i `get_doc_embedder()` sprawdzają `_text_embedder is None` bez locka. Dwa równoczesne requesty mogą załadować model dwa razy → podwójne zużycie VRAM → OOM.

**Fix:**
```python
# Na górze pliku dodaj:
import threading
_embedder_lock = threading.Lock()

# W get_text_embedder():
def get_text_embedder():
    global _text_embedder
    if _text_embedder is not None:
        return _text_embedder
    with _embedder_lock:
        if _text_embedder is not None:  # double-check
            return _text_embedder
        # ... załaduj model ...
        _text_embedder = embedder
    return _text_embedder

# Identycznie dla get_doc_embedder()
```

---

## LOW (4)

### L1. chat.py:518 — GET /rag/debug bez auth

**Plik:** `backend_app/routes/chat.py:518`

**Problem:** Ujawnia stan wewnętrzny: kolekcje Qdrant, liczby dokumentów, cache stats, sample content.

**Fix:** Dodaj `require_api_key(req)`.

---

### L2. model_switch.py:126 — Deprecated `regex=` w Pydantic v2

**Plik:** `backend_app/routes/model_switch.py:126`

**Problem:** `Query(..., regex="^(llm|vlm)$")` — `regex` jest deprecated w Pydantic v2.

**Fix:**
```python
# BYŁO:
Query(..., regex="^(llm|vlm)$")

# MA BYĆ:
Query(..., pattern="^(llm|vlm)$")
```

---

### L3. admin.py:93-94 — WebSocket close() może rzucić wyjątek

**Plik:** `backend_app/routes/admin.py:93-94`

**Problem:** W `except Exception` wywołuje `await ws.close()` — jeśli WebSocket już zamknięty, close() sam rzuci wyjątek (unhandled).

**Fix:**
```python
# BYŁO:
except Exception:
    await ws.close()

# MA BYĆ:
except Exception:
    try:
        await ws.close()
    except Exception:
        pass
```

---

### L4. monitoring.py:2 — Unused import

**Plik:** `backend_app/monitoring.py:2`

**Problem:** `import time` — nigdy nie używany w pliku.

**Fix:** Usuń linię `import time`.

---

## KOLEJNOŚĆ NAPRAW

1. **CRITICAL** (C1, C2, C3) — natychmiastowe crashe
2. **HIGH ścieżki** (H1-H5) — 11 złych ścieżek w 5 plikach
3. **HIGH security** (H6-H10) — auth, path traversal, alias
4. **MEDIUM** (M1-M8) — Settings, SSRF, timing attack, leaks
5. **LOW** (L1-L4) — kosmetyka

---

*Wygenerowano: 2026-03-22 przez Claude Code (audyt bezpieczeństwa)*
