import asyncio
import logging
import os
import time

from ..config import settings
from ..file_registry import (
    WATCH_DIRS,
    get_connection,
    register_file,
    scan_directory,
)

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# H2: Watcher — asyncio background task monitorujący WATCH_DIRS
# Uruchamiany w lifespan() backendu; zastępuje zewnętrzny watch_nextcloud.py
# Flaga: KLIMTECH_WATCHER_ENABLED=true (domyślnie false — fallback na skrypt)
# ---------------------------------------------------------------------------

WATCHER_ENABLED: bool = (
    os.getenv("KLIMTECH_WATCHER_ENABLED", "false").lower() == "true"
)
WATCHER_INTERVAL: int = int(os.getenv("KLIMTECH_WATCHER_INTERVAL", "30"))  # sekundy


def _get_known_paths() -> set[str]:
    """Zwraca zbiór ścieżek już zarejestrowanych w file_registry."""
    try:
        with get_connection() as conn:
            rows = conn.execute("SELECT path FROM files").fetchall()
        return {r["path"] for r in rows}
    except Exception:
        return set()


def _find_new_files() -> list[dict]:
    """Skanuje WATCH_DIRS i zwraca pliki nieobecne w rejestrze."""
    known = _get_known_paths()
    new_files = []
    for watch_dir in WATCH_DIRS:
        for entry in scan_directory(watch_dir):
            if entry["path"] not in known:
                new_files.append(entry)
    return new_files


async def watch_loop() -> None:
    """Pętla asyncio — sprawdza nowe pliki co WATCHER_INTERVAL sekund."""
    from ..services.ingest_service import ingest_file_background

    logger.info(
        "[H2] Watcher uruchomiony (interval=%ds, dirs=%d)",
        WATCHER_INTERVAL,
        len(WATCH_DIRS),
    )
    while True:
        try:
            new_files = await asyncio.get_event_loop().run_in_executor(
                None, _find_new_files
            )
            if new_files:
                logger.info("[H2] Nowe pliki do zaindeksowania: %d", len(new_files))
            for f in new_files:
                try:
                    register_file(f["path"])
                    await asyncio.get_event_loop().run_in_executor(
                        None, ingest_file_background, f["path"]
                    )
                    logger.info("[H2] Zaindeksowano: %s", f["filename"])
                except Exception as e:
                    logger.warning("[H2] Błąd ingestu %s: %s", f["filename"], e)
        except asyncio.CancelledError:
            logger.info("[H2] Watcher zatrzymany")
            break
        except Exception as e:
            logger.exception("[H2] Nieoczekiwany błąd watchera: %s", e)

        await asyncio.sleep(WATCHER_INTERVAL)
