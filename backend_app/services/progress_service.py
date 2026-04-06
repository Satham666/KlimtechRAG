import asyncio
import json
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, Optional

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Progress Service — śledzenie postępu ingestu (D2)
# SSE stream per task_id: parsowanie → chunking → embedding → zapis
# ---------------------------------------------------------------------------

_MAX_EVENTS = 200       # max zdarzeń w kolejce na task
_TASK_TTL = 600         # czas życia zadania (10 min)


class ProgressTask:
    """Pojedyncze zadanie ingestowania z kolejką SSE eventów."""

    def __init__(self, task_id: str, filename: str) -> None:
        self.task_id = task_id
        self.filename = filename
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_EVENTS)
        self.created_at = time.monotonic()
        self.done = False

    def emit(self, stage: str, message: str, current: int = 0, total: int = 0) -> None:
        """Emituje event postępu (thread-safe przez put_nowait)."""
        event = {
            "task_id": self.task_id,
            "filename": self.filename,
            "stage": stage,
            "message": message,
            "current": current,
            "total": total,
            "pct": int(current / total * 100) if total > 0 else 0,
            "ts": time.time(),
        }
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # stary event przepada — kolejka pełna

    def finish(self, chunks: int = 0, error: str = "") -> None:
        """Zamyka task z eventem końcowym."""
        self.done = True
        stage = "done" if not error else "error"
        msg = f"Zaindeksowano {chunks} chunków" if not error else f"Błąd: {error}"
        self.emit(stage, msg, chunks, chunks)
        try:
            self.queue.put_nowait(None)  # sentinel — zakończ stream
        except asyncio.QueueFull:
            pass


class ProgressTracker:
    """Rejestr aktywnych zadań ingestowania (singleton)."""

    def __init__(self) -> None:
        self._tasks: Dict[str, ProgressTask] = {}

    def create_task(self, filename: str) -> ProgressTask:
        """Tworzy nowe zadanie i zwraca je."""
        task_id = uuid.uuid4().hex[:12]
        task = ProgressTask(task_id, filename)
        self._tasks[task_id] = task
        self._cleanup_stale()
        logger.debug("[Progress] Nowe zadanie: %s → %s", task_id, filename)
        return task

    def get_task(self, task_id: str) -> Optional[ProgressTask]:
        return self._tasks.get(task_id)

    def _cleanup_stale(self) -> None:
        """Usuwa zadania starsze niż TTL."""
        now = time.monotonic()
        stale = [
            tid for tid, t in self._tasks.items()
            if now - t.created_at > _TASK_TTL
        ]
        for tid in stale:
            del self._tasks[tid]


# Singleton
_tracker = ProgressTracker()


def get_tracker() -> ProgressTracker:
    """Zwraca globalny tracker."""
    return _tracker


async def stream_progress(task_id: str) -> AsyncGenerator[str, None]:
    """Async generator SSE dla danego task_id.

    Wysyła eventy do klienta aż do zakończenia (None sentinel w kolejce).
    """
    tracker = get_tracker()
    task = tracker.get_task(task_id)

    if task is None:
        yield "data: " + json.dumps({"error": "Task not found", "task_id": task_id}) + "\n\n"
        return

    # Heartbeat żeby klient nie timeout-ował
    yield ": heartbeat\n\n"

    deadline = time.monotonic() + _TASK_TTL
    while time.monotonic() < deadline:
        try:
            event = await asyncio.wait_for(task.queue.get(), timeout=5.0)
        except asyncio.TimeoutError:
            yield ": ping\n\n"
            if task.done:
                break
            continue

        if event is None:  # sentinel
            yield "data: [DONE]\n\n"
            break

        yield "data: " + json.dumps(event) + "\n\n"

        if event.get("stage") in ("done", "error"):
            yield "data: [DONE]\n\n"
            break
