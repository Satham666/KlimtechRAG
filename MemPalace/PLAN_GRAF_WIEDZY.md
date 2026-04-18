# PLAN: Graf Wiedzy w Dashboardzie KlimtechRAG

**Opcja A** — własna wizualizacja 3D grafu wiedzy zbudowana na istniejącej infrastrukturze (FastAPI + Qdrant + index.html).

**Cel:** Interaktywny graf dokumentów i ich powiązań semantycznych, zintegrowany z dashboardem KlimtechRAG, zasilany danymi z Qdrant.

**Priorytet:** 🟡 (nice-to-have, nie blokuje RAG pipeline)
**Szacowany czas:** 3–4 dni robocze
**Wpływ na VRAM:** ZERO — cała logika grafu to CPU + frontend JS

---

## Architektura

```
Qdrant (klimtech_docs)          FastAPI
┌──────────────────┐       ┌──────────────┐       ┌────────────────────┐
│ punkty z wektorami│──────▶│ GET /v1/graph │──────▶│ index.html         │
│ + payload.source  │       │              │       │ 3d-force-graph CDN │
│ + payload.content │       │ cosine sim   │       │ interaktywny 3D    │
└──────────────────┘       │ → edges JSON │       └────────────────────┘
                           └──────────────┘
```

**Kluczowa idea:** Węzły grafu = dokumenty (unikalne `source`). Krawędzie = podobieństwo semantyczne między centroidami wektorów dokumentów. Im wyższy cosine similarity między dwoma dokumentami, tym silniejsza krawędź.

---

## Etapy wdrożenia

### Etap 1: Endpoint `/v1/graph` w FastAPI (1.5 dnia)

**Plik:** `backend_app/routes/graph.py`

**Logika:**

1. Połącz się z Qdrant (`klimtech_docs`) przez `qdrant_client`
2. Scroll po wszystkich punktach — zbierz unikalne `source` (nazwy dokumentów)
3. Dla każdego dokumentu oblicz centroid (średnia wektorów wszystkich jego chunków)
4. Oblicz macierz cosine similarity między centroidami
5. Filtruj krawędzie: tylko pary z `similarity > próg` (np. 0.75)
6. Zwróć JSON:

```json
{
  "nodes": [
    {"id": "raport_q3.pdf", "chunks": 42, "group": "raporty"},
    {"id": "norma_iso9001.pdf", "chunks": 18, "group": "normy"}
  ],
  "links": [
    {"source": "raport_q3.pdf", "target": "norma_iso9001.pdf", "value": 0.82}
  ],
  "meta": {
    "total_documents": 15,
    "total_chunks": 340,
    "similarity_threshold": 0.75
  }
}
```

**Wymagania bezpieczeństwa:**

- `Depends(require_api_key)` na endpoincie
- Parametr `threshold` z walidacją `Field(ge=0.5, le=0.99)`
- Limit dokumentów (np. max 200 węzłów) — duże kolekcje mogą być ciężkie
- Brak `shell=True`, brak logowania treści dokumentów

**Zależności Python:** `numpy` (już w projekcie) do obliczenia cosine similarity. Żadnych nowych pakietów.

**Uwaga dot. wydajności:** Scroll po wszystkich wektorach z Qdrant może być wolny przy dużych kolekcjach. Rozważ cache z TTL (np. 5 min) w dict in-memory lub opcjonalny parametr `?refresh=true`.

---

### Etap 2: Rejestracja routera w main.py (0.5 godziny)

**Plik:** `backend_app/main.py`

Kroki:

1. Import: `from .routes.graph import router as graph_router`
2. Dodaj: `app.include_router(graph_router)`
3. Dodaj do `__init__.py` w routes jeśli potrzebne

---

### Etap 3: Frontend — karta grafu w index.html (1.5 dnia)

**Plik:** `backend_app/static/index.html`

**Biblioteka:** `3d-force-graph` z CDN (vasturiano/3d-force-graph)

```
https://unpkg.com/3d-force-graph
```

Alternatywnie wersja 2D jeśli 3D jest za ciężkie na starszych przeglądarkach:

```
https://unpkg.com/force-graph
```

**Implementacja:**

1. Dodaj nową kartę `<article>` w grid dashboardu (obok GPU Dashboard, Indeksowanie RAG)
2. Tytuł: "Graf Wiedzy"
3. Przycisk "Załaduj graf" → fetch do `/v1/graph`
4. Renderuj w `<div id="graph-container">` z 3d-force-graph
5. Konfiguracja wizualna:
   - Kolor węzłów wg `group` (subfolder źródłowy)
   - Rozmiar węzłów proporcjonalny do `chunks` (więcej chunków = większy dokument)
   - Grubość krawędzi proporcjonalna do `value` (similarity)
   - Tooltip na hover: nazwa pliku, liczba chunków, top-3 powiązania
   - Klik na węzeł → opcjonalnie otwórz szczegóły dokumentu

