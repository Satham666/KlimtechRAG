import logging
import os
from typing import Set

from pydantic import AnyHttpUrl

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # fallback dla starszych wersji


def _detect_base() -> str:
    from pathlib import Path

    env = os.environ.get("KLIMTECH_BASE_PATH", "").strip()
    if env and Path(env).exists():
        return env
    backup_path = Path("/media/lobo/BACKUP/KlimtechRAG")
    if backup_path.exists():
        return str(backup_path)
    return "/media/lobo/BACKUP/KlimtechRAG"


BASE = _detect_base()


class Settings(BaseSettings):
    """Centralna konfiguracja backendu KlimtechRAG.

    Wartości można nadpisywać przez zmienne środowiskowe lub plik .env.
    Prefiks zmiennych: KLIMTECH_
    """

    # --- Ścieżki bazowe ---
    base_path: str = BASE
    data_path: str = f"{BASE}/data"
    upload_base: str = f"{BASE}/data/uploads"  # JEDYNA ścieżka dla plików RAG
    file_registry_db: str = f"{BASE}/data/file_registry.db"

    # --- Nextcloud ---
    nextcloud_container: str = "nextcloud"  # nazwa kontenera Podman
    nextcloud_user: str = "admin"  # użytkownik Nextcloud

    # --- LLM ---
    llm_base_url: AnyHttpUrl = "http://localhost:8082/v1"
    llm_api_key: str = "sk-dummy"
    llm_model_name: str = ""  # pusty = auto-detect

    # --- Embedding ---
    embedding_model: str = "intfloat/multilingual-e5-large"
    # cpu / cuda:0 / cuda:0,cuda:1 (przyszłe karty)
    embedding_device: str = os.getenv("KLIMTECH_EMBEDDING_DEVICE", "cpu")

    # --- Qdrant ---
    qdrant_url: AnyHttpUrl = "http://localhost:6333"
    qdrant_collection: str = "klimtech_docs"

    # --- Pliki / ingest ---
    max_file_size_bytes: int = 200 * 1024 * 1024  # 200 MB

    # Rozszerzenia obsługiwane przez ingest (tekst/dokumenty)
    allowed_extensions_docs: Set[str] = {
        ".pdf",
        ".md",
        ".txt",
        ".py",
        ".js",
        ".ts",
        ".json",
        ".yml",
        ".yaml",
        ".doc",
        ".docx",
        ".odt",
        ".rtf",
        ".mp3",
        ".wav",
        ".ogg",
        ".flac",
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
    }

    # Rozszerzenia kodu (git_sync / repo ingest)
    allowed_extensions_code: Set[str] = {
        ".py",
        ".js",
        ".ts",
        ".json",
        ".yml",
        ".yaml",
        ".md",
        ".txt",
    }

    # --- Bezpieczeństwo / API ---
    api_key: str | None = None  # None = auth wyłączone (dev)
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 60

    # --- Logowanie ---
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_json: bool = False

    # --- Filesystem tool ---
    fs_root: str = BASE
    fs_max_file_bytes_read: int = 512 * 1024  # 512 KB
    fs_max_file_bytes_grep: int = 1024 * 1024  # 1 MB
    fs_max_matches_grep: int = 200

    class Config:
        env_prefix = "KLIMTECH_"
        env_file = os.path.join(BASE, ".env")
        case_sensitive = False
        extra = "ignore"


def setup_logging():
    """
    Konfiguruje jeden logger dla całej aplikacji KlimtechRAG.
    Wszystkie moduły używają tego samego loggera -> jeden plik logów.
    """
    import logging
    from pathlib import Path

    log_dir = os.path.join(BASE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "backend.log")

    log_level = getattr(logging, os.getenv("LOG_LEVEL", "DEBUG").upper(), logging.DEBUG)

    # Format z prefiksem modułu
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Root logger dla całej aplikacji
    root_logger = logging.getLogger("klimtechrag")
    root_logger.setLevel(log_level)

    # Usuń stare handlery (zapobiegaj duplikatom)
    root_logger.handlers.clear()

    # FileHandler - główny plik logów
    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)

    # StreamHandler - STDERR (widoczny w terminalu)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)  # INFO na STDOUT, DEBUG tylko do pliku
    root_logger.addHandler(stream_handler)

    return root_logger


def get_logger(name: str = "klimtechrag"):
    """
    Pobiera logger dla modułu.
    Użycie: logger = get_logger(__name__) lub get_logger("klimtechrag.mój_moduł")
    """
    return logging.getLogger(name)


def validate_config() -> None:
    """Weryfikuje środowisko przed startem backendu. Pada szybko z czytelnym komunikatem.

    Sprawdza: katalog bazowy, plik .env, Qdrant, llama-server (port 8082).
    Błędy krytyczne → sys.exit(1). Ostrzeżenia → log WARN, kontynuuj.
    """
    import socket
    import sys
    import urllib.request
    from pathlib import Path

    errors: list[str] = []
    warnings: list[str] = []

    # 1. Katalog bazowy
    if not Path(BASE).exists():
        errors.append(f"Katalog bazowy nie istnieje: {BASE}")

    # 2. Plik .env
    env_file = Path(BASE) / ".env"
    if not env_file.exists():
        warnings.append(
            f"Brak pliku .env: {env_file} (kontynuuję z domyślnymi wartościami)"
        )

    # 3. Qdrant ping
    try:
        urllib.request.urlopen("http://localhost:6333/healthz", timeout=3)
    except Exception:
        errors.append(
            "Qdrant niedostępny na localhost:6333 — uruchom: podman start qdrant"
        )

    # 4. Port 8082 (llama-server) — tylko ostrzeżenie, LLM jest opcjonalny na starcie
    try:
        with socket.create_connection(("localhost", 8082), timeout=2):
            pass
    except OSError:
        warnings.append(
            "llama-server niedostępny na porcie 8082 — modele LLM nie będą działać"
            " do czasu uruchomienia serwera"
        )

    for w in warnings:
        logging.getLogger("klimtechrag").warning("⚠️  %s", w)

    if errors:
        for e in errors:
            logging.getLogger("klimtechrag").critical("❌ STARTUP ERROR: %s", e)
        sys.exit(1)


settings = Settings()
