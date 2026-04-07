import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..models.schemas import (
    SessionCreateRequest,
    SessionMessage,
    SessionMessagesResponse,
    SessionResponse,
)
from ..services.session_service import (
    add_message,
    create_session,
    delete_session,
    get_messages,
    get_session,
    list_sessions,
    update_session_title,
)
from ..utils.dependencies import require_api_key

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])
logger = logging.getLogger("klimtechrag")


@router.get("", response_model=list[SessionResponse])
async def list_sessions_endpoint(
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(require_api_key),
):
    """Zwraca listę sesji posortowanych od najnowszej."""
    return list_sessions(limit=limit, offset=offset)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session_endpoint(
    body: SessionCreateRequest,
    _: str = Depends(require_api_key),
):
    """Tworzy nową sesję. Zwraca {id, title, created_at, updated_at}."""
    return create_session(title=body.title)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_endpoint(
    session_id: str,
    _: str = Depends(require_api_key),
):
    """Zwraca metadane sesji."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def rename_session_endpoint(
    session_id: str,
    body: SessionCreateRequest,
    _: str = Depends(require_api_key),
):
    """Zmienia tytuł sesji."""
    if not update_session_title(session_id, body.title):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    session = get_session(session_id)
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session_endpoint(
    session_id: str,
    _: str = Depends(require_api_key),
):
    """Usuwa sesję wraz ze wszystkimi wiadomościami."""
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@router.get("/{session_id}/messages", response_model=SessionMessagesResponse)
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    page: int = Query(1, ge=1, description="Numer strony"),
    page_size: int = Query(50, ge=1, le=200, description="Liczba wyników na stronę"),
    _: str = Depends(require_api_key),
):
    """Zwraca historię wiadomości sesji w kolejności chronologicznej."""
    import math
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    all_messages = get_messages(session_id, limit=9999, offset=0)
    total = len(all_messages)
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    offset_calc = (page - 1) * page_size
    paginated_messages = all_messages[offset_calc : offset_calc + page_size]

    return SessionMessagesResponse(
        session_id=session_id,
        data=[SessionMessage(**m) for m in paginated_messages],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


class MessageCreateRequest(BaseModel):
    role: str   # "user" | "assistant"
    content: str


@router.post("/{session_id}/messages", status_code=201)
async def add_message_endpoint(
    session_id: str,
    body: MessageCreateRequest,
    _: str = Depends(require_api_key),
):
    """Dodaje wiadomość do sesji (używane przez UI po zakończeniu streamu)."""
    from ..services.session_service import add_message, get_session
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    if body.role not in ("user", "assistant", "system"):
        raise HTTPException(status_code=400, detail="role must be user|assistant|system")
    return add_message(session_id, body.role, body.content)


@router.delete("/{session_id}/messages")
async def clear_session_messages(
    session_id: str,
    _: str = Depends(require_api_key),
):
    """Usuwa wszystkie wiadomości sesji, zachowuje samą sesję."""
    from ..services.session_service import get_session, _conn

    if not get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    with _conn() as conn:
        cur = conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
        deleted = cur.rowcount

    logger.info("[clear-messages] Usunięto %d wiadomości z sesji %s", deleted, session_id)
    return {"session_id": session_id, "deleted_messages": deleted}


@router.get("/{session_id}/export.md")
async def export_session_markdown(
    session_id: str,
    _: str = Depends(require_api_key),
):
    """Eksportuje historię sesji jako plik Markdown do pobrania."""
    from fastapi.responses import Response
    from ..services.session_service import get_session, get_messages

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    messages = get_messages(session_id, limit=500)
    lines = [
        f"# {session['title'] or 'KlimtechRAG — Historia rozmowy'}",
        f"\n_Sesja: {session_id} | Utworzona: {session['created_at']}_\n",
        "---\n",
    ]
    for msg in messages:
        role_label = "**Użytkownik**" if msg["role"] == "user" else "**Asystent**"
        lines.append(f"### {role_label}  \n_{msg['created_at']}_\n")
        lines.append(msg["content"] + "\n")
        lines.append("---\n")

    content = "\n".join(lines)
    filename = (session["title"] or "sesja").replace(" ", "_")[:40] + ".md"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}/export.json")
async def export_session_json(
    session_id: str,
    _: str = Depends(require_api_key),
):
    """Eksportuje historię sesji jako JSON (kompatybilny z POST /v1/sessions/import)."""
    import json
    from fastapi.responses import Response
    from ..services.session_service import get_session, get_messages

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    messages = get_messages(session_id, limit=500)
    export_data = {
        "id": session["id"],
        "title": session["title"],
        "created_at": session["created_at"],
        "messages": [
            {
                "role": msg["role"],
                "content": msg["content"],
                "created_at": msg["created_at"],
            }
            for msg in messages
        ],
    }

    content = json.dumps(export_data, ensure_ascii=False, indent=2)
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{session_id}.json"'},
    )


@router.get("/export-all")
async def export_all_sessions(
    limit: int = 500,
    _: str = Depends(require_api_key),
):
    """Eksportuje wszystkie sesje z wiadomościami jako JSON (backup)."""
    import json
    from fastapi.responses import Response
    from ..services.session_service import list_sessions, get_messages

    limit = min(limit, 500)
    sessions = list_sessions(limit=limit, offset=0)

    export_data = []
    for session in sessions:
        messages = get_messages(session["id"], limit=500)
        export_data.append({
            "id": session["id"],
            "title": session["title"],
            "created_at": session["created_at"],
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "created_at": msg["created_at"],
                }
                for msg in messages
            ],
        })

    content = json.dumps(export_data, ensure_ascii=False, indent=2)
    return Response(
        content=content.encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="sessions_backup.json"'},
    )


@router.get("/stats")
async def sessions_stats(_: str = Depends(require_api_key)):
    """Zwraca statystyki sesji: liczba sesji, wiadomości, ostatnia aktywność."""
    from ..services.session_service import get_sessions_stats
    return get_sessions_stats()


class CleanupRequest(BaseModel):
    max_age_days: int = 30


@router.post("/cleanup")
async def cleanup_sessions(
    body: CleanupRequest,
    _: str = Depends(require_api_key),
):
    """Usuwa sesje starsze niż max_age_days (domyślnie 30 dni)."""
    from ..services.session_service import cleanup_old_sessions

    if body.max_age_days < 1:
        raise HTTPException(status_code=400, detail="max_age_days musi być >= 1")
    deleted = cleanup_old_sessions(max_age_days=body.max_age_days)
    return {"deleted": deleted, "max_age_days": body.max_age_days}


@router.post("/cleanup-old")
async def cleanup_old_sessions_endpoint(
    days: int = 30,
    _: str = Depends(require_api_key),
):
    """Usuwa puste sesje starsze niż N dni.

    ?days=30  — próg wieku w dniach (min 1, max 365)
    """
    from datetime import timedelta
    from ..services.session_service import _conn

    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days musi być >= 1 i <= 365")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM sessions WHERE updated_at < ? AND id NOT IN (SELECT session_id FROM messages)",
            (cutoff,),
        )
        conn.commit()
        deleted = cur.rowcount

    logger.info("[cleanup-old] Usunięto %d pustych sesji starszych niż %d dni", deleted, days)
    return {"deleted": deleted, "days_threshold": days}


@router.get("/search")
async def search_sessions(
    q: str,
    limit: int = 20,
    _: str = Depends(require_api_key),
):
    """Przeszukuje tytuły i treść wiadomości sesji.

    ?q=zapytanie  — fraza do wyszukania (min 2 znaki)
    ?limit=20     — max wyników
    """
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Parametr 'q' musi mieć min. 2 znaki")
    pattern = f"%{q.strip()}%"
    from ..services.session_service import _conn
    with _conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT s.id, s.title, s.created_at, s.updated_at "
            "FROM sessions s LEFT JOIN messages m ON s.id = m.session_id "
            "WHERE s.title LIKE ? OR m.content LIKE ? "
            "ORDER BY s.updated_at DESC LIMIT ?",
            (pattern, pattern, min(limit, 100)),
        ).fetchall()
    return {
        "query": q,
        "total": len(rows),
        "sessions": [dict(r) for r in rows],
    }


class SessionImportRequest(BaseModel):
    title: str = ""
    messages: list[dict]   # [{role, content, created_at?}]


@router.post("/import", response_model=SessionResponse, status_code=201)
async def import_session(
    body: SessionImportRequest,
    _: str = Depends(require_api_key),
):
    """Importuje sesję z listy wiadomości (np. z exportChat UI).

    Akceptuje format: {title, messages: [{role, content}]}
    """
    from ..services.session_service import create_session, add_message

    if not body.messages:
        raise HTTPException(status_code=400, detail="messages nie może być puste")

    valid_roles = {"user", "assistant", "ai", "system"}
    session = create_session(title=body.title or "Zaimportowana sesja")

    for msg in body.messages:
        role = str(msg.get("role", "user")).lower()
        content = str(msg.get("content", "")).strip()
        if role == "ai":
            role = "assistant"
        if role not in valid_roles or not content:
            continue
        add_message(session["id"], role, content)

    logger.info("[F4] Zaimportowano sesję: %s (%d wiadomości)", session["id"], len(body.messages))
    return session


# ---------------------------------------------------------------------------
# GET /v1/sessions/{session_id}/context — kontekst dla LLM
# ---------------------------------------------------------------------------

@router.get("/{session_id}/context")
async def session_llm_context(
    session_id: str,
    max_messages: int = 20,
    _: str = Depends(require_api_key),
):
    """Zwraca historię sesji w formacie [{role, content}] gotowym dla LLM.

    ?max_messages=20  — ile ostatnich wiadomości zwrócić (max 100)
    """
    from ..services.session_service import get_session, get_history_for_llm

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesja nie istnieje")

    max_messages = min(max_messages, 100)
    messages = get_history_for_llm(session_id, max_messages=max_messages)

    return {
        "session_id": session_id,
        "title": session.get("title", ""),
        "messages_count": len(messages),
        "context": messages,
    }


# ---------------------------------------------------------------------------
# POST /v1/sessions/bulk-delete — usuwanie wielu sesji naraz
# ---------------------------------------------------------------------------

class BulkDeleteRequest(BaseModel):
    ids: list[str]


@router.post("/bulk-delete", status_code=200)
async def bulk_delete_sessions(
    body: BulkDeleteRequest,
    _: str = Depends(require_api_key),
):
    """Usuwa wiele sesji naraz po liście ID.

    Body: {"ids": ["id1", "id2", ...]}
    Zwraca liczbę faktycznie usuniętych sesji.
    """
    from ..services.session_service import delete_session

    if not body.ids:
        raise HTTPException(status_code=400, detail="ids nie może być puste")
    if len(body.ids) > 100:
        raise HTTPException(status_code=400, detail="Maksymalnie 100 sesji naraz")

    deleted = 0
    for session_id in body.ids:
        try:
            delete_session(session_id)
            deleted += 1
        except Exception:
            pass

    logger.info("[bulk-delete] Usunięto %d z %d sesji", deleted, len(body.ids))
    return {"requested": len(body.ids), "deleted": deleted}


# ---------------------------------------------------------------------------
# GET /v1/sessions/{id}/summary — podsumowanie sesji bez pełnej historii
# ---------------------------------------------------------------------------

@router.get("/{session_id}/summary")
async def get_session_summary(
    session_id: str,
    _: str = Depends(require_api_key),
):
    """Zwraca podsumowanie sesji: tytuł, liczba wiadomości, pierwsza/ostatnia wiadomość."""
    from ..services.session_service import get_session, get_messages

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    messages = get_messages(session_id, limit=1000)

    first_msg = None
    last_msg = None
    if messages:
        first = messages[0]
        last = messages[-1]
        first_msg = f"[{first['role']}] {first['content'][:100]}"
        last_msg = f"[{last['role']}] {last['content'][:100]}"

    return {
        "session_id": session_id,
        "title": session.get("title"),
        "messages_count": len(messages),
        "first_message": first_msg,
        "last_message": last_msg,
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
    }
