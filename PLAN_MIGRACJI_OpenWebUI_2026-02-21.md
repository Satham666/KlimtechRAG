# 🚀 Plan Migracji: Open WebUI + Qdrant RAG
## Na bazie KlimtechRAG — 2026-02-21

---

## 0. Analiza sytuacji wyjściowej

### Co masz teraz

```
/media/lobo/BACKUP/KlimtechRAG/
│
├── llama.cpp-server          ← LLM: Bielik-11B-Q5  [port 8082]
│                                   OpenAI-compatible API
│
├── backend_app (FastAPI)     ← RAG backend          [port 8000]
│   ├── /v1/chat/completions    (OpenAI-compatible + wbudowany RAG)
│   ├── /upload + /ingest_path  (indeksowanie plików)
│   └── /rag/debug              (diagnostyka)
│
├── Qdrant (Podman)           ← Baza wektorów        [port 6333]
│   └── kolekcja: klimtech_docs (5114 punktów)
│
├── Nextcloud (Podman)        ← Źródło dokumentów    [port 8443]
│   └── RAG_Dane/ (watchdog obserwuje)
│
└── n8n (Podman)              ← Automatyzacje        [port 5678]
```

### Kluczowe ograniczenia sprzętowe

| Zasób | Pojemność | Zajęte |
|-------|-----------|--------|
| VRAM AMD Instinct | 16 GB | LLM: ~14 GB (93%) |
| VRAM wolne | ~2 GB | Embedding e5-large: ~2.5 GB |
| **Wniosek** | LLM + GPU-embedding **nie zmieszczą się jednocześnie** | → embedding na CPU lub oddzielnie |

---

## 1. Dostępne architektury — analiza

### Wariant A — OWUI jako frontend, KlimtechRAG jako backend ⭐ ZALECANE

```
Przeglądarka
    ↓ HTTP
Open WebUI [port 3000]
    ↓ OpenAI API calls
KlimtechRAG Backend [port 8000]   ← RAG tutaj, niezmieniony
    ↓                ↓
  llama.cpp        Qdrant
  [port 8082]    [port 6333]
                klimtech_docs
                (5114 punktów)
```

**Zalety:**
- Zero zmian w backendzie
- Nie tracisz 5114 istniejących chunków
- OWUI daje nowoczesny UI, historię konwersacji, multi-user
- RAG działa tak jak teraz — przez `/v1/chat/completions`

**Wady:**
- Nie korzystasz z OWUI Knowledge Base (upload przez OWUI nie trafi do Qdrant)
- Upload dokumentów nadal przez KlimtechRAG UI lub curl

---

### Wariant B — OWUI jako pełny RAG (natywny Qdrant)

```
Przeglądarka
    ↓
Open WebUI [port 3000]
    ↓ chat          ↓ embeddings + retrieval
llama.cpp         Qdrant [port 6333]
[port 8082]     kolekcja: open-webui (NOWA)
```

**Zalety:**
- OWUI Knowledge Base — drag & drop pliki w UI
- Natywna integracja, lepsza kontrola nad RAG
- Qdrant panel do podglądu kolekcji

**Wady:**
- ⚠️ Musisz re-indeksować wszystkie dokumenty od nowa (inne nazwy kolekcji)
- ⚠️ OWUI używa innego modelu embeddingowego — niezgodność z `klimtech_docs`
- ⚠️ VRAM conflict: llama.cpp 14GB + OWUI embedding ~2.5GB = za dużo
- KlimtechRAG backend staje się tylko narzędziem do ingestionu z Nextcloud

---

### Wariant C — Hybrydowy (optymalny długoterminowo)

```
Przeglądarka
    ↓
Open WebUI [port 3000]
    ↓ chat                    ↓ embeddings przez API
llama.cpp                 KlimtechRAG [port 8000]
[port 8082]               (jako serwer embeddingów)
    ↑                              ↓
    └─────────── Qdrant ───────────┘
                [port 6333]
             klimtech_docs (wspólna!)
```

OWUI używa KlimtechRAG jako zewnętrznego serwera embeddingów → ta sama kolekcja, te same wektory. Wymaga konfiguracji `RAG_EMBEDDING_ENGINE=openai` i `RAG_EMBEDDING_OPENAI_BATCH_SIZE` w OWUI.

---

## 2. Rekomendacja i harmonogram

**Zaczynam od Wariantu A** (bezpieczny, szybki — 1 dzień roboty).
**Opcjonalnie Wariant C** (pełna integracja — tydzień, bez utraty danych).

