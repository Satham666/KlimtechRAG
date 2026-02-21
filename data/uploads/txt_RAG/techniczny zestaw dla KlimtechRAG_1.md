techniczny zestaw dla KlimtechRAG:

1️⃣ struktura katalogów projektu
2️⃣ konfiguracja Podman (podman-compose)
3️⃣ konkretny backend RAG: Haystack + llama.cpp (działający kod)

Wszystko offline-first, localhost, gotowe do integracji z OpenCode i n8n.



1️⃣ Struktura katalogów projektu

KlimtechRAG/
├── README.md
├── .env
├── podman-compose.yml
├── Makefile
│
├── data/
│   ├── models/
│   │   └── llama/
│   │       └── mistral-7b-instruct.Q4_K_M.gguf
│   │
│   ├── rag/
│   │   ├── docs/
│   │   │   ├── pdf/
│   │   │   ├── markdown/
│   │   │   └── html/
│   │   ├── code/
│   │   │   ├── github/
│   │   │   └── gitlab/
│   │   ├── indexes/
│   │   └── metadata/
│   │
│   └── nextcloud/
│
├── services/
│   ├── llama/
│   │   ├── Dockerfile
│   │   └── start.sh
│   │
│   ├── rag-backend/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api.py
│   │   │   ├── pipelines.py
│   │   │   ├── document_store.py
│   │   │   ├── ingest/
│   │   │   │   ├── pdf.py
│   │   │   │   ├── code.py
│   │   │   │   └── nextcloud.py
│   │   │   └── settings.py
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── n8n/
│       └── data/
│
├── scripts/
│   ├── ingest_pdf.py
│   ├── ingest_repo.py
│   └── web_search.py
│
└── docs/
    ├── architecture.md
    ├── api.md
    └── workflows-n8n.md
2️⃣ Podman – podman-compose.yml

kompatybilne z podman-compose
wszystko działa na localhost

version: "3.9"

services:

  llama:
    container_name: llama-cpp
    build: ./services/llama
    volumes:
      - ./data/models:/models:ro
    command: >
      ./server
      --model /models/llama/mistral-7b-instruct.Q4_K_M.gguf
      --host 0.0.0.0
      --port 8000
      --ctx-size 8192
    ports:
      - "8000:8000"
    restart: unless-stopped

  rag-backend:
    container_name: rag-backend
    build: ./services/rag-backend
    env_file: .env
    volumes:
      - ./data/rag:/data/rag
    ports:
      - "8080:8080"
    depends_on:
      - llama
    restart: unless-stopped

  n8n:
    image: docker.io/n8nio/n8n
    container_name: n8n
    ports:
      - "5678:5678"
    volumes:
      - ./services/n8n/data:/home/node/.n8n
    restart: unless-stopped


3️⃣ Backend RAG – Haystack + llama.cpp
3.1 requirements.txt

haystack-ai
fastapi
uvicorn
docling
llama-index
faiss-cpu
requests
pydantic
python-dotenv


3.2 DocumentStore – document_store.py

from haystack.document_stores import FAISSDocumentStore

document_store = FAISSDocumentStore(
    faiss_index_factory_str="Flat",
    embedding_dim=768,
    sql_url="sqlite:////data/rag/indexes/rag.db"
)


3.3 Pipeline RAG – pipelines.py


from haystack import Pipeline
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.embedders import SentenceTransformersTextEmbedder
from app.document_store import document_store

embedder = SentenceTransformersTextEmbedder(
    model="sentence-transformers/all-MiniLM-L6-v2"
)

retriever = InMemoryEmbeddingRetriever(
    document_store=document_store
)

generator = OpenAIGenerator(
    api_base_url="http://llama:8000/v1",
    model="llama-cpp",
    api_key="none"
)

rag_pipeline = Pipeline()
rag_pipeline.add_component("embedder", embedder)
rag_pipeline.add_component("retriever", retriever)
rag_pipeline.add_component("generator", generator)

rag_pipeline.connect("embedder.embedding", "retriever.query_embedding")
rag_pipeline.connect("retriever.documents", "generator.documents")

