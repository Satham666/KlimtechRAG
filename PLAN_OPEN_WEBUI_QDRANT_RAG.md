# Plan Migracji: Open WebUI + Qdrant RAG na bazie KlimtechRAG

*Wygenerowano: 2026-02-22*

---

## 1. Podsumowanie decyzyjne

### Dlaczego Open WebUI zamiast własnego backendu?

| Aspekt | KlimtechRAG (własny) | Open WebUI |
|--------|---------------------|------------|
| **UI/UX** | Prosty HTML, dużo problemów | Profesjonalny, responsywny, motywy |
| **Zarządzanie dokumentami** | Własny file_registry.db | Wbudowane + metadata |
| **RAG** | Ręczna konfiguracja Qdrant | Natywna integracja z Qdrant |
| **Użytkownicy** | Brak / własny system | Pełny system auth + role |
| **Multimodal** | Częściowy (VLM nie działa) | Pełny (obrazy, audio, video) |
| **MCP** | Brak | Natywne wsparcie |
| **Web Search** | DuckDuckGo hardcoded | Konfigurowalne (SearXNG, Google, etc.) |
| **Community** | Tylko Ty | Aktywna społeczność, pluginy |
| **Czas rozwoju** | Ciągłe naprawy | Gotowe, tylko konfiguracja |

### Co zachowujemy z KlimtechRAG?

```
ZACHOWUJEMY:
├── Baza Qdrant (klimtech_docs)
├── Model embedding: intfloat/multilingual-e5-large
├── Pliki w data/uploads/ (PDF, TXT, JSON)
├── Watchdog do monitoringu Nextcloud
├── Skrypty OCR (ingest_pdfCPU.py, ingest_pdfGPU.py)
├── Model LLM: Bielik-11B przez llama.cpp-server
└── GPU: AMD Instinct 16GB

PORZUCAMY:
├── backend_app/ (cały katalog)
├── Własny UI czatu
├── file_registry.py (SQLite)
├── Ręczne zarządzanie sesjami
└── Wszystkie problemy z cache, HNSW, etc.
```

---

## 2. Architektura docelowa

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ARCHITEKTURA DOCZELOWA                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐      │
│  │  Open WebUI    │     │  MCP Server    │     │  llama.cpp     │      │
│  │  (port 8080)   │────▶│  (port 8001)   │◀────│  (port 8082)   │      │
│  │                │     │                │     │  Bielik-11B    │      │
│  └───────┬────────┘     └───────┬────────┘     └────────────────┘      │
│          │                      │                                       │
│          │                      │                                       │
│          ▼                      ▼                                       │
│  ┌────────────────┐     ┌────────────────┐                             │
│  │    Qdrant      │     │   Postgres     │                             │
│  │  (port 6333)   │     │  (port 5432)   │                             │
│  │  klimtech_docs │     │  Open WebUI DB │                             │
│  └───────┬────────┘     └────────────────┘                             │
│          │                                                              │
│          │                                                              │
│          ▼                                                              │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                    DATA LAYER                                   │    │
│  ├────────────────┬────────────────┬────────────────┬─────────────┤    │
│  │  PDF_RAG/      │  Doc_RAG/      │  Nextcloud/    │ Git repos/  │    │
│  │  Dokumenty PDF │  TXT, MD, JSON │  Sync folder   │ Code        │    │
│  └────────────────┴────────────────┴────────────────┴─────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Fazy implementacji

### FAZA 0: Przygotowanie środowiska (1-2h)

#### 3.0.1 Wymagania systemowe

```bash
# Sprawdzenie portów
ss -tlnp | grep -E "8080|6333|5432|8082"

# Oczyszczenie starych procesów
pkill -f watch_nextcloud
pkill -f backend_app
```

#### 3.0.2 Instalacja Open WebUI

