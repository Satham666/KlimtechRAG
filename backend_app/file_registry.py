import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .config import settings

DB_PATH = settings.file_registry_db
UPLOAD_BASE = settings.upload_base

WATCH_DIRS = [
    f"{UPLOAD_BASE}/Audio_RAG",
    f"{UPLOAD_BASE}/Doc_RAG",
    f"{UPLOAD_BASE}/Images_RAG",
    f"{UPLOAD_BASE}/json_RAG",
    f"{UPLOAD_BASE}/pdf_RAG",
    f"{UPLOAD_BASE}/txt_RAG",
    f"{UPLOAD_BASE}/Video_RAG",
]


@dataclass
class FileRecord:
    path: str
    filename: str
    extension: str
    directory: str
    size_bytes: int
    mtime: float
    content_hash: Optional[str]
    indexed_at: Optional[str]
    chunks_count: int
    status: str


def get_db_path() -> str:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                extension TEXT NOT NULL,
                directory TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                mtime REAL NOT NULL,
                content_hash TEXT,
                indexed_at TEXT,
                chunks_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_ext ON files(extension)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_files_dir ON files(directory)")
        conn.commit()


def compute_file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_directory(directory: str) -> List[dict]:
    files = []
    if not os.path.exists(directory):
        return files
    for entry in os.scandir(directory):
        if entry.is_file() and not entry.name.startswith("."):
            files.append(
                {
                    "path": entry.path,
                    "filename": entry.name,
                    "extension": os.path.splitext(entry.name)[1].lower(),
                    "size": entry.stat().st_size,
                    "mtime": entry.stat().st_mtime,
                }
            )
    return files


def scan_all_directories() -> List[dict]:
    all_files = []
    for dir_path in WATCH_DIRS:
        all_files.extend(scan_directory(dir_path))
    return all_files


def register_file(path: str, compute_hash: bool = False) -> Optional[int]:
    if not os.path.exists(path):
        return None

    filename = os.path.basename(path)
    extension = os.path.splitext(filename)[1].lower()
    directory = os.path.dirname(path)
    size = os.path.getsize(path)
    mtime = os.path.getmtime(path)

    content_hash = None
    if compute_hash and size < 10 * 1024 * 1024:
        try:
            content_hash = compute_file_hash(path)
        except Exception:
            pass

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO files (path, filename, extension, directory, size_bytes, mtime, content_hash, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(path) DO UPDATE SET
                size_bytes = excluded.size_bytes,
                mtime = excluded.mtime,
                content_hash = COALESCE(excluded.content_hash, content_hash),
                updated_at = CURRENT_TIMESTAMP
        """,
            (path, filename, extension, directory, size, mtime, content_hash),
        )
        conn.commit()
        return cursor.lastrowid



def find_duplicate_by_hash(content_hash: str):
    if not content_hash: return None
    with get_connection() as conn:
        row = conn.execute("SELECT path FROM files WHERE content_hash = ? LIMIT 1",(content_hash,)).fetchone()
        return row["path"] if row else None

def mark_indexed(path: str, chunks_count: int):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE files SET
                indexed_at = CURRENT_TIMESTAMP,
                chunks_count = ?,
                status = 'indexed',
                updated_at = CURRENT_TIMESTAMP
            WHERE path = ?
        """,
            (chunks_count, path),
        )
        conn.commit()


def mark_failed(path: str, error: str):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE files SET
                status = 'error',
                error_message = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE path = ?
        """,
            (error[:500], path),
        )
        conn.commit()


def get_pending_files() -> List[FileRecord]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM files WHERE status = 'pending' ORDER BY mtime DESC
        """).fetchall()
        return [_row_to_record(r) for r in rows]


def get_by_extension(ext: str) -> List[FileRecord]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE extension = ? ORDER BY filename", (ext.lower(),)
        ).fetchall()
        return [_row_to_record(r) for r in rows]


def get_by_status(status: str) -> List[FileRecord]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE status = ? ORDER BY updated_at DESC", (status,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]


def get_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        indexed = conn.execute(
            "SELECT COUNT(*) FROM files WHERE status = 'indexed'"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM files WHERE status = 'pending'"
        ).fetchone()[0]
        errors = conn.execute(
            "SELECT COUNT(*) FROM files WHERE status = 'error'"
        ).fetchone()[0]
        total_chunks = conn.execute(
            "SELECT COALESCE(SUM(chunks_count), 0) FROM files"
        ).fetchone()[0]

        by_ext = conn.execute("""
            SELECT extension, COUNT(*) as cnt, SUM(chunks_count) as chunks
            FROM files GROUP BY extension ORDER BY cnt DESC
        """).fetchall()

        indexed_today = conn.execute(
            "SELECT COUNT(*) FROM files WHERE status = 'indexed' "
            "AND date(indexed_at) = date('now')"
        ).fetchone()[0]

        return {
            "total_files": total,
            "indexed": indexed,
            "pending": pending,
            "errors": errors,
            "total_chunks": total_chunks,
            "indexed_today": indexed_today,
            "by_extension": [
                {"ext": r[0], "count": r[1], "chunks": r[2]} for r in by_ext
            ],
        }


def list_files(
    extension: Optional[str] = None, status: Optional[str] = None, limit: int = 100
) -> List[FileRecord]:
    with get_connection() as conn:
        query = "SELECT * FROM files WHERE 1=1"
        params = []

        if extension:
            query += " AND extension = ?"
            params.append(extension.lower())
        if status:
            query += " AND status = ?"
            params.append(status)

        query += f" ORDER BY filename LIMIT {limit}"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_record(r) for r in rows]


def sync_with_filesystem():
    registered = 0
    for dir_path in WATCH_DIRS:
        if not os.path.exists(dir_path):
            continue
        for entry in os.scandir(dir_path):
            if entry.is_file() and not entry.name.startswith("."):
                register_file(entry.path)
                registered += 1
    return registered


def _row_to_record(row: sqlite3.Row) -> FileRecord:
    return FileRecord(
        path=row["path"],
        filename=row["filename"],
        extension=row["extension"],
        directory=row["directory"],
        size_bytes=row["size_bytes"],
        mtime=row["mtime"],
        content_hash=row["content_hash"],
        indexed_at=row["indexed_at"],
        chunks_count=row["chunks_count"] or 0,
        status=row["status"],
    )


if __name__ == "__main__":
    init_db()
    print("Synchronizacja z systemem plików...")
    count = sync_with_filesystem()
    print(f"Zarejestrowano/odświeżono {count} plików")

    stats = get_stats()
    print(f"\nStatystyki:")
    print(f"  Pliki: {stats['total_files']}")
    print(f"  Zindeksowane: {stats['indexed']}")
    print(f"  Oczekujące: {stats['pending']}")
    print(f"  Błędy: {stats['errors']}")
    print(f"  Chunki: {stats['total_chunks']}")

    print(f"\nWg rozszerzenia:")
    for ext in stats["by_extension"][:10]:
        print(f"  {ext['ext']:8} {ext['count']:4} plików, {ext['chunks']:5} chunków")
