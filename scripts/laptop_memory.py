#!/usr/bin/env python3
"""
laptop_memory.py — lekki klient pamięci sesji dla laptopa.

Używa fastembed (ONNX, bez GPU) + qdrant-client do zapisu/odczytu
snapshotów sesji w kolekcji supervisor_memory (dim=1024).

Użycie:
  python3 laptop_memory.py save --done "co zrobiono" --next "co dalej" [--notes "uwagi"] [--git "plik1,plik2"]
  python3 laptop_memory.py load [--limit 1]
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone

VENV_PYTHON = "/home/tamiel/programy/klimtech-embed-venv/bin/python3"
QDRANT_URL = "http://localhost:6333"
COLLECTION = "supervisor_memory"
MODEL = "intfloat/multilingual-e5-large"


def get_clients():
    try:
        from fastembed import TextEmbedding
        from qdrant_client import QdrantClient
    except ImportError:
        print("ERROR: Uruchom przez klimtech-embed-venv:", file=sys.stderr)
        print(f"  {VENV_PYTHON} {__file__} ...", file=sys.stderr)
        sys.exit(1)
    embedder = TextEmbedding(MODEL)
    client = QdrantClient(url=QDRANT_URL)
    return embedder, client


def cmd_save(args):
    embedder, client = get_clients()

    tekst = f"{args.done}. Następny krok: {args.next}."
    if args.notes:
        tekst += f" Uwagi: {args.notes}"

    git_status = [f.strip() for f in args.git.split(",")] if args.git else []

    embedding = list(list(embedder.embed([tekst]))[0])

    snap_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    payload = {
        "typ": "snapshot",
        "ostatni_krok": args.done,
        "nastepny_krok": args.next,
        "git_status": git_status,
        "uwagi": args.notes or None,
        "timestamp": timestamp,
        "source": "laptop",
    }

    from qdrant_client.models import PointStruct
    client.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(id=snap_id, vector=embedding, payload=payload)],
    )

    print(json.dumps({"status": "ok", "id": snap_id, "timestamp": timestamp}, ensure_ascii=False))


def cmd_load(args):
    from qdrant_client import QdrantClient
    client = QdrantClient(url=QDRANT_URL)

    results = client.scroll(
        collection_name=COLLECTION,
        limit=100,
        with_payload=True,
        with_vectors=False,
    )

    points = results[0]
    if not points:
        print(json.dumps({"status": "empty", "message": "Brak snapshotów w supervisor_memory"}))
        return

    points.sort(key=lambda p: p.payload.get("timestamp", ""), reverse=True)
    points = points[:args.limit]

    for p in points:
        pl = p.payload
        print(json.dumps({
            "id": str(p.id),
            "timestamp": pl.get("timestamp"),
            "ostatni_krok": pl.get("ostatni_krok"),
            "nastepny_krok": pl.get("nastepny_krok"),
            "git_status": pl.get("git_status", []),
            "uwagi": pl.get("uwagi"),
            "source": pl.get("source", "server"),
        }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Laptop memory client dla KlimtechRAG")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_save = sub.add_parser("save", help="Zapisz snapshot sesji")
    p_save.add_argument("--done", required=True, help="Co zostało zrobione")
    p_save.add_argument("--next", required=True, help="Co zrobić następnym razem")
    p_save.add_argument("--notes", help="Dodatkowe uwagi")
    p_save.add_argument("--git", help="Lista plików (oddzielone przecinkami)")

    p_load = sub.add_parser("load", help="Wczytaj ostatnie snapshoty")
    p_load.add_argument("--limit", type=int, default=1, help="Ile snapshotów (domyślnie 1)")

    args = parser.parse_args()
    if args.cmd == "save":
        cmd_save(args)
    elif args.cmd == "load":
        cmd_load(args)


if __name__ == "__main__":
    main()