**Opcja A: Docker (zalecane)**
```bash
# Stwórz docker-compose.yml
cat > ~/KlimtechRAG/docker-compose.openwebui.yml << 'EOF'
version: '3.8'

services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - OPENAI_API_BASE_URL=http://host.docker.internal:8082/v1
      - OPENAI_API_KEY=sk-dummy
      - DATA_DIR=/app/backend/data
      - DATABASE_URL=postgresql://klimtech:klimtech123@postgres:5432/openwebui
      - QDRANT_URI=http://qdrant:6333
      - RAG_EMBEDDING_MODEL=intfloat/multilingual-e5-large
      - ENABLE_RAG_WEB_SEARCH=true
      - RAG_WEB_SEARCH_ENGINE=duckduckgo
      - ENABLE_SIGNUP=true
      - DEFAULT_LOCALE=pl
    volumes:
      - ./data/openwebui:/app/backend/data
      - ./data/uploads:/app/backend/data/uploads:ro
    depends_on:
      - postgres
      - qdrant
    extra_hosts:
      - "host.docker.internal:host-gateway"

  postgres:
    image: postgres:16
    container_name: openwebui-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=klimtech
      - POSTGRES_PASSWORD=klimtech123
      - POSTGRES_DB=openwebui
    volumes:
      - ./data/postgres_openwebui:/var/lib/postgresql/data
    ports:
      - "5433:5432"

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    restart: unless-stopped
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
EOF

# Uruchomienie
docker-compose -f docker-compose.openwebui.yml up -d
```

**Opcja B: Natywna instalacja (bez Docker)**
```bash
# Klonowanie
cd ~/KlimtechRAG
git clone https://github.com/open-webui/open-webui.git
cd open-webui

# Backend
cd backend
pip install -r requirements.txt

# Frontend (opcjonalnie - dev)
cd ../
npm install
npm run build

# Konfiguracja
cp .env.example .env
```

#### 3.0.3 Konfiguracja zmiennych środowiskowych

```bash
# ~/.bashrc lub ~/.zshrc
cat >> ~/.bashrc << 'EOF'

# Open WebUI Configuration
export OPENAI_API_BASE_URL="http://localhost:8082/v1"
export OPENAI_API_KEY="sk-dummy"
export QDRANT_URI="http://localhost:6333"
export DATABASE_URL="postgresql://klimtech:klimtech123@localhost:5433/openwebui"
export RAG_EMBEDDING_MODEL="intfloat/multilingual-e5-large"
export DATA_DIR="$HOME/KlimtechRAG/data/openwebui"
EOF

source ~/.bashrc
```

---

### FAZA 1: Konfiguracja Open WebUI (2-3h)

#### 3.1.1 Pierwsze uruchomienie

1. Otwórz `http://localhost:8080`
2. Stwórz konto admin (to automatycznie utworzy konto z uprawnieniami admin)
3. Przejdź do **Settings → Admin Settings**

#### 3.1.2 Konfiguracja modelu LLM

**Settings → Connections → OpenAI API:**

| Parametr | Wartość |
|----------|---------|
| API Base URL | `http://localhost:8082/v1` |
| API Key | `sk-dummy` (dowolny) |
| Model | `bielik-11b-v3` (z llama.cpp) |

**Weryfikacja:**
```bash
# Test połączenia z llama.cpp
curl http://localhost:8082/v1/models
# Powinno zwrócić: {"object":"list","data":[{"id":"bielik..."}]}
```

#### 3.1.3 Konfiguracja Qdrant dla RAG

**Settings → Documents → Vector Database:**

| Parametr | Wartość |
|----------|---------|
| Vector Database | `Qdrant` |
| Qdrant URI | `http://localhost:6333` |
| Qdrant API Key | (puste dla lokalnego) |
| Collection Name | `klimtech_docs` (istniejąca) |

#### 3.1.4 Konfiguracja Embeddingu

**Settings → Documents → Embedding:**

| Parametr | Wartość |
|----------|---------|
| Embedding Model | `intfloat/multilingual-e5-large` |
| Embedding Batch Size | `32` |
| Device | `cuda` lub `cpu` |

#### 3.1.5 Konfiguracja RAG

**Settings → Documents → RAG:**

| Parametr | Wartość | Opis |
|----------|---------|------|
| Top K | `10` | Ile dokumentów pobierać |
| Text Splitter | `recursive_character` | Podział tekstu |
| Chunk Size | `1500` | Rozmiar chunka |
| Chunk Overlap | `150` | Nakładanie chunków |

---

### FAZA 2: Migracja danych (2-4h)

#### 3.2.1 Migracja istniejących dokumentów

