# Podsumowanie sesji KlimtechRAG - 2026-02-20 19:17

## 1. Wykonane zmiany

### Faza 1: Porządkowanie plików

| Plik | Zmiana | Status |
|------|--------|--------|
| `monitoring.py` | Usunięto duplikat kodu (linie 72-108) | ✅ |
| `config.py` | Dodano ścieżki: `base_path`, `upload_base`, `nextcloud_base`, `file_registry_db` | ✅ |
| `config.py` | `llm_model_name: str = ""` (pusty, nie sztywny model) | ✅ |
| `file_registry.py` | Używa `settings` zamiast sztywnych ścieżek | ✅ |

### Faza 2: Refaktoryzacja main.py

**Przed:** 1350 linii (monolit)  
**Po:** 89 linii + moduły

Nowa struktura:
```
backend_app/
├── main.py              # 89 linii (tylko app + middleware)
├── config.py            # 95 linii (+ ścieżki)
├── file_registry.py     # 307 linii
├── monitoring.py        # 112 linii
├── fs_tools.py          # 193 linii
│
├── models/
│   ├── __init__.py
│   └── schemas.py       # Pydantic models
│
├── routes/
│   ├── chat.py          # /query, /v1/chat/completions
│   ├── ingest.py        # /ingest, /upload, /ingest_path
│   ├── filesystem.py    # /fs/*
│   ├── admin.py         # /health, /files/*
│   └── ui.py            # /, /chat (HTML)
│
├── services/
│   ├── qdrant.py        # Singleton QdrantDocumentStore
│   ├── embeddings.py    # Singleton embedder
│   ├── rag.py           # RAG pipeline
│   └── llm.py           # OpenAIGenerator wrapper
│
├── utils/
│   ├── rate_limit.py
│   └── tools.py
│
└── scripts/
    ├── ingest_pdfCPU.py
    ├── ingest_pdfGPU.py
    ├── ingest_repo.py
    ├── model_parametr.py
    └── watch_nextcloud.py
```

### Porządkowanie głównego katalogu

**Przed:** 10+ plików .py w głównym katalogu  
**Po:** 3 pliki
```
~/KlimtechRAG/
├── .env
├── start_klimtech.py
├── stop_klimtech.py
├── DRZEWO.md            # Dokumentacja struktury
├── backend_app/
└── data/
```

Usunięto: `start_klimtech_backup.py`, `pytest.ini`, `__pycache__`, `.pytest_cache`, `.ruff_cache`

### Naprawy importów i ścieżek

| Plik | Problem | Rozwiązanie |
|------|---------|-------------|
| `start_klimtech.py` | `from model_parametr import...` | `from backend_app.scripts.model_parametr import...` |
| `start_klimtech.py` | watchdog path | `backend_app/scripts/watch_nextcloud.py` |
| `watch_nextcloud.py` | sztywne ścieżki | używa `settings.nextcloud_base`, `settings.upload_base` |
| `watch_nextcloud.py` | brak sys.path | dodano `sys.path.insert(0, ...)` |

### PDF Handler - inteligentna ekstrakcja

W `routes/ingest.py` dodano:
```python
def extract_pdf_text(file_path: str) -> str:
    # Najpierw pdftotext (szybkie, sekundy)
    # Jeśli puste -> Docling OCR
```

---

## 2. Nierozwiązane problemy

### 🔴 KRYTYCZNY: HNSW nie indeksuje się automatycznie

```
indexed_vectors_count: 0  # Powinno być = points_count
points_count: 2149
```

**Przyczyna:** `full_scan_threshold: 10000` - Qdrant nie buduje HNSW dla małych kolekcji

**Tymczasowe rozwiązanie (manualne):**
```bash
curl -X PATCH "http://localhost:6333/collections/klimtech_docs" -H "Content-Type: application/json" -d '{"hnsw_config": {"full_scan_threshold": 10}}'
curl -X POST "http://localhost:6333/collections/klimtech_docs/index" -H "Content-Type: application/json" -d '{"wait": true}'
```

