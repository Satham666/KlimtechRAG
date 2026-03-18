"""
KlimtechRAG Watchdog v3.0
Obserwuje foldery Nextcloud RAG_Dane/* i wywołuje /ingest_path dla nowych plików.
Działa jako singleton (PID file w logs/).
"""
import atexit
import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path

# Dodaj katalog projektu do sys.path (niezależnie od CWD)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend_app.config import settings
from backend_app.file_registry import init_db, register_file, mark_indexed, mark_failed

# ---------------------------------------------------------------------------
# Logging — do pliku i konsoli
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Singleton — PID file (lokalizacja musi zgadzać się ze stop_klimtech.py!)
# ---------------------------------------------------------------------------

PID_FILE = os.path.join(log_dir, "klimtech_watchdog.pid")   # logs/klimtech_watchdog.pid


def check_already_running():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)   # sprawdź czy proces żyje
            print(f"Watchdog już działa (PID: {old_pid}). Wychodzę.")
            sys.exit(0)
        except (ProcessLookupError, ValueError, OSError):
            pass   # stary PID file — możemy nadpisać

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))
    logger.info("Watchdog uruchomiony (PID: %d)", os.getpid())


def cleanup_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
        logger.info("PID file usunięty")


check_already_running()
atexit.register(cleanup_pid)

# ---------------------------------------------------------------------------
# Katalogi do obserwowania — JEDYNE źródło plików RAG
# ---------------------------------------------------------------------------

UPLOADS_RAG = settings.upload_base    # /media/lobo/BACKUP/.../data/uploads

WATCH_DIRS = [
    # Główne źródło plików
    f"{UPLOADS_RAG}/Doc_RAG",
    f"{UPLOADS_RAG}/Audio_RAG",
    f"{UPLOADS_RAG}/Video_RAG",
    f"{UPLOADS_RAG}/Images_RAG",
    f"{UPLOADS_RAG}/json_RAG",
    f"{UPLOADS_RAG}/pdf_RAG",
    f"{UPLOADS_RAG}/txt_RAG",
]

BACKEND_PORT = os.getenv("BACKEND_API_PORT", "8000")
INGEST_PATH_URL = f"http://localhost:{BACKEND_PORT}/ingest_path"   # ← /ingest_path (nie /ingest)
INGEST_TIMEOUT = int(os.getenv("INGEST_TIMEOUT", "7200"))
MAX_RETRIES = int(os.getenv("INGEST_MAX_RETRIES", "3"))

# Rozszerzenia które można zindeksować jako tekst
TEXT_INDEXABLE = {".pdf", ".txt", ".md", ".py", ".js", ".ts",
                  ".json", ".yml", ".yaml", ".doc", ".docx", ".odt", ".rtf"}

file_queue: queue.Queue = queue.Queue()
processing_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Czekanie na stabilność pliku (upload w toku)
# ---------------------------------------------------------------------------

def wait_for_stable_file(path: str, max_attempts: int = 10, delay: float = 2.0) -> bool:
    last_size = -1
    for _ in range(max_attempts):
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            return False
        if size == last_size and size > 0:
            return True
        last_size = size
        time.sleep(delay)
    return False


# ---------------------------------------------------------------------------
# Ingest przez /ingest_path (wydajniejsze niż multipart upload)
# ---------------------------------------------------------------------------