**Skrypt migracji:**
```python
# ~/KlimtechRAG/scripts/migrate_to_openwebui.py
"""
Migracja dokumentów z klimtech_docs (Qdrant) do Open WebUI.

Open WebUI używa własnych kolekcji Qdrant:
- Każdy dokument ma collection_id w Postgres
- Chunki są w Qdrant z metadata
"""

import requests
import os
from pathlib import Path

QDRANT_URL = "http://localhost:6333"
OPENWEBUI_URL = "http://localhost:8080"
OPENWEBUI_TOKEN = "YOUR_API_KEY"  # Z Settings → Account → API Keys

def get_existing_documents():
    """Pobierz dokumenty z klimtech_docs"""
    response = requests.post(
        f"{QDRANT_URL}/collections/klimtech_docs/points/scroll",
        json={"limit": 1000, "with_payload": True}
    )
    return response.json()["result"]["points"]

def upload_to_openwebui(file_path: str, collection_name: str = None):
    """Upload pliku do Open WebUI"""
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {}
        if collection_name:
            data["collection_name"] = collection_name
        
        response = requests.post(
            f"{OPENWEBUI_URL}/api/v1/documents/",
            headers={"Authorization": f"Bearer {OPENWEBUI_TOKEN}"},
            files=files,
            data=data
        )
    return response.json()

def main():
    # 1. Pobierz listę plików
    uploads_dir = Path.home() / "KlimtechRAG" / "data" / "uploads"
    
    # 2. Znajdź wszystkie pliki
    files = []
    for ext in ["*.pdf", "*.txt", "*.md", "*.json"]:
        files.extend(uploads_dir.rglob(ext))
    
    print(f"Znaleziono {len(files)} plików")
    
    # 3. Upload do Open WebUI
    for file_path in files:
        print(f"Upload: {file_path.name}")
        try:
            result = upload_to_openwebui(str(file_path))
            print(f"  ✓ {result.get('id', 'OK')}")
        except Exception as e:
            print(f"  ✗ {e}")

if __name__ == "__main__":
    main()
```

#### 3.2.2 Migracja przez API (alternatywa)

```bash
# Bezpośredni import do Open WebUI
for file in ~/KlimtechRAG/data/uploads/pdf_RAG/*.pdf; do
    curl -X POST "http://localhost:8080/api/v1/documents/" \
        -H "Authorization: Bearer YOUR_API_KEY" \
        -F "file=@$file" \
        -F "collection_name=Migrated Documents"
done
```

#### 3.2.3 Weryfikacja migracji

```bash
# Sprawdź dokumenty w Open WebUI
curl -s "http://localhost:8080/api/v1/documents/" \
    -H "Authorization: Bearer YOUR_API_KEY" | jq '.[] | {id, filename}'

# Sprawdź punkty w Qdrant
curl -s "http://localhost:6333/collections" | jq '.result.collections[]'
```

---

### FAZA 3: Konfiguracja MCP Server (3-4h)

#### 3.3.1 Stworzenie MCP Server dla KlimtechRAG

