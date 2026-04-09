"""
agent_memory — Pamięć agentów w Qdrant (kolekcja agent_memory, dim=1024).

Endpointy:
  POST /v1/agent/memory         — zapisz wpis pamięci
  GET  /v1/agent/memory/search  — szukaj podobnych wpisów
  GET  /v1/agent/memory/recent  — ostatnie N wpisów
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..utils.dependencies import require_api_key
from ..config import settings

logger = logging.getLogger("klimtechrag")

router = APIRouter(prefix="/v1/agent", tags=["agent_memory"])

COLLECTION_NAME = "agent_memory"
EMBEDDING_DIM = 1024

# ---------------------------------------------------------------------------
# Modele danych
# ---------------------------------------------------------------------------

MEMORY_TYPES = {
    "błąd_agenta",
    "decyzja",
    "uwaga_sonnet",
    "plik_kontekst",
    "wynik_testu",
    "wzorzec_sukcesu",
    "snapshot",
    "sesja_przerwana",
    "plan_niezrealizowany",
    "decyzja_nadzorcza",
    "kontekst_przerwania",
    "wzorzec_błędu_ucznia",
}


class MemoryEntry(BaseModel):
    """Wpis do zapisania w pamięci agenta."""

    typ: str = Field(..., description="Typ wpisu: błąd_agenta, decyzja, snapshot, itd.")
    content: str = Field(..., min_length=1, description="Treść wpisu")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Dodatkowe metadane")


class MemoryResult(BaseModel):
    id: str
    typ: str
    content: str
    score: float
    timestamp: str
    meta: Dict[str, Any]


class MemorySaveResponse(BaseModel):
    id: str
    message: str


class MemorySearchResponse(BaseModel):
    data: List[MemoryResult]
    total: int


# ---------------------------------------------------------------------------
# Lazy inicjalizacja kolekcji agent_memory
# ---------------------------------------------------------------------------

_store = None


def _get_store():
    """Lazy singleton — nie ładuje nic dopóki nie zażądano."""
    global _store
    if _store is None:
        from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

        _store = QdrantDocumentStore(
            url=str(settings.qdrant_url),
            index=COLLECTION_NAME,
            embedding_dim=EMBEDDING_DIM,
            recreate_index=False,
        )
        logger.info("[agent_memory] Kolekcja '%s' gotowa", COLLECTION_NAME)
    return _store


# ---------------------------------------------------------------------------
# POST /v1/agent/memory — zapisz wpis
# ---------------------------------------------------------------------------


@router.post("/memory", response_model=MemorySaveResponse, status_code=201)
async def save_memory(
    entry: MemoryEntry,
    _: None = Depends(require_api_key),
) -> MemorySaveResponse:
    """Zapisuje wpis do pamięci agenta w Qdrant.

    Wpis jest embeddowany (e5-large) i przechowywany w kolekcji agent_memory.
    Dostęp wyłącznie przez API key — tylko Sonnet zapisuje do tej kolekcji.
    """
    if entry.typ not in MEMORY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Nieznany typ wpisu: '{entry.typ}'. Dozwolone: {sorted(MEMORY_TYPES)}",
        )

    from haystack.dataclasses import Document
    from ..services import get_text_embedder

    entry_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    meta = {
        "typ": entry.typ,
        "timestamp": timestamp,
        **{k: v for k, v in entry.meta.items()},
    }

    try:
        embedding_result = get_text_embedder().run(text=entry.content)
        embedding = embedding_result.get("embedding")

        doc = Document(
            id=entry_id,
            content=entry.content,
            meta=meta,
            embedding=embedding,
        )

        store = _get_store()
        store.write_documents([doc])

        logger.info(
            "[agent_memory] Zapisano wpis id=%s typ=%s",
            entry_id,
            entry.typ,
        )
        return MemorySaveResponse(id=entry_id, message="Wpis zapisany")

    except Exception as e:
        logger.exception("[agent_memory] Błąd zapisu: %s", e)
        raise HTTPException(status_code=500, detail=f"Błąd zapisu do pamięci: {e}")


# ---------------------------------------------------------------------------
# GET /v1/agent/memory/search — szukaj semantycznie
# ---------------------------------------------------------------------------


@router.get("/memory/search", response_model=MemorySearchResponse)
async def search_memory(
    q: str = Query(..., min_length=1, description="Zapytanie semantyczne"),
    limit: int = Query(5, ge=1, le=50),
    typ: Optional[str] = Query(None, description="Filtr po typie wpisu"),
    _: None = Depends(require_api_key),
) -> MemorySearchResponse:
    """Wyszukuje wpisy z pamięci agenta semantycznie (cosine similarity).

    Opcjonalnie filtruje po typie wpisu.
    """
    from ..services import get_text_embedder
    from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

    try:
        query_embedding = get_text_embedder().run(text=q)

        retriever = QdrantEmbeddingRetriever(
            document_store=_get_store(),
            top_k=limit * 2 if typ else limit,
        )
        result = retriever.run(
            query_embedding=query_embedding["embedding"],
        )
        docs = result.get("documents", [])

        if typ:
            docs = [d for d in docs if d.meta.get("typ") == typ]

        docs = docs[:limit]

        results = [
            MemoryResult(
                id=doc.id or "",
                typ=doc.meta.get("typ", ""),
                content=doc.content or "",
                score=round(float(getattr(doc, "score", 0.0) or doc.meta.get("score", 0.0)), 4),
                timestamp=doc.meta.get("timestamp", ""),
                meta={k: v for k, v in doc.meta.items() if k not in ("typ", "timestamp")},
            )
            for doc in docs
        ]

        logger.info("[agent_memory] Szukano: '%s' → %d wyników", q[:60], len(results))
        return MemorySearchResponse(data=results, total=len(results))

    except Exception as e:
        logger.exception("[agent_memory] Błąd wyszukiwania: %s", e)
        raise HTTPException(status_code=500, detail=f"Błąd wyszukiwania: {e}")


# ---------------------------------------------------------------------------
# GET /v1/agent/memory/recent — ostatnie N wpisów
# ---------------------------------------------------------------------------


@router.get("/memory/recent", response_model=MemorySearchResponse)
async def recent_memory(
    limit: int = Query(10, ge=1, le=100),
    typ: Optional[str] = Query(None, description="Filtr po typie wpisu"),
    _: None = Depends(require_api_key),
) -> MemorySearchResponse:
    """Zwraca ostatnie wpisy z pamięci (posortowane po timestamp malejąco)."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue, ScrollRequest

    try:
        client = QdrantClient(url=str(settings.qdrant_url))

        scroll_filter = None
        if typ:
            scroll_filter = Filter(
                must=[FieldCondition(key="typ", match=MatchValue(value=typ))]
            )

        records, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
            order_by="timestamp",
        )

        results = [
            MemoryResult(
                id=str(r.id),
                typ=r.payload.get("typ", ""),
                content=r.payload.get("document", {}).get("content", "") or r.payload.get("content", ""),
                score=0.0,
                timestamp=r.payload.get("timestamp", ""),
                meta={k: v for k, v in r.payload.items() if k not in ("typ", "timestamp", "document")},
            )
            for r in records
        ]

        logger.info("[agent_memory] Recent %d wpisów (typ=%s)", len(results), typ)
        return MemorySearchResponse(data=results, total=len(results))

    except Exception as e:
        logger.exception("[agent_memory] Błąd recent: %s", e)
        raise HTTPException(status_code=500, detail=f"Błąd pobierania wpisów: {e}")