**Do zrobienia:** Dodać automatyczne indeksowanie przy starcie backendu (częściowo dodane w `services/qdrant.py` ale nie działa)

### 🟡 ŚREDNI: Watchdog - wiele instancji

Po każdym restarcie powstaje nowa instancja watchdog:
```
lobo  70693 ... watch_nextcloud.py
lobo  71945 ... watch_nextcloud.py
lobo  74396 ... watch_nextcloud.py
```

**Rozwiązanie:** `pkill -f watch_nextcloud` przed restartem

### 🟡 ŚREDNI: RAG nie działa po restarcie

Model halucynuje - nie widzi dokumentów w bazie.

**Workflow:**
1. `/upload` - tylko zapisuje plik, NIE indeksuje
2. Watchdog powinien wywołać `/ingest_path`
3. Ale HNSW nie jest budowany

---

## 3. Przydatne komendy

### Qdrant

```bash
# Status kolekcji
curl -s http://localhost:6333/collections/klimtech_docs | python3 -m json.tool | grep -E "points_count|indexed_vectors"

# Usuń kolekcję
curl -X DELETE "http://localhost:6333/collections/klimtech_docs"

# Wymuś indeksowanie HNSW
curl -X POST "http://localhost:6333/collections/klimtech_docs/index" -H "Content-Type: application/json" -d '{"wait": true}'

# Zmień threshold
curl -X PATCH "http://localhost:6333/collections/klimtech_docs" -H "Content-Type: application/json" -d '{"hnsw_config": {"full_scan_threshold": 10}}'

# Przeglądaj dokumenty
curl -s -X POST "http://localhost:6333/collections/klimtech_docs/points/scroll" -H "Content-Type: application/json" -d '{"limit": 3, "with_payload": true}' | python3 -m json.tool
```

### Backend

```bash
# Health check
curl -s http://localhost:8000/health | python3 -m json.tool

# Stats plików
curl -s http://localhost:8000/files/stats | python3 -m json.tool

# Pliki pending
curl -s http://localhost:8000/files/pending | python3 -m json.tool

# Indeksuj pending
curl -X POST "http://localhost:8000/ingest_all?limit=5"
```

### System

```bash
# Sprawdź procesy
ps aux | grep watch_nextcloud

# Zabij watchdog
pkill -f watch_nextcloud

# Sprawdź porty
ss -tlnp | grep -E "8000|6333|8082"
```

---

## 4. Workflow do poprawy

### Obecny (nie działa poprawnie):

```
1. Wrzuć plik przez UI → /upload
2. Plik zapisany w data/uploads/pdf_RAG/
3. Watchdog powinien wykryć → nie działa
4. Użytkownik ręcznie: curl /ingest_all
5. Plik zindeksowany → HNSW nie zbudowany
6. Model halucynuje
```

### Docelowy:

```
1. Wrzuć plik przez UI → /upload
2. Plik zapisany + automatycznie /ingest_path
3. Embedding stworzony
4. HNSW automatycznie zbudowany
5. Model widzi kontekst
```

---

## 5. Następne kroki

1. **Naprawić automatyczne indeksowanie HNSW** - dodać do `services/qdrant.py` sprawdzanie i budowanie indeksu przy starcie

2. **Naprawić watchdog** - upewnić się że tylko jedna instancja działa i loguje

3. **Zmienić `/upload`** - automatycznie wywoływać indeksowanie po zapisie pliku

4. **Przetestować end-to-end** - wrzucić plik → zapytać model → dostać odpowiedź z kontekstem

5. **Stworzyć folder z logami** - każde pliki .py które są uruchamiane muszą mieć  pliki .log na czas budowy aplikacj aby lepiej wychwytywac ewentualne błędy podczas tworzenia i ulepszania programu.
---

## 6. Struktura plików po zmianach

