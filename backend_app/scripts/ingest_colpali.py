"""
backend_app/scripts/ingest_colpali.py

Skrypt do masowego indeksowania PDF przez ColPali.
Uruchamiaj OSOBNO od start_klimtech_v3.py (konflikt VRAM z LLM).

Użycie:
    # Jeden plik:
    python3 -m backend_app.scripts.ingest_colpali --file /ścieżka/do/plik.pdf

    # Cały katalog PDF:
    python3 -m backend_app.scripts.ingest_colpali --dir /media/lobo/BACKUP/KlimtechRAG/data/uploads/pdf_RAG

    # Z konkretnym modelem:
    python3 -m backend_app.scripts.ingest_colpali --dir ./pdf_RAG --model vidore/colpali-v1.3-hf

    # Sprawdź status kolekcji:
    python3 -m backend_app.scripts.ingest_colpali --status

Uwagi:
    - ColPali (PaliGemma-3B) zajmuje ~6-8 GB VRAM — ZATRZYMAJ LLM przed uruchomieniem!
    - batch_size=4 dla 16GB VRAM (możesz zwiększyć do 8 jeśli GPU ma więcej)
    - Każda strona PDF = osobny punkt w kolekcji klimtech_colpali
    - Duplikaty są nadpisywane (upsert po deterministycznym ID)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time

# Dodaj root projektu do PYTHONPATH
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend_app.services.colpali_embedder import (
    COLPALI_COLLECTION,
    DEFAULT_MODEL,
    ensure_collection,
    get_qdrant_client,
    index_pdf,
    search,
    unload_model,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_pdfs(directory: str) -> list[str]:
    pdfs = []
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    return pdfs


def print_status(client=None):
    if client is None:
        client = get_qdrant_client()
    try:
        info = client.get_collection(COLPALI_COLLECTION)
        pts  = info.points_count
        vecs = info.vectors_count
        print(f"\n{'='*55}")
        print(f"   Kolekcja: {COLPALI_COLLECTION}")
        print(f"   Punkty (strony): {pts}")
        print(f"   Wektory:         {vecs}")
        print(f"{'='*55}")
    except Exception as e:
        print(f"\n❌ Kolekcja niedostępna: {e}")
        print("   Uruchom indeksowanie aby ją utworzyć.")


def confirm_vram() -> bool:
    print("\n" + "="*55)
    print("   ⚠️  UWAGA — VRAM")
    print("="*55)
    print("   ColPali (PaliGemma-3B) potrzebuje ~6-8 GB VRAM.")
    print("   Upewnij się że LLM (llama-server) jest zatrzymany!")
    print("   Możesz to zrobić klikając [5] Zatrzymaj w menu")
    print("   start_klimtech_v3.py lub:")
    print("   $ pkill -f llama-server")
    print("="*55)
    ans = input("\n   Kontynuować? [t/N]: ").strip().lower()
    return ans in ("t", "tak", "y", "yes")


# ---------------------------------------------------------------------------
# Główna logika
# ---------------------------------------------------------------------------

def run_ingest_file(path: str, model: str, batch_size: int) -> None:
    if not os.path.isfile(path):
        print(f"❌ Plik nie istnieje: {path}")
        sys.exit(1)
    if not path.lower().endswith(".pdf"):
        print(f"❌ Tylko pliki PDF są obsługiwane: {path}")
        sys.exit(1)

    client = get_qdrant_client()
    t0 = time.time()
    pages = index_pdf(path, model_name=model, batch_size=batch_size, client=client)
    elapsed = time.time() - t0
    print(f"\n✅ Zaindeksowano {pages} stron w {elapsed:.1f}s  ({elapsed/pages:.1f}s/str)")
    print_status(client)


def run_ingest_dir(directory: str, model: str, batch_size: int) -> None:
    pdfs = find_pdfs(directory)
    if not pdfs:
        print(f"❌ Brak plików PDF w katalogu: {directory}")
        sys.exit(1)

    print(f"\n📁 Znaleziono {len(pdfs)} plików PDF w {directory}")
    for i, p in enumerate(pdfs):
        size_mb = os.path.getsize(p) / 1024 / 1024
        print(f"  [{i+1:3d}] {os.path.basename(p)}  ({size_mb:.1f} MB)")

    client = get_qdrant_client()
    ensure_collection(client)

    t_total = time.time()
    total_pages = 0
    errors = []

    for i, pdf_path in enumerate(pdfs):
        print(f"\n[{i+1}/{len(pdfs)}] {os.path.basename(pdf_path)}")
        t0 = time.time()
        try:
            pages = index_pdf(
                pdf_path,
                model_name=model,
                batch_size=batch_size,
                client=client,
            )
            total_pages += pages
            elapsed = time.time() - t0
            print(f"    ✅ {pages} stron  ({elapsed:.1f}s)")
        except Exception as e:
            logger.exception("Błąd indeksowania %s", pdf_path)
            errors.append((pdf_path, str(e)))
            print(f"    ❌ Błąd: {e}")

    elapsed_total = time.time() - t_total
    print(f"\n{'='*55}")
    print(f"   Gotowe!")
    print(f"   Pliki: {len(pdfs) - len(errors)}/{len(pdfs)}")
    print(f"   Stron: {total_pages}")
    print(f"   Czas:  {elapsed_total:.1f}s")
    if errors:
        print(f"   Błędy ({len(errors)}):")
        for path, err in errors:
            print(f"     - {os.path.basename(path)}: {err}")
    print("="*55)
    print_status(client)


def run_test_search(query: str, model: str) -> None:
    print(f"\n🔍 Szukam: '{query}'")
    results = search(query, top_k=5, model_name=model)
    if not results:
        print("   Brak wyników (kolekcja pusta?)")
        return
    print(f"\n   Wyniki (top {len(results)}):")
    for r in results:
        p = r.payload or {}
        print(f"   Score: {r.score:.4f}  |  {p.get('doc_id','?')}  str. {p.get('page','?')+1}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="KlimtechRAG — indeksowanie PDF przez ColPali",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file",   metavar="PLIK.PDF",  help="Indeksuj jeden plik PDF")
    group.add_argument("--dir",    metavar="KATALOG",   help="Indeksuj katalog z PDF-ami")
    group.add_argument("--status", action="store_true", help="Pokaż status kolekcji Qdrant")
    group.add_argument("--search", metavar="ZAPYTANIE", help="Testowe wyszukiwanie")

    parser.add_argument(
        "--model", default=DEFAULT_MODEL,
        help=f"Model ColPali (domyślnie: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--batch", type=int, default=4,
        help="Liczba stron na batch (domyślnie: 4)",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Pomiń potwierdzenie VRAM",
    )

    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.search:
        run_test_search(args.search, args.model)
        return

    # Przed indeksowaniem — sprawdź VRAM
    if not args.yes:
        if not confirm_vram():
            print("Anulowano.")
            sys.exit(0)

    print(f"\n🤖 Model:      {args.model}")
    print(f"   Batch size: {args.batch} stron")
    print(f"   Kolekcja:   {COLPALI_COLLECTION}")

    try:
        if args.file:
            run_ingest_file(args.file, args.model, args.batch)
        elif args.dir:
            run_ingest_dir(args.dir, args.model, args.batch)
    finally:
        unload_model()


if __name__ == "__main__":
    main()
