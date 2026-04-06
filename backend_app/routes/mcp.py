import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ..utils.dependencies import require_api_key

router = APIRouter(prefix="/mcp", tags=["mcp"])
logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# W2: MCP Compatibility — JSON-RPC 2.0 endpoint
# Protokół: Model Context Protocol v2024-11-05
# Narzędzia: rag_query, list_documents, ingest_text
# ---------------------------------------------------------------------------

_MCP_VERSION = "2024-11-05"
_SERVER_INFO = {"name": "klimtechrag-mcp", "version": "1.0.0"}

_TOOLS = [
    {
        "name": "rag_query",
        "description": (
            "Przeszukuje bazę wiedzy KlimtechRAG i zwraca odpowiedź na pytanie "
            "na podstawie zindeksowanych dokumentów."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Pytanie do bazy wiedzy"},
                "top_k": {"type": "integer", "default": 5, "description": "Liczba dokumentów kontekstu"},
                "category": {"type": "string", "description": "Opcjonalny filtr kategorii (np. medicine, law)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_documents",
        "description": "Zwraca listę zindeksowanych dokumentów w bazie RAG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50, "description": "Maksymalna liczba wyników"},
                "status": {"type": "string", "default": "indexed", "description": "Filtr statusu: indexed|pending|error"},
            },
        },
    },
    {
        "name": "ingest_text",
        "description": "Indeksuje przekazany tekst w bazie RAG.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Treść dokumentu do zaindeksowania"},
                "filename": {"type": "string", "description": "Nazwa pliku (np. dokument.txt)"},
                "category": {"type": "string", "description": "Kategoria dokumentu (opcjonalnie)"},
            },
            "required": ["text", "filename"],
        },
    },
]


def _ok(req_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


async def _handle_method(method: str, params: dict, req_id: Any) -> dict:
    """Dyspozytornia metod JSON-RPC."""

    # ── initialize ──────────────────────────────────────────────────────────
    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": _MCP_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": _SERVER_INFO,
        })

    # ── notifications/initialized (no response needed, but return ok) ───────
    if method == "notifications/initialized":
        return _ok(req_id, {})

    # ── tools/list ──────────────────────────────────────────────────────────
    if method == "tools/list":
        return _ok(req_id, {"tools": _TOOLS})

    # ── tools/call ──────────────────────────────────────────────────────────
    if method == "tools/call":
        tool_name = params.get("name", "")
        args: dict = params.get("arguments", {})
        return await _call_tool(req_id, tool_name, args)

    # ── nieznana metoda ─────────────────────────────────────────────────────
    return _err(req_id, -32601, f"Method not found: {method}")


async def _call_tool(req_id: Any, tool_name: str, args: dict) -> dict:
    """Wywołuje konkretne narzędzie MCP."""

    if tool_name == "rag_query":
        return await _tool_rag_query(req_id, args)
    if tool_name == "list_documents":
        return await _tool_list_documents(req_id, args)
    if tool_name == "ingest_text":
        return await _tool_ingest_text(req_id, args)

    return _err(req_id, -32602, f"Unknown tool: {tool_name}")


async def _tool_rag_query(req_id: Any, args: dict) -> dict:
    """Narzędzie: rag_query — wyszukiwanie w bazie wiedzy."""
    from ..services.chat_service import handle_chat_completions

    query: str = args.get("query", "").strip()
    if not query:
        return _err(req_id, -32602, "Argument 'query' is required")

    top_k: int = int(args.get("top_k", 5))

    try:
        answer, sources = handle_chat_completions(
            user_message=query,
            use_rag=True,
            web_search=False,
            top_k=top_k,
            request_id=uuid.uuid4().hex[:8],
        )
        return _ok(req_id, {
            "content": [
                {"type": "text", "text": answer},
            ],
            "sources": sources,
        })
    except Exception as e:
        logger.exception("[MCP] rag_query error: %s", e)
        return _err(req_id, -32603, f"RAG query error: {e}")


async def _tool_list_documents(req_id: Any, args: dict) -> dict:
    """Narzędzie: list_documents — lista zindeksowanych plików."""
    from ..file_registry import get_connection

    limit: int = int(args.get("limit", 50))
    status: str = args.get("status", "indexed")

    try:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT filename, extension, chunks_count, indexed_at, status FROM files "
                "WHERE status = ? ORDER BY indexed_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        docs = [dict(r) for r in rows]
        return _ok(req_id, {
            "content": [
                {"type": "text", "text": f"Znaleziono {len(docs)} dokumentów (status={status})"},
            ],
            "documents": docs,
            "total": len(docs),
        })
    except Exception as e:
        logger.exception("[MCP] list_documents error: %s", e)
        return _err(req_id, -32603, f"list_documents error: {e}")


async def _tool_ingest_text(req_id: Any, args: dict) -> dict:
    """Narzędzie: ingest_text — indeksuje tekst w RAG."""
    import os
    import tempfile

    from ..services.ingest_service import ingest_file_background

    text: str = args.get("text", "").strip()
    filename: str = args.get("filename", "mcp_doc.txt").strip()

    if not text:
        return _err(req_id, -32602, "Argument 'text' is required")
    if not filename:
        return _err(req_id, -32602, "Argument 'filename' is required")

    # Sanityzacja nazwy pliku
    filename = os.path.basename(filename.replace("..", "").lstrip("/"))
    if not filename:
        filename = "mcp_doc.txt"

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=os.path.splitext(filename)[1] or ".txt",
            prefix="mcp_",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            tmp.write(text)
            tmp_path = tmp.name

        # Uruchom ingest synchronicznie (brak ProgressTask)
        ingest_file_background(tmp_path)

        return _ok(req_id, {
            "content": [
                {"type": "text", "text": f"Plik '{filename}' zaindeksowany pomyślnie."},
            ],
            "filename": filename,
            "status": "indexed",
        })
    except Exception as e:
        logger.exception("[MCP] ingest_text error: %s", e)
        return _err(req_id, -32603, f"ingest_text error: {e}")


# ---------------------------------------------------------------------------
# Endpoint HTTP
# ---------------------------------------------------------------------------


@router.post("")
async def mcp_jsonrpc(
    request: Request,
    _: str = Depends(require_api_key),
):
    """JSON-RPC 2.0 endpoint MCP — obsługuje initialize, tools/list, tools/call."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            _err(None, -32700, "Parse error"),
            status_code=400,
        )

    # Obsługa batcha (lista requestów)
    if isinstance(body, list):
        results = []
        for item in body:
            result = await _dispatch(item)
            if result is not None:
                results.append(result)
        return JSONResponse(results)

    result = await _dispatch(body)
    if result is None:
        return JSONResponse({}, status_code=204)
    return JSONResponse(result)


async def _dispatch(body: dict) -> dict | None:
    """Przetwarza pojedynczy JSON-RPC request."""
    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params") or {}

    if body.get("jsonrpc") != "2.0":
        return _err(req_id, -32600, "Invalid Request — jsonrpc must be '2.0'")

    # Notyfikacje (brak id) nie wymagają odpowiedzi
    if req_id is None and method.startswith("notifications/"):
        return None

    try:
        return await _handle_method(method, params, req_id)
    except Exception as e:
        logger.exception("[MCP] Internal error for method %s: %s", method, e)
        return _err(req_id, -32603, f"Internal error: {e}")