```
~/KlimtechRAG/
├── .env
├── start_klimtech.py
├── stop_klimtech.py
├── DRZEWO.md
├── backend_app/
│   ├── main.py
│   ├── config.py
│   ├── file_registry.py
│   ├── monitoring.py
│   ├── fs_tools.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── utils/
│   └── scripts/
├── data/
│   ├── file_registry.db
│   ├── qdrant/
│   └── uploads/
├── llama.cpp/
└── venv/
```

---

## 7. Konfiguracja

### .env (przykład)
```
KLIMTECH_LLM_BASE_URL=http://localhost:8082/v1
KLIMTECH_LLM_API_KEY=sk-dummy
KLIMTECH_LLM_MODEL_NAME=
KLIMTECH_QDRANT_URL=http://localhost:6333
KLIMTECH_QDRANT_COLLECTION=klimtech_docs
KLIMTECH_EMBEDDING_MODEL=intfloat/multilingual-e5-large
```

## 8. sugestie z innego modelu

Analiza KlimtechRAG - Sesje nr 1 i nr 2
Co zostało zrobione (potwierdzone w kodzie)
Refaktoryzacja z monolitu (1350 linii) na moduły jest faktycznie wykonana - widać to w przesłanych plikach. Struktura routes/services/utils istnieje i jest spójna. Import ścieżek przez settings zamiast hardkodowanych wartości - tak, widać to w qdrant.py, ingest.py, rate_limit.py.
ensure_indexed() w qdrant.py jest zaimplementowane - sprawdza indexed_vectors_count == 0 i wywołuje endpoint /index. Problem opisany w sesji nr 2 ("częściowo dodane ale nie działa") - kod jest tam, ale prawdopodobnie API Qdrant nie akceptuje POST /collections/{name}/index w tej formie (ten endpoint nie istnieje w standardowym Qdrant API).

