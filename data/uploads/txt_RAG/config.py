import os
from typing import Set

from pydantic import AnyHttpUrl

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # fallback dla starszych wersji


class Settings(BaseSettings):
    """Centralna konfiguracja backendu KlimtechRAG.

    Wartości można nadpisywać przez zmienne środowiskowe lub plik .env.
    """

    # --- Podstawowe serwisy ---
    qdrant_url: AnyHttpUrl = "http://localhost:6333"
    qdrant_collection: str = "klimtech_docs"

    llm_base_url: AnyHttpUrl = "http://localhost:8082/v1"
    llm_api_key: str = "sk-dummy"
    llm_model_name: str = "speakleash_Bielik-11B-v3.0-Instruct-Q8_0"

    # --- Modele embeddingowe ---
    embedding_model: str = "intfloat/multilingual-e5-large"

    # --- Pliki / ingest ---
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50 MB, można zmienić w .env

    # Dozwolone rozszerzenia dokumentów (Nextcloud, /ingest)
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
        ".mp3",
        ".mp4",
        ".jpeg",
        ".jpg",
        ".png",
    }

    # Dozwolone rozszerzenia kodu (git_sync)
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
    api_key: str | None = None  # jeśli None, auth wyłączone (dev)
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 60

    # --- Logowanie ---
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_json: bool = False

    # --- Dostęp do systemu plików (ls) ---
    # Katalog bazowy, poniżej którego wolno wykonywać operacje typu „ls”.
    fs_root: str = "/home/lobo/KlimtechRAG"

    # Limity bezpieczeństwa dla operacji na plikach
    fs_max_file_bytes_read: int = 512 * 1024  # 512 KB na pojedynczy plik read
    fs_max_file_bytes_grep: int = 1024 * 1024  # 1 MB na pojedynczy plik grep
    fs_max_matches_grep: int = 200  # maks. liczba dopasowań zwracanych przez grep

    class Config:
        env_prefix = "KLIMTECH_"
        env_file = os.path.join(os.path.expanduser("~"), "KlimtechRAG", ".env")
        case_sensitive = False
        extra = "ignore"  # ignoruj zmienne z .env bez prefiksu KLIMTECH_


settings = Settings()

