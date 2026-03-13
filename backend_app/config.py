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
    home_path = Path.home() / "KlimtechRAG"
    if home_path.exists():
        return str(home_path)
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
    upload_base: str = f"{BASE}/data/uploads"          # backup / lokalny upload
    nextcloud_base: str = (                            # ← GŁÓWNE MIEJSCE PLIKÓW
        f"{BASE}/data/nextcloud/data/admin/files/RAG_Dane"
    )
    file_registry_db: str = f"{BASE}/data/file_registry.db"

    # --- Nextcloud ---
    nextcloud_container: str = "nextcloud"             # nazwa kontenera Podman
    nextcloud_user: str = "admin"                      # użytkownik Nextcloud

    # --- LLM ---
    llm_base_url: AnyHttpUrl = "http://localhost:8082/v1"
    llm_api_key: str = "sk-dummy"
    llm_model_name: str = ""                           # pusty = auto-detect

    # --- Embedding ---
    embedding_model: str = "intfloat/multilingual-e5-large"
    # cpu / cuda:0 / cuda:0,cuda:1 (przyszłe karty)
    embedding_device: str = os.getenv("KLIMTECH_EMBEDDING_DEVICE", "cpu")

    # --- Qdrant ---
    qdrant_url: AnyHttpUrl = "http://localhost:6333"
    qdrant_collection: str = "klimtech_docs"

    # --- Open WebUI ---
    owui_port: int = 3000
    owui_data_dir: str = f"{BASE}/data/open-webui"
    owui_container: str = "open-webui"

    # --- Pliki / ingest ---
    max_file_size_bytes: int = 200 * 1024 * 1024       # 200 MB

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
    api_key: str | None = None                         # None = auth wyłączone (dev)
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 60

    # --- Logowanie ---
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_json: bool = False

    # --- Filesystem tool ---
    fs_root: str = BASE
    fs_max_file_bytes_read: int = 512 * 1024           # 512 KB
    fs_max_file_bytes_grep: int = 1024 * 1024          # 1 MB
    fs_max_matches_grep: int = 200

    class Config:
        env_prefix = "KLIMTECH_"
        env_file = os.path.join(BASE, ".env")
        case_sensitive = False
        extra = "ignore"


settings = Settings()
