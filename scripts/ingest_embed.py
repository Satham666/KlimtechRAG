#!/usr/bin/env python3
"""
ingest_embed.py — Standalone embedding skrypt dla KlimtechRAG
=============================================================
Skanuje modele_LLM/ i uruchamia wybrany model GGUF przez llama.cpp
jako serwer embeddingów (port 8083), następnie indeksuje dokumenty do Qdrant.

Użycie:
    python3 ingest_embed.py                        # Menu wyboru modelu
    python3 ingest_embed.py --file /ścieżka/plik   # Konkretny plik
    python3 ingest_embed.py --dir /ścieżka/katalog # Cały katalog
    python3 ingest_embed.py --model 1              # Numer z listy bez menu
"""

import os
import sys
import signal
import argparse
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

# ── Ustawienia GPU przed importem torch/transformers ──────────────────────────
os.environ.setdefault("HIP_VISIBLE_DEVICES", "0")
os.environ.setdefault("HSA_OVERRIDE_GFX_VERSION", "9.0.6")
os.environ.setdefault("GPU_MAX_ALLOC_PERCENT", "100")
os.environ.setdefault("HSA_ENABLE_SDMA", "0")

# ── Ścieżki ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path("/home/lobo/KlimtechRAG")
MODELE_DIR = BASE_DIR / "modele_LLM"
LLAMA_BIN  = BASE_DIR / "llama.cpp" / "build" / "bin" / "llama-server"
EMBED_PORT = 8083
EMBED_URL  = f"http://localhost:{EMBED_PORT}"

sys.path.insert(0, str(BASE_DIR))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = BASE_DIR / "logs" / "ingest_embed.log"
LOG_FILE.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("ingest_embed")

# ── Globalny proces llama-server ──────────────────────────────────────────────
_llama_proc: Optional[subprocess.Popen] = None


def _cleanup(signum=None, frame=None):
    """Cleanup przy Ctrl+C — zatrzymuje llama-server embedding."""
    global _llama_proc
    if _llama_proc and _llama_proc.poll() is None:
        logger.info("\n🛑 Zatrzymuję llama-server embedding (PID: %d)...", _llama_proc.pid)
        _llama_proc.terminate()
        try:
            _llama_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _llama_proc.kill()
        logger.info("✅ llama-server zatrzymany")
    print("\n👋 Do widzenia!")
    sys.exit(0)


signal.signal(signal.SIGINT, _cleanup)
signal.signal(signal.SIGTERM, _cleanup)


# ── Skanowanie modeli z modele_LLM/ ──────────────────────────────────────────

def skanuj_modele() -> list[dict]:
    """Skanuje modele_LLM/ rekurencyjnie i zwraca listę plików GGUF."""
    if not MODELE_DIR.exists():
        logger.error("Katalog modeli nie istnieje: %s", MODELE_DIR)
        return []

    pliki = sorted(MODELE_DIR.rglob("*.gguf"))
    modele = []
    for p in pliki:
        rozmiar_gb = p.stat().st_size / 1024**3
        # Pokaż podkatalog jeśli model jest w podkatalogu
        podkatalog = p.parent.name if p.parent != MODELE_DIR else ""
        modele.append({
            "sciezka": p,
            "nazwa": p.name,
            "rozmiar": rozmiar_gb,
            "podkatalog": podkatalog,
        })
    return modele


