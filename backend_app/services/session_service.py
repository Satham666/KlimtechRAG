import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from ..config import settings

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Session Service — persistentna historia czatu (F4)
# SQLite: sessions + messages; ścieżka: {data_path}/sessions.db
# ---------------------------------------------------------------------------

SESSIONS_DB_PATH = f"{settings.data_path}/sessions.db"

_MAX_HISTORY = int(50)          # ile ostatnich wiadomości wczytywać jako kontekst
_TITLE_MAX_LEN = int(120)       # auto-tytuł skrócony do N znaków


@contextmanager
def _conn():
    conn = sqlite3.connect(SESSIONS_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_sessions_db() -> None:
    """Tworzy tabele sessions i messages jeśli nie istnieją."""
    import os
    os.makedirs(settings.data_path, exist_ok=True)
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """)
        conn.commit()
    logger.info("[F4] Sessions DB initialized: %s", SESSIONS_DB_PATH)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(title: str = "") -> dict:
    """Tworzy nową sesję, zwraca dict z id/title/created_at."""
    session_id = uuid.uuid4().hex[:16]
    now = _now()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, title[:_TITLE_MAX_LEN], now, now),
        )
        conn.commit()
    logger.debug("[F4] Nowa sesja: %s", session_id)
    return {"id": session_id, "title": title, "created_at": now, "updated_at": now}


def list_sessions(limit: int = 50, offset: int = 0) -> list[dict]:
    """Zwraca listę sesji posortowanych od najnowszej."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> Optional[dict]:
    """Zwraca sesję po ID lub None."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def update_session_title(session_id: str, title: str) -> bool:
    """Aktualizuje tytuł sesji."""
    now = _now()
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title[:_TITLE_MAX_LEN], now, session_id),
        )
        conn.commit()
    return cur.rowcount > 0


def delete_session(session_id: str) -> bool:
    """Usuwa sesję i jej wiadomości (CASCADE)."""
    with _conn() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    logger.info("[F4] Usunięto sesję: %s", session_id)
    return cur.rowcount > 0


def add_message(session_id: str, role: str, content: str) -> dict:
    """Dodaje wiadomość do sesji, aktualizuje updated_at sesji."""
    now = _now()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        conn.commit()
        msg_id = cur.lastrowid
    return {"id": msg_id, "session_id": session_id, "role": role, "content": content, "created_at": now}


def get_messages(session_id: str, limit: int = _MAX_HISTORY, offset: int = 0) -> list[dict]:
    """Zwraca wiadomości sesji w kolejności chronologicznej."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC LIMIT ? OFFSET ?",
            (session_id, limit, offset),
        ).fetchall()
    return [dict(r) for r in rows]


def get_history_for_llm(session_id: str, max_messages: int = _MAX_HISTORY) -> list[dict]:
    """Zwraca ostatnie N wiadomości jako listę {role, content} do kontekstu LLM."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, max_messages),
        ).fetchall()
    # Odwróć — najstarsze pierwsze
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def auto_title_from_message(content: str) -> str:
    """Generuje auto-tytuł z pierwszej wiadomości użytkownika."""
    short = content.strip().replace("\n", " ")
    return short[:_TITLE_MAX_LEN] if len(short) <= _TITLE_MAX_LEN else short[:_TITLE_MAX_LEN - 1] + "…"
