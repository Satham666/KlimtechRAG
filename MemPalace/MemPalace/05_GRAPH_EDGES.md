# 05_GRAPH_EDGES — Krawędzie grafu z istniejących danych

**Zadanie:** Zbuduj relacje między dokumentami bez nowych modeli AI
**Czas:** 2 dni
**Zależności:** 02_METADATA_HIERARCHY
**VRAM:** 0 MB (CPU + Qdrant queries)
**Pliki do utworzenia:** `backend_app/services/graph_service.py`, `backend_app/scripts/build_graph.py`

---

## KONTEKST DLA ROBOTNIKA

Cel: zbudować graf wiedzy podobny do Obsidian Graph View.
Węzły = unikalne dokumenty (source). Krawędzie = relacje między nimi.
Trzy typy krawędzi, zero nowych modeli:

1. **same_wing** — dokumenty z tym samym `wing` w payload Qdrant
2. **semantic** — cosine similarity > 0.75 między embeddingami dokumentów
3. **co_retrieved** — dokumenty pojawiające się razem w wynikach RAG

Storage: tabela `document_graph` w `file_registry.db` (SQLite).

---

## KROK 1: Rozszerz file_registry.db o tabelę grafu

Dodaj do `backend_app/file_registry.py` migrację:

```python
def _ensure_graph_table(conn):
    """Tworzy tabelę document_graph jeśli nie istnieje."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_graph (
            source_a TEXT NOT NULL,
            source_b TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            weight REAL DEFAULT 0.5,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (source_a, source_b, edge_type)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_graph_source_a
        ON document_graph(source_a)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_graph_edge_type
        ON document_graph(edge_type)
    """)
    conn.commit()
```

Wywołaj `_ensure_graph_table(conn)` w funkcji inicjalizującej DB
(np. w `init_registry()` lub `_get_connection()`).

---

## KROK 2: Utwórz backend_app/services/graph_service.py

```python
"""
graph_service.py — Budowanie i odpytywanie grafu wiedzy dokumentów.

Typy krawędzi:
    same_wing    — wspólna domena tematyczna (z metadanych Qdrant)
    semantic     — cosine similarity > próg między embeddingami
    co_retrieved — dokumenty pojawiające się razem w wynikach RAG
"""
import logging
import sqlite3
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("klimtechrag")

QDRANT_URL = "http://localhost:6333"
COLLECTION = "klimtech_docs"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "file_registry.db"


def _get_conn() -> sqlite3.Connection:
    """Zwraca połączenie do SQLite z tabelą grafu."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def add_edge(source_a: str, source_b: str,
             edge_type: str, weight: float = 0.5) -> None:
    """Dodaj krawędź do grafu (lub zaktualizuj wagę)."""
    if source_a == source_b:
        return
    # Normalizuj kolejność (a < b) żeby uniknąć duplikatów
    a, b = sorted([source_a, source_b])
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO document_graph "
            "(source_a, source_b, edge_type, weight) VALUES (?, ?, ?, ?)",
            (a, b, edge_type, weight),
        )
        conn.commit()
    finally:
        conn.close()


def get_edges(source: Optional[str] = None,
              edge_type: Optional[str] = None,
              min_weight: float = 0.0) -> list:
    """Pobierz krawędzie z filtrami."""
    conn = _get_conn()
    try:
        query = "SELECT source_a, source_b, edge_type, weight FROM document_graph WHERE weight >= ?"
        params = [min_weight]
        if source:
            query += " AND (source_a = ? OR source_b = ?)"
            params.extend([source, source])
        if edge_type:
            query += " AND edge_type = ?"
            params.append(edge_type)
        rows = conn.execute(query, params).fetchall()
        return [
            {"source_a": r[0], "source_b": r[1],
             "edge_type": r[2], "weight": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


def get_nodes() -> list:
    """Pobierz unikalne dokumenty z metadanymi z Qdrant."""
    nodes = {}
    offset = None

    while True:
        body = {
            "limit": 100,
            "with_payload": True,
            "with_vector": False,
        }
        if offset is not None:
            body["offset"] = offset

        try:
            r = httpx.post(
                QDRANT_URL + "/collections/" + COLLECTION + "/points/scroll",
                json=body,
                timeout=30,
            )
            data = r.json()
        except Exception as e:
            logger.error("Błąd Qdrant scroll: %s", e)
            break

        points = data["result"]["points"]
        next_offset = data["result"].get("next_page_offset")

        for p in points:
            payload = p["payload"]
            source = payload.get("source", "")
            if source and source not in nodes:
                nodes[source] = {
                    "id": source,
                    "wing": payload.get("wing", "unknown"),
                    "room": payload.get("room", ""),
                    "hall": payload.get("hall", "inny"),
                    "chunks": 0,
                }
            if source in nodes:
                nodes[source]["chunks"] += 1

        if next_offset is None:
            break
        offset = next_offset

    return list(nodes.values())


def build_wing_edges() -> int:
    """Buduje krawędzie same_wing między dokumentami w tej samej domenie."""
    nodes = get_nodes()
    wings = {}
    for node in nodes:
        w = node["wing"]
        if w not in wings:
            wings[w] = []
        wings[w].append(node["id"])

    count = 0
    for wing, sources in wings.items():
        if len(sources) < 2:
            continue
        # Ogranicz: max 50 krawędzi per wing (unikaj eksplozji)
        for i, a in enumerate(sources[:50]):
            for b in sources[i + 1:50]:
                add_edge(a, b, "same_wing", weight=0.3)
                count += 1

    logger.info("Utworzono %d krawędzi same_wing", count)
    return count


def log_co_retrieval(sources: list) -> None:
    """
    Zapisz krawędzie co_retrieved gdy retrieval zwraca wiele dokumentów.

    Wywołuj po każdym RAG query z listą source z wyników.
    """
    unique = list(set(sources))
    if len(unique) < 2:
        return

    for i, a in enumerate(unique):
        for b in unique[i + 1:]:
            # Inkrementuj wagę (więcej co-retrievali = silniejsza relacja)
            conn = _get_conn()
            try:
                existing = conn.execute(
                    "SELECT weight FROM document_graph "
                    "WHERE source_a = ? AND source_b = ? AND edge_type = ?",
                    (*sorted([a, b]), "co_retrieved"),
                ).fetchone()

                new_weight = min((existing[0] if existing else 0) + 0.1, 1.0)
                add_edge(a, b, "co_retrieved", weight=new_weight)
            finally:
                conn.close()
```