def wybierz_model(model_arg: Optional[str], modele: list[dict]) -> dict:
    """Interaktywny wybór modelu lub przez argument CLI."""
    if not modele:
        logger.error("Brak modeli GGUF w %s", MODELE_DIR)
        sys.exit(1)

    # --model 2 (numer)
    if model_arg and model_arg.isdigit():
        idx = int(model_arg) - 1
        if 0 <= idx < len(modele):
            return modele[idx]
        logger.error("Nieprawidłowy numer modelu: %s (dostępne 1-%d)", model_arg, len(modele))
        sys.exit(1)

    # Interaktywne menu
    print("\n" + "=" * 60)
    print("  DOSTĘPNE MODELE GGUF  —  modele_LLM/")
    print("=" * 60)
    for i, m in enumerate(modele, 1):
        podkat = f"[{m['podkatalog']}]  " if m["podkatalog"] else ""
        print(f"[{i}]  {podkat}{m['nazwa']}  ({m['rozmiar']:.1f} GB)")
    print("=" * 60)

    try:
        wybor = input("Wybierz numer modelu [1]: ").strip() or "1"
    except (KeyboardInterrupt, EOFError):
        _cleanup()

    if not wybor.isdigit() or not (1 <= int(wybor) <= len(modele)):
        logger.error("Nieprawidłowy wybór: %s", wybor)
        sys.exit(1)

    return modele[int(wybor) - 1]


# ── llama-server jako serwer embeddingów (port 8083) ─────────────────────────

def uruchom_llama_embed(model_info: dict) -> subprocess.Popen:
    """Uruchamia llama-server z --embedding na porcie 8083."""
    global _llama_proc

    if not LLAMA_BIN.exists():
        logger.error("Nie znaleziono llama-server: %s", LLAMA_BIN)
        sys.exit(1)

    sciezka = model_info["sciezka"]
    logger.info("🚀 Uruchamiam llama-server (embedding) na porcie %d...", EMBED_PORT)
    logger.info("   Model: %s", sciezka.name)

    cmd = [
        str(LLAMA_BIN),
        "-m", str(sciezka),
        "--host", "0.0.0.0",
        "--port", str(EMBED_PORT),
        "--embedding",       # tryb embeddingowy
        "-ngl", "-1",        # wszystkie warstwy na GPU
        "--pooling", "mean", # pooling mean dla embeddingów
        "-c", "512",         # krótki kontekst — embedding nie potrzebuje więcej
        "-b", "512",
        "-t", "8",
    ]

    env = os.environ.copy()
    env["HIP_VISIBLE_DEVICES"] = "0"
    env["HSA_OVERRIDE_GFX_VERSION"] = "9.0.6"
    env["GPU_MAX_ALLOC_PERCENT"] = "100"
    env["HSA_ENABLE_SDMA"] = "0"

    log_out = open(BASE_DIR / "logs" / "embed_server_stdout.log", "w")
    log_err = open(BASE_DIR / "logs" / "embed_server_stderr.log", "w")

    proc = subprocess.Popen(cmd, env=env, stdout=log_out, stderr=log_err)
    _llama_proc = proc

    logger.info("⏳ Czekam aż llama-server będzie gotowy...")
    import requests
    for i in range(30):
        time.sleep(1)
        try:
            r = requests.get(f"{EMBED_URL}/health", timeout=2)
            if r.status_code == 200:
                logger.info("✅ llama-server gotowy (PID: %d)", proc.pid)
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            logger.error("❌ llama-server padł przy starcie!")
            logger.error("   Sprawdź: logs/embed_server_stderr.log")
            sys.exit(1)
        if i % 5 == 4:
            logger.info("   ...czekam (%ds)", i + 1)

    logger.error("❌ Timeout — llama-server nie odpowiada po 30s")
    _cleanup()
    sys.exit(1)


