import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend_app.config import settings
from backend_app.file_registry import init_db, register_file, mark_indexed, mark_failed

log_dir = os.path.join(settings.base_path, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "watchdog.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
logger = logging.getLogger("klimtechrag.watcher")

PID_FILE = os.path.join(log_dir, "klimtech_watchdog.pid")


def check_already_running():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            old_pid = f.read().strip()
        try:
            os.kill(int(old_pid), 0)
            print(f"Watchdog już działa (PID: {old_pid}). Wychodzę.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            pass

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    logger.info("Watchdog uruchomiony (PID: %d)", os.getpid())


def cleanup_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
        logger.info("PID file usunięty")


import atexit

check_already_running()
atexit.register(cleanup_pid)

NEXTCLOUD_RAG = f"{settings.nextcloud_base}"
UPLOADS_RAG = f"{settings.upload_base}"

WATCH_DIRS = [
    f"{NEXTCLOUD_RAG}/Doc_RAG",
    f"{NEXTCLOUD_RAG}/Audio_RAG",
    f"{NEXTCLOUD_RAG}/Video_RAG",
    f"{NEXTCLOUD_RAG}/Images_RAG",
    f"{NEXTCLOUD_RAG}/json_RAG",
    f"{NEXTCLOUD_RAG}/pdf_RAG",
    f"{NEXTCLOUD_RAG}/txt_RAG",
    f"{UPLOADS_RAG}/Doc_RAG",
    f"{UPLOADS_RAG}/Audio_RAG",
    f"{UPLOADS_RAG}/Video_RAG",
    f"{UPLOADS_RAG}/Images_RAG",
    f"{UPLOADS_RAG}/json_RAG",
    f"{UPLOADS_RAG}/pdf_RAG",
    f"{UPLOADS_RAG}/txt_RAG",
]

API_URL = f"http://localhost:{os.getenv('BACKEND_API_PORT', '8000')}/ingest_path"
INGEST_TIMEOUT = int(os.getenv("INGEST_TIMEOUT", "7200"))
MAX_RETRIES = int(os.getenv("INGEST_MAX_RETRIES", "3"))

file_queue: queue.Queue = queue.Queue()
processing_lock = threading.Lock()


def wait_for_stable_file(path: str, max_attempts: int = 10, delay: float = 2.0) -> bool:
    last_size = -1
    for _ in range(max_attempts):
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            return False
        if size == last_size:
            return True
        last_size = size
        time.sleep(delay)
    return False


def ingest_file(file_path: str, retries: int = MAX_RETRIES) -> bool:
    file_name = os.path.basename(file_path)
    file_size_mb = os.path.getsize(file_path) / 1024 / 1024

    for attempt in range(1, retries + 1):
        try:
            logger.info(
                "[%s] Przetwarzanie %s (%.1f MB), próba %d/%d",
                file_name,
                file_name,
                file_size_mb,
                attempt,
                retries,
            )

            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
                response = requests.post(API_URL, files=files, timeout=INGEST_TIMEOUT)

            if response.status_code == 200:
                result = response.json()
                chunks = result.get("chunks_processed", 0)
                logger.info("[%s] OK - zaindeksowano %d fragmentów", file_name, chunks)
                mark_indexed(file_path, chunks)
                return True
            elif response.status_code == 429:
                wait_time = 60
                logger.warning(
                    "[%s] Rate limit, czekam %ds przed ponowną próbą",
                    file_name,
                    wait_time,
                )
                time.sleep(wait_time)
                continue
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error("[%s] Błąd %s", file_name, error_msg)
                if attempt < retries:
                    wait_time = attempt * 30
                    logger.info("[%s] Ponowna próba za %ds...", file_name, wait_time)
                    time.sleep(wait_time)
                    continue
                mark_failed(file_path, error_msg)
                return False

        except requests.exceptions.Timeout:
            error_msg = f"Timeout po {INGEST_TIMEOUT}s"
            logger.error(
                "[%s] %s (próba %d/%d)", file_name, error_msg, attempt, retries
            )
            if attempt < retries:
                wait_time = attempt * 60
                logger.info("[%s] Ponowna próba za %ds...", file_name, wait_time)
                time.sleep(wait_time)
                continue
            mark_failed(file_path, error_msg)
            return False

        except requests.exceptions.ConnectionError as e:
            error_msg = f"ConnectionError: {str(e)[:100]}"
            logger.error("[%s] %s", file_name, error_msg)
            if attempt < retries:
                wait_time = attempt * 30
                logger.info("[%s] Ponowna próba za %ds...", file_name, wait_time)
                time.sleep(wait_time)
                continue
            mark_failed(file_path, error_msg)
            return False

        except Exception as e:
            error_msg = f"Exception: {str(e)[:100]}"
            logger.error("[%s] %s", file_name, error_msg)
            mark_failed(file_path, error_msg)
            return False

    return False


def queue_processor():
    while True:
        try:
            file_path = file_queue.get(timeout=1)
            if file_path is None:
                break

            with processing_lock:
                ingest_file(file_path)

            file_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error("Błąd w procesorze kolejki: %s", str(e)[:200])


class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return

        file_path = str(event.src_path)
        if any(
            file_path.lower().endswith(ext) for ext in settings.allowed_extensions_docs
        ):
            logger.info("[WATCH] Nowy plik: %s", os.path.basename(file_path))
            if wait_for_stable_file(file_path):
                register_file(file_path)
                file_queue.put(file_path)
            else:
                logger.warning("[WATCH] Plik zniknął lub niestabilny: %s", file_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        file_path = str(event.dest_path) if event.dest_path else str(event.src_path)
        if any(
            file_path.lower().endswith(ext) for ext in settings.allowed_extensions_docs
        ):
            if wait_for_stable_file(file_path):
                register_file(file_path)
                file_queue.put(file_path)
        else:
            logger.info(
                "[WATCH] Ignoruję plik binarny: %s", os.path.basename(file_path)
            )


if __name__ == "__main__":
    init_db()
    processor_thread = threading.Thread(target=queue_processor, daemon=True)
    processor_thread.start()

    event_handler = NewFileHandler()
    observer = Observer()

    print("\n" + "=" * 50)
    print("  KlimtechRAG Watchdog v2.0")
    print(f"  Timeout: {INGEST_TIMEOUT}s | Retries: {MAX_RETRIES}")
    print("=" * 50 + "\n")

    for dir_path in WATCH_DIRS:
        if os.path.exists(dir_path):
            logger.info("Monitoring: %s", dir_path)
            observer.schedule(event_handler, dir_path, recursive=True)
        else:
            logger.warning("Folder nie istnieje: %s", dir_path)

    observer.start()

    try:
        while True:
            time.sleep(5)
            q_size = file_queue.qsize()
            if q_size > 0:
                logger.info("Pliki w kolejce: %d", q_size)
    except KeyboardInterrupt:
        logger.info("Zatrzymywanie...")
        observer.stop()
        file_queue.put(None)
        observer.join()
        processor_thread.join(timeout=5)
        logger.info("Zatrzymano.")