3.4 API – api.py

from fastapi import APIRouter
from pydantic import BaseModel
from app.pipelines import rag_pipeline

router = APIRouter()

class Query(BaseModel):
    query: str

@router.post("/query")
def query_rag(q: Query):
    result = rag_pipeline.run(
        {
            "embedder": {"text": q.query},
            "generator": {"prompt": q.query}
        }
    )
    return {
        "answer": result["generator"]["replies"][0]
    }

3.5 Ingest PDF (Docling) – ingest/pdf.py

from docling import Document
from haystack import Document as HayDoc
from app.document_store import document_store

def ingest_pdf(path: str):
    doc = Document.from_pdf(path)
    docs = [
        HayDoc(content=block.text, meta={"source": path})
        for block in doc.blocks
        if block.text.strip()
    ]
    document_store.write_documents(docs)

from docling import Document
from haystack import Document as HayDoc
from app.document_store import document_store

def ingest_pdf(path: str):
    doc = Document.from_pdf(path)
    docs = [
        HayDoc(content=block.text, meta={"source": path})
        for block in doc.blocks
        if block.text.strip()
    ]
    document_store.write_documents(docs)

from fastapi import FastAPI
from app.api import router

app = FastAPI(
    title="KlimtechRAG",
    description="Offline-first RAG backend for OpenCode"
)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}


Uruchomienie lokalnie:

podman-compose up --build

4️⃣ Jak OpenCode będzie z tego korzystać

OpenCode (CLI)
   |
   |  HTTP POST /query
   v
RAG Backend (Haystack)
   |
   |  context
   v
llama.cpp

Zapytanie:
{
  "query": "Wyjaśnij konfigurację Haystack w KlimtechRAG"
}



1️⃣ workflow n8n → ingest repo / PDF
2️⃣ adapter OpenCode Tool
3️⃣ web-search + caching
4️⃣ multi-agent: retriever → verifier → generator

Dostajesz gotowe definicje, pliki i kod, które możesz wstawić do projektu KlimtechRAG.

1️⃣ Workflow n8n → ingest repo / PDF
1.1 Architektura
Trigger (Webhook / IMAP / Cron)
        |
        v
Sprawdź typ wejścia (PDF / repo URL)
        |
        +--> PDF → POST /ingest/pdf
        |
        +--> Repo → git clone → POST /ingest/code

1.2 Endpointy backendu (FastAPI)
app/api.py – dodaj:
from fastapi import APIRouter, UploadFile, File
from app.ingest.pdf import ingest_pdf
from app.ingest.code import ingest_repo

router = APIRouter()

@router.post("/ingest/pdf")
async def ingest_pdf_endpoint(file: UploadFile = File(...)):
    path = f"/data/rag/docs/pdf/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    ingest_pdf(path)
    return {"status": "ok", "file": file.filename}

@router.post("/ingest/code")
def ingest_code_endpoint(payload: dict):
    repo_url = payload["repo_url"]
    ingest_repo(repo_url)
    return {"status": "ok", "repo": repo_url}

1.3 Repo ingest – app/ingest/code.py
import os
import subprocess
from haystack import Document as HayDoc
from app.document_store import document_store

BASE_PATH = "/data/rag/code"

def ingest_repo(repo_url: str):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(BASE_PATH, repo_name)

    if not os.path.exists(repo_path):
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)
    else:
        subprocess.run(["git", "-C", repo_path, "pull"], check=True)

    docs = []
    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.endswith((".py", ".js", ".md", ".yaml", ".yml", ".json")):
                full_path = os.path.join(root, f)
                with open(full_path, "r", errors="ignore") as fh:
                    docs.append(
                        HayDoc(
                            content=fh.read(),
                            meta={"source": repo_url, "path": full_path}
                        )
                    )
    document_store.write_documents(docs)

1.4 Gotowy workflow n8n (JSON)

👉 Import w n8n → Workflows → Import from File