```
Tydzień 1: Wariant A    → OWUI jako UI nad istniejącym backendem
Tydzień 2-3: Wariant C  → OWUI Knowledge Base + wspólna kolekcja Qdrant
```

---

## 3. FAZA 1 — Wariant A: OWUI jako frontend

### 3.1 Napraw ścieżki przed migracją

Z `notatki.md` wynika że projekt przeniesiony do `/media/lobo/BACKUP/KlimtechRAG/`.
**Najpierw popraw we wszystkich plikach**, zanim ruszysz z OWUI:

```bash
cd /media/lobo/BACKUP/KlimtechRAG

# Znajdź wszystkie stare ścieżki
grep -r "/home/lobo/KlimtechRAG" backend_app/ --include="*.py" -l
grep -r "/home/lobo/KlimtechRAG" *.py -l

# Podejrzyj co trzeba zmienić
grep -rn "/home/lobo/KlimtechRAG" backend_app/ --include="*.py"
```

**Zmień w `.env`:**
```bash
# .env — stare (do zmiany):
KLIMTECH_BASE_PATH=/home/lobo/KlimtechRAG

# .env — nowe:
KLIMTECH_BASE_PATH=/media/lobo/BACKUP/KlimtechRAG
```

**config.py** — jeśli `base_path` czyta z `.env`, wystarczy zmiana w `.env`.
Jeśli jest hardkodowane, zmień też w `config.py`:
```python
base_path: str = "/media/lobo/BACKUP/KlimtechRAG"
data_path: str = "/media/lobo/BACKUP/KlimtechRAG/data"
upload_base: str = "/media/lobo/BACKUP/KlimtechRAG/data/uploads"
# itd.
```

---

### 3.2 Instalacja Open WebUI (Podman)

```bash
# Sprawdź czy Podman działa
podman --version

# Pobierz obraz OWUI
podman pull ghcr.io/open-webui/open-webui:main

# Sprawdź dostępne porty
ss -tlnp | grep -E "3000|8080|8000|8082|6333"
```

---

### 3.3 Uruchomienie OWUI (Podman)

```bash
# Utwórz katalog danych OWUI
mkdir -p /media/lobo/BACKUP/KlimtechRAG/data/open-webui

# Uruchom OWUI
podman run -d \
  --name open-webui \
  --network host \
  -v /media/lobo/BACKUP/KlimtechRAG/data/open-webui:/app/backend/data \
  -e OPENAI_API_BASE_URLS="http://localhost:8000" \
  -e OPENAI_API_KEYS="sk-dummy" \
  -e ENABLE_OLLAMA_API="False" \
  -e PORT="3000" \
  -e WEBUI_AUTH="False" \
  ghcr.io/open-webui/open-webui:main
```

> **Ważne:** `--network host` zamiast bridge — żeby OWUI widział `localhost:8000` (KlimtechRAG) i `localhost:6333` (Qdrant). W Podman na Linuxie `--network host` działa bezpośrednio.

**Sprawdź czy działa:**
```bash
podman logs open-webui -f   # obserwuj logi
curl -s http://localhost:3000 | head -5   # powinien zwrócić HTML
```

---

### 3.4 Konfiguracja OWUI — połączenie z KlimtechRAG

Po otwarciu `http://localhost:3000` w przeglądarce:

1. Utwórz konto admina (pierwsze logowanie)
2. Przejdź: **Admin Panel → Settings → Connections**
3. W sekcji **OpenAI API**:
   - URL: `http://localhost:8000/v1`
   - API Key: `sk-dummy` (lub wartość z `.env` `KLIMTECH_API_KEY`)
4. Kliknij **Save → Verify connection**
5. W sekcji **Ollama** — wyłącz lub pozostaw puste

**Model który się pojawi:** Backend `/v1/models` musi zwrócić listę. Sprawdź czy endpoint istnieje:

```bash
curl -s http://localhost:8000/v1/models | python3 -m json.tool
```

Jeśli endpoint nie istnieje w KlimtechRAG, dodaj go (patrz sekcja 3.5).

---

### 3.5 Endpoint `/v1/models` w KlimtechRAG (jeśli brakuje)

OWUI wymaga tego endpointu żeby wylistować modele. Dodaj do `routes/chat.py`:

