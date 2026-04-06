import time
import uuid
from typing import List

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "klimtech-rag"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False
    use_rag: bool = False
    top_k: int = 5
    web_search: bool = False


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
    sources: List[str] = Field(default_factory=list)


class QueryRequest(BaseModel):
    query: str
    category_filter: str | None = None  # np. "medicine", "law" — filtruje Qdrant po meta.category


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


class IngestPathRequest(BaseModel):
    path: str


# ---------------------------------------------------------------------------
# B7: /v1/chunks — Low-level retrieval bez LLM
# ---------------------------------------------------------------------------

class ChunksRequest(BaseModel):
    text: str
    limit: int = 10
    context_filter: dict = Field(default_factory=dict)  # np. {"source": "raport.pdf"}


class ChunkResult(BaseModel):
    id: str = ""
    content: str
    score: float = 0.0
    source: str = ""
    meta: dict = Field(default_factory=dict)


class ChunksResponse(BaseModel):
    object: str = "list"
    data: List[ChunkResult]
    total: int


# ---------------------------------------------------------------------------
# H1: Standaryzacja IngestResponse (OpenAI-compatible)
# ---------------------------------------------------------------------------

class IngestItem(BaseModel):
    doc_id: str
    source: str
    status: str       # indexed | skipped | error | duplicate | cached
    chunks_count: int = 0
    collection: str = "klimtech_docs"


class IngestResponse(BaseModel):
    object: str = "ingest.result"
    data: List[IngestItem]