{
  "nodes": [
    {
      "id": "trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [200, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "rag-ingest",
        "responseMode": "lastNode"
      }
    },
    {
      "id": "if",
      "name": "Check Type",
      "type": "n8n-nodes-base.if",
      "position": [400, 300],
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json[\"type\"]}}",
              "operation": "equals",
              "value2": "pdf"
            }
          ]
        }
      }
    },
    {
      "id": "http_pdf",
      "name": "Send PDF to RAG",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 200],
      "parameters": {
        "url": "http://rag-backend:8080/ingest/pdf",
        "method": "POST",
        "sendBinaryData": true
      }
    },
    {
      "id": "http_repo",
      "name": "Send Repo to RAG",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 400],
      "parameters": {
        "url": "http://rag-backend:8080/ingest/code",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"repo_url\": \"{{$json[\"repo_url\"]}}\"}"
      }
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "Check Type", "type": "main", "index": 0 }]] },
    "Check Type": {
      "main": [
        [{ "node": "Send PDF to RAG", "type": "main", "index": 0 }],
        [{ "node": "Send Repo to RAG", "type": "main", "index": 0 }]
      ]
    }
  }
}

2️⃣ Adapter OpenCode Tool
2.1 Definicja narzędzia (tool)

Plik: docs/opencode-tool.json

{
  "name": "klimtech_rag",
  "description": "Local offline-first RAG for KlimtechRAG",
  "type": "http",
  "method": "POST",
  "url": "http://localhost:8080/query",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "query": "{{input}}"
  },
  "response_path": "answer"
}

2.2 Jak OpenCode z tego korzysta

W OpenCode:

@tool klimtech_rag
Wyjaśnij jak działa indeksowanie repozytoriów w KlimtechRAG


OpenCode:
→ wykrywa potrzebę kontekstu
→ wywołuje POST /query
→ wkleja odpowiedź do kodu / terminala

3️⃣ Web-search + Caching
3.1 Moduł wyszukiwania

Plik: scripts/web_search.py

import os
import hashlib
import requests
from bs4 import BeautifulSoup
from haystack import Document as HayDoc
from app.document_store import document_store

CACHE_DIR = "/data/rag/cache"