```python
from ..services.llm import get_llm_component
from ..config import settings

@router.get("/v1/models")
async def list_models():
    """Zwraca listę dostępnych modeli — wymagane przez OpenAI-compatible clients."""
    model_name = settings.llm_model_name or "klimtech-rag"
    return {
        "object": "list",
        "data": [
            {
                "id": model_name,
                "object": "model",
                "created": 1700000000,
                "owned_by": "klimtechrag",
            }
        ]
    }
```

---

### 3.6 Wyłącz RAG w OWUI (Wariant A)

W OWUI RAG musi być wyłączony — bo RAG robi już backend:

**Admin Panel → Settings → Documents:**
- `Enable RAG Hybrid Search` → OFF
- `Enable Web Search` → według preferencji
- Zostaw puste pola Qdrant (nie konfiguruj)

---

### 3.7 Dodaj OWUI do start_klimtech.py

```python
# W start_klimtech.py — dodaj po uruchomieniu backendu:

OWUI_DATA_DIR = os.path.join(BASE_DIR, "data", "open-webui")
os.makedirs(OWUI_DATA_DIR, exist_ok=True)

owui_cmd = [
    "podman", "start", "open-webui"  # restart jeśli kontener istnieje
]
# Lub jeśli kontener nie istnieje:
owui_cmd_new = [
    "podman", "run", "-d",
    "--name", "open-webui",
    "--network", "host",
    "-v", f"{OWUI_DATA_DIR}:/app/backend/data",
    "-e", "OPENAI_API_BASE_URLS=http://localhost:8000",
    "-e", "OPENAI_API_KEYS=sk-dummy",
    "-e", "ENABLE_OLLAMA_API=False",
    "-e", "PORT=3000",
    "ghcr.io/open-webui/open-webui:main"
]

subprocess.run(owui_cmd, capture_output=True)
print("✅ Open WebUI dostępny na: http://localhost:3000")
```

**I do stop_klimtech.py:**
```python
subprocess.run(["podman", "stop", "open-webui"], capture_output=True)
```

---

### 3.8 Wynik Fazy 1

Po zakończeniu tej fazy masz:

```
http://localhost:3000    → Open WebUI (nowy, ładny interfejs)
http://localhost:8000    → KlimtechRAG Backend (nadal działa)
http://localhost:8082    → llama.cpp (bez zmian)
http://localhost:6333    → Qdrant (bez zmian, 5114 punktów)
```

Użytkownik pisze pytanie w OWUI → OWUI wysyła je do `localhost:8000/v1/chat/completions` → backend pobiera kontekst z Qdrant → wysyła do llama.cpp → odpowiedź wraca do OWUI.

---

## 4. FAZA 2 — Wariant C: Pełna integracja OWUI + Qdrant

> ⚠️ **Warunek wstępny:** Faza 1 musi działać stabilnie.

### Cel Fazy 2

OWUI będzie używał Qdrant bezpośrednio do RAG, ale z **tym samym modelem embeddingowym** co KlimtechRAG (`intfloat/multilingual-e5-large`, wymiar 1024). Dzięki temu nie tracisz 5114 istniejących chunków i możesz używać OWUI Knowledge Base UI.

### Architektura docelowa

```
OWUI [port 3000]
  │
  ├─ Chat → llama.cpp [port 8082]         (bezpośrednio, bez warstwy backend)
  │
  ├─ Embeddings → KlimtechRAG [port 8000] (backend jako serwer embeddingów)
  │               endpoint: /v1/embeddings
  │
  └─ Vector DB → Qdrant [port 6333]
                 kolekcja: klimtech_docs   (ta sama co teraz!)

KlimtechRAG Backend [port 8000]
  ├─ /v1/embeddings                       (NOWY — serwuje embeddingi dla OWUI)
  ├─ /upload + /ingest_path               (ingest z Nextcloud — bez zmian)
  └─ /rag/debug, /health                  (diagnostyka — bez zmian)
```

---

### 4.1 Dodaj endpoint `/v1/embeddings` do KlimtechRAG

OWUI potrzebuje tego endpointu do tworzenia embeddingów przy ingestowaniu i wyszukiwaniu.
Dodaj do `routes/chat.py` (lub nowy router):

