📋 Nowy, szczegółowy plan wdrożenia KlimtechRAG

    Uwaga: poniżej znajdują się informacje, które udało się wyodrębnić z przesłanego pliku Plan_instalacji_RAG_NR_3.md.
    Nie posiadam treści plików AGENTS.md oraz klimtech_rag, więc nie mogę ich włączyć do planu. Jeżeli udostępnisz ich zawartość, chętnie uzupełnię dokument.

1️⃣ Co już zostało zrobione
Etap	Działania wykonane
1. Konfiguracja środowiska	• Instalacja Ubuntu 24.04.3 LTS • Aktualizacja pakietów (apt update && apt upgrade) • Instalacja narzędzi deweloperskich (build‑essential, git, curl, wget) • Instalacja Pythona 3 (≥ 3.10) i utworzenie wirtualnego środowiska venv
2. Konteneryzacja (Podman)	• Instalacja i konfiguracja Podman jako zamiennika Dockera • Przygotowanie sieci kontenerowej oraz wolumenów na SSD FireCuda
3. Usługi bazowe (kontenery)	• Uruchomienie bazy wektorowej (Qdrant lub Weaviate) • Deploy Nextcloud + PostgreSQL/MariaDB, mapowanie woluminów na SSD • Deploy n8n (automatyzacja) i podstawowa konfiguracja credentialów
4. „Mózg operacyjny” – llama.cpp	• Skompilowanie llama.cpp z optymalizacjami AVX2/AVX512 dla AMD Ryzen 9 9950X • Pobranie kwantowanego modelu LLM (Llama 3 Instruct lub Mistral, 7‑14 B, 32 GB RAM) • Uruchomienie llama‑server na porcie 8080 (OpenAI‑compatible API)
5. Backend RAG (Haystack + Docling + FastAPI)	• Instalacja bibliotek: haystack-ai, docling, llama-index, fastapi, sentence‑transformers • Implementacja komponentu integrującego Docling (parsowanie PDF → Markdown/tekst) • Stworzenie pipeline‑ów: Ingestion → Vector Store oraz Retrieval → Prompt Builder → Generator (llama.cpp) • Udostępnienie dwóch endpointów FastAPI (/ingest, /query) na porcie 8000
6. Integracja z repozytoriami GitHub/GitLab	• Skrypty synchronizujące (git clone, git pull) uruchamiane cyklicznie (Cron/n8n) • Rozszerzenie pipeline‑u o indeksowanie kodu (.py, .js, .md) • Dodanie prostego komponentu DuckDuckGo‑search do pobierania treści WWW “w locie”
7. Automatyzacja w n8n	• Workflow „Nowa dokumentacja”: wykrywanie nowych plików w Nextcloud → wywołanie /ingest • Workflow „Powiadomienia”: monitorowanie skrzynki IMAP → powiadomienia na Signal/Telegram
8. Integracja z OpenCode (IDE)	• Instalacja OpenCode.ai na Ubuntu • Definicja nowego narzędzia (Tool) w konfiguracji OpenCode, które wywołuje http://localhost:8000/query • Testowanie pełnego loopa: zapytanie w terminalu → API → Haystack/Doling → odpowiedź w edytorze
9. Optymalizacja i testy sprzętowe	• Strojenie parametrów llama.cpp (liczba wątków, batch size) oraz ewentualny PyTorch • Stress‑testy dużych PDF oraz równoczesnych zapytań RAG
2️⃣ Co jeszcze trzeba zrobić
Zadanie	Szczegóły	Priorytet
A. Uporządkowanie struktury katalogów Nextcloud	• Utworzyć trzy dedykowane foldery: Video_RAG, Audio_RAG, Doc_RAG. • Ograniczyć dostęp modelu i n8n tylko do tych folderów. • Skonfigurować odpowiednie prawa dostępu (read/write)	Wysoki
B. Watchdog / monitor folderu	• Napisać skrypt (np. w Pythonie) monitorujący Doc_RAG i automatycznie wywołujący /ingest przy wykryciu nowego pliku. • Zapewnić obsługę kilku typów plików (PDF, TXT, DOCX, MP3/MP4).	Wysoki
C. Skalowanie dysków	• Zamontować SSD 2 TB jako główny magazyn wektorów i tymczasowych plików. • HDD 5 TB przeznaczyć na archiwalne repozytoria i starsze dane.	Średni
D. Rozbudowa integracji OpenCode	• Dodanie możliwości przełączania pomiędzy różnymi modelami (tekst, audio, kod). • Implementacja własnych „agentów” w OpenCode, które będą wywoływać różne endpointy (np. audio‑query).	Średni
E. Pełna synchronizacja repozytoriów GitHub	• Skrypt ingest_repo.py powinien iterować po 295 repozytoriach, klonować je na HDD 5 TB i uruchamiać pipeline indeksujący kod. • Zaplanować regularne odświeżanie (np. co 24 h).	Średni
F. Dokumentacja i testy jednostkowe	• Dodać testy (pytest) dla kluczowych komponentów: parser Docling, retriever, generator. • Stworzyć README z instrukcją uruchamiania całego stacku (docker‑compose‑like script).	Niski
G. Backup i disaster recovery	• Skonfigurować codzienne snapshoty SSD oraz replikację na HDD. • Przygotować skrypt przywracania środowiska (restore‑env.sh).	Niski
3️⃣ Sugestie i rekomendacje

    Użycie docker-compose zamiast ręcznych poleceń Podman
        Choć Podman jest świetny, docker‑compose.yml (działający pod Podman) pozwoli na wersjonowanie całej infrastruktury i szybką rekonfigurację.

    Rozważenie Qdrant jako domyślnej bazy wektorowej
        Qdrant oferuje wbudowane filtry metadata i lepszą skalowalność przy dużych zbiorach (setki GB).

    Cache‑owanie wyników wyszukiwania internetowego
        Dodaj warstwę Redis, aby nie powtarzać kosztownych zapytań DuckDuckGo przy identycznych zapytaniach.

    Obsługa multimediów
        Dla audio/video warto dodać modele Whisper (transkrypcja) i Whisper‑X (segmentacja) – mogą być uruchamiane jako oddzielne mikro‑serwisy i integrowane w pipeline RAG.

    Bezpieczeństwo
        Włącz TLS w llama‑server oraz w FastAPI (np. przy użyciu cert‑bot).
        Ogranicz dostęp do portów 8080/8000 jedynie do localhost lub sieci VPN.

    Monitorowanie i logowanie
        Prometheus + Grafana do zbierania metryk (CPU, RAM, liczba zapytań, czas odpowiedzi).
        Centralny system logów (ELK) ułatwi debugowanie.

    Rozbudowa OpenCode
        Skorzystaj z plugin‑ów OpenCode, aby dodać własne szablony komend (np. rag‑doc <ścieżka>).
        Udostępnij możliwość definiowania „profilów” modelu (tekst‑heavy vs. code‑heavy).

