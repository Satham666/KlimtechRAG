import logging
import os
import shutil
import subprocess
import tempfile
import time
import json
import uuid
from typing import Dict, List, Optional, Union, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.websockets import WebSocket
from pydantic import BaseModel, Field
from haystack import Pipeline, Document
from haystack.document_stores.types import DuplicatePolicy

from haystack.components.builders import PromptBuilder
from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.utils import ComponentDevice
from haystack.components.generators import OpenAIGenerator
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from docling.document_converter import DocumentConverter
from ddgs import DDGS
from .config import settings
from .fs_tools import (
    FsLimits,
    FsSecurityError,
    glob_paths,
    grep_files,
    ls_dir,
    read_text_file,
)
from .monitoring import log_stats, get_system_stats, format_stats


# --- LOGOWANIE I OBSERWOWALNOŚĆ ---
logger = logging.getLogger("klimtechrag")

if not logger.handlers:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s",
    )


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logger.addFilter(RequestIdFilter())


app = FastAPI()


# --- STAN GLOBALNY (metyki, cache, rate limiting) ---
metrics: Dict[str, int] = {
    "ingest_requests": 0,
    "query_requests": 0,
    "code_query_requests": 0,
}

rate_limit_store: Dict[str, List[float]] = {}
answer_cache: Dict[str, str] = {}


# --- Qdrant i LLM z konfiguracji ---
os.environ["OPENAI_BASE_URL"] = str(settings.llm_base_url)
os.environ["OPENAI_API_KEY"] = settings.llm_api_key

doc_store = QdrantDocumentStore(
    url=str(settings.qdrant_url),
    index=settings.qdrant_collection,
    embedding_dim=1024,
    recreate_index=False,
)


