"""routes/graph.py — Endpointy API grafu wiedzy dokumentów (MemPalace).

Endpointy:
    GET /v1/graph/data?min_weight=&edge_type=  — nodes + edges (JSON, wymaga API key)
    GET /v1/graph/node/{source}                — sąsiedzi dokumentu (JSON, wymaga API key)
    GET /graph                                 — HTML wizualizacji 3d-force-graph (bez auth, jak /)
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from ..services.graph_service import get_edges, get_nodes
from ..utils.dependencies import require_api_key

logger = logging.getLogger("klimtechrag")

router = APIRouter(tags=["graph"])

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
GRAPH_HTML = os.path.join(STATIC_DIR, "graph.html")


@router.get("/v1/graph/data", dependencies=[Depends(require_api_key)])
async def get_graph_data(
    min_weight: float = 0.0,
    edge_type: Optional[str] = None,
) -> dict:
    """Zwraca węzły + krawędzie grafu dokumentów (do wizualizacji).

    Filtry:
        min_weight — tylko krawędzie o wadze >= min_weight
        edge_type  — only same_wing / semantic / co_retrieved (None = wszystkie)
    """
    nodes = get_nodes()
    edges = get_edges(
        edge_type=edge_type if edge_type else None,
        min_weight=min_weight,
    )
    edge_types_count: dict[str, int] = {}
    for e in edges:
        et = e["edge_type"]
        edge_types_count[et] = edge_types_count.get(et, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "edge_types": edge_types_count,
        },
    }


@router.get("/v1/graph/node/{source:path}", dependencies=[Depends(require_api_key)])
async def get_node_neighbors(source: str) -> dict:
    """Zwraca sąsiadów danego dokumentu (po `source`)."""
    edges = get_edges(source=source, min_weight=0.0)
    neighbors: set[str] = set()
    for e in edges:
        other = e["source_b"] if e["source_a"] == source else e["source_a"]
        if other and other != source:
            neighbors.add(other)

    return {
        "source": source,
        "neighbors": sorted(neighbors),
        "edges": edges,
        "count": len(neighbors),
    }


@router.get("/graph", response_class=HTMLResponse)
async def serve_graph_ui() -> HTMLResponse:
    """Serwuje HTML wizualizacji 3d-force-graph (bez auth, jak `/`)."""
    try:
        with open(GRAPH_HTML, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content=(
                "<!DOCTYPE html><html><head><title>Graph — brak pliku</title></head>"
                "<body><h1>graph.html nie istnieje</h1>"
                "<p>Wygeneruj statyczny plik w Kroku 6/6 (static/graph.html).</p>"
                "</body></html>"
            ),
            status_code=404,
        )