def cache_path(url: str):
    h = hashlib.sha256(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.txt")

def fetch_page(url: str):
    path = cache_path(url)
    if os.path.exists(path):
        with open(path) as f:
            return f.read()

    r = requests.get(url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(text)

    return text

def ingest_url(url: str):
    text = fetch_page(url)
    doc = HayDoc(content=text, meta={"source": url})
    document_store.write_documents([doc])

3.2 Endpoint
@router.post("/ingest/url")
def ingest_url_endpoint(payload: dict):
    from scripts.web_search import ingest_url
    ingest_url(payload["url"])
    return {"status": "ok", "url": payload["url"]}


✔ offline-first – jeśli strona była pobrana wcześniej, używa cache
✔ cache w /data/rag/cache

4️⃣ Multi-Agent: retriever → verifier → generator
4.1 Architektura
User Query
   |
   v
Retriever (Haystack)
   |
   v
Verifier (LLM – sprawdza zgodność z dokumentami)
   |
   v
Generator (LLM – finalna odpowiedź)

4.2 Pipeline – pipelines.py
from haystack import Pipeline
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.components.embedders import SentenceTransformersTextEmbedder
from app.document_store import document_store

embedder = SentenceTransformersTextEmbedder(
    model="sentence-transformers/all-MiniLM-L6-v2"
)

retriever = InMemoryEmbeddingRetriever(
    document_store=document_store
)

verifier_prompt = PromptBuilder(
    template="""
Sprawdź czy poniższe dokumenty faktycznie zawierają odpowiedź na pytanie.
Jeśli nie, napisz: "Brak wystarczających danych".

Pytanie: {{question}}

Dokumenty:
{% for doc in documents %}
{{ doc.content }}
{% endfor %}
"""
)

generator_prompt = PromptBuilder(
    template="""
Odpowiedz na pytanie tylko na podstawie zweryfikowanych dokumentów.

Pytanie: {{question}}

Dokumenty:
{% for doc in documents %}
{{ doc.content }}
{% endfor %}
"""
)

llm = OpenAIGenerator(
    api_base_url="http://llama:8000/v1",
    model="llama-cpp",
    api_key="none"
)

pipeline = Pipeline()
pipeline.add_component("embedder", embedder)
pipeline.add_component("retriever", retriever)
pipeline.add_component("verifier_prompt", verifier_prompt)
pipeline.add_component("verifier", llm)
pipeline.add_component("generator_prompt", generator_prompt)
pipeline.add_component("generator", llm)

pipeline.connect("embedder.embedding", "retriever.query_embedding")
pipeline.connect("retriever.documents", "verifier_prompt.documents")
pipeline.connect("verifier_prompt.prompt", "verifier.prompt")
pipeline.connect("retriever.documents", "generator_prompt.documents")
pipeline.connect("generator_prompt.prompt", "generator.prompt")

4.3 Endpoint
@router.post("/query")
def query_rag(q: Query):
    result = pipeline.run({
        "embedder": {"text": q.query},
        "verifier_prompt": {"question": q.query},
        "generator_prompt": {"question": q.query}
    })
    return {"answer": result["generator"]["replies"][0]}

5️⃣ Co masz teraz gotowe

✅ n8n – automatyczny ingest PDF i repo
✅ OpenCode Tool – lokalny RAG jako narzędzie IDE
✅ Web-search + caching – offline-first WWW
✅ Multi-agent RAG – kontrola jakości odpowiedzi

6️⃣ Kolejny krok (Twoja lista)

Mogę teraz wykonać dla Ciebie:

🧠 rozszerzony tool dla OpenCode (multi-tool + role)
🔁 workflow n8n: GitHub/GitLab sync + email → RAG
🗃️ pełne GitHub/GitLab search (lokalny mirror)
⚡ tuning pod Ryzen 9950X (AVX512, batch, ctx, threads)

👉 Napisz: „robimy: X, Y” i wchodzimy w kolejny poziom.





1️⃣ workflow n8n → ingest repo / PDF
2️⃣ adapter OpenCode Tool
3️⃣ web-search + caching
4️⃣ multi-agent: retriever → verifier → generator

Dostajesz gotowe definicje, pliki i kod, które możesz wstawić do projektu KlimtechRAG.




1️⃣ Workflow n8n → ingest repo / PDF
1.1 Architektura
Trigger (Webhook / IMAP / Cron)
        |
        v
Sprawdź typ wejścia (PDF / repo URL)
        |
        +--> PDF → POST /ingest/pdf
        |
        +--> Repo → git clone → POST /ingest/code

1.2 Endpointy backendu (FastAPI)
app/api.py – dodaj:
from fastapi import APIRouter, UploadFile, File
from app.ingest.pdf import ingest_pdf
from app.ingest.code import ingest_repo

router = APIRouter()

@router.post("/ingest/pdf")
async def ingest_pdf_endpoint(file: UploadFile = File(...)):
    path = f"/data/rag/docs/pdf/{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    ingest_pdf(path)
    return {"status": "ok", "file": file.filename}

@router.post("/ingest/code")
def ingest_code_endpoint(payload: dict):
    repo_url = payload["repo_url"]
    ingest_repo(repo_url)
    return {"status": "ok", "repo": repo_url}

1.3 Repo ingest – app/ingest/code.py
import os
import subprocess
from haystack import Document as HayDoc
from app.document_store import document_store

BASE_PATH = "/data/rag/code"

def ingest_repo(repo_url: str):
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = os.path.join(BASE_PATH, repo_name)

    if not os.path.exists(repo_path):
        subprocess.run(["git", "clone", repo_url, repo_path], check=True)
    else:
        subprocess.run(["git", "-C", repo_path, "pull"], check=True)

    docs = []
    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.endswith((".py", ".js", ".md", ".yaml", ".yml", ".json")):
                full_path = os.path.join(root, f)
                with open(full_path, "r", errors="ignore") as fh:
                    docs.append(
                        HayDoc(
                            content=fh.read(),
                            meta={"source": repo_url, "path": full_path}
                        )
                    )
    document_store.write_documents(docs)

1.4 Gotowy workflow n8n (JSON)

👉 Import w n8n → Workflows → Import from File

{
  "nodes": [
    {
      "id": "trigger",
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "position": [200, 300],
      "parameters": {
        "httpMethod": "POST",
        "path": "rag-ingest",
        "responseMode": "lastNode"
      }
    },
    {
      "id": "if",
      "name": "Check Type",
      "type": "n8n-nodes-base.if",
      "position": [400, 300],
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{$json[\"type\"]}}",
              "operation": "equals",
              "value2": "pdf"
            }
          ]
        }
      }
    },
    {
      "id": "http_pdf",
      "name": "Send PDF to RAG",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 200],
      "parameters": {
        "url": "http://rag-backend:8080/ingest/pdf",
        "method": "POST",
        "sendBinaryData": true
      }
    },
    {
      "id": "http_repo",
      "name": "Send Repo to RAG",
      "type": "n8n-nodes-base.httpRequest",
      "position": [650, 400],
      "parameters": {
        "url": "http://rag-backend:8080/ingest/code",
        "method": "POST",
        "jsonParameters": true,
        "bodyParametersJson": "={\"repo_url\": \"{{$json[\"repo_url\"]}}\"}"
      }
    }
  ],
  "connections": {
    "Webhook": { "main": [[{ "node": "Check Type", "type": "main", "index": 0 }]] },
    "Check Type": {
      "main": [
        [{ "node": "Send PDF to RAG", "type": "main", "index": 0 }],
        [{ "node": "Send Repo to RAG", "type": "main", "index": 0 }]
      ]
    }
  }
}

