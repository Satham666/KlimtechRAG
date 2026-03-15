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
    use_rag: bool = True
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


class IngestPathRequest(BaseModel):
    path: str
