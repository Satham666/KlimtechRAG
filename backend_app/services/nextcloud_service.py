import logging
import os
import subprocess

from ..config import settings

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# Nextcloud Service — zapis plików i rescan
# Wydzielony z routes/ingest.py (A1b refaktoryzacja)
# ---------------------------------------------------------------------------

EXT_TO_DIR: dict[str, str] = {
    ".pdf": "pdf_RAG",
    ".txt": "txt_RAG",
    ".md": "txt_RAG",
    ".py": "txt_RAG",
    ".js": "txt_RAG",
    ".ts": "txt_RAG",
    ".json": "json_RAG",
    ".yml": "txt_RAG",
    ".yaml": "txt_RAG",
    ".mp3": "Audio_RAG",
    ".wav": "Audio_RAG",
    ".ogg": "Audio_RAG",
    ".flac": "Audio_RAG",
    ".mp4": "Video_RAG",
    ".avi": "Video_RAG",
    ".mkv": "Video_RAG",
    ".mov": "Video_RAG",
    ".jpg": "Images_RAG",
    ".jpeg": "Images_RAG",
    ".png": "Images_RAG",
    ".gif": "Images_RAG",
    ".bmp": "Images_RAG",
    ".webp": "Images_RAG",
    ".doc": "Doc_RAG",
    ".docx": "Doc_RAG",
    ".odt": "Doc_RAG",
    ".rtf": "Doc_RAG",
}

# Rozszerzenia które ingest potrafi przetworzyć na tekst
TEXT_INDEXABLE: set[str] = {
    ".pdf",
    ".txt",
    ".md",
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
}


def save_to_uploads(file_content: bytes, filename: str, ext: str) -> tuple[str, str]:
    """Zapisuje plik do odpowiedniego podfolderu uploads na podstawie rozszerzenia.

    Zwraca (ścieżka_docelowa, nazwa_podfolderu).
    """
    subdir = EXT_TO_DIR.get(ext, "Doc_RAG")
    target_dir = os.path.join(settings.upload_base, subdir)
    os.makedirs(target_dir, exist_ok=True)

    target_path = os.path.join(target_dir, filename)
    base_name = os.path.splitext(filename)[0]
    counter = 1
    while os.path.exists(target_path):
        target_path = os.path.join(target_dir, f"{base_name}_{counter}{ext}")
        counter += 1

    with open(target_path, "wb") as f:
        f.write(file_content)

    logger.info("[Upload] Zapisano: %s → %s", filename, target_path)
    return target_path, subdir


def rescan_nextcloud(subdir: str) -> None:
    """Wywołuje occ files:scan przez Podman — Nextcloud widzi nowe pliki.

    Nieblokujące — błąd nie zatrzymuje pipeline.
    """
    try:
        nc_path = f"/{settings.nextcloud_user}/files/RAG_Dane/{subdir}"
        result = subprocess.run(
            [
                "podman", "exec", settings.nextcloud_container,
                "php", "occ", "files:scan",
                "--path", nc_path, "--shallow",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info("[NC] Rescan OK: %s", nc_path)
        else:
            logger.warning("[NC] Rescan błąd (nie krytyczny): %s", result.stderr[:200])
    except subprocess.TimeoutExpired:
        logger.warning("[NC] Rescan timeout — Nextcloud może pokazać plik z opóźnieniem")
    except Exception as e:
        logger.warning("[NC] Rescan wyjątek: %s", e)
