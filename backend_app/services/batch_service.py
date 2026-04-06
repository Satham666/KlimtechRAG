import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# W5: Batch Processing — asyncio queue z priorytetami i retry logic
# Kolejka: LOW=2, NORMAL=1, HIGH=0 (niższa liczba = wyższy priorytet)
# Retry: exponential backoff (2^n sekundy, max 3 próby)
# ---------------------------------------------------------------------------

_MAX_RETRIES = int(3)
_BASE_BACKOFF = float(2.0)   # sekundy
_QUEUE_MAX = int(500)


class Priority(int, Enum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass(order=True)
class BatchItem:
    priority: int
    enqueued_at: float = field(compare=False, default_factory=time.monotonic)
    file_path: str = field(compare=False, default="")
    retries: int = field(compare=False, default=0)
    task_id: Optional[str] = field(compare=False, default=None)


class BatchQueue:
    """Asyncio priority queue do przetwarzania plików w tle."""

    def __init__(self) -> None:
        from collections import deque
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=_QUEUE_MAX)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._stats = {"processed": 0, "errors": 0, "retried": 0}
        self._log: deque = deque(maxlen=100)   # log ostatnich 100 operacji

    def enqueue(self, file_path: str, priority: Priority = Priority.NORMAL, task_id: Optional[str] = None) -> bool:
        """Dodaje plik do kolejki. Zwraca False gdy kolejka pełna."""
        item = BatchItem(priority=priority.value, file_path=file_path, task_id=task_id)
        try:
            self._queue.put_nowait(item)
            logger.debug("[W5] Enqueue: %s (priority=%s)", file_path, priority.name)
            return True
        except asyncio.QueueFull:
            logger.warning("[W5] Kolejka pełna — pominięto: %s", file_path)
            return False

    async def start_worker(self) -> None:
        """Uruchamia worker loop jako asyncio task."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("[W5] Batch worker uruchomiony")

    async def stop_worker(self) -> None:
        """Zatrzymuje worker loop."""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("[W5] Batch worker zatrzymany. Stats: %s", self._stats)

    async def _worker_loop(self) -> None:
        """Główna pętla workera — pobiera z kolejki i indeksuje."""
        from .ingest_service import ingest_file_background

        while self._running:
            try:
                item: BatchItem = await asyncio.wait_for(self._queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            await self._process_item(item, ingest_file_background)
            self._queue.task_done()

    async def _process_item(self, item: BatchItem, ingest_fn) -> None:
        """Przetwarza jeden element z retry logic."""
        try:
            logger.info("[W5] Processing: %s (retry=%d)", item.file_path, item.retries)
            await asyncio.get_event_loop().run_in_executor(None, ingest_fn, item.file_path)
            self._stats["processed"] += 1
            self._log.append({"path": item.file_path, "status": "ok", "ts": time.time()})
        except Exception as e:
            logger.warning("[W5] Błąd przetwarzania %s: %s", item.file_path, e)
            self._stats["errors"] += 1
            if item.retries < _MAX_RETRIES:
                backoff = _BASE_BACKOFF ** item.retries
                logger.info("[W5] Retry za %.1fs: %s", backoff, item.file_path)
                await asyncio.sleep(backoff)
                item.retries += 1
                self._stats["retried"] += 1
                try:
                    self._queue.put_nowait(item)
                except asyncio.QueueFull:
                    logger.error("[W5] Kolejka pełna przy retry: %s", item.file_path)
            else:
                logger.error("[W5] Wyczerpano retries dla: %s", item.file_path)
                self._log.append({"path": item.file_path, "status": "failed", "ts": time.time()})

    def clear(self) -> int:
        """Czyści wszystkie oczekujące elementy z kolejki. Zwraca liczbę usuniętych."""
        cleared = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
                cleared += 1
            except Exception:
                break
        logger.info("[W5] Kolejka wyczyszczona: %d elementów", cleared)
        return cleared

    def history(self, limit: int = 50) -> list:
        """Zwraca ostatnie N operacji batch z logiem."""
        items = list(self._log)
        return items[-limit:]

    def stats(self) -> dict:
        """Zwraca statystyki kolejki."""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "running": self._running,
        }


# Singleton
_batch_queue: Optional[BatchQueue] = None


def get_batch_queue() -> BatchQueue:
    """Zwraca globalną kolejkę batch (lazy init)."""
    global _batch_queue
    if _batch_queue is None:
        _batch_queue = BatchQueue()
    return _batch_queue