```python
from ..services import text_embedder

@router.post("/v1/embeddings")
async def create_embeddings(
    body: dict,
    req: Request,
):
    """OpenAI-compatible embeddings endpoint dla OWUI."""
    input_text = body.get("input", "")
    
    # input może być stringiem lub listą stringów
    if isinstance(input_text, str):
        inputs = [input_text]
    else:
        inputs = input_text
    
    embeddings = []
    for i, text in enumerate(inputs):
        result = text_embedder.run(text=text)
        embedding = result["embedding"]
        embeddings.append({
            "object": "embedding",
            "embedding": embedding,
            "index": i,
        })
    
    return {
        "object": "list",
        "data": embeddings,
        "model": "intfloat/multilingual-e5-large",
        "usage": {
            "prompt_tokens": sum(len(t.split()) for t in inputs),
            "total_tokens": sum(len(t.split()) for t in inputs),
        }
    }
```

**Test:**
```bash
curl -s -X POST "http://localhost:8000/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"input": "test zdanie"}' | python3 -m json.tool | head -20
```

Powinieneś dostać JSON z polem `data[0].embedding` zawierającym wektor 1024 elementów.

---

### 4.2 Zmień konfigurację OWUI na Fazę 2

Zatrzymaj kontener, usuń go i uruchom z nowymi zmiennymi:

```bash
podman stop open-webui && podman rm open-webui

podman run -d \
  --name open-webui \
  --network host \
  -v /media/lobo/BACKUP/KlimtechRAG/data/open-webui:/app/backend/data \
  \
  -e OPENAI_API_BASE_URLS="http://localhost:8082" \
  -e OPENAI_API_KEYS="sk-dummy" \
  -e ENABLE_OLLAMA_API="False" \
  \
  -e VECTOR_DB="qdrant" \
  -e QDRANT_URI="http://localhost:6333" \
  -e QDRANT_API_KEY="" \
  \
  -e RAG_EMBEDDING_ENGINE="openai" \
  -e RAG_EMBEDDING_MODEL="intfloat/multilingual-e5-large" \
  -e RAG_OPENAI_API_BASE_URL="http://localhost:8000/v1" \
  -e RAG_OPENAI_API_KEY="sk-dummy" \
  \
  -e CHUNK_SIZE="500" \
  -e CHUNK_OVERLAP="50" \
  \
  -e PORT="3000" \
  ghcr.io/open-webui/open-webui:main
```

**Co robią te zmienne:**

| Zmienna | Wartość | Opis |
|---------|---------|------|
| `OPENAI_API_BASE_URLS` | `http://localhost:8082` | Teraz bezpośrednio llama.cpp |
| `VECTOR_DB` | `qdrant` | Używaj Qdrant zamiast ChromaDB |
| `QDRANT_URI` | `http://localhost:6333` | Adres Qdrant |
| `RAG_EMBEDDING_ENGINE` | `openai` | Użyj zewnętrznego serwera do embeddingów |
| `RAG_OPENAI_API_BASE_URL` | `http://localhost:8000/v1` | KlimtechRAG jako serwer embeddingów |
| `RAG_EMBEDDING_MODEL` | `intfloat/multilingual-e5-large` | Ten sam model co w KlimtechRAG! |

---

### 4.3 Mapowanie kolekcji Qdrant

**Problem:** OWUI tworzy własną kolekcję `open-webui` w Qdrant, a istniejące 5114 chunków jest w `klimtech_docs`.

**Rozwiązanie A — Zachowaj obie kolekcje (najprostsze):**
- `klimtech_docs` — stara, obsługiwana przez KlimtechRAG backend
- `open-webui` — nowa, obsługiwana przez OWUI
- Dokumenty re-indeksowane przez OWUI Knowledge Base trafią do `open-webui`
- Stary KlimtechRAG ingest nadal zasilą `klimtech_docs`
- Rozbieżność — ale prosta w implementacji

**Rozwiązanie B — Migracja do wspólnej kolekcji:**

```bash
# Wyeksportuj snapshot klimtech_docs
curl -X POST "http://localhost:6333/collections/klimtech_docs/snapshots"

# Sprawdź snapshot
curl "http://localhost:6333/collections/klimtech_docs/snapshots"

# Następnie w OWUI: Admin → Documents → skonfiguruj kolekcję jako klimtech_docs
# (wymaga zmiennej QDRANT_COLLECTION_NAME jeśli OWUI ją obsługuje)
```

> Uwaga: OWUI nie ma bezpośredniego ustawienia nazwy kolekcji — używa domyślnie `open-webui`. Jeśli chcesz `klimtech_docs`, trzeba by patchować kod OWUI lub zaakceptować Rozwiązanie A.

**Rekomendacja: Zacznij od Rozwiązania A.** Stary content w `klimtech_docs` będzie dostępny przez `/v1/chat/completions` KlimtechRAG. Nowy content uploadowany przez OWUI trafi do `open-webui`.