```python
# ~/KlimtechRAG/mcp_server/klimtech_mcp.py
"""
MCP Server wystawiający funkcje RAG dla klientów MCP.
Umożliwia integrację z Claude Desktop, Open WebUI i innymi.
"""

from mcp.server.fastmcp import FastMCP, Context
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import os

# Konfiguracja
QDRANT_URL = os.getenv("QDRANT_URI", "http://localhost:6333")
COLLECTION_NAME = "klimtech_docs"
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

# Inicjalizacja
mcp = FastMCP("KlimtechRAG")
qdrant = QdrantClient(url=QDRANT_URL)
embedder = SentenceTransformer(EMBEDDING_MODEL)

# === NARZĘDZIA ===

@mcp.tool()
def search_documents(query: str, top_k: int = 5) -> list[dict]:
    """
    Wyszukaj dokumenty w bazie wiedzy Klimtech.
    
    Args:
        query: Zapytanie tekstowe
        top_k: Ilość wyników (domyślnie 5)
    
    Returns:
        Lista dokumentów z treścią i metadanymi
    """
    # Generuj embedding
    embedding = embedder.encode(query).tolist()
    
    # Szukaj w Qdrant
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=top_k
    )
    
    return [
        {
            "content": hit.payload.get("content", "")[:500],
            "source": hit.payload.get("source", "unknown"),
            "score": hit.score,
            "id": str(hit.id)
        }
        for hit in results
    ]

@mcp.tool()
def get_document(doc_id: str) -> dict:
    """
    Pobierz pełny dokument po ID.
    
    Args:
        doc_id: UUID dokumentu w Qdrant
    
    Returns:
        Pełna treść dokumentu z metadanymi
    """
    from uuid import UUID
    
    result = qdrant.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[UUID(doc_id)]
    )
    
    if not result:
        return {"error": "Document not found"}
    
    point = result[0]
    return {
        "id": str(point.id),
        "content": point.payload.get("content", ""),
        "source": point.payload.get("source"),
        "metadata": point.payload
    }

@mcp.tool()
def list_collections() -> list[str]:
    """
    Lista dostępnych kolekcji w Qdrant.
    """
    collections = qdrant.get_collections()
    return [c.name for c in collections.collections]

@mcp.tool()
def get_collection_stats(collection_name: str = COLLECTION_NAME) -> dict:
    """
    Statystyki kolekcji (ilość dokumentów, rozmiar).
    
    Args:
        collection_name: Nazwa kolekcji (domyślnie klimtech_docs)
    """
    info = qdrant.get_collection(collection_name)
    return {
        "points_count": info.points_count,
        "indexed_vectors": info.indexed_vectors_count,
        "status": info.status.value
    }

@mcp.tool()
def ingest_document(file_path: str) -> dict:
    """
    Zindeksuj dokument do bazy wiedzy.
    
    Args:
        file_path: Ścieżka do pliku
    
    Returns:
        Status indeksowania
    """
    # Implementacja podobna do obecnej z ingest.py
    # ...
    pass

# === ZASOBY ===

@mcp.resource("qdrant://{collection}")
def list_collection_documents(collection: str) -> str:
    """Lista dokumentów w kolekcji"""
    results = qdrant.scroll(
        collection_name=collection,
        limit=100,
        with_payload=False
    )
    return "\n".join([str(p.id) for p in results[0]])

@mcp.resource("doc://{doc_id}")
def get_document_resource(doc_id: str) -> str:
    """Pełna treść dokumentu"""
    doc = get_document(doc_id)
    return doc.get("content", "Not found")

# === PROMPTY ===

@mcp.prompt()
def summarize_document(doc_id: str) -> str:
    """Stwórz prompt do streszczenia dokumentu"""
    doc = get_document(doc_id)
    return f"""Podsumuj poniższy dokument w 3-5 punktach:

Źródło: {doc.get('source', 'nieznane')}

Treść:
{doc.get('content', '')[:3000]}

Streszczenie:"""

@mcp.prompt()
def compare_documents(doc_id_1: str, doc_id_2: str) -> str:
    """Porównaj dwa dokumenty"""
    doc1 = get_document(doc_id_1)
    doc2 = get_document(doc_id_2)
    
    return f"""Porównaj poniższe dwa dokumenty:

DOKUMENT 1 ({doc1.get('source')}):
{doc1.get('content', '')[:1500]}

DOKUMENT 2 ({doc2.get('source')}):
{doc2.get('content', '')[:1500]}

Podobieństwa i różnice:"""

# Uruchomienie
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

#### 3.3.2 Konfiguracja MCP w Open WebUI

Open WebUI wspiera MCP od wersji 0.3.x:

**Settings → Tools → MCP Servers:**

```json
{
  "klimtech-rag": {
    "url": "http://localhost:8001/mcp",
    "transport": "streamable-http"
  }
}
```

#### 3.3.3 Uruchomienie MCP Server

```bash
# Instalacja MCP SDK
pip install mcp[cli]

# Uruchomienie
cd ~/KlimtechRAG/mcp_server
python klimtech_mcp.py
# Serwer na http://localhost:8001/mcp

# Lub jako usługa systemd
cat > /etc/systemd/system/klimtech-mcp.service << 'EOF'
[Unit]
Description=KlimtechRAG MCP Server
After=network.target

