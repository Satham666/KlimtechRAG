# 06_GRAPH_API_VIZ — API grafu i wizualizacja D3.js

**Zadanie:** Endpoint API `/v1/graph/data` + interaktywny graf w przeglądarce
**Czas:** 2 dni
**Zależności:** 05_GRAPH_EDGES
**VRAM:** 0 MB (frontend JS + FastAPI endpoint)
**Pliki do utworzenia:** `backend_app/routes/graph.py`, `backend_app/static/graph.html`

---

## KONTEKST DLA ROBOTNIKA

Graf dokumentów z poprzedniego kroku jest w SQLite (tabela `document_graph`).
Trzeba: 1) endpoint FastAPI zwracający nodes+edges jako JSON,
2) plik HTML z D3.js force-directed graph (jak w Obsidian).

**KRYTYCZNE ograniczenia JS:**
- Plik graph.html będzie serwowany statycznie — osobny od index.html
- NIE używaj template literals (backticks `) w żadnym JS
- NIE używaj const/let — używaj var
- NIE używaj arrow functions (=>) — używaj function()
- D3.js pobierz z CDN: https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js
- Kolory węzłów po wing, rozmiar po chunks_count

---

## KROK 1: Utwórz backend_app/routes/graph.py

```python
"""
graph.py — Endpointy API dla grafu wiedzy dokumentów.
"""
import logging
from fastapi import APIRouter, Depends, Request
from ..utils.dependencies import require_api_key
from ..services.graph_service import get_nodes, get_edges

logger = logging.getLogger("klimtechrag")
router = APIRouter(tags=["graph"])


@router.get("/v1/graph/data", dependencies=[Depends(require_api_key)])
async def get_graph_data(
    min_weight: float = 0.0,
    edge_type: str = "",
):
    """
    Zwraca dane grafu: nodes + edges.

    Query params:
        min_weight: minimalna waga krawędzi (0.0 - 1.0)
        edge_type: filtruj typ krawędzi (same_wing|semantic|co_retrieved)

    Returns:
        {"nodes": [...], "edges": [...], "stats": {...}}
    """
    nodes = get_nodes()

    edge_filter = edge_type if edge_type else None
    edges = get_edges(
        edge_type=edge_filter,
        min_weight=min_weight,
    )

    # Statystyki
    edge_types = {}
    for e in edges:
        t = e["edge_type"]
        edge_types[t] = edge_types.get(t, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "edge_types": edge_types,
        },
    }


@router.get("/v1/graph/node/{source}", dependencies=[Depends(require_api_key)])
async def get_node_neighbors(source: str):
    """Zwraca sąsiadów konkretnego dokumentu."""
    edges = get_edges(source=source, min_weight=0.0)
    neighbors = set()
    for e in edges:
        other = e["source_b"] if e["source_a"] == source else e["source_a"]
        neighbors.add(other)

    return {
        "source": source,
        "neighbors": list(neighbors),
        "edges": edges,
    }
```

**Zarejestruj router w main.py:**
```python
from .routes.graph import router as graph_router
app.include_router(graph_router)
```

**Test:**
```bash
curl -sk "http://localhost:8000/v1/graph/data?min_weight=0.3" \
  -H "Authorization: Bearer sk-local" | python3 -m json.tool | head -30
```

---

## KROK 2: Utwórz backend_app/static/graph.html

Plik wizualizacji — CAŁY JS bez backticks, const, let, arrow functions:

```html
<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KlimtechRAG — Graf Wiedzy</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #1a1a2e; color: #e0e0e0;
  font-family: 'Segoe UI', system-ui, sans-serif;
  overflow: hidden;
}
#controls {
  position: fixed; top: 10px; left: 10px; z-index: 10;
  background: rgba(26,26,46,0.9); padding: 12px; border-radius: 8px;
  border: 1px solid #333;
}
#controls label { display: block; margin: 4px 0; font-size: 13px; }
#controls select, #controls input { margin-left: 8px; }
#info {
  position: fixed; bottom: 10px; left: 10px; z-index: 10;
  background: rgba(26,26,46,0.9); padding: 10px; border-radius: 8px;
  border: 1px solid #333; font-size: 12px; max-width: 400px;
}
#tooltip {
  position: absolute; background: rgba(0,0,0,0.85); color: #fff;
  padding: 8px 12px; border-radius: 6px; font-size: 12px;
  pointer-events: none; display: none; z-index: 20;
}
svg { width: 100vw; height: 100vh; }
</style>
</head>
<body>