---

## KROK 3: Skrypt budowania krawędzi semantycznych

Utwórz `backend_app/scripts/build_graph.py`:

```python
#!/usr/bin/env python3
"""
build_graph.py — Buduje krawędzie semantyczne między dokumentami.

Dla każdego dokumentu: oblicza średni embedding, szuka top-3 sąsiadów,
tworzy krawędź 'semantic' jeśli similarity > próg.

Użycie:
    python3 -m backend_app.scripts.build_graph --threshold 0.75
    python3 -m backend_app.scripts.build_graph --wings-only
"""
import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend_app.services.graph_service import (
    add_edge, build_wing_edges, get_nodes,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("build_graph")

QDRANT_URL = "http://localhost:6333"
COLLECTION = "klimtech_docs"


def compute_doc_embeddings() -> dict:
    """Oblicz średni embedding dla każdego dokumentu."""
    doc_vectors = defaultdict(list)
    offset = None

    while True:
        body = {"limit": 100, "with_payload": True, "with_vector": True}
        if offset is not None:
            body["offset"] = offset

        r = httpx.post(
            QDRANT_URL + "/collections/" + COLLECTION + "/points/scroll",
            json=body,
            timeout=60,
        )
        data = r.json()
        points = data["result"]["points"]
        next_offset = data["result"].get("next_page_offset")

        for p in points:
            source = p["payload"].get("source", "")
            vector = p.get("vector", [])
            if source and vector:
                doc_vectors[source].append(vector)

        if next_offset is None:
            break
        offset = next_offset

    # Średni embedding per dokument
    result = {}
    for source, vectors in doc_vectors.items():
        if vectors:
            dim = len(vectors[0])
            avg = [0.0] * dim
            for v in vectors:
                for i in range(dim):
                    avg[i] += v[i]
            n = len(vectors)
            result[source] = [x / n for x in avg]

    logger.info("Obliczono embeddingi dla %d dokumentów", len(result))
    return result


def build_semantic_edges(threshold: float = 0.75, top_k: int = 3) -> int:
    """Buduj krawędzie semantic na podstawie cosine similarity."""
    doc_embeddings = compute_doc_embeddings()
    count = 0

    for source, embedding in doc_embeddings.items():
        # Szukaj najbliższych sąsiadów (z wykluczeniem self)
        r = httpx.post(
            QDRANT_URL + "/collections/" + COLLECTION + "/points/search",
            json={
                "vector": embedding,
                "limit": top_k * 5,  # więcej bo filtrujemy
                "with_payload": True,
                "filter": {
                    "must_not": [
                        {"key": "source", "match": {"value": source}}
                    ]
                },
            },
            timeout=30,
        )
        results = r.json().get("result", [])

        # Deduplikuj po source i weź top_k
        seen = set()
        neighbors = 0
        for hit in results:
            neighbor = hit["payload"].get("source", "")
            score = hit.get("score", 0)
            if neighbor and neighbor not in seen and score >= threshold:
                add_edge(source, neighbor, "semantic", weight=round(score, 4))
                seen.add(neighbor)
                neighbors += 1
                count += 1
                if neighbors >= top_k:
                    break

    logger.info("Utworzono %d krawędzi semantic (threshold=%.2f)", count, threshold)
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--wings-only", action="store_true")
    args = parser.parse_args()

    # Zawsze buduj wing edges
    wing_count = build_wing_edges()
    print("Krawędzie same_wing:", wing_count)

    if not args.wings_only:
        sem_count = build_semantic_edges(threshold=args.threshold)
        print("Krawędzie semantic:", sem_count)

    # Podsumowanie
    nodes = get_nodes()
    print("Węzłów (dokumentów):", len(nodes))


if __name__ == "__main__":
    main()
```

**Test:**
```bash
python3 -m backend_app.scripts.build_graph --wings-only
```

---

## KROK 4: Podepnij co_retrieval logging w chat.py

W `routes/chat.py`, po RAG retrieval, dodaj:

```python
from ..services.graph_service import log_co_retrieval

# Po retrieval — zbierz source z wyników
sources = [doc.meta.get("source", "") for doc in local_docs if doc.meta.get("source")]
if len(sources) >= 2:
    log_co_retrieval(sources)
```

---

## RAPORTOWANIE

| Krok | Status | Uwagi |
|------|--------|-------|
| 1. Tabela document_graph | PASS/FAIL | DDL bez błędów |
| 2. graph_service.py | PASS/FAIL | import działa |
| 3. build_graph.py --wings-only | PASS/FAIL | ile krawędzi |
| 3b. build_graph.py (semantic) | PASS/FAIL | ile krawędzi |
| 4. co_retrieval logging | PASS/FAIL | krawędzie po query |
