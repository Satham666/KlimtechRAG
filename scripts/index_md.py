#!/usr/bin/env python3
"""Indeksowanie plików tekstowych (.md/.txt) do lokalnego Qdrant.

Embedding: intfloat/multilingual-e5-large (dim=1024) przez sentence-transformers.
Idempotencja: UUID deterministyczny z SHA-256 treści chunka.
Device auto-detect: CUDA/ROCm jeśli dostępne, inaczej CPU.

Przykłady:
    # Wszystkie .md w root projektu:
    python3 scripts/index_md.py --extensions .md

    # Konkretny plik:
    python3 scripts/index_md.py --file /path/to/session.txt

    # Cały folder z .md + .txt, osobna kolekcja:
    python3 scripts/index_md.py --root ./docs --extensions .md .txt --collection docs_kb

    # Wymuszone CPU (bez GPU):
    python3 scripts/index_md.py --device cpu
"""
from __future__ import annotations

import argparse
import hashlib
import time
import uuid
from pathlib import Path
from typing import Iterator

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

INFRA_EXCLUDE = {
    ".git", "venv", "ttkb_tut", "__pycache__", ".ruff_cache",
    "node_modules", ".claude", "logs", "modele_LLM", "ssl",
}


def iter_files(root: Path, extensions: set[str], exclude: set[str]) -> Iterator[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in exclude for part in path.parts):
            continue
        if path.suffix.lower() not in extensions:
            continue
        yield path


def chunk_words(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)]


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def main() -> None:
    default_root = Path(__file__).resolve().parent.parent
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=str(default_root),
                   help="Katalog główny do przeszukania (domyślnie: parent skryptu)")
    p.add_argument("--file", nargs="*", default=[],
                   help="Konkretne pliki do zaindeksowania (pomija --root/--extensions)")
    p.add_argument("--extensions", nargs="+", default=[".md"])
    p.add_argument("--collection", default="kb_md")
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--chunk-words", type=int, default=400)
    p.add_argument("--overlap", type=int, default=50)
    p.add_argument("--qdrant-url", default="http://localhost:6333")
    p.add_argument("--model", default="intfloat/multilingual-e5-large")
    p.add_argument("--device", default="auto",
                   help="cuda:0 / cpu / auto (domyślnie: auto — wybiera CUDA/ROCm jeśli dostępne)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--exclude-dirs", nargs="*", default=[],
                   help="Dodatkowe katalogi do wykluczenia (poza INFRA)")
    args = p.parse_args()

    root = Path(args.root).resolve()

    if args.file:
        files = sorted({Path(f).resolve() for f in args.file if Path(f).is_file()})
        print(f"Indeksuję konkretne pliki: {len(files)}")
    else:
        exts = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in args.extensions}
        exclude = INFRA_EXCLUDE | set(args.exclude_dirs)
        files = sorted(iter_files(root, exts, exclude))
        print(f"Znaleziono plików ({','.join(sorted(exts))}): {len(files)}")

    all_chunks: list[tuple[str, int, str, float]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  [!] błąd odczytu {f}: {e}")
            continue
        mtime = f.stat().st_mtime
        try:
            rel = str(f.relative_to(root))
        except ValueError:
            rel = str(f)
        for i, c in enumerate(chunk_words(text, args.chunk_words, args.overlap)):
            all_chunks.append((rel, i, c, mtime))
    print(f"Łącznie chunków: {len(all_chunks)}")

    if args.dry_run:
        for rel, i, c, _ in all_chunks[:5]:
            print(f"  [{rel} #{i}] {c[:100]}…")
        print("…(dry-run, koniec)")
        return

    device = resolve_device(args.device)
    print(f"Ładuję model {args.model} na {device}…")
    t0 = time.time()
    model = SentenceTransformer(args.model, device=device)
    t_model = time.time() - t0
    print(f"Model załadowany w {t_model:.1f}s")

    print(f"Qdrant: {args.qdrant_url}")
    client = QdrantClient(url=args.qdrant_url)
    existing = {c.name for c in client.get_collections().collections}
    if args.collection not in existing:
        print(f"Tworzę kolekcję {args.collection} dim=1024 Cosine")
        client.create_collection(
            collection_name=args.collection,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
    else:
        print(f"Kolekcja {args.collection} istnieje")

    total = len(all_chunks)
    t_start = time.time()
    t_embed = 0.0
    t_upsert = 0.0

    for i in range(0, total, args.batch):
        batch = all_chunks[i:i + args.batch]
        texts = [f"passage: {c[2]}" for c in batch]

        t1 = time.time()
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        t_embed += time.time() - t1

        points = []
        for (rel, idx, content, mtime), vec in zip(batch, vecs):
            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
            point_id = str(uuid.UUID(sha[:32]))
            points.append(PointStruct(
                id=point_id,
                vector=vec.tolist(),
                payload={
                    "source": rel,
                    "chunk_idx": idx,
                    "mtime": mtime,
                    "sha256": sha,
                    "text": content,
                },
            ))

        t2 = time.time()
        client.upsert(collection_name=args.collection, points=points)
        t_upsert += time.time() - t2

        done = i + len(batch)
        if (i // args.batch) % 10 == 0 or done == total:
            elapsed = time.time() - t_start
            rate = done / elapsed if elapsed > 0 else 0
            print(f"  {done}/{total} ({rate:.1f} chunk/s, {elapsed:.1f}s)")

    total_time = time.time() - t_start
    rate = total / total_time if total_time > 0 else 0
    print()
    print(f"Zakończone: {total} chunków w {total_time:.1f}s ({rate:.1f} chunk/s)")
    print(f"  - embedding: {t_embed:.1f}s ({total/t_embed:.1f} chunk/s GPU)")
    print(f"  - upsert:    {t_upsert:.1f}s")
    print(f"  - ładowanie modelu: {t_model:.1f}s")

    try:
        import torch
        if torch.cuda.is_available():
            print(f"VRAM peak: {torch.cuda.max_memory_allocated()/1024**2:.0f} MB")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