<div id="controls">
  <strong>KlimtechRAG Graph</strong>
  <label>Min. waga: <input type="range" id="weightSlider" min="0" max="100" value="20"></label>
  <label>Typ krawędzi:
    <select id="edgeTypeSelect">
      <option value="">Wszystkie</option>
      <option value="same_wing">same_wing</option>
      <option value="semantic">semantic</option>
      <option value="co_retrieved">co_retrieved</option>
    </select>
  </label>
  <div id="statsBox"></div>
</div>

<div id="info"></div>
<div id="tooltip"></div>
<svg id="graph"></svg>

<script>
/* KlimtechRAG Knowledge Graph — D3.js Force-Directed */
/* UWAGA: brak backticks, const, let, arrow functions */

var API_BASE = window.location.origin;
var API_KEY = "sk-local";

var WING_COLORS = {
  "construction": "#e74c3c",
  "medicine": "#2ecc71",
  "it_technology": "#3498db",
  "law": "#f39c12",
  "electrical": "#9b59b6",
  "automotive": "#1abc9c",
  "finance": "#e67e22",
  "education": "#27ae60",
  "unknown": "#7f8c8d"
};

var svg = d3.select("#graph");
var width = window.innerWidth;
var height = window.innerHeight;

var g = svg.append("g");

/* Zoom */
var zoom = d3.zoom()
  .scaleExtent([0.1, 5])
  .on("zoom", function(event) {
    g.attr("transform", event.transform);
  });
svg.call(zoom);

var simulation = null;
var currentNodes = [];
var currentEdges = [];

function getColor(wing) {
  return WING_COLORS[wing] || WING_COLORS["unknown"];
}

function getRadius(chunks) {
  return Math.max(4, Math.min(20, Math.sqrt(chunks) * 2));
}

function fetchGraph(minWeight, edgeType) {
  var url = API_BASE + "/v1/graph/data?min_weight=" + minWeight;
  if (edgeType) {
    url = url + "&edge_type=" + edgeType;
  }

  fetch(url, {
    headers: {"Authorization": "Bearer " + API_KEY}
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    currentNodes = data.nodes;
    currentEdges = data.edges;
    renderGraph(data);
    var statsBox = document.getElementById("statsBox");
    statsBox.innerHTML = "Nodes: " + data.stats.total_nodes +
      " | Edges: " + data.stats.total_edges;
  })
  .catch(function(err) {
    console.error("Fetch error:", err);
  });
}

