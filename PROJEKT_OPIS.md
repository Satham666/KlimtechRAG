# KlimtechRAG — Opis Projektu

Lokalny system RAG (Retrieval-Augmented Generation) zbudowany na FastAPI + Haystack + Qdrant.
Działa na serwerze z AMD Instinct 16 GB VRAM w sieci lokalnej (192.168.31.x).

## Architektura

```
Użytkownik → UI (index.html) → FastAPI Backend (port 8000/8443)
                                    ├── Qdrant (port 6333) — wektory dokumentów
                                    ├── llama-server (port 8082) — LLM (Bielik/Qwen)
                                    └── SQLite — file_registry.db + sessions.db
```

## Główne funkcje (stan v7.7)

| Funkcja | Opis | Plik |
|---------|------|------|
| Chat completions | OpenAI-compatible `/v1/chat/completions` | routes/chat.py |
| RAG retrieval | Hybrid search: dense + BM25 + reranking | services/retrieval_service.py |
| Smart Router | Auto-decyzja RAG vs Direct LLM | services/router_service.py |
| Ingest pipeline | PDF/TXT/DOCX → chunk → embed → Qdrant | services/ingest_service.py |
| SSE streaming | Token-by-token chat + postęp ingestu | services/streaming_service.py |
| Session history | Persistentna historia czatu (SQLite) | services/session_service.py |
| MCP Compatibility | JSON-RPC 2.0: rag_query/list_documents/ingest_text | routes/mcp.py |
| Answer Verification | Drugi pass LLM weryfikujący odpowiedź | services/verification_service.py |
| Watcher | Asyncio background task monitorujący upload dirs | services/watcher_service.py |
| Batch Processing | Priority queue z retry i exponential backoff | services/batch_service.py |
| Embeddable Widget | Self-contained JS bubble chat | static/klimtech-widget.js |
| ColPali | Multi-vector PDF visual indexing | services/colpali_embedder.py |
| VLM | Analiza obrazów (Qwen2.5-VL) | services/vlm_service.py |
| Workspaces | Izolowane przestrzenie dokumentów | routes/workspaces.py |

## Zmienne środowiskowe (kluczowe)

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `KLIMTECH_BASE_PATH` | auto | Ścieżka bazowa projektu |
| `KLIMTECH_EMBEDDING_DEVICE` | `cpu` | `cpu` lub `cuda:0` |
| `KLIMTECH_ANSWER_VERIFICATION` | `false` | B5 weryfikacja odpowiedzi |
| `KLIMTECH_WATCHER_ENABLED` | `false` | H2 watcher katalogów |
| `KLIMTECH_CONTEXTUAL_ENRICHMENT` | `false` | C4 enrichment chunków |
| `KLIMTECH_BM25_WEIGHT` | `0.3` | Waga BM25 w hybrid search |

## Kolekcje Qdrant

| Kolekcja | Wymiar | Model |
|----------|--------|-------|
| `klimtech_docs` | 1024 | multilingual-e5-large |
| `klimtech_colpali` | 128 | ColPali v1.3 |

## Uruchomienie (serwer)

```fish
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate.fish
bash scripts/check_project.sh
python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000
```

## Embed widget (sieć lokalna)

```html
<script>
  window.KlimtechWidget = { apiUrl: "http://192.168.31.70:8000", apiKey: "sk-local", useRag: true };
</script>
<script src="http://192.168.31.70:8000/static/klimtech-widget.js"></script>
```