def ingest_file_via_api(file_path: str, retries: int = MAX_RETRIES) -> bool:
    file_name = os.path.basename(file_path)
    suffix = os.path.splitext(file_name)[1].lower()

    if suffix not in TEXT_INDEXABLE:
        logger.info("[WATCH] %s — format %s zapisany ale nie indeksowalny (audio/video/img)", file_name, suffix)
        return True   # nie błąd — po prostu nie indeksujemy

    file_size_mb = os.path.getsize(file_path) / 1024 / 1024

    for attempt in range(1, retries + 1):
        try:
            logger.info(
                "[%s] Ingest (%.1f MB), próba %d/%d", file_name, file_size_mb, attempt, retries
            )
            response = requests.post(
                INGEST_PATH_URL,
                json={"path": file_path},   # ← JSON z ścieżką (nie multipart)
                timeout=INGEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                chunks = result.get("chunks_processed", 0)
                logger.info("[%s] ✅ %d chunków w Qdrant", file_name, chunks)
                return True

            elif response.status_code == 429:
                wait_time = 60
                logger.warning("[%s] Rate limit, czekam %ds", file_name, wait_time)
                time.sleep(wait_time)
                continue

            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error("[%s] ❌ %s", file_name, error_msg)
                if attempt < retries:
                    time.sleep(attempt * 30)
                    continue
                mark_failed(file_path, error_msg)
                return False

        except requests.exceptions.Timeout:
            error_msg = f"Timeout po {INGEST_TIMEOUT}s"
            logger.error("[%s] %s (próba %d/%d)", file_name, error_msg, attempt, retries)
            if attempt < retries:
                time.sleep(attempt * 60)
                continue
            mark_failed(file_path, error_msg)
            return False

        except requests.exceptions.ConnectionError as e:
            error_msg = f"ConnectionError: {str(e)[:100]}"
            logger.error("[%s] %s", file_name, error_msg)
            if attempt < retries:
                time.sleep(attempt * 30)
                continue
            mark_failed(file_path, error_msg)
            return False

        except Exception as e:
            mark_failed(file_path, str(e)[:100])
            logger.error("[%s] Exception: %s", file_name, e)
            return False

    return False


# ---------------------------------------------------------------------------
# Procesor kolejki (jeden wątek — sekwencyjne przetwarzanie)
# ---------------------------------------------------------------------------

def queue_processor():
    while True:
        try:
            file_path = file_queue.get(timeout=1)
            if file_path is None:
                break
            with processing_lock:
                ingest_file_via_api(file_path)
            file_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error("Błąd w procesorze kolejki: %s", str(e)[:200])


# ---------------------------------------------------------------------------
# Handler zdarzeń systemu plików
# ---------------------------------------------------------------------------

class NewFileHandler(FileSystemEventHandler):
    def _handle(self, file_path: str):
        if any(file_path.lower().endswith(ext) for ext in settings.allowed_extensions_docs):
            logger.info("[WATCH] Nowy plik: %s", os.path.basename(file_path))
            if wait_for_stable_file(file_path):
                register_file(file_path)
                file_queue.put(file_path)
            else:
                logger.warning("[WATCH] Plik zniknął/niestabilny: %s", file_path)

    def on_created(self, event):
        if not event.is_directory:
            self._handle(str(event.src_path))

    def on_moved(self, event):
        if not event.is_directory:
            # Nextcloud często robi move (tmp → docelowy) przy uploadzie
            self._handle(str(event.dest_path) if event.dest_path else str(event.src_path))


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    processor_thread = threading.Thread(target=queue_processor, daemon=True)
    processor_thread.start()

    event_handler = NewFileHandler()
    observer = Observer()

    print("\n" + "=" * 55)
    print("  KlimtechRAG Watchdog v3.0")
    print(f"  Backend: {INGEST_PATH_URL}")
    print(f"  Timeout: {INGEST_TIMEOUT}s | Retries: {MAX_RETRIES}")
    print("=" * 55 + "\n")

    active_dirs = 0
    for dir_path in WATCH_DIRS:
        if os.path.exists(dir_path):
            logger.info("📂 Monitoring: %s", dir_path)
            observer.schedule(event_handler, dir_path, recursive=True)
            active_dirs += 1
        else:
            logger.warning("⚠️  Folder nie istnieje (tworzę): %s", dir_path)
            try:
                os.makedirs(dir_path, exist_ok=True)
                observer.schedule(event_handler, dir_path, recursive=True)
                active_dirs += 1
            except Exception as e:
                logger.error("Nie mogę stworzyć folderu: %s — %s", dir_path, e)

    logger.info("Monitoruję %d folderów", active_dirs)
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
