"""graph_service.py — Budowanie i odpytywanie grafu wiedzy dokumentów.

MVP: runtime wing extraction z pola `category` w payload Qdrant.
Nie wymaga migracji istniejących punktów (pole `wing` jest opcjonalne —
fallback do `category.split(".")[0]`).

Typy krawędzi:
    same_wing    — wspólna domena top-level (z `category` w payload Qdrant)
    semantic     — cosine similarity > próg między centroidami dokumentów
    co_retrieved — dokumenty pojawiające się razem w wynikach RAG

Storage: tabela `document_graph` w SQLite (file_registry.db), zarządzana
przez `file_registry.init_db()`.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from ..config import settings
from ..file_registry import get_connection

logger = logging.getLogger("klimtechrag")

QDRANT_BASE = f"{settings.qdrant_url}collections/{settings.qdrant_collection}"


def _extract_wing(payload: dict) -> str:
    """Wyciągnij wing (top-level domenę) z payload Qdrant.

    Kolejność: explicit `wing` → split `category` po kropce → "unknown".
    """
    wing = payload.get("wing")
    if wing:
        return str(wing)
    category = payload.get("category", "")
    if category and "." in category:
        return category.split(".")[0]
    return category or "unknown"


def add_edge(
    source_a: str,
    source_b: str,
    edge_type: str,
    weight: float = 0.5,
) -> None:
    """Dodaj krawędź do grafu (lub zaktualizuj wagę).

    Kolejność source_a/source_b jest normalizowana alfabetycznie,
    aby uniknąć duplikatów (a,b) i (b,a).
    """
    if source_a == source_b or not source_a or not source_b:
        return
    a, b = sorted([source_a, source_b])
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO document_graph "
            "(source_a, source_b, edge_type, weight) VALUES (?, ?, ?, ?)",
            (a, b, edge_type, float(weight)),
        )
        conn.commit()


def get_edges(
    source: Optional[str] = None,
    edge_type: Optional[str] = None,
    min_weight: float = 0.0,
) -> list[dict]:
    """Pobierz krawędzie z opcjonalnymi filtrami."""
    query = (
        "SELECT source_a, source_b, edge_type, weight "
        "FROM document_graph WHERE weight >= ?"
    )
    params: list = [float(min_weight)]
    if source:
        query += " AND (source_a = ? OR source_b = ?)"
        params.extend([source, source])
    if edge_type:
        query += " AND edge_type = ?"
        params.append(edge_type)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "source_a": r[0],
            "source_b": r[1],
            "edge_type": r[2],
            "weight": r[3],
        }
        for r in rows
    ]


def get_nodes() -> list[dict]:
    """Pobierz unikalne dokumenty (węzły grafu) z Qdrant.

    Scroll po całej kolekcji, grupowanie po `source`, zliczanie chunków.
    """
    nodes: dict[str, dict] = {}
    offset = None

    while True:
        body: dict = {
            "limit": 100,
            "with_payload": True,
            "with_vector": False,
        }
        if offset is not None:
            body["offset"] = offset

        try:
            r = httpx.post(
                f"{QDRANT_BASE}/points/scroll",
                json=body,
                timeout=30,
            )
            data = r.json()
        except Exception as e:
            logger.error("Graph: błąd Qdrant scroll: %s", e)
            break

        result = data.get("result", {})
        points = result.get("points", [])
        next_offset = result.get("next_page_offset")

        for p in points:
            payload = p.get("payload", {}) or {}
            source = payload.get("source", "")
            if not source:
                continue
            if source not in nodes:
                nodes[source] = {
                    "id": source,
                    "wing": _extract_wing(payload),
                    "category": payload.get("category", ""),
                    "chunks": 0,
                }
            nodes[source]["chunks"] += 1

        if not next_offset:
            break
        offset = next_offset

    return list(nodes.values())


def build_wing_edges(max_per_wing: int = 50, weight: float = 0.3) -> int:
    """Buduj krawędzie `same_wing` między dokumentami z tej samej domeny.

    `max_per_wing` ogranicza kliki w dużych wings (liczba krawędzi rośnie O(n²)).
    """
    nodes = get_nodes()
    wings: dict[str, list[str]] = {}
    for node in nodes:
        wings.setdefault(node["wing"], []).append(node["id"])

    count = 0
    for wing, sources in wings.items():
        if len(sources) < 2:
            continue
        subset = sources[:max_per_wing]
        for i, a in enumerate(subset):
            for b in subset[i + 1:]:
                add_edge(a, b, "same_wing", weight=weight)
                count += 1

    logger.info("Graph: utworzono %d krawędzi same_wing", count)
    return count


def log_co_retrieval(sources: list[str]) -> None:
    """Zapisz krawędzie `co_retrieved` dla dokumentów zwróconych razem z RAG.

    Inkrementuje wagę (cap 1.0) — częste współ-retrievalu = silniejsza relacja.
    """
    unique = list({s for s in sources if s})
    if len(unique) < 2:
        return

    for i, a in enumerate(unique):
        for b in unique[i + 1:]:
            pair = tuple(sorted([a, b]))
            with get_connection() as conn:
                existing = conn.execute(
                    "SELECT weight FROM document_graph "
                    "WHERE source_a = ? AND source_b = ? AND edge_type = ?",
                    (pair[0], pair[1], "co_retrieved"),
                ).fetchone()
            prev = existing[0] if existing else 0.0
            new_weight = min(prev + 0.1, 1.0)
            add_edge(a, b, "co_retrieved", weight=round(new_weight, 3))
