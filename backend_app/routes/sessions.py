import logging

import logging

from fastapi import APIRouter, Depends, HTTPException
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
    _: str = Depends(require_api_key),
):
    """Zwraca historię wiadomości sesji w kolejności chronologicznej."""
    if not get_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    messages = get_messages(session_id, limit=limit, offset=offset)
    return SessionMessagesResponse(
        session_id=session_id,
        data=[SessionMessage(**m) for m in messages],
        total=len(messages),
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