**JS — przypomnienie konwencji KlimtechRAG:**

- Użyj `var` zamiast `const/let`
- Konkatenacja stringów przez `+` (bez template literals z backticks)
- Brak modułów ES6 — skrypt inline w `<script>` tagu

**Slider progu similarity:**

- Input range `0.5 — 0.95` z krokiem 0.05
- Zmiana progu → re-fetch `/v1/graph?threshold=X` → re-render
- Pozwala eksplorować gęste vs rzadkie powiązania

---

### Etap 4: Grupowanie węzłów wg subfolderu (0.5 dnia)

**Opcjonalne, ale wartościowe.**

Payload w Qdrant zawiera `path` (pełna ścieżka pliku). Z niej można wyciągnąć subfolder:

- `/docs/raporty/q3.pdf` → group: `raporty`
- `/docs/normy/iso9001.pdf` → group: `normy`

Mapowanie subfolder → kolor w JS. Daje natychmiastową orientację wizualną — klastry dokumentów z tego samego tematu powinny być blisko siebie w grafie (bo semantycznie podobne) I mieć ten sam kolor (bo z tego samego folderu).

Jeśli klaster kolorów "rozpada się" — sygnał, że dokumenty z jednego folderu są tematycznie różnorodne.

---

## Czego NIE robimy (świadome ograniczenia)

| Element | Powód |
|---------|-------|
| Wikilinki `[[]]` w markdown | KlimtechRAG używa wektorów, nie ręcznych linków — graf semantyczny jest cenniejszy |
| Obsidian/Logseq jako zależność | Zero nowych aplikacji na serwerze — wszystko w istniejącym stacku |
| Edycja notatek z poziomu grafu | Dashboard jest read-only — edycja następuje na laptopie → git → serwer |
| Graf dla `klimtech_colpali` | ColPali to multi-vector (strony PDF) — centroid nie ma sensu. Tylko `klimtech_docs` |
| Neo4j / graph database | Overkill — Qdrant + cosine similarity wystarczy. Brak nowych kontenerów Podman |
| Real-time update grafu | Graf to snapshot — odświeżany na żądanie przyciskiem, nie WebSocket |

---

## Zależności od istniejącego kodu

| Plik | Co wykorzystujemy |
|------|-------------------|
| `backend_app/services/qdrant.py` | `doc_store`, konfiguracja kolekcji |
| `backend_app/config.py` | `settings.qdrant_url`, `settings.qdrant_collection` |
| `backend_app/utils/dependencies.py` | `require_api_key` |
| `backend_app/static/index.html` | Grid layout, styl kart, ciemny motyw |
| `scripts/ingest_embed.py` | Payload format (`source`, `path`, `content`) — musi być spójny |

---

## Testowanie

1. **Unit:** Endpoint `/v1/graph` zwraca poprawny JSON z nodes/links
2. **Integracja:** Po ingest kilku plików → graf pokazuje klastry
3. **Edge case:** Pusta kolekcja → graceful empty state ("Brak dokumentów")
4. **Edge case:** 1 dokument → 1 węzeł, 0 krawędzi
5. **Wydajność:** 100+ dokumentów — czas odpowiedzi < 5s (z cache < 100ms)

---

## Kolejność commitów (atomowe kroki)

```
1. feat(graph): add /v1/graph endpoint with cosine similarity matrix
2. feat(graph): register graph router in main.py
3. feat(ui): add knowledge graph card with 3d-force-graph
4. feat(ui): add similarity threshold slider
5. feat(graph): add subfolder-based grouping colors
6. feat(graph): add in-memory cache with TTL
```

**Branch:** `feature/knowledge-graph`
**Deployment:** laptop → `git push` → serwer `git pull` → restart backend

---

## Porównanie z Obsidian Graph View

| Aspekt | Obsidian Graph | KlimtechRAG Graph |
|--------|---------------|-------------------|
| Dane | Ręczne wikilinki `[[]]` | Automatyczne — cosine similarity wektorów |
| Odkrywanie | Tylko jawne powiązania | Ukryte powiązania semantyczne |
| Źródło prawdy | Pliki .md w vault | Qdrant (ten sam co RAG) |
| Aktualizacja | Natychmiast przy edycji | Po re-ingest + refresh |
| Instalacja | Osobna aplikacja Electron | Wbudowane w istniejący dashboard |
| 3D | Tylko z pluginem | Natywne (3d-force-graph) |

---

*Data utworzenia: 2026-04-14*
*Kontekst: KlimtechRAG — graf wiedzy jako alternatywa dla Obsidian (Opcja A)*