[Service]
Type=simple
User=lobo
WorkingDirectory=/home/lobo/KlimtechRAG/mcp_server
ExecStart=/home/lobo/KlimtechRAG/venv/bin/python klimtech_mcp.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable klimtech-mcp
sudo systemctl start klimtech-mcp
```

---

### FAZA 4: Integracja z Nextcloud (2h)

#### 3.4.1 Adaptacja watchdog

```python
# ~/KlimtechRAG/scripts/watch_nextcloud_openwebui.py
"""
Watchdog monitorujący Nextcloud i wysyłający pliki do Open WebUI API.
"""

import os
import time
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

OPENWEBUI_URL = "http://localhost:8080"
OPENWEBUI_TOKEN = os.getenv("OPENWEBUI_API_KEY")
WATCH_DIRS = [
    "/home/lobo/KlimtechRAG/data/nextcloud/lobo/files/RAG_Dane",
    "/home/lobo/KlimtechRAG/data/uploads"
]

class OpenWebUIHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        print(f"[NEW] {file_path}")
        
        # Upload do Open WebUI
        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    f"{OPENWEBUI_URL}/api/v1/documents/",
                    headers={"Authorization": f"Bearer {OPENWEBUI_TOKEN}"},
                    files={"file": f}
                )
            result = response.json()
            print(f"  → Uploaded: {result.get('id', 'error')}")
        except Exception as e:
            print(f"  → Error: {e}")