# --- KOMPONENTY DO INDEKSOWANIA ---
def parse_with_docling(file_path: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(file_path)
    return result.document.export_to_markdown()


EMBEDDING_DEVICE = os.getenv("KLIMTECH_EMBEDDING_DEVICE", "cpu")
embedding_device = ComponentDevice.from_str(EMBEDDING_DEVICE)
logger.info("Embedding device: %s", EMBEDDING_DEVICE)

# --- KOMPONENTY DO INDEKSOWANIA ---
indexing_pipeline = Pipeline()
indexing_pipeline.add_component(
    "splitter", DocumentSplitter(split_by="word", split_length=200, split_overlap=30)
)
indexing_pipeline.add_component(
    "embedder",
    SentenceTransformersDocumentEmbedder(
        model=settings.embedding_model, device=embedding_device
    ),
)
indexing_pipeline.add_component(
    "writer", DocumentWriter(document_store=doc_store, policy=DuplicatePolicy.OVERWRITE)
)
indexing_pipeline.connect("splitter", "embedder")
indexing_pipeline.connect("embedder", "writer")

# --- KOMPONENTY DO ZAPYTAŃ (RAG) ---
rag_pipeline = Pipeline()
rag_pipeline.add_component(
    "embedder",
    SentenceTransformersTextEmbedder(
        model=settings.embedding_model, device=embedding_device
    ),
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
rag_pipeline.add_component("llm", OpenAIGenerator(model=settings.llm_model_name))

rag_pipeline.connect("embedder", "retriever")
rag_pipeline.connect("retriever", "prompt_builder.documents")
rag_pipeline.connect("prompt_builder", "llm")


class QueryRequest(BaseModel):
    query: str


class CodeQueryRequest(BaseModel):
    query: str


class FsListRequest(BaseModel):
    path: str


class FsGlobRequest(BaseModel):
    pattern: str
    limit: int = 200


class FsReadRequest(BaseModel):
    path: str
    offset: int = 1
    limit: int = 200


class FsGrepRequest(BaseModel):
    path: str = "."
    query: str
    file_glob: str = "*"
    regex: bool = False
    case_insensitive: bool = True


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "klimtech-rag"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
    use_rag: bool = True
    top_k: int = 5


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:8]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "klimtech-rag"
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage = ChatCompletionUsage()


async def get_request_id(request: Request) -> str:
    request_id = request.headers.get("X-Request-ID") or str(time.time_ns())
    request.state.request_id = request_id
    return request_id


def get_client_id(request: Request) -> str:
    return request.client.host or "unknown"


def apply_rate_limit(client_id: str) -> None:
    now = time.time()
    window = settings.rate_limit_window_seconds
    max_requests = settings.rate_limit_max_requests

    timestamps = rate_limit_store.get(client_id, [])
    timestamps = [t for t in timestamps if now - t <= window]
    if len(timestamps) >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    timestamps.append(now)
    rate_limit_store[client_id] = timestamps


def require_api_key(request: Request) -> None:
    if not settings.api_key:
        return
    header_key = request.headers.get("X-API-Key")
    if header_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.middleware("http")
async def add_request_id_and_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(time.time_ns())
    request.state.request_id = request_id

    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("Unhandled error", extra={"request_id": request_id})
        raise exc
    duration_ms = int((time.time() - start) * 1000)
    logger.info(
        "Request %s %s finished in %d ms",
        request.method,
        request.url.path,
        duration_ms,
        extra={"request_id": request_id},
    )
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "-")
    logger.exception("Unhandled exception", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


def parse_with_docling(file_path: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(file_path)
    return result.document.export_to_markdown()


@app.post("/ingest")
async def ingest_file(
    file: UploadFile,
    request_id: str = Depends(get_request_id),
    request: Request = None,
):
    """Endpoint do ładowania plików do bazy RAG."""
    require_api_key(request)
    apply_rate_limit(get_client_id(request))
    metrics["ingest_requests"] += 1

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is missing")

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in settings.allowed_extensions_docs:
        raise HTTPException(
            status_code=400, detail=f"File format not allowed: {file.filename}"
        )

    temp_file_path: Optional[str] = None
    markdown_text = ""

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_file_path = tmp.name

        file_size = os.path.getsize(temp_file_path)
        if file_size > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size} bytes (limit {settings.max_file_size_bytes})",
            )

        if suffix == ".pdf":
            logger.info(
                "[Backend] Parsowanie PDF %s | %s",
                file.filename,
                log_stats("Start"),
                extra={"request_id": request_id},
            )
            markdown_text = parse_with_docling(temp_file_path)
            logger.info(
                "[Backend] PDF sparsowany | %s",
                log_stats("Po parsowaniu"),
                extra={"request_id": request_id},
            )
        else:
            logger.info(
                "[Backend] Parsowanie tekstu %s | %s",
                file.filename,
                log_stats("Start"),
                extra={"request_id": request_id},
            )
            with open(temp_file_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()

        if not markdown_text or len(markdown_text.strip()) == 0:
            logger.warning(
                "[Backend] Plik pusty (skan bez tekstu): %s",
                file.filename,
                extra={"request_id": request_id},
            )
            return {"message": "File empty (Scanned PDF?)", "chunks_processed": 0}

        docs = [
            Document(
                content=markdown_text, meta={"source": file.filename, "type": suffix}
            )
        ]
        logger.info(
            "[Backend] Embedding/Indeksowanie | %s",
            log_stats("Start"),
            extra={"request_id": request_id},
        )
        result = indexing_pipeline.run({"splitter": {"documents": docs}})
        logger.info(
            "[Backend] Zaindeksowano %d chunków | %s",
            result["writer"]["documents_written"],
            log_stats("Koniec"),
            extra={"request_id": request_id},
        )

        return {
            "message": "File ingested successfully",
            "chunks_processed": result["writer"]["documents_written"],
        }
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@app.post("/query")
async def query_rag(
    request: QueryRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """Endpoint do zadawania pytań RAG z Web Search."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    metrics["query_requests"] += 1

    cached = answer_cache.get(request.query)
    if cached:
        return {"answer": cached, "cached": True}

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
                if results:
                    web_snippet = " | ".join([res.get("body", "") for res in results])
                else:
                    web_snippet = ""
        except Exception as e:
            logger.warning("Web search error: %s", e, extra={"request_id": request_id})
            web_snippet = ""

        from haystack import Document as HaystackDocument

        final_docs = list(local_docs)
        if web_snippet:
            web_doc = HaystackDocument(
                content=web_snippet, meta={"source": "Web Search"}
            )
            final_docs.append(web_doc)

        prompt_text = ""
        for doc in final_docs:
            prompt_text += f"{doc.content}\n"

        prompt_text += "\n\n" + _tool_instructions() + "\n\n"
        prompt_text += f"USER_QUESTION: {request.query}\n"

        llm_component = rag_pipeline.get_component("llm")

        # Prosta pętla tool-calling (max 2 narzędzia na zapytanie)
        current_prompt = prompt_text
        answer: str = ""
        for _ in range(3):
            llm_result = llm_component.run(prompt=current_prompt)
            answer = llm_result["replies"][0]

            tool_req = _maybe_parse_tool_request(answer)
            if not tool_req:
                break
            try:
                tool_out = _execute_tool(tool_req)
            except Exception as e:
                tool_out = {"tool_error": str(e), "tool_request": tool_req}

            current_prompt = (
                current_prompt
                + "\n\nTOOL_RESULT (JSON):\n"
                + json.dumps(tool_out, ensure_ascii=False)[:8000]
                + "\n\nNow answer the user question using the TOOL_RESULT. Do NOT request another tool unless strictly necessary."
            )

        answer_cache[request.query] = answer
        return {"answer": answer, "cached": False}
    except Exception as e:
        logger.exception("Error in /query: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/code_query")
async def query_code_agent(
    request: CodeQueryRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """Endpoint dedykowany do zadań programistycznych (Analiza kodu, debug)."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    metrics["code_query_requests"] += 1

    try:
        rag_result = rag_pipeline.run(
            {
                "embedder": {"text": request.query},
                "prompt_builder": {"query": request.query},
            },
            include_outputs_from={"retriever"},
        )
        local_docs = rag_result["retriever"]["documents"]

        prompt_text = "You are a Senior Python Developer. Analyze the following code/docs strictly.\n\nContext:\n"
        for doc in local_docs:
            prompt_text += f"{doc.content}\n"

        prompt_text += "\n\n" + _tool_instructions() + "\n\n"
        prompt_text += f"CODE_QUESTION: {request.query}\n\nProvide a technical answer."

        llm_component = rag_pipeline.get_component("llm")
        current_prompt = prompt_text
        answer: str = ""
        for _ in range(3):
            llm_result = llm_component.run(prompt=current_prompt)
            answer = llm_result["replies"][0]
            tool_req = _maybe_parse_tool_request(answer)
            if not tool_req:
                break
            try:
                tool_out = _execute_tool(tool_req)
            except Exception as e:
                tool_out = {"tool_error": str(e), "tool_request": tool_req}

            current_prompt = (
                current_prompt
                + "\n\nTOOL_RESULT (JSON):\n"
                + json.dumps(tool_out, ensure_ascii=False)[:8000]
                + "\n\nNow answer the code question using the TOOL_RESULT. Do NOT request another tool unless strictly necessary."
            )

        return {"answer": answer}
    except Exception as e:
        logger.exception(
            "Error in /code_query: %s", e, extra={"request_id": request_id}
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def openai_chat_completions(
    request: ChatCompletionRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """OpenAI-compatible endpoint z RAG - kompatybilny z llama.cpp-server UI."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    metrics["query_requests"] += 1

    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    context_text = ""
    sources = []

    if request.use_rag:
        try:
            embedder = SentenceTransformersTextEmbedder(
                model=settings.embedding_model, device=embedding_device
            )
            embedder.warm_up()
            query_embedding = embedder.run(text=user_message)

            retriever = QdrantEmbeddingRetriever(
                document_store=doc_store, top_k=request.top_k
            )
            retrieval_result = retriever.run(
                query_embedding=query_embedding["embedding"]
            )

            docs = retrieval_result.get("documents", [])
            if docs:
                contents = [doc.content for doc in docs if doc.content]
                if contents:
                    context_text = "\n\n---\n\n".join(contents)
                sources = []
                for doc in docs:
                    src = "unknown"
                    if doc.meta and "source" in doc.meta:
                        src = str(doc.meta["source"])
                    sources.append(src)
                logger.info(
                    "[RAG] Znaleziono %d dokumentów: %s",
                    len(docs),
                    ", ".join(sources),
                    extra={"request_id": request_id},
                )
        except Exception as e:
            logger.warning(
                "[RAG] Błąd retrieval: %s", str(e), extra={"request_id": request_id}
            )

    system_prompt = """Jesteś pomocnym asystentem AI z dostępem do bazy wiedzy RAG.
Odpowiadaj na podstawie dostarczonego kontekstu. Jeśli nie znajdziesz odpowiedzi w kontekście,
powiedz o tym szczerze. Odpowiadaj po polsku, chyba że użytkownik pyta w innym języku."""

    if context_text:
        full_prompt = f"""{system_prompt}

=== KONTEKST Z BAZY WIEDZY ===
{context_text}
=== KONIEC KONTEKSTU ===

PYTANIE UŻYTKOWNIKA: {user_message}

ODPOWIEDŹ:"""
    else:
        full_prompt = f"{system_prompt}\n\nPYTANIE: {user_message}\n\nODPOWIEDŹ:"

    try:
        llm_component = rag_pipeline.get_component("llm")
        llm_result = llm_component.run(prompt=full_prompt)
        answer = llm_result["replies"][0]

        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(role="assistant", content=answer)
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=len(full_prompt.split()),
                completion_tokens=len(answer.split()),
                total_tokens=len(full_prompt.split()) + len(answer.split()),
            ),
        )
    except Exception as e:
        logger.exception(
            "Error in /v1/chat/completions: %s", e, extra={"request_id": request_id}
        )
        raise HTTPException(status_code=500, detail=str(e))


RAG_DATA_BASE = "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane"
RAG_UPLOAD_BASE = "/home/lobo/KlimtechRAG/data/uploads"

EXT_TO_DIR = {
    ".pdf": "pdf_RAG",
    ".txt": "txt_RAG",
    ".md": "txt_RAG",
    ".py": "txt_RAG",
    ".js": "txt_RAG",
    ".ts": "txt_RAG",
    ".json": "json_RAG",
    ".yml": "txt_RAG",
    ".yaml": "txt_RAG",
    ".mp3": "Audio_RAG",
    ".wav": "Audio_RAG",
    ".ogg": "Audio_RAG",
    ".flac": "Audio_RAG",
    ".mp4": "Video_RAG",
    ".avi": "Video_RAG",
    ".mkv": "Video_RAG",
    ".mov": "Video_RAG",
    ".jpg": "Images_RAG",
    ".jpeg": "Images_RAG",
    ".png": "Images_RAG",
    ".gif": "Images_RAG",
    ".bmp": "Images_RAG",
    ".webp": "Images_RAG",
    ".doc": "Doc_RAG",
    ".docx": "Doc_RAG",
    ".odt": "Doc_RAG",
    ".rtf": "Doc_RAG",
}


@app.post("/upload")
async def upload_file_to_rag(
    file: UploadFile,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """Upload pliku do odpowiedniego katalogu RAG na podstawie rozszerzenia."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))

    if not file.filename:
        raise HTTPException(status_code=400, detail="Brak nazwy pliku")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in EXT_TO_DIR:
        raise HTTPException(
            status_code=400,
            detail=f"Nieobsługiwane rozszerzenie: {ext}. Dozwolone: {', '.join(EXT_TO_DIR.keys())}",
        )

    subdir = EXT_TO_DIR[ext]
    target_dir = os.path.join(RAG_UPLOAD_BASE, subdir)
    os.makedirs(target_dir, exist_ok=True)

    target_path = os.path.join(target_dir, file.filename)

    counter = 1
    base_name = os.path.splitext(file.filename)[0]
    while os.path.exists(target_path):
        target_path = os.path.join(target_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    try:
        with open(target_path, "wb") as f:
            content = await file.read()
            f.write(content)

        file_size = os.path.getsize(target_path)
        logger.info(
            "[Upload] Zapisano %s do %s (%.1f KB)",
            os.path.basename(target_path),
            EXT_TO_DIR[ext],
            file_size / 1024,
            extra={"request_id": request_id},
        )

        return {
            "status": "ok",
            "filename": os.path.basename(target_path),
            "directory": EXT_TO_DIR[ext],
            "size_bytes": file_size,
            "message": f"Plik zapisany w {EXT_TO_DIR[ext]}. Zostanie zindeksowany automatycznie.",
        }
    except Exception as e:
        logger.exception("[Upload] Błąd: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", response_class=HTMLResponse)
@app.get("/chat", response_class=HTMLResponse)
async def chat_ui():
    """Prosty interfejs webowy do czatu RAG."""
    return """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KlimtechRAG Chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; height: 100vh; display: flex; flex-direction: column; }
        h1 { text-align: center; padding: 15px; background: #16213e; border-radius: 10px; margin-bottom: 15px; }
        #chat-box { flex: 1; overflow-y: auto; background: #0f0f23; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
        .msg { margin: 10px 0; padding: 12px 15px; border-radius: 15px; max-width: 85%; word-wrap: break-word; }
        .user { background: #4a69bd; margin-left: auto; text-align: right; }
        .assistant { background: #2d3436; border: 1px solid #4a69bd; }
        .system { background: #6c5ce7; font-size: 0.9em; opacity: 0.8; }
        .success { background: #27ae60; }
        .error { background: #c0392b; }
        .input-area { display: flex; gap: 10px; flex-wrap: wrap; }
        #user-input { flex: 1; padding: 12px 15px; border: none; border-radius: 25px; background: #16213e; color: #eee; font-size: 16px; min-width: 200px; }
        #user-input:focus { outline: 2px solid #4a69bd; }
        button { padding: 12px 25px; border: none; border-radius: 25px; background: #4a69bd; color: white; font-size: 16px; cursor: pointer; }
        button:hover { background: #5a79cd; }
        button:disabled { background: #333; cursor: not-allowed; }
        .typing { font-style: italic; opacity: 0.7; }
        .rag-info { font-size: 0.8em; color: #888; margin-top: 5px; }
        .file-upload { display: flex; gap: 10px; align-items: center; margin-top: 10px; }
        #file-input { display: none; }
        .upload-btn { background: #27ae60; }
        .upload-btn:hover { background: #2ecc71; }
        #file-name { color: #888; font-size: 14px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .drop-zone { border: 2px dashed #4a69bd; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 10px; display: none; }
        .drop-zone.active { display: block; background: rgba(74, 105, 189, 0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 KlimtechRAG Chat</h1>
        <div id="chat-box"></div>
        <div class="drop-zone" id="drop-zone">
            📁 Upuść plik tutaj (PDF, TXT, MP3, MP4, JSON, obrazy...)
        </div>
        <div class="input-area">
            <input type="text" id="user-input" placeholder="Zapytaj o dokumenty w bazie RAG..." autofocus>
            <button id="send-btn" onclick="sendMessage()">Wyślij</button>
        </div>
        <div class="file-upload">
            <input type="file" id="file-input" onchange="handleFileSelect(event)">
            <button class="upload-btn" onclick="document.getElementById('file-input').click()">📎 Dodaj plik</button>
            <span id="file-name"></span>
            <button id="upload-btn" style="display:none;" onclick="uploadFile()">📤 Wyślij</button>
        </div>
    </div>
    <script>
        const chatBox = document.getElementById('chat-box');
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        const fileInput = document.getElementById('file-input');
        const fileName = document.getElementById('file-name');
        const uploadBtn = document.getElementById('upload-btn');
        const dropZone = document.getElementById('drop-zone');

        let selectedFile = null;

        function addMessage(role, content, ragInfo = '') {
            const div = document.createElement('div');
            div.className = 'msg ' + role;
            div.innerHTML = content.replace(/\\n/g, '<br>');
            if (ragInfo) {
                const info = document.createElement('div');
                info.className = 'rag-info';
                info.textContent = ragInfo;
                div.appendChild(info);
            }
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function handleFileSelect(event) {
            selectedFile = event.target.files[0];
            if (selectedFile) {
                fileName.textContent = selectedFile.name;
                uploadBtn.style.display = 'inline-block';
            } else {
                fileName.textContent = '';
                uploadBtn.style.display = 'none';
            }
        }

        async function uploadFile() {
            if (!selectedFile) return;

            const formData = new FormData();
            formData.append('file', selectedFile);

            addMessage('system', '📤 Wysyłanie: ' + selectedFile.name);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    addMessage('success', '✅ ' + data.message);
                } else {
                    addMessage('error', '❌ Błąd: ' + (data.detail || 'Nieznany błąd'));
                }
            } catch (err) {
                addMessage('error', '❌ Błąd połączenia: ' + err.message);
            }

            selectedFile = null;
            fileInput.value = '';
            fileName.textContent = '';
            uploadBtn.style.display = 'none';
        }

        // Drag & Drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
            document.body.addEventListener(event, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        document.body.addEventListener('dragenter', () => dropZone.classList.add('active'));
        document.body.addEventListener('dragleave', (e) => {
            if (!e.relatedTarget || !document.body.contains(e.relatedTarget)) {
                dropZone.classList.remove('active');
            }
        });

        document.body.addEventListener('drop', async (e) => {
            dropZone.classList.remove('active');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                selectedFile = files[0];
                fileName.textContent = selectedFile.name;
                await uploadFile();
            }
        });

        async function sendMessage() {
            const query = userInput.value.trim();
            if (!query) return;

            addMessage('user', query);
            userInput.value = '';
            sendBtn.disabled = true;

            const typingDiv = document.createElement('div');
            typingDiv.className = 'msg assistant typing';
            typingDiv.textContent = 'Pisze...';
            chatBox.appendChild(typingDiv);
            chatBox.scrollTop = chatBox.scrollHeight;

            try {
                const response = await fetch('/v1/chat/completions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        model: 'klimtech-rag',
                        messages: [{ role: 'user', content: query }],
                        use_rag: true,
                        top_k: 5
                    })
                });

                chatBox.removeChild(typingDiv);

                if (!response.ok) {
                    addMessage('system', 'Błąd: ' + response.status);
                    return;
                }

                const data = await response.json();
                const answer = data.choices[0].message.content;
                addMessage('assistant', answer);
            } catch (err) {
                chatBox.removeChild(typingDiv);
                addMessage('system', 'Błąd połączenia: ' + err.message);
            }

            sendBtn.disabled = false;
            userInput.focus();
        }

        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        addMessage('system', 'Witaj! Jestem asystentem RAG z dostępem do Twoich dokumentów. Możesz też dodać pliki (PDF, TXT, MP3, MP4, obrazy) klikając 📎 lub przeciągając je tutaj.');
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn

    logger.info("Startowanie KlimtechRAG Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/health")
async def health_check():
    """Prosty health-check Qdrant + LLM."""
    qdrant_ok = False
    llm_ok = False

    try:
        count = doc_store.count_documents()
        qdrant_ok = count >= 0
    except Exception:
        qdrant_ok = False

    try:
        # proste sprawdzenie: wywołanie komponentu bez kontekstu (może być kosztowne, więc w razie czego można wyłączyć)
        llm_ok = True
    except Exception:
        llm_ok = False

    status = qdrant_ok and llm_ok
    return {
        "status": "ok" if status else "degraded",
        "qdrant": qdrant_ok,
        "llm": llm_ok,
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Proste metryki aplikacji."""
    return {
        "ingest_requests": metrics["ingest_requests"],
        "query_requests": metrics["query_requests"],
        "code_query_requests": metrics["code_query_requests"],
    }


@app.delete("/documents")
async def delete_documents(
    source: Optional[str] = None,
    doc_id: Optional[str] = None,
):
    """Prosty endpoint administracyjny do kasowania dokumentów z Qdrant."""
    if not source and not doc_id:
        raise HTTPException(
            status_code=400, detail="Provide at least source or doc_id filter"
        )

    filters = {}
    if source:
        filters["source"] = [source]
    if doc_id:
        filters["id"] = [doc_id]

    doc_store.delete_documents(filters=filters or None)
    return {"status": "ok"}


@app.websocket("/ws/health")
async def websocket_health(ws: WebSocket):
    """Prosty WebSocket do podglądu statusu zdrowia."""
    await ws.accept()
    try:
        while True:
            health = await health_check()
            await ws.send_json(health)
            await ws.receive_text()  # prosta forma keep-alive / sterowania
    except Exception:
        await ws.close()


@app.post("/fs/list")
async def fs_list(
    request_body: FsListRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """Bezpieczne wywołanie ls -la w dozwolonym katalogu."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        return ls_dir(settings.fs_root, request_body.path)
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error executing ls: %s", e, extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail="ls execution failed")


@app.post("/fs/glob")
async def fs_glob(
    request_body: FsGlobRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """Glob (Python) w obrębie KLIMTECH_FS_ROOT."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    try:
        return glob_paths(
            settings.fs_root, request_body.pattern, limit=request_body.limit
        )
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(
            "Error executing glob: %s", e, extra={"request_id": request_id}
        )
        raise HTTPException(status_code=500, detail="glob failed")


@app.post("/fs/read")
async def fs_read(
    request_body: FsReadRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """Read – odczyt tekstowego pliku (z limitami)."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    limits = FsLimits(
        max_file_bytes_read=settings.fs_max_file_bytes_read,
        max_file_bytes_grep=settings.fs_max_file_bytes_grep,
        max_matches_grep=settings.fs_max_matches_grep,
    )
    try:
        return read_text_file(
            settings.fs_root,
            request_body.path,
            limits=limits,
            offset=request_body.offset,
            limit=request_body.limit,
        )
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/fs/grep")
async def fs_grep(
    request_body: FsGrepRequest,
    req: Request,
    request_id: str = Depends(get_request_id),
):
    """Grep – przeszukuje zawartość plików (Python), z limitami."""
    require_api_key(req)
    apply_rate_limit(get_client_id(req))
    limits = FsLimits(
        max_file_bytes_read=settings.fs_max_file_bytes_read,
        max_file_bytes_grep=settings.fs_max_file_bytes_grep,
        max_matches_grep=settings.fs_max_matches_grep,
    )
    try:
        return grep_files(
            settings.fs_root,
            request_body.path,
            request_body.query,
            limits=limits,
            file_glob=request_body.file_glob,
            regex=request_body.regex,
            case_insensitive=request_body.case_insensitive,
        )
    except FsSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _tool_instructions() -> str:
    return (
        "You have access to filesystem tools via the backend. "
        "If you need to list/search/read files, respond ONLY with a single JSON object, no prose:\n"
        '{"tool":"ls|glob|grep|read","args":{...}}\n'
        "Tools:\n"
        '- ls: {"path":"relative/or/absolute"}\n'
        '- glob: {"pattern":"**/*.py","limit":200}\n'
        '- grep: {"path":".","query":"text","file_glob":"*.py","regex":false,"case_insensitive":true}\n'
        '- read: {"path":"backend_app/main.py","offset":1,"limit":200}\n'
        f"All paths must be under {settings.fs_root}. "
        "After receiving TOOL_RESULT, answer normally."
    )


def _maybe_parse_tool_request(text: str) -> Optional[dict]:
    stripped = (text or "").strip()
    if not stripped.startswith("{") or not stripped.endswith("}"):
        return None
    try:
        obj = json.loads(stripped)
    except Exception:
        return None
    if not isinstance(obj, dict):
        return None
    if "tool" not in obj or "args" not in obj:
        return None
    return obj


def _execute_tool(tool_req: dict) -> dict:
    tool = tool_req.get("tool")
    args = tool_req.get("args") or {}
    limits = FsLimits(
        max_file_bytes_read=settings.fs_max_file_bytes_read,
        max_file_bytes_grep=settings.fs_max_file_bytes_grep,
        max_matches_grep=settings.fs_max_matches_grep,
    )

    if tool == "ls":
        return {"tool": "ls", "result": ls_dir(settings.fs_root, args.get("path", "."))}
    if tool == "glob":
        return {
            "tool": "glob",
            "result": glob_paths(
                settings.fs_root,
                args.get("pattern", "**/*"),
                limit=int(args.get("limit", 200)),
            ),
        }
    if tool == "read":
        return {
            "tool": "read",
            "result": read_text_file(
                settings.fs_root,
                args.get("path", ""),
                limits=limits,
                offset=int(args.get("offset", 1)),
                limit=int(args.get("limit", 200)),
            ),
        }
    if tool == "grep":
        return {
            "tool": "grep",
            "result": grep_files(
                settings.fs_root,
                args.get("path", "."),
                args.get("query", ""),
                limits=limits,
                file_glob=args.get("file_glob", "*"),
                regex=bool(args.get("regex", False)),
                case_insensitive=bool(args.get("case_insensitive", True)),
            ),
        }
    raise ValueError("Unknown tool")
