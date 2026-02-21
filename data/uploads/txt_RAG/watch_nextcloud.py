import logging
import os
import queue
import threading
import time
from pathlib import Path

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend_app.config import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("klimtechrag.watcher")


WATCH_DIRS = [
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/Doc_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/Audio_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/Video_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/Images_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/json_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/pdf_RAG",
    "/home/lobo/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/txt_RAG",
    "/home/lobo/KlimtechRAG/data/uploads/Doc_RAG",
    "/home/lobo/KlimtechRAG/data/uploads/Audio_RAG",
    "/home/lobo/KlimtechRAG/data/uploads/Video_RAG",
    "/home/lobo/KlimtechRAG/data/uploads/Images_RAG",
    "/home/lobo/KlimtechRAG/data/uploads/json_RAG",
    "/home/lobo/KlimtechRAG/data/uploads/pdf_RAG",
    "/home/lobo/KlimtechRAG/data/uploads/txt_RAG",
]

API_URL = f"http://localhost:{os.getenv('BACKEND_API_PORT', '8000')}/ingest"
INGEST_TIMEOUT = int(os.getenv("INGEST_TIMEOUT", "1800"))
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
                logger.error(
                    "[%s] Błąd HTTP %d: %s",
                    file_name,
                    response.status_code,
                    response.text[:500],
                )
                if attempt < retries:
                    wait_time = attempt * 30
                    logger.info("[%s] Ponowna próba za %ds...", file_name, wait_time)
                    time.sleep(wait_time)
                    continue
                return False

        except requests.exceptions.Timeout:
            logger.error(
                "[%s] Timeout po %ds (próba %d/%d)",
                file_name,
                INGEST_TIMEOUT,
                attempt,
                retries,
            )
            if attempt < retries:
                wait_time = attempt * 60
                logger.info("[%s] Ponowna próba za %ds...", file_name, wait_time)
                time.sleep(wait_time)
                continue
            return False

        except requests.exceptions.ConnectionError as e:
            logger.error("[%s] Błąd połączenia: %s", file_name, str(e)[:200])
            if attempt < retries:
                wait_time = attempt * 30
                logger.info("[%s] Ponowna próba za %ds...", file_name, wait_time)
                time.sleep(wait_time)
                continue
            return False

        except Exception as e:
            logger.error("[%s] Nieoczekiwany błąd: %s", file_name, str(e)[:200])
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

        file_path = event.src_path
        if any(
            file_path.lower().endswith(ext) for ext in settings.allowed_extensions_docs
        ):
            logger.info("[WATCH] Nowy plik: %s", os.path.basename(file_path))
            if wait_for_stable_file(file_path):
                file_queue.put(file_path)
            else:
                logger.warning("[WATCH] Plik zniknął lub niestabilny: %s", file_path)

    def on_moved(self, event):
        if event.is_directory:
            return

        file_path = event.dest_path if event.dest_path else event.src_path
        if any(
            file_path.lower().endswith(ext) for ext in settings.allowed_extensions_docs
        ):
            if wait_for_stable_file(file_path):
                file_queue.put(file_path)
        else:
            logger.info(
                "[WATCH] Ignoruję plik binarny: %s", os.path.basename(file_path)
            )


if __name__ == "__main__":
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
