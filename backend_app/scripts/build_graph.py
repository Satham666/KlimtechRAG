#!/usr/bin/env python3
"""build_graph.py — Buduje krawędzie grafu wiedzy dokumentów w SQLite.

Krawędzie:
    same_wing — wspólna domena top-level (runtime z `category` w payload)
    semantic  — cosine similarity > próg między centroidami embeddingów

Użycie:
    python3 -m backend_app.scripts.build_graph --wings-only
    python3 -m backend_app.scripts.build_graph --threshold 0.75 --top-k 3
    python3 -m backend_app.scripts.build_graph --reset

Zależność: tabela `document_graph` musi istnieć (tworzona w file_registry.init_db()).
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend_app.config import settings  # noqa: E402
from backend_app.file_registry import get_connection, init_db  # noqa: E402
from backend_app.services.graph_service import (  # noqa: E402
    add_edge,
    build_wing_edges,
    get_nodes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("build_graph")

QDRANT_BASE = f"{settings.qdrant_url}collections/{settings.qdrant_collection}"


def compute_doc_embeddings() -> dict[str, list[float]]:
    """Oblicz centroid (średni embedding) każdego dokumentu.

    Scroll po całej kolekcji Qdrant z with_vector=True, grupowanie per source,
    sumowanie wektorów, dzielenie przez liczbę chunków.
    """
    doc_vectors: dict[str, list[list[float]]] = defaultdict(list)
    offset = None
    scanned = 0

    while True:
        body: dict = {
            "limit": 100,
            "with_payload": True,
            "with_vector": True,
        }
        if offset is not None:
            body["offset"] = offset

        r = httpx.post(
            f"{QDRANT_BASE}/points/scroll",
            json=body,
            timeout=60,
        )
        data = r.json()
        result = data.get("result", {})
        points = result.get("points", [])
        next_offset = result.get("next_page_offset")

        for p in points:
            payload = p.get("payload", {}) or {}
            source = payload.get("source", "")
            vector = p.get("vector", [])
            if source and vector:
                doc_vectors[source].append(vector)
            scanned += 1

        logger.info("Skanowano %d punktów, %d dokumentów", scanned, len(doc_vectors))
        if not next_offset:
            break
        offset = next_offset

    centroids: dict[str, list[float]] = {}
    for source, vectors in doc_vectors.items():
        if not vectors:
            continue
        dim = len(vectors[0])
        acc = [0.0] * dim
        for v in vectors:
            for i in range(dim):
                acc[i] += v[i]
        n = len(vectors)
        centroids[source] = [x / n for x in acc]

    logger.info("Obliczono centroidy dla %d dokumentów", len(centroids))
    return centroids


def build_semantic_edges(threshold: float = 0.75, top_k: int = 3) -> int:
    """Buduj krawędzie `semantic` na podstawie cosine similarity centroidów.

    Dla każdego dokumentu: search w Qdrant po jego centroidzie → top kandydatów,
    filtrowanie samego siebie, deduplikacja po source, dodanie krawędzi jeśli
    score >= threshold.
    """
    centroids = compute_doc_embeddings()
    count = 0

    for source, embedding in centroids.items():
        body = {
            "vector": embedding,
            "limit": top_k * 10,
            "with_payload": True,
        }
        try:
            r = httpx.post(
                f"{QDRANT_BASE}/points/search",
                json=body,
                timeout=30,
            )
            results = r.json().get("result", [])
        except Exception as e:
            logger.warning("Search failed for %s: %s", source[:40], e)
            continue

        seen: set[str] = set()
        added = 0
        for hit in results:
            payload = hit.get("payload", {}) or {}
            neighbor = payload.get("source", "")
            score = float(hit.get("score", 0.0))
            if not neighbor or neighbor == source or neighbor in seen:
                continue
            if score < threshold:
                continue
            add_edge(source, neighbor, "semantic", weight=round(score, 4))
            seen.add(neighbor)
            added += 1
            count += 1
            if added >= top_k:
                break

    logger.info(
        "Utworzono %d krawędzi semantic (threshold=%.2f, top_k=%d)",
        count, threshold, top_k,
    )
    return count


def reset_graph() -> int:
    """Usuń wszystkie krawędzie z tabeli document_graph."""
    with get_connection() as conn:
        removed = conn.execute("SELECT COUNT(*) FROM document_graph").fetchone()[0]
        conn.execute("DELETE FROM document_graph")
        conn.commit()
    logger.info("Usunięto %d krawędzi", removed)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="KlimtechRAG Graph Builder")
    parser.add_argument(
        "--threshold", type=float, default=0.75,
        help="Min cosine similarity dla krawędzi semantic (0.5-0.99)",
    )
    parser.add_argument(
        "--top-k", type=int, default=3,
        help="Ile sąsiadów semantycznych per dokument",
    )
    parser.add_argument(
        "--wings-only", action="store_true",
        help="Buduj tylko krawędzie same_wing (bez semantic)",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Usuń wszystkie krawędzie przed budową",
    )
    parser.add_argument(
        "--max-per-wing", type=int, default=50,
        help="Limit krawędzi same_wing per domena (zapobiega eksplozji)",
    )
    args = parser.parse_args()

    if not 0.5 <= args.threshold <= 0.99:
        parser.error("threshold musi być w [0.5, 0.99]")

    # Upewnij się, że tabela istnieje (idempotentne CREATE IF NOT EXISTS)
    init_db()

    if args.reset:
        reset_graph()

    wing_count = build_wing_edges(max_per_wing=args.max_per_wing)
    print(f"Krawędzie same_wing: {wing_count}")

    if not args.wings_only:
        sem_count = build_semantic_edges(
            threshold=args.threshold,
            top_k=args.top_k,
        )
        print(f"Krawędzie semantic: {sem_count}")

    nodes = get_nodes()
    print(f"Węzłów (dokumentów): {len(nodes)}")


if __name__ == "__main__":
    main()