function renderGraph(data) {
  g.selectAll("*").remove();

  var nodeMap = {};
  data.nodes.forEach(function(n) { nodeMap[n.id] = n; });

  /* Filtruj krawędzie — oba węzły muszą istnieć */
  var edges = data.edges.filter(function(e) {
    return nodeMap[e.source_a] && nodeMap[e.source_b];
  });

  /* D3 links */
  var links = edges.map(function(e) {
    return {
      source: e.source_a,
      target: e.source_b,
      type: e.edge_type,
      weight: e.weight
    };
  });

  /* Simulation */
  if (simulation) simulation.stop();

  simulation = d3.forceSimulation(data.nodes)
    .force("link", d3.forceLink(links).id(function(d) { return d.id; }).distance(80))
    .force("charge", d3.forceManyBody().strength(-120))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(function(d) {
      return getRadius(d.chunks) + 2;
    }));

  /* Krawędzie */
  var link = g.append("g")
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke", function(d) {
      if (d.type === "semantic") return "#3498db";
      if (d.type === "co_retrieved") return "#2ecc71";
      return "#555";
    })
    .attr("stroke-opacity", function(d) { return 0.3 + d.weight * 0.5; })
    .attr("stroke-width", function(d) { return 0.5 + d.weight * 2; });

  /* Węzły */
  var node = g.append("g")
    .selectAll("circle")
    .data(data.nodes)
    .join("circle")
    .attr("r", function(d) { return getRadius(d.chunks); })
    .attr("fill", function(d) { return getColor(d.wing); })
    .attr("stroke", "#fff")
    .attr("stroke-width", 0.5)
    .call(d3.drag()
      .on("start", function(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y;
      })
      .on("drag", function(event, d) {
        d.fx = event.x; d.fy = event.y;
      })
      .on("end", function(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null;
      })
    );

  /* Tooltip */
  var tooltip = document.getElementById("tooltip");

  node.on("mouseover", function(event, d) {
    tooltip.style.display = "block";
    tooltip.innerHTML = d.id + "<br>Wing: " + d.wing +
      "<br>Hall: " + d.hall + "<br>Chunks: " + d.chunks;
    tooltip.style.left = (event.pageX + 12) + "px";
    tooltip.style.top = (event.pageY - 10) + "px";

    /* Podświetl sąsiadów */
    var neighbors = new Set();
    links.forEach(function(l) {
      var sid = (typeof l.source === "object") ? l.source.id : l.source;
      var tid = (typeof l.target === "object") ? l.target.id : l.target;
      if (sid === d.id) neighbors.add(tid);
      if (tid === d.id) neighbors.add(sid);
    });

    node.attr("opacity", function(n) {
      return (n.id === d.id || neighbors.has(n.id)) ? 1.0 : 0.15;
    });
    link.attr("opacity", function(l) {
      var sid = (typeof l.source === "object") ? l.source.id : l.source;
      var tid = (typeof l.target === "object") ? l.target.id : l.target;
      return (sid === d.id || tid === d.id) ? 0.8 : 0.05;
    });
  });

  node.on("mouseout", function() {
    tooltip.style.display = "none";
    node.attr("opacity", 1.0);
    link.attr("opacity", function(d) { return 0.3 + d.weight * 0.5; });
  });

  /* Tick */
  simulation.on("tick", function() {
    link
      .attr("x1", function(d) { return d.source.x; })
      .attr("y1", function(d) { return d.source.y; })
      .attr("x2", function(d) { return d.target.x; })
      .attr("y2", function(d) { return d.target.y; });
    node
      .attr("cx", function(d) { return d.x; })
      .attr("cy", function(d) { return d.y; });
  });
}

/* Event listeners */
document.getElementById("weightSlider").addEventListener("input", function() {
  var val = this.value / 100;
  var edgeType = document.getElementById("edgeTypeSelect").value;
  fetchGraph(val, edgeType);
});

document.getElementById("edgeTypeSelect").addEventListener("change", function() {
  var val = document.getElementById("weightSlider").value / 100;
  fetchGraph(val, this.value);
});

/* Initial load */
fetchGraph(0.2, "");
</script>
</body>
</html>
```

---

## KROK 3: Dodaj route serwujący graph.html

W `backend_app/routes/ui.py` lub `main.py`:

```python
from fastapi.responses import FileResponse

@app.get("/graph")
async def serve_graph():
    """Serwuj stronę wizualizacji grafu."""
    graph_path = Path(__file__).parent / "static" / "graph.html"
    return FileResponse(str(graph_path), media_type="text/html")
```

**Test:** Otwórz w przeglądarce: `https://192.168.31.70:8443/graph`

---

## RAPORTOWANIE

| Krok | Status | Uwagi |
|------|--------|-------|
| 1. /v1/graph/data endpoint | PASS/FAIL | zwraca JSON |
| 2. graph.html renderuje | PASS/FAIL | brak błędów JS w konsoli |
| 3. /graph route | PASS/FAIL | strona się ładuje |
| 4. Interakcja (hover/drag/zoom) | PASS/FAIL | tooltip + highlight |