def embed_tekst(tekst: str) -> list[float]:
    """Wysyła tekst do llama-server i zwraca wektor embeddingu."""
    import requests
    resp = requests.post(
        f"{EMBED_URL}/embeddings",
        json={"input": tekst},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    # llama-server: {"data": [{"embedding": [...], "index": 0}]}
    return data["data"][0]["embedding"]


# ── Ekstrakcja tekstu z plików ────────────────────────────────────────────────

def ekstrakcja_pdf(sciezka: Path) -> str:
    """PDF: pdftotext (szybkie), fallback PyMuPDF."""
    try:
        wynik = subprocess.run(
            ["pdftotext", "-layout", str(sciezka), "-"],
            capture_output=True, text=True, timeout=120,
        )
        tekst = wynik.stdout.strip()
        if tekst and len(tekst) > 100:
            logger.info("  📄 pdftotext: %d znaków", len(tekst))
            return tekst
    except Exception:
        pass

    try:
        import fitz
        doc = fitz.open(str(sciezka))
        tekst = "\n".join(p.get_text() for p in doc)
        doc.close()
        if tekst.strip():
            logger.info("  📄 PyMuPDF: %d znaków", len(tekst))
            return tekst.strip()
    except Exception as e:
        logger.debug("PyMuPDF błąd: %s", e)

    logger.warning("  ⚠️  Brak tekstu w: %s", sciezka.name)
    return ""


def ekstrakcja_tekstu(sciezka: Path) -> str:
    """Wybiera metodę ekstrakcji na podstawie rozszerzenia."""
    suffix = sciezka.suffix.lower()
    if suffix == ".pdf":
        return ekstrakcja_pdf(sciezka)
    try:
        return sciezka.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.warning("Błąd odczytu %s: %s", sciezka.name, e)
        return ""


# ── Segmentacja tekstu ────────────────────────────────────────────────────────

def podziel_na_chunki(tekst: str, dlugosc_slow: int = 300, overlap: int = 30) -> list[str]:
    """Dzieli tekst na chunki po słowach z nakładaniem."""
    slowa = tekst.split()
    chunki = []
    i = 0
    while i < len(slowa):
        chunk = " ".join(slowa[i:i + dlugosc_slow])
        if chunk.strip():
            chunki.append(chunk)
        i += dlugosc_slow - overlap
    return chunki


# ── Indeksowanie do Qdrant ────────────────────────────────────────────────────

def indeksuj_plik(sciezka: Path, model_nazwa: str) -> int:
    """Indeksuje plik — embeduje przez llama-server i zapisuje do Qdrant."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
    import uuid

    logger.info("📖 %s", sciezka.name)
    tekst = ekstrakcja_tekstu(sciezka)

    if not tekst or len(tekst.strip()) < 50:
        logger.warning("  ⏭️  Pominięto (za mało tekstu)")
        return 0

    chunki = podziel_na_chunki(tekst)
    logger.info("  📦 %d chunków", len(chunki))

    from backend_app.config import settings
    klient = QdrantClient(url=str(settings.qdrant_url))
    kolekcja = settings.qdrant_collection

    # Sprawdź wymiar embeddingu
    pierwszy_embed = embed_tekst(chunki[0])
    dim = len(pierwszy_embed)
    logger.info("  📐 Wymiar: %d", dim)

    # Sprawdź zgodność kolekcji
    try:
        info = klient.get_collection(kolekcja)
        obecny_dim = info.config.params.vectors.size
        if obecny_dim != dim:
            logger.error(
                "  ❌ Niezgodność wymiarów! Kolekcja=%d, model=%d",
                obecny_dim, dim,
            )
            logger.error("     Usuń kolekcję: curl -X DELETE http://localhost:6333/collections/%s", kolekcja)
            return 0
    except Exception:
        # Kolekcja nie istnieje — utwórz
        logger.info("  🆕 Tworzę kolekcję %s (dim=%d)", kolekcja, dim)
        klient.recreate_collection(
            collection_name=kolekcja,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    # Embeduj wszystkie chunki i zapisz
    punkty = []
    for i, chunk in enumerate(chunki):
        try:
            wektor = pierwszy_embed if i == 0 else embed_tekst(chunk)
            punkty.append(PointStruct(
                id=str(uuid.uuid4()),
                vector=wektor,
                payload={
                    "content": chunk,
                    "source": sciezka.name,
                    "path": str(sciezka),
                    "chunk_idx": i,
                    "embedding_model": model_nazwa,
                },
            ))
        except KeyboardInterrupt:
            _cleanup()
        except Exception as e:
            logger.warning("  Błąd chunk %d: %s", i, e)

    if punkty:
        klient.upsert(collection_name=kolekcja, points=punkty)
        logger.info("  ✅ Zapisano %d punktów do Qdrant", len(punkty))

    return len(punkty)


def wymus_hnsw():
    """Wymusza budowę indeksu HNSW w Qdrant."""
    try:
        import requests
        from backend_app.config import settings
        url = f"{settings.qdrant_url}/collections/{settings.qdrant_collection}"
        requests.patch(url, json={"hnsw_config": {"full_scan_threshold": 10}}, timeout=10)
        logger.info("✅ HNSW threshold obniżony — indeks zostanie zbudowany")
    except Exception as e:
        logger.warning("HNSW błąd: %s", e)


# ── Główna funkcja ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="KlimtechRAG — Embedding GPU z modele_LLM/"
    )
    parser.add_argument("--file",    type=str, help="Ścieżka do pliku")
    parser.add_argument("--dir",     type=str, help="Katalog z plikami")
    parser.add_argument("--model",   type=str, help="Numer modelu z listy (np. 1)")
    parser.add_argument("--no-hnsw", action="store_true", help="Nie wymuszaj HNSW")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  KlimtechRAG — Ingest Embedding (GPU / llama.cpp)")
    print("=" * 60)

    # Skanuj i wybierz model
    modele = skanuj_modele()
    model_info = wybierz_model(args.model, modele)
    logger.info("📦 Model: %s (%.1f GB)", model_info["nazwa"], model_info["rozmiar"])

    # Uruchom llama-server jako serwer embeddingów
    uruchom_llama_embed(model_info)

    # Zbierz pliki do przetworzenia
    pliki: list[Path] = []

    if args.file:
        p = Path(args.file)
        if not p.exists():
            logger.error("Plik nie istnieje: %s", args.file)
            _cleanup()
        pliki = [p]

    elif args.dir:
        d = Path(args.dir)
        if not d.is_dir():
            logger.error("Katalog nie istnieje: %s", args.dir)
            _cleanup()
        pliki = sorted(d.rglob("*.pdf")) + \
                sorted(d.rglob("*.txt")) + \
                sorted(d.rglob("*.md"))
        logger.info("📁 Katalog %s: %d plików", d, len(pliki))

    else:
        # Domyślnie: data/uploads/ — wszystkie podkatalogi
        uploads = BASE_DIR / "data" / "uploads"
        pliki = sorted(uploads.rglob("*.pdf")) + \
                sorted(uploads.rglob("*.txt")) + \
                sorted(uploads.rglob("*.md"))
        logger.info("📁 Domyślny katalog uploads/: %d plików", len(pliki))

    if not pliki:
        logger.info("ℹ️  Brak plików do przetworzenia")
        _cleanup()

    print(f"\n📋 Do indeksowania: {len(pliki)} plików\n")

    # Indeksowanie
    total   = 0
    bledy   = 0
    t_start = time.time()

    for i, plik in enumerate(pliki, 1):
        print(f"[{i}/{len(pliki)}] {plik.name}")
        try:
            chunki = indeksuj_plik(plik, model_info["nazwa"])
            total += chunki
        except KeyboardInterrupt:
            _cleanup()
        except Exception as e:
            logger.error("  ❌ %s: %s", plik.name, e)
            bledy += 1

    czas = time.time() - t_start

    print("\n" + "=" * 60)
    print(f"  ✅ Zakończono!")
    print(f"  📊 Pliki: {len(pliki) - bledy}/{len(pliki)}")
    print(f"  📦 Punkty w Qdrant: {total}")
    print(f"  ⏱️  Czas: {czas:.1f}s")
    print(f"  📝 Log: {LOG_FILE}")
    print("=" * 60)

    if not args.no_hnsw and total > 0:
        wymus_hnsw()

    _cleanup()


if __name__ == "__main__":
    main()