Błędy znalezione w kodzie
1. ensure_indexed() - błędny endpoint Qdrant
python# To nie istnieje w Qdrant API:
requests.post(index_url, json={"wait": True}, timeout=60)
# Prawidłowo: zmiana threshold wymusza przebudowę
requests.put(f"{url}/hnsw_config", ...)
2. admin.py - brakujący import HTTPException
python# Linia ~44 używa HTTPException ale nie importuje jej z fastapi
from fastapi import APIRouter, Depends, Request, WebSocket  # brak HTTPException!
```

**3. `admin.py` - `@router.on_event("startup")` - deprecated w nowszym FastAPI**, powinno być `lifespan` w `main.py`.

**4. `ingest.py` - `/upload` nie indeksuje** - plik jest zapisywany, ale watchdog jest zawodny. To jest główna przyczyna problemu RAG.

**5. `chat.py` - cache bez TTL** - `answer_cache: Dict[str, str] = {}` rośnie bez ograniczeń i nie ma expiry. Po zindeksowaniu nowych dokumentów stare odpowiedzi z cache nadal wracają (halucynacje z poprzedniej sesji).

---

## Co się powtarza (duplikaty)

`require_api_key()` i `get_request_id()` są zdefiniowane identycznie w **trzech plikach**: `chat.py`, `filesystem.py`, `ingest.py`. Powinno być w jednym miejscu, np. `utils/dependencies.py`.

---

## Główny problem: model nie widzi bazy RAG

Masz de facto **trzy niezależne punkty awarii** w pipeline:
```
```
Upload → Watchdog (zawodny) → ingest_path → Qdrant → HNSW → Retrieval → LLM
Każdy z nich może cicho zawalić się i model dostaje pusty kontekst.
Sugestie rozwiązań
Sugestia 1 - Najprostsza: /upload sam wywołuje indeksowanie
Zamiast polegać na watchdogu, bezpośrednio po zapisie pliku wywołaj ingest_path wewnętrznie:
python@router.post("/upload")
async def upload_file_to_rag(...):
    # ... zapisz plik ...
    
    # Automatyczne indeksowanie zamiast watchdog
    background_tasks.add_task(ingest_file_background, target_path)
    return {"status": "ok", "message": "Plik zapisany, indeksowanie w tle..."}

async def ingest_file_background(file_path: str):
    try:
        # logika z ingest_path
        ...
        # Po indeksowaniu - wymuś HNSW
        fix_hnsw()
    except Exception as e:
        mark_failed(file_path, str(e))
Sugestia 2 - Naprawić ensure_indexed() - prawidłowe API Qdrant
pythondef ensure_indexed():
    url = f"{settings.qdrant_url}/collections/{settings.qdrant_collection}"
    resp = requests.get(url, timeout=5).json()
    indexed = resp.get("result", {}).get("indexed_vectors_count", 0)
    points = resp.get("result", {}).get("points_count", 0)
    
    if points > 0 and indexed < points:
        # Prawidłowy sposób: obniż threshold żeby wymusić budowę HNSW
        requests.patch(url, json={"hnsw_config": {"full_scan_threshold": 10}}, timeout=10)
        logger.info("HNSW threshold obniżony, indeksowanie nastąpi automatycznie")
Sugestia 3 - Diagnostyczny endpoint /rag/debug
Dodaj endpoint który pokaże cały pipeline:
python@router.get("/rag/debug")
async def rag_debug(query: str = "test"):
    result = {}
    # 1. Stan Qdrant
    qdrant_info = requests.get(f"{settings.qdrant_url}/collections/{settings.qdrant_collection}").json()
    result["qdrant_points"] = qdrant_info.get("result", {}).get("points_count", 0)
    result["qdrant_indexed"] = qdrant_info.get("result", {}).get("indexed_vectors_count", 0)
    
    # 2. Test retrieval
    embedding = text_embedder.run(text=query)["embedding"]
    retriever = QdrantEmbeddingRetriever(document_store=doc_store, top_k=3)
    docs = retriever.run(query_embedding=embedding)["documents"]
    result["retrieved_docs"] = len(docs)
    result["sample"] = docs[0].content[:200] if docs else None
    
    return result
Sugestia 4 - Wyczyść cache po indeksowaniu
python# W ingest_path i ingest_all - po udanym indeksowaniu:
from ..routes.chat import answer_cache
answer_cache.clear()
logger.info("Cache wyczyszczony po nowym indeksowaniu")
Sugestia 5 - Logi do pliku (punkt z sesji nr 2)
W main.py dodaj FileHandler:
pythonimport logging
logging.basicConfig(
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/backend.log"),
    ],
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)

Priorytety
Najważniejsze do zrobienia w kolejności:

Napraw ensure_indexed() - zmień endpoint na PATCH z hnsw_config
Dodaj auto-indeksowanie w /upload - usuń zależność od watchdoga
Napraw brakujący import HTTPException w admin.py
Dodaj /rag/debug - bez diagnostyki ciężko wykryć gdzie pipeline pada
Wyczyść cache po indeksowaniu - żeby model nie serwował starych odpowiedzi
Wynieś require_api_key i get_request_id do utils/dependencies.py
```

### Modele
- **LLM:** Bielik-11B-v3.0-Instruct.Q5_K_M.gguf (przez llama.cpp-server, port 8082)
- **Embedding:** intfloat/multilingual-e5-large (wymiar: 1024)
- **VLM (planowany):** LFM2.5-VL-1.6B-F16.gguf dla obrazów

---

*Podsumowanie wygenerowane: 2026-02-20 19:17*

Główne punkty:
1. ✅ Refaktoryzacja zakończona (main.py: 1350 → 89 linii)
2. ✅ Porządek w strukturze katalogów
3. 🔴 HNSW nie indeksuje się automatycznie - główny problem RAG
4. 🔴 Wiele instancji watchdog - zabij przed restartem: pkill -f watch_nextcloud
Po powrocie - pierwsze kroki:
# 1. Zabij stare procesy
pkill -f watch_nextcloud
# 2. Uruchom
./start_klimtech.py
# 3. Wymuś indeksowanie HNSW
curl -X POST "http://localhost:6333/collections/klimtech_docs/index" -H "Content-Type: application/json" -d '{"wait": true}'