---

### 4.4 Weryfikacja Fazy 2

```bash
# 1. Sprawdź endpoint embeddingów
curl -s -X POST "http://localhost:8000/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"input": "Klimatyzacja przemysłowa"}' | python3 -c "
import json, sys
d = json.load(sys.stdin)
emb = d['data'][0]['embedding']
print(f'OK! Wymiar wektora: {len(emb)}')
"

# 2. Sprawdź czy OWUI widzi Qdrant
curl -s http://localhost:6333/collections | python3 -m json.tool

# 3. Test RAG w OWUI
# Wrzuć dokument przez OWUI → Workspace → Knowledge → + Create
# Następnie w czacie użyj # przed pytaniem żeby przeszukać bazę

# 4. Sprawdź czy kolekcja open-webui powstała
curl -s http://localhost:6333/collections/open-webui | python3 -m json.tool
```

---

## 5. Rozwiązywanie konfliktów VRAM

Przy Fazie 2 OWUI wysyła zapytania embeddingowe do KlimtechRAG backendu. Embedding e5-large potrzebuje ~2.5GB VRAM ale LLM zajmuje 14GB/16GB.

### Opcja 1: Embedding na CPU (domyślne, bezpieczne)

W `start_klimtech.py` backend startuje z:
```python
backend_env = {
    "KLIMTECH_EMBEDDING_DEVICE": "cpu",  # embedding na CPU
    ...
}
```

Embedding CPU jest wolniejszy (~18s/batch) ale nie koliduje z LLM na GPU. Przy zapytaniach OWUI to 1 embedding na raz — wystarczająco szybko.

### Opcja 2: Sekwencyjne GPU (zaawansowane)

Przy masowym ingestowaniu: zatrzymaj LLM, uruchom embedding GPU, po zakończeniu wróć LLM:

```bash
# Wstrzymaj LLM
pkill llama-server

# Uruchom GPU embedding
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python -m backend_app.main &

# Zaindeksuj wszystko
curl -X POST "http://localhost:8000/ingest_all?limit=100"

# Wróć do normalnego trybu
kill %1
./start_klimtech.py
```

---

## 6. Nowa struktura katalogów po migracji

```
/media/lobo/BACKUP/KlimtechRAG/
├── .env                              ← zaktualizowane ścieżki
├── start_klimtech.py                 ← + uruchamianie OWUI
├── stop_klimtech.py                  ← + zatrzymywanie OWUI
├── start_backend_gpu.sh
│
├── backend_app/
│   ├── routes/
│   │   ├── chat.py                   ← + /v1/models, /v1/embeddings (Faza 2)
│   │   └── ...
│   └── ...
│
├── data/
│   ├── file_registry.db
│   ├── qdrant/                       ← baza Qdrant (klimtech_docs)
│   ├── uploads/
│   └── open-webui/                   ← NOWY: dane Open WebUI
│       ├── webui.db                  (SQLite z historiami konwersacji)
│       └── uploads/
│
├── modele_LLM/                       ← modele GGUF
│   ├── AudioLLM/
│   └── ...
│
└── logs/
    ├── backend.log
    ├── watchdog.log
    └── open-webui.log                ← NOWY
```

---

## 7. Aktualizacja pliku `.env`

```bash
# === KlimtechRAG ===
KLIMTECH_BASE_PATH=/media/lobo/BACKUP/KlimtechRAG
KLIMTECH_DATA_PATH=/media/lobo/BACKUP/KlimtechRAG/data
KLIMTECH_UPLOAD_BASE=/media/lobo/BACKUP/KlimtechRAG/data/uploads
KLIMTECH_NEXTCLOUD_BASE=/media/lobo/BACKUP/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane
KLIMTECH_FILE_REGISTRY_DB=/media/lobo/BACKUP/KlimtechRAG/data/file_registry.db

# === LLM ===
KLIMTECH_LLM_BASE_URL=http://localhost:8082/v1
KLIMTECH_LLM_API_KEY=sk-dummy
KLIMTECH_LLM_MODEL_NAME=
KLIMTECH_EMBEDDING_MODEL=intfloat/multilingual-e5-large

# === Qdrant ===
KLIMTECH_QDRANT_URL=http://localhost:6333
KLIMTECH_QDRANT_COLLECTION=klimtech_docs

# === Modele ===
LLAMA_MODELS_DIR=/media/lobo/BACKUP/KlimtechRAG/modele_LLM
LLAMA_API_PORT=8082

# === Open WebUI ===
OWUI_PORT=3000
OWUI_DATA_DIR=/media/lobo/BACKUP/KlimtechRAG/data/open-webui
```