def main():
    observer = Observer()
    handler = OpenWebUIHandler()
    
    for path in WATCH_DIRS:
        if os.path.exists(path):
            observer.schedule(handler, path, recursive=True)
            print(f"Watching: {path}")
    
    observer.start()
    print("Watchdog running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    main()
```

---

### FAZA 5: Konfiguracja zaawansowana (opcjonalnie)

#### 3.5.1 Web Search (SearXNG)

```yaml
# docker-compose.searxng.yml
version: '3.8'

services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    ports:
      - "8888:8080"
    environment:
      - BASE_URL=http://localhost:8888/
    volumes:
      - ./data/searxng:/etc/searxng
```

**Open WebUI Settings:**
- RAG_WEB_SEARCH_ENGINE: `searxng`
- SEARXNG_URL: `http://localhost:8888`

#### 3.5.2 TTS/STT lokalne

Open WebUI wspiera lokalne TTS/STT:

**Settings → Audio:**
- Speech-to-Text Engine: `faster-whisper` lub `whisper.cpp`
- Text-to-Speech Engine: `coqui-tts` lub `piper`

```bash
# Instalacja faster-whisper
pip install faster-whisper

# Model do ~/.cache/huggingface/hub/
```

#### 3.5.3 Pipeline'y przetwarzania dokumentów

**Custom ingestion pipeline w Open WebUI:**

Open WebUI pozwala na definiowanie własnych pipeline'ów przez API:

```python
# Przykład: dodanie OCR dla skanów
import requests

def process_pdf_with_ocr(pdf_path):
    # Użyj istniejących skryptów
    # ...
    
    # Wyślij do Open WebUI
    with open(processed_text_path, "r") as f:
        text = f.read()
    
    # Utwórz dokument z tekstem
    response = requests.post(
        "http://localhost:8080/api/v1/documents/create",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "name": pdf_path.stem,
            "content": text,
            "collection_name": "OCR Documents"
        }
    )
    return response.json()
```

---

## 4. Komendy operacyjne

### 4.1 Codzienne

```bash
# Start usług
docker-compose -f docker-compose.openwebui.yml up -d

# Status
docker-compose -f docker-compose.openwebui.yml ps

# Logi
docker-compose -f docker-compose.openwebui.yml logs -f open-webui

# Backup bazy
docker exec openwebui-postgres pg_dump -U klimtech openwebui > backup_$(date +%Y%m%d).sql

# Stop
docker-compose -f docker-compose.openwebui.yml down
```

### 4.2 Diagnostyka

```bash
# Sprawdź połączenie z LLM
curl -X POST http://localhost:8082/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "bielik", "messages": [{"role": "user", "content": "test"}]}'

# Sprawdź Qdrant
curl http://localhost:6333/collections/klimtech_docs

# Sprawdź dokumenty w Open WebUI
curl -s http://localhost:8080/api/v1/documents/ \
  -H "Authorization: Bearer $OPENWEBUI_API_KEY" | jq length
```

### 4.3 Zarządzanie użytkownikami

```bash
# Lista użytkowników (jako admin)
curl -s http://localhost:8080/api/v1/users/ \
  -H "Authorization: Bearer $ADMIN_API_KEY" | jq

# Zmiana roli użytkownika
curl -X PATCH http://localhost:8080/api/v1/users/{user_id}/role \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

---

## 5. Struktura katalogów po migracji

```
~/KlimtechRAG/
├── docker-compose.openwebui.yml    # Główny plik compose
├── .env                            # Zmienne środowiskowe
│
├── mcp_server/                     # NOWY: MCP Server
│   ├── klimtech_mcp.py
│   └── requirements.txt
│
├── scripts/                        # Skrypty pomocnicze
│   ├── migrate_to_openwebui.py
│   ├── watch_nextcloud_openwebui.py
│   ├── ingest_pdfCPU.py            # Zachowane
│   └── ingest_pdfGPU.py            # Zachowane
│
├── data/
│   ├── qdrant/                     # Baza wektorowa
│   ├── postgres_openwebui/         # NOWY: Baza Open WebUI
│   ├── openwebui/                  # NOWY: Dane Open WebUI
│   ├── uploads/                    # Dokumenty (zachowane)
│   └── nextcloud/                  # Nextcloud (zachowane)
│
├── llama.cpp/                      # llama.cpp binaries
│
├── models/                         # Modele GGUF
│   └── Bielik-11B-v3.0-Instruct.Q5_K_M.gguf
│
└── logs/                           # Logi (zachowane)

# USUNIĘTE:
# ├── backend_app/ (cały katalog)
# ├── start_klimtech.py (zastąpione przez docker-compose)
# └── stop_klimtech.py
```

---

## 6. Harmonogram

| Tydzień | Faza | Zadania | Czas |
|---------|------|---------|------|
| 1 | Faza 0 + 1 | Instalacja, konfiguracja podstawowa | 4-5h |
| 2 | Faza 2 | Migracja dokumentów | 2-4h |
| 3 | Faza 3 | MCP Server | 3-4h |
| 4 | Faza 4 | Nextcloud integration | 2h |
| 5+ | Faza 5 | Zaawansowane funkcje | opcjonalnie |

**Całkowity czas: 11-19 godzin** (zamiast niekończących się napraw)

---

## 7. Ryzyka i mitigacja

| Ryzyko | Prawdopodobieństwo | Mitigacja |
|--------|-------------------|-----------|
| Open WebUI nie wspiera modelu | Niskie | llama.cpp jest kompatybilny z OpenAI API |
| Problemy z embedding GPU | Średnie | Fallback na CPU, modyfikacja kodu Open WebUI |
| Migracja utraci metadane | Średnie | Przeniesienie przez API z zachowaniem source |
| MCP nie działa z Open WebUI | Niskie | Alternatywnie: bezpośrednie API |
| Docker konflikty portów | Niskie | Zmiana portów w compose |

---

## 8. Zasoby

### Dokumentacja
- Open WebUI Docs: https://docs.openwebui.com/
- MCP Specification: https://modelcontextprotocol.io/
- Qdrant Docs: https://qdrant.tech/documentation/

### Repozytoria
- Open WebUI: https://github.com/open-webui/open-webui
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Qdrant: https://github.com/qdrant/qdrant

### Konfiguracja RAG w Open WebUI
- https://docs.openwebui.com/tutorials/tips/rag-tutorial/
- https://github.com/open-webui/open-webui/discussions/11597

---

## 9. Decyzja

**Rekomendacja: PRZEJŚCIE NA OPEN WEBUI**

Powody:
1. **Oszczędność czasu** - gotowe rozwiązanie zamiast ciągłych napraw
2. **Lepsze UI/UX** - profesjonalny interfejs z motywami
3. **Community** - aktywna społeczność, regularne aktualizacje
4. **MCP natywne** - przyszłościowa integracja
5. **Multimodal** - pełne wsparcie dla różnych typów danych
6. **Skalowalność** - gotowe do produkcji

**Następny krok:** Zatwierdź plan i rozpocznij od Fazy 0.

---

*Plan wygenerowany: 2026-02-22*