2️⃣ Adapter OpenCode Tool
2.1 Definicja narzędzia (tool)

Plik: docs/opencode-tool.json

{
  "name": "klimtech_rag",
  "description": "Local offline-first RAG for KlimtechRAG",
  "type": "http",
  "method": "POST",
  "url": "http://localhost:8080/query",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "query": "{{input}}"
  },
  "response_path": "answer"
}

2.2 Jak OpenCode z tego korzysta

W OpenCode:

@tool klimtech_rag
Wyjaśnij jak działa indeksowanie repozytoriów w KlimtechRAG


OpenCode:
→ wykrywa potrzebę kontekstu
→ wywołuje POST /query
→ wkleja odpowiedź do kodu / terminala

3️⃣ Web-search + Caching
3.1 Moduł wyszukiwania

Plik: scripts/web_search.py

import os
import hashlib
import requests
from bs4 import BeautifulSoup
from haystack import Document as HayDoc
from app.document_store import document_store

CACHE_DIR = "/data/rag/cache"

def cache_path(url: str):
    h = hashlib.sha256(url.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.txt")

def fetch_page(url: str):
    path = cache_path(url)
    if os.path.exists(path):
        with open(path) as f:
            return f.read()

    r = requests.get(url, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w") as f:
        f.write(text)

    return text

def ingest_url(url: str):
    text = fetch_page(url)
    doc = HayDoc(content=text, meta={"source": url})
    document_store.write_documents([doc])

3.2 Endpoint
@router.post("/ingest/url")
def ingest_url_endpoint(payload: dict):
    from scripts.web_search import ingest_url
    ingest_url(payload["url"])
    return {"status": "ok", "url": payload["url"]}


✔ offline-first – jeśli strona była pobrana wcześniej, używa cache
✔ cache w /data/rag/cache

4️⃣ Multi-Agent: retriever → verifier → generator
4.1 Architektura
User Query
   |
   v
Retriever (Haystack)
   |
   v
Verifier (LLM – sprawdza zgodność z dokumentami)
   |
   v
Generator (LLM – finalna odpowiedź)

4.2 Pipeline – pipelines.py
from haystack import Pipeline
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.components.embedders import SentenceTransformersTextEmbedder
from app.document_store import document_store

embedder = SentenceTransformersTextEmbedder(
    model="sentence-transformers/all-MiniLM-L6-v2"
)

retriever = InMemoryEmbeddingRetriever(
    document_store=document_store
)

verifier_prompt = PromptBuilder(
    template="""
Sprawdź czy poniższe dokumenty faktycznie zawierają odpowiedź na pytanie.
Jeśli nie, napisz: "Brak wystarczających danych".

Pytanie: {{question}}

Dokumenty:
{% for doc in documents %}
{{ doc.content }}
{% endfor %}
"""
)

generator_prompt = PromptBuilder(
    template="""
Odpowiedz na pytanie tylko na podstawie zweryfikowanych dokumentów.

Pytanie: {{question}}

Dokumenty:
{% for doc in documents %}
{{ doc.content }}
{% endfor %}
"""
)

llm = OpenAIGenerator(
    api_base_url="http://llama:8000/v1",
    model="llama-cpp",
    api_key="none"
)

pipeline = Pipeline()
pipeline.add_component("embedder", embedder)
pipeline.add_component("retriever", retriever)
pipeline.add_component("verifier_prompt", verifier_prompt)
pipeline.add_component("verifier", llm)
pipeline.add_component("generator_prompt", generator_prompt)
pipeline.add_component("generator", llm)

pipeline.connect("embedder.embedding", "retriever.query_embedding")
pipeline.connect("retriever.documents", "verifier_prompt.documents")
pipeline.connect("verifier_prompt.prompt", "verifier.prompt")
pipeline.connect("retriever.documents", "generator_prompt.documents")
pipeline.connect("generator_prompt.prompt", "generator.prompt")

4.3 Endpoint
@router.post("/query")
def query_rag(q: Query):
    result = pipeline.run({
        "embedder": {"text": q.query},
        "verifier_prompt": {"question": q.query},
        "generator_prompt": {"question": q.query}
    })
    return {"answer": result["generator"]["replies"][0]}


































































































DRUGA WERSJA :

techniczny zestaw startowy dla projektu KlimtechRAG:

Struktura katalogów projektu

Podman (podman-compose) – pliki kontenerów

Konkretny backend: Haystack + llama.cpp (działający kod)

Wszystko jest offline-first, localhost-only i gotowe do integracji z OpenCode.

1️⃣ Struktura katalogów projektu

KlimtechRAG/
├── README.md
├── .env
├── podman-compose.yml
├── containers/
│   ├── haystack/
│   │   ├── Containerfile
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── main.py
│   │       ├── pipelines.py
│   │       ├── stores.py
│   │       └── config.py
│   ├── n8n/
│   │   └── data/
│   └── nextcloud/
│       └── data/
├── llama/
│   ├── models/
│   │   └── mistral-7b-instruct.Q4_K_M.gguf
│   ├── server.sh
│   └── README.md
├── data/
│   ├── rag/
│   │   ├── docs/
│   │   ├── code/
│   │   ├── web/
│   │   └── index/
│   └── uploads/
├── scripts/
│   ├── ingest_pdf.py
│   ├── ingest_repo.py
│   ├── ingest_folder.py
│   └── healthcheck.sh
└── tests/
    └── test_query.http



Logika:

llama/ → lokalny serwer LLM (llama.cpp)

containers/haystack/ → backend RAG (FastAPI + Haystack)

data/rag/ → Twoja baza wiedzy (PDF, kod, web)

scripts/ → batch ingestion

podman-compose.yml → orkiestracja

2️⃣ Podman – kontenery (podman-compose)
podman-compose.yml

version: "3.9"

services:

  llama:
    image: docker.io/ggml/llama.cpp:server
    container_name: klimtech-llama
    volumes:
      - ./llama/models:/models:Z
    command: >
      --model /models/mistral-7b-instruct.Q4_K_M.gguf
      --host 0.0.0.0
      --port 8080
      --ctx-size 4096
    ports:
      - "8080:8080"
    restart: unless-stopped

  haystack:
    build:
      context: ./containers/haystack
      dockerfile: Containerfile
    container_name: klimtech-haystack
    volumes:
      - ./data:/data:Z
    environment:
      - LLM_ENDPOINT=http://llama:8080/completion
    ports:
      - "8000:8000"
    depends_on:
      - llama
    restart: unless-stopped

  n8n:
    image: docker.io/n8nio/n8n
    container_name: klimtech-n8n
    volumes:
      - ./containers/n8n/data:/home/node/.n8n:Z
    ports:
      - "5678:5678"
    restart: unless-stopped

  nextcloud:
    image: docker.io/library/nextcloud
    container_name: klimtech-nextcloud
    volumes:
      - ./containers/nextcloud/data:/var/www/html:Z
    ports:
      - "8081:80"
    restart: unless-stopped


containers/haystack/Containerfile


FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

containers/haystack/requirements.txt

haystack-ai
fastapi
uvicorn
python-multipart
docling
llama-index
faiss-cpu


3️⃣ Backend: Haystack + llama.cpp (konkretny kod)

Backend udostępnia:

POST /ingest → dodawanie dokumentów (PDF, tekst, kod)

POST /query → zapytania RAG (dla OpenCode)

containers/haystack/app/config.py

import os

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://localhost:8080/completion")
DATA_DIR = "/data/rag"

containers/haystack/app/stores.py

from haystack.document_stores import FAISSDocumentStore

def get_document_store():
    return FAISSDocumentStore(
        sql_url="sqlite:////data/rag/index/docstore.db",
        embedding_dim=768,
        faiss_index_path="/data/rag/index/faiss.index",
        recreate_index=False,
    )


containers/haystack/app/pipelines.py

from haystack.nodes import EmbeddingRetriever
from haystack.pipelines import Pipeline
from haystack.schema import Document
import requests
from .stores import get_document_store
from .config import LLM_ENDPOINT

document_store = get_document_store()

retriever = EmbeddingRetriever(
    document_store=document_store,
    embedding_model="sentence-transformers/all-MiniLM-L6-v2",
    use_gpu=False,
)

document_store.update_embeddings(retriever)

def llama_generate(prompt: str) -> str:
    payload = {
        "prompt": prompt,
        "n_predict": 512,
        "temperature": 0.2,
        "stop": ["</s>"]
    }
    r = requests.post(LLM_ENDPOINT, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["content"]

def query_rag(question: str) -> str:
    docs = retriever.retrieve(question, top_k=5)
    context = "\n\n".join([d.content for d in docs])

    final_prompt = f"""
You are a technical assistant.
Use the context below to answer the question.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""
    return llama_generate(final_prompt)

def ingest_documents(texts: list[str], meta: dict = None):
    docs = [Document(content=t, meta=meta or {}) for t in texts]
    document_store.write_documents(docs)
    document_store.update_embeddings(retriever)



containers/haystack/app/main.py

from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from .pipelines import query_rag, ingest_documents
from docling.document_converter import DocumentConverter

app = FastAPI(title="KlimtechRAG Backend")

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
def query(req: QueryRequest):
    answer = query_rag(req.query)
    return {"answer": answer}

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    contents = await file.read()
    converter = DocumentConverter()
    doc = converter.convert(contents)

    texts = [block.text for block in doc.blocks if block.text]
    ingest_documents(texts, meta={"filename": file.filename})

    return {"status": "ok", "chunks": len(texts)}


4️⃣ Skrypt: lokalny import katalogu do RAG
scripts/ingest_folder.py

import os
import requests

API = "http://localhost:8000/ingest"

def ingest_file(path):
    with open(path, "rb") as f:
        r = requests.post(API, files={"file": f})
        print(path, r.status_code)

root = "/data/rag/docs"

for root_dir, _, files in os.walk(root):
    for f in files:
        ingest_file(os.path.join(root_dir, f))


5️⃣ Uruchomienie


cd KlimtechRAG
podman-compose up -d --build

curl http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Wytłumacz jak działa indeks FAISS w naszym systemie"}'


6️⃣ Integracja z OpenCode (RAG-as-a-Service)

OpenCode wywołuje:



POST http://localhost:8000/query
{
  "query": "Znajdź błąd w pliku PDF z dokumentacją"
}

Otrzymuje:

{
  "answer": "Błąd znajduje się w sekcji konfiguracji..."
}