---

## 8. Checklist wykonania

### Faza 1 (Wariant A)
- [ ] Popraw ścieżki w config.py i .env na `/media/lobo/BACKUP/KlimtechRAG/`
- [ ] Sprawdź `/v1/models` endpoint (`curl localhost:8000/v1/models`)
- [ ] Dodaj endpoint jeśli brak (patrz 3.5)
- [ ] Zainstaluj Open WebUI: `podman pull ghcr.io/open-webui/open-webui:main`
- [ ] Uruchom OWUI z `--network host` i `OPENAI_API_BASE_URLS=http://localhost:8000`
- [ ] Otwórz `http://localhost:3000`, utwórz konto admina
- [ ] Skonfiguruj OpenAI connection → `http://localhost:8000/v1`
- [ ] Wyłącz OWUI RAG w Admin Panel
- [ ] Test: zadaj pytanie w OWUI → sprawdź `/rag/debug` czy kontekst trafia
- [ ] Dodaj OWUI do `start_klimtech.py` i `stop_klimtech.py`

### Faza 2 (Wariant C) — opcjonalna
- [ ] Dodaj endpoint `/v1/embeddings` do KlimtechRAG
- [ ] Test endpointu embeddingów
- [ ] Zrestartuj OWUI z nowymi zmiennymi (VECTOR_DB, QDRANT_URI, RAG_EMBEDDING_ENGINE)
- [ ] Sprawdź czy kolekcja `open-webui` powstała w Qdrant
- [ ] Wrzuć dokument przez OWUI Knowledge Base
- [ ] Test: zapytaj o zawartość uploadowanego dokumentu
- [ ] Zadecyduj: dwie kolekcje vs migracja `klimtech_docs`

---

## 9. Znane ryzyka i obejścia

| Ryzyko | Prawdopodobieństwo | Obejście |
|--------|-------------------|----------|
| OWUI nie widzi modelu (brak `/v1/models`) | Wysokie | Dodaj endpoint (sekcja 3.5) |
| Qdrant Faza 2: błąd `collection_exists` | Średnie | Upewnij się że Podman z Qdrant działa zanim startujesz OWUI |
| OWUI używa innego wymiaru embeddingów | Wysokie | Musisz zmusić OWUI do użycia `RAG_OPENAI_API_BASE_URL` (sekcja 4.2) |
| Konflikt VRAM przy Fazie 2 | Niskie przy CPU embedding | Zostaw `KLIMTECH_EMBEDDING_DEVICE=cpu` |
| `stop_klimtech.py` nie zabija OWUI | Pewne | Musi być: `podman stop open-webui` (sekcja 3.7) |
| PID file watchdog w złym miejscu | Pewne (znany bug) | Napraw przed migracją (analiza z 21-02) |

---

## 10. Po zakończeniu migracji — docelowy stack

```
http://localhost:3000   → Open WebUI         (główny UI użytkownika)
http://localhost:8000   → KlimtechRAG        (RAG backend + embeddingi + ingest)
http://localhost:8082   → llama.cpp-server   (LLM: Bielik-11B)
http://localhost:6333   → Qdrant             (baza wektorów)
http://localhost:8443   → Nextcloud          (źródło dokumentów)
http://localhost:5678   → n8n                (automatyzacje)
```

**Workflow docelowy po Fazie 1:**
```
Użytkownik → OWUI → zadaje pytanie
→ OWUI → KlimtechRAG /v1/chat/completions
→ Backend pobiera kontekst z Qdrant (klimtech_docs)
→ Backend generuje odpowiedź przez llama.cpp
→ Odpowiedź z kontekstem wraca do OWUI
```

**Workflow docelowy po Fazie 2:**
```
Użytkownik wrzuca plik → OWUI Knowledge Base
→ OWUI pyta KlimtechRAG /v1/embeddings o wektor
→ OWUI zapisuje do Qdrant (open-webui)

Użytkownik zadaje pytanie → OWUI
→ OWUI pobiera embedding z KlimtechRAG
→ OWUI szuka w Qdrant
→ OWUI wysyła kontekst + pytanie do llama.cpp
→ Odpowiedź wraca
```

---

*Plan wygenerowany: 2026-02-21 | Wersja: 1.0*
*Oparty na analizie sesji nr 1, nr 2 i kodu z 2026-02-21*