4️⃣ Szczegółowy plan działania (krok po kroku)
Krok 1 – Finalizacja struktury Nextcloud

# w kontenerze Nextcloud
mkdir -p /var/www/html/data/Video_RAG \
         /var/www/html/data/Audio_RAG \
         /var/www/html/data/Doc_RAG
# ustaw odpowiednie ACL
chmod -R 770 /var/www/html/data/*_RAG

Krok 2 – Implementacja Watchdog (Python)

# watch_nextcloud.py
import time, os, requests
WATCH_DIR = "/mnt/nextcloud/Doc_RAG"
API_URL = "http://localhost:8000/ingest"

def process_file(path):
    with open(path, "rb") as f:
        files = {"file": f}
        r = requests.post(API_URL, files=files)
        print(f"{path} → {r.status_code}")

while True:
    for fname in os.listdir(WATCH_DIR):
        full = os.path.join(WATCH_DIR, fname)
        if os.path.isfile(full) and not fname.endswith(".processed"):
            process_file(full)
            os.rename(full, full + ".processed")
    time.sleep(30)

Dodaj jako usługę systemd, aby uruchamiała się przy starcie.
Krok 3 – Skalowanie dysków

# montowanie SSD jako /data/ssd
sudo mkfs.ext4 /dev/nvme0n1
sudo mount /dev/nvme0n1 /data/ssd
# montowanie HDD jako /data/hdd
sudo mkfs.ext4 /dev/sdb1
sudo mount /dev/sdb1 /data/hdd
# dodaj wpisy do /etc/fstab

Krok 4 – Rozbudowa OpenCode

    Edytuj ~/.opencode/config.yaml → dodaj sekcję tools:

    tools:
      - name: klimtech_rag_query
        description: "Zapytanie do lokalnego RAG"
        endpoint: http://localhost:8000/query
        method: POST
        payload:
          query: "{{input}}"

    Przetestuj w terminalu:

    > Opisz mi dokument z Nextcloud

Krok 5 – Synchronizacja repozytoriów

#!/bin/bash
BASE=/data/hdd/GitHub_database_RAG
for REPO in $(cat repos_list.txt); do
    if [ -d "$BASE/$REPO/.git" ]; then
        git -C "$BASE/$REPO" pull
    else
        git clone "https://github.com/$REPO.git" "$BASE/$REPO"
    fi
done
# Po synchronizacji wywołaj ingest_repo.py
python ingest_repo.py "$BASE"

Krok 6 – Monitoring i backup

    Prometheus: dodaj exporter node_exporter oraz podman_exporter.
    Grafana: dashboard z wykresami obciążenia CPU, czasu odpowiedzi LLM, liczby zapytań.
    Backup: rsync -a /data/ssd/ /backup/ssd_snapshot_$(date +%F) (cron codzienny).

5️⃣ Drzewo katalogów w ~/KlimtechRAG

~/KlimtechRAG
├── AGENTS.md
├── backend_app
│   ├── main.py
│   ├── plik_testowy.py
│   └── __pycache__/
├── data
│   ├── n8n/
│   ├── nextcloud/
│   ├── nextcloud_db/
│   ├── postgres/
│   └── qdrant/
├── git_sync
│   ├── ingest_repo.py
│   └── opencode/
├── llama.cpp
│   ├── AUTHORS
│   ├── CMakeLists.txt
│   ├── README.md
│   ├── build/
│   ├── cmake/
│   ├── docs/
│   ├── examples/
│   ├── ggml/
│   ├── gguf-py/
│   ├── models/
│   ├── scripts/
│   └── src/
├── pytest.ini
├── start_klimtech.sh
├── venv/
│   ├── bin/
│   ├── include/
│   ├── lib/
│   ├── lib64/
│   └── pyvenv.cfg
└── watch_nextcloud.py

6️⃣ Zawartość pliku AGENTS.md

# KlimtechRAG - Agent Guidelines

## Project Overview
RAG system with Python 3.12, FastAPI, Haystack, and Qdrant. Indexes documents (PDF, text, code, audio, video) with LLM-based query responses.

## Build, Lint, and Test Commands

### Tests
```bash
pytest                        # All tests
pytest backend_app            # Specific directory
pytest backend_app/test_file.py::test_func  # Single test
pytest -k "pattern"           # By pattern
pytest -v                     # Verbose
pytest --cov=backend_app      # Coverage
```

### Linting
```bash
ruff check .                  # Check code quality
ruff check --fix .            # Auto-fix
ruff check --statistics .     # Stats
```

### Formatting
```bash
ruff format .                 # Format code
ruff format --check .         # Check formatting
ruff format --diff .          # Show diff
```

## Code Style

### Python Version
Python 3.12.3

### Type Hints
Use type hints for all function arguments and returns. Import from `typing` when needed.
```python
def is_text_file(file_path: str) -> bool:
    ...
```

### Naming
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_snake_case`

### Imports
Order: standard → third-party → local. Separate groups with blank lines.
```python
import os
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from haystack import Pipeline
```

### Error Handling
Use try-except with print for debugging. Raise HTTPException for API errors. Always cleanup in finally blocks.
```python
try:
    result = pipeline.run(...)
    return {"message": "Success"}
except Exception as e:
    print(f"Error: {e}")
    raise HTTPException(status_code=500, detail=str(e))
finally:
    if temp_file_path and os.path.exists(temp_file_path):
        os.unlink(temp_file_path)
```

### Docstrings/Comments
Triple-quoted docstrings for functions (English for endpoints). Inline comments in Polish.
```python
async def ingest_file(file: UploadFile):
    """Endpoint do ładowania plików PDF do bazy RAG."""
    # 1. Sprawdzenie rozszerzenia pliku
    suffix = os.path.splitext(file.filename)[1].lower()
```

### File Structure
1. Imports
2. Environment variables & constants
3. Helper functions
4. Pipeline/component setup
5. Pydantic models
6. API endpoints
7. Signal handlers
8. Main execution block

### API Endpoints
Use async functions, Pydantic models for requests, HTTPException for errors.
```python
@app.post("/ingest")
async def ingest_file(file: UploadFile):
    try:
        result = process_file(file)
        return {"message": "Success", "chunks": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Project Structure
- `backend_app/main.py` - FastAPI application
- `git_sync/ingest_repo.py` - Git repo sync
- `watch_nextcloud.py` - File system watcher
- `pytest.ini` - Test paths: `backend_app`, `git_sync`; ignore: `data`, `llama.cpp`, `venv`

### Key Tech
FastAPI, Haystack, Qdrant, Pydantic, Docling, Watchdog, pytest, ruff

### Best Practices
1. Clean up temp files in `finally` blocks
2. Validate file extensions/sizes before processing
3. Use meaningful variable names
4. Print debug messages with prefixes: `[DEBUG]`, `[ERROR]`
5. Use environment variables for config
6. Handle signals gracefully

### Testing
Tests in `backend_app/` or `git_sync/`. Files start with `test_` or end with `_test.py`. Use pytest fixtures, test success/error cases, mock external dependencies.

### Common Patterns
- **File processing**: `tempfile.NamedTemporaryFile(delete=False)`, cleanup in `finally`
- **Folder traversal**: `os.walk()` with directory filtering
- **API requests**: `requests.post()` with timeout and error handling
- **Pipeline**: Haystack Pipeline with `connect()` method

### Folder Blacklist
Skip: `node_modules`, `.git`, `__pycache__`, `.venv`, `venv`, `build`, `dist`, `.idea`

### Allowed Extensions
`.pdf`, `.md`, `.txt`, `.py`, `.json`, `.yml`, `.yaml`, `.mp3`, `.mp4`, `.jpeg`, `.jpg`, `.js`, `.ts`

### File Size Limit
Maximum 500 KB. Check with `os.path.getsize()`.

### Running
```bash
cd backend_app && python main.py
python watch_nextcloud.py
bash start_klimtech.sh
```

### Services
- Backend: http://localhost:8000
- LLM: http://localhost:8081
- Qdrant: http://localhost:6333


7️⃣ Zawartość pliku klimtech_rag


```bash
ls /home/lobo/.opencode/bin
klimtech_rag*  opencode*
cat /home/lobo/.opencode/bin/klimtech_rag 
```

```bash
#!/bin/bash
# Skrypt łączący OpenCode z KlimtechRAG
# Użycie: klimtech_rag "Pytanie użytkownika"

QUERY="$1"

curl -s -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"${QUERY}\"}"
```



# pliki Python i .sh:

- main.py

```python
import os
import shutil
import tempfile
import mimetypes
import signal
import sys
from typing import List

from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel
from haystack import Pipeline, Document
from haystack.document_stores.types import DuplicatePolicy

from haystack.components.preprocessors import DocumentSplitter
from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.components.writers import DocumentWriter
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack.components.generators import OpenAIGenerator

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from ddgs import DDGS

# --- KONFIGURACJA ŚRODOWISKOWA (Dla LLM) ---
os.environ["OPENAI_BASE_URL"] = "http://localhost:8081/v1"
os.environ["OPENAI_API_KEY"] = "sk-dummy"

EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
LLM_MODEL_NAME = "gpt-3.5-turbo"

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".md",
    ".txt",
    ".py",
    ".json",
    ".yml",
    ".yaml",
    ".mp3",
    ".mp4",
    ".jpeg",
    ".jpg",
}
app = FastAPI()

# Konfiguracja Qdrant
doc_store = QdrantDocumentStore(
    url="http://localhost:6333",
    index="klimtech_docs",
    embedding_dim=1024,
    recreate_index=False,
)


# --- FUNKCJA POMOCNICZA: Filtracja Typów Plików ---
def is_text_file(file_path: str) -> bool:
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type.startswith(
            ("text/", "application/pdf", "application/json", "application/javascript")
        )
    return False


# --- KOMPONENTY DO INDEKSOWANIA ---
def parse_with_docling(file_path: str) -> str:
    options = PdfPipelineOptions()
    options.generate_page_images = False
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(options=options)}
    )
    result = converter.convert(file_path)
    return result.document.export_to_markdown()


indexing_pipeline = Pipeline()
indexing_pipeline.add_component(
    "splitter", DocumentSplitter(split_by="word", split_length=200, split_overlap=30)
)
indexing_pipeline.add_component(
    "embedder", SentenceTransformersDocumentEmbedder(model=EMBEDDING_MODEL)
)
indexing_pipeline.add_component(
    "writer", DocumentWriter(document_store=doc_store, policy=DuplicatePolicy.OVERWRITE)
)
indexing_pipeline.connect("splitter", "embedder")
indexing_pipeline.connect("embedder", "writer")

# --- KOMPONENTY DO ZAPYTAŃ (RAG) ---
rag_pipeline = Pipeline()
rag_pipeline.add_component(
    "embedder", SentenceTransformersTextEmbedder(model=EMBEDDING_MODEL)
)
rag_pipeline.add_component(
    "retriever", QdrantEmbeddingRetriever(document_store=doc_store, top_k=3)
)
rag_pipeline.add_component(
    "prompt_builder",
    PromptBuilder(
        template="Given these documents:\n{% for doc in documents %}\n{{ doc.content }}\n{% endfor %}\n\nAnswer: {{query}}",
        required_variables=["documents", "query"],
    ),
)
rag_pipeline.add_component("llm", OpenAIGenerator(model=LLM_MODEL_NAME))

rag_pipeline.connect("embedder", "retriever")
rag_pipeline.connect("retriever", "prompt_builder.documents")
rag_pipeline.connect("prompt_builder", "llm")


class QueryRequest(BaseModel):
    query: str


@app.post("/ingest")
async def ingest_file(file: UploadFile):
    """Endpoint do ładowania plików PDF do bazy RAG."""
    # 1. Sprawdzenie rozszerzenia pliku
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail=f"File format not allowed: {file.filename}"
        )

    temp_file_path = None
    markdown_text = ""

    try:
        # 2. Zapisujemy plik tymczasowo
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_file_path = tmp.name

        # 3. Sprawdzamy czy to PDF (Docling) czy tekst/markdown
        if suffix == ".pdf":
            print(f"[DEBUG - Backend] Parsowanie PDF...")
            markdown_text = parse_with_docling(temp_file_path)
        else:
            # Dla plików tekstowych czytamy je bezpośrednio
            print(f"[DEBUG - Backend] Parsowanie tekstu...")
            with open(temp_file_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()

        # 4. Sprawdzenie czy tekst nie jest pusty (zabezpieczenie)
        if not markdown_text or len(markdown_text.strip()) == 0:
            print(f"[DEBUG - Backend] Plik pusty (skan bez tekstu): {file.filename}")
            # Zwracamy 0 fragmentów, ale błędu 500 nie ma
            return {"message": "File empty (Scanned PDF?)", "chunks_processed": 0}

        docs = [
            Document(
                content=markdown_text, meta={"source": file.filename, "type": suffix}
            )
        ]
        result = indexing_pipeline.run({"splitter": {"documents": docs}})

        return {
            "message": "File ingested successfully",
            "chunks_processed": result["writer"]["documents_written"],
        }
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}
    finally:
        # CZYSZCZENIE PLIKU TYMCZASOWEGO jest KONIECZNE
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@app.post("/query")
async def query_rag(request: QueryRequest):
    """Endpoint do zadawania pytań RAG z Web Search."""
    try:
        rag_result = rag_pipeline.run(
            {
                "embedder": {"text": request.query},
                "prompt_builder": {"query": request.query},
            },
            include_outputs_from={"retriever"},
        )
        local_docs = rag_result["retriever"]["documents"]

        web_snippet = ""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(request.query, max_results=2))
                web_snippet = " | ".join([res["body"] for res in results])
        except Exception as e:
            print(f"Web search error: {e}")
            web_snippet = "Brak wyników z sieci."

        from haystack import Document

        web_doc = Document(content=web_snippet, meta={"source": "Web Search"})
        final_docs = local_docs + [web_doc]

        prompt_text = ""
        for doc in final_docs:
            prompt_text += f"{doc.content}\n"

        prompt_text += f"\n\nAnswer: {request.query}"

        llm_component = rag_pipeline.get_component("llm")
        llm_result = llm_component.run(prompt=prompt_text)
        answer = llm_result["replies"][0]

        return {"answer": answer}
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# --- OBSŁUGA SYGNAŁU (Signal Handling) ---
def handle_sigint(signum, frame):
    print("\nZatrzymywanie serwera...")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_sigint)

if __name__ == "__main__":
    import uvicorn

    print("Startowanie KlimtechRAG Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

```

- watch_nexcloud.py

```python
import os
import time
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- KONFIGURACJA ---
WATCH_DIRS = [
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/Doc_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/data/admin/files/RAG_Dane/Audio_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/Video_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/Images_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/json_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/pdf_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/txt_RAG",
]

API_URL = "http://localhost:8000/ingest"

# Rozszerzenia, które we wszyłam do Backendu (Wszystko! Wszystkie pójdzie do RAG jako "tekst".
# Pliki audio/video/obrazy będą zapisane jako "tekst" (np. `[Audio_RAG: Plik rider.mp3]`) i skrypt Watchdog je po prostu wyślije (skip), ale zapisze do bazy jako tekst. LLM odpowie co z tym zrobić (np. "Ten plik zawiera nagranie o pogodzie").

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".py", ".json", ".mp3", ".mp4", ".jpeg", ".jpg", ".png"}

# --- OBSŁUGA ZDARZEŃ ---
class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if any(file_path.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            print(f"[INFO] Nowy plik: {os.path.basename(file_path)}")
            ingest_file(file_path)
        else:
            # Jeśli plik nie jest "tekstowy" (np. `.mp3`, `.mp4`, `.jpg`), oznaczamy go jako "zignorowany" ("Plik binarny").
            # Dodamy informację w JSON, ale Backend powinien zwrócić `0 chunks_processed` (zero), żeby nie zanieśmieć bazę danymi śmieci.
            # ALE! Zróbmy tak (skip z indeksacji) - 0 chunks.

    def on_moved(self, event):
        if event.is_directory:
            return

        file_path = event.dest_path if event.dest_path else event.src_path
        if any(file_path.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
            ingest_file(file_path)
        else:
            # Plik binarny (.mp3, .jpg, .png).
            print(f"[SKIP] Ignorujemy plik binarny: {os.path.basename(file_path)}")

def ingest_file(file_path):
    """Wysyła plik do backendu RAG (Tylko tekst!)"""
    print(f"[INFO] Przetwarzam: {os.path.basename(file_path)}")
    try:
        # Nie używamy tymczasowych plików. Wczytamy plik bezpośrednio (`rb`).
        with open(file_path, 'rb') as f:
            content = f.read()

        # Wszystkie pliki traktujemy jako tekst. Docling i LLM muszą się z tym poradzić.
        
        docs = [
            Document(
                content=content, meta={"source": os.path.basename(file_path), "type": os.path.splitext(file_path)[1].lower()}
            )
        ]

        # Wysyłamy do Backendu.
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(API_URL, files=files, timeout=30)
            
        if response.status_code == 200:
            result = response.json()
            print(f"[SUCCESS] Zaindeksowano {result.get('chunks_processed', 0)} fragmentów.")
            print(f"[DEBUG] Treść dokumentu (pierwsze 100 znaków): {content[:100]}") # Debug - abyświdzieć, co backend dostał.
        else:
            print(f"[WARN] Backend: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] Błąd podczas przetwarzania: {e}")

if __name__ == "__main__":
    event_handler = NewFileHandler()
    observer = Observer()
    
    print("Startowanie monitoringu KlimtechRAG (Smart Filter - Wszystkie typy plików):")
    for dir_path in WATCH_DIRS:
        print(f" -> Monitoring: {dir_path}")
    
    observer.schedule(event_handler, *WATCH_DIRS, recursive=True)
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        print("\nMonitorowanie zatrzymane.")
```

- ingest_repo.py

```python
import os
import requests
import sys
import signal
from watchdog.observers import Observer

# --- Ten plik ma nazwę ingest_repo.py ---


# Konfiguracja
API_URL = "http://localhost:8000/ingest"

ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".py", ".js", ".ts", ".json", ".yml", ".yaml", ".mp3", ".mp4", ".jpeg", ".jpg"}
MAX_FILE_SIZE = 500 * 1024  # 500 KB

# Foldery do pominięcia (blacklist)
SKIP_FOLDERS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
    ".idea",
}


def ingest_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"BŁĄD: Folder nie istnieje: {folder_path}")
        return

    print(f"🚀 Rozpoczynam indeksowanie folderu: {folder_path}")
    processed_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(folder_path):
        # Usuń foldery z blacklisty
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]

        for file in files:
            if any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                file_path = os.path.join(root, file)

                if os.path.getsize(file_path) > MAX_FILE_SIZE:
                    skipped_count += 1
                    continue

                relative_path = os.path.relpath(file_path, folder_path)
                print(f"📄 Wysyłanie: {relative_path}...", end=" ")

                try:
                    with open(file_path, "rb") as f:
                        files_dict = {"file": (file, f)}
                        response = requests.post(API_URL, files=files_dict, timeout=30)

                    if response.status_code == 200:
                        print("✅ OK")
                        processed_count += 1
                    else:
                        print(f"❌ BŁĄD: {response.text}")
                except Exception as e:
                    print(f"⚠️  BŁĄD POŁĄCZENIA: {e}")
            else:
                skipped_count += 1

    print(
        f"\n🎉 Zakończono! Przetworzono {processed_count} plików. Pominięto: {skipped_count}."
    )

if __name__ == "__main__":
    # Wybór ścieżki: argument z wiersza poleceń lub domyślna
    if len(sys.argv) > 1:
        target_folder = sys.argv[1]
    else:
        # Domyślnie indeksujemy pobrane repozytorium opencode
        target_folder = "/home/lobo/KlimtechRAG/git_sync/opencode"

    ingest_folder(target_folder)
    observer = Observer()
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
        print("\nZatrzymywanie monitoringu...")
```

- start_klimtech.sh

```bash
#!/bin/bash
# Skrypt Startowy dla KlimtechRAG

echo "🚀 Startowanie usług KlimtechRAG..."

# 1. Backend (Python) w tle
echo "🔧 Uruchamianie Backend RAG..."
cd ~/KlimtechRAG/backend_app
python main.py &
BACKEND_PID=$!
echo "   -> Backend PID: $BACKEND_PID"

# 2. LLM Server (llama.cpp) w tle
echo "🧠 Uruchamianie LLM Server..."
cd ~/KlimtechRAG/llama.cpp
./build/bin/llama-server -m models/LFM2-2.6B-Q5_K_M.gguf --host 0.0.0.0 --port 8081 -c 4096 -ngl 99 &
LLM_PID=$!
echo "   -> LLM PID: $LLM_PID"

# 3. Watchdog (Python) w tle
echo "👁 Uruchamianie Watchdog..."
cd ~/KlimtechRAG
python watch_nextcloud.py &
WATCHDOG_PID=$!
echo "   -> Watchdog PID: $WATCHDOG_PID"

# Oczekiwanie, aby wszystko wystartowało
sleep 5

echo "✅ Gotowe! Usługi działają w tle."
echo "📋 Backend: http://localhost:8000 (PID $BACKEND_PID)"
echo "🧠 LLM:     http://localhost:8081 (PID $LLM_PID)"
echo "👁 Watchdog: Monitoruje ~/KlimtechRAG/data/nextcloud... (PID $WATCHDOG_PID)"
echo ""
echo "Wpisz 'pkill -f start_klimtech' aby zatrzymać WSZYSTKO."
```
# Dodatkowe i przydatne komendy :

```bash
```bash
sudo pkill python && sudo pkill -f 'uvicorn backend_app.main:app --host 0.0.0.0 --port 8000' && sudo pkill -f './build/bin/llama-server -m models/LFM2-2.6B-Q5_K_M.gguf --host 0.0.0.0 --port 8081 -c 4096 -ngl 99' && pkill -f 'python watch_nextcloud.py' && sudo pkill -f  start_klimtech.sh

podman start qdrant nextcloud postgres_nextcloud n8n
podman stop qdrant nextcloud postgres_nextcloud n8n
podman restart qdrant nextcloud postgres_nextcloud n8n

podman ps
 
podman restart qdrant nextcloud postgres_nextcloud n8n  
 
podman exec -it nextcloud cat /var/www/html/config/config.php | grep -i datadirectory

podman exec -it nextcloud bash

cd /var/www/html
ls -la data/

chmod -R 777 data/
chown -R www-data:www-data data/

chmod -R 777 data/
chown -R www-data:www-data data/


find . -name "*rag*" -o -name "*klimtech*" 2>/dev/null | grep -v node_modules | grep -v .git | grep -v __pycache__ | grep -v venv | head -20
```

