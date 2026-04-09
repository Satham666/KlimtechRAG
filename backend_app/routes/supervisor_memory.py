"""
supervisor_memory — Pamięć nadzorcy (Sonnet) w Qdrant (kolekcja supervisor_memory, dim=1024).

Endpointy:
  POST /v1/supervisor/snapshot        — zapisz snapshot sesji
  GET  /v1/supervisor/memory/search   — szukaj podobnych wpisów
  GET  /v1/supervisor/memory/recent   — ostatnie N wpisów
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

router = APIRouter(prefix="/v1/supervisor", tags=["supervisor_memory"])

COLLECTION_NAME = "supervisor_memory"
EMBEDDING_DIM = 1024

# ---------------------------------------------------------------------------
# Modele danych
# ---------------------------------------------------------------------------

SNAPSHOT_TYPES = {
    "snapshot",
    "plan_niezrealizowany",
    "decyzja_nadzorcza",
    "kontekst_przerwania",
    "wzorzec_błędu_ucznia",
    "sesja_przerwana",
}


class SessionSnapshot(BaseModel):
    """Snapshot stanu sesji zapisywany przez Sonnet na końcu sesji."""

    typ: str = Field("snapshot", description="Typ wpisu: snapshot, sesja_przerwana, itd.")
    ostatni_krok: str = Field(..., min_length=1, description="Co zostało ostatnio zrobione")
    nastepny_krok: str = Field(..., min_length=1, description="Co zrobić w następnej sesji")
    git_status: List[str] = Field(default_factory=list, description="Lista zmodyfikowanych plików")
    uwagi: Optional[str] = Field(None, description="Dodatkowe uwagi dla następnej sesji")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Dodatkowe metadane")


class SnapshotResult(BaseModel):
    id: str
    typ: str
    ostatni_krok: str
    nastepny_krok: str
    git_status: List[str]
    uwagi: Optional[str]
    score: float
    timestamp: str
    meta: Dict[str, Any]


class SnapshotSaveResponse(BaseModel):
    id: str
    message: str


class SnapshotSearchResponse(BaseModel):
    data: List[SnapshotResult]
    total: int


# ---------------------------------------------------------------------------
# Lazy inicjalizacja kolekcji supervisor_memory
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
        logger.info("[supervisor_memory] Kolekcja '%s' gotowa", COLLECTION_NAME)
    return _store


def _payload_to_result(payload: Dict[str, Any], score: float = 0.0, doc_id: str = "") -> SnapshotResult:
    """Konwertuje payload Qdrant na SnapshotResult."""
    return SnapshotResult(
        id=doc_id,
        typ=payload.get("typ", "snapshot"),
        ostatni_krok=payload.get("ostatni_krok", ""),
        nastepny_krok=payload.get("nastepny_krok", ""),
        git_status=payload.get("git_status", []),
        uwagi=payload.get("uwagi"),
        score=round(float(score), 4),
        timestamp=payload.get("timestamp", ""),
        meta={k: v for k, v in payload.items()
              if k not in ("typ", "ostatni_krok", "nastepny_krok", "git_status", "uwagi", "timestamp")},
    )


# ---------------------------------------------------------------------------
# POST /v1/supervisor/snapshot — zapisz snapshot sesji
# ---------------------------------------------------------------------------


@router.post("/snapshot", response_model=SnapshotSaveResponse, status_code=201)
async def save_snapshot(
    snap: SessionSnapshot,
    _: None = Depends(require_api_key),
) -> SnapshotSaveResponse:
    """Zapisuje snapshot sesji do pamięci nadzorcy w Qdrant.

    Przeznaczony wyłącznie dla Sonnet — zapisuje stan na końcu sesji,
    żeby następna sesja mogła odtworzyć kontekst.
    """
    if snap.typ not in SNAPSHOT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Nieznany typ: '{snap.typ}'. Dozwolone: {sorted(SNAPSHOT_TYPES)}",
        )

    from haystack.dataclasses import Document
    from ..services import get_text_embedder

    snap_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Tekst do embeddingu — synteza kluczowych pól
    tekst = f"{snap.ostatni_krok}. Następny krok: {snap.nastepny_krok}."
    if snap.uwagi:
        tekst += f" Uwagi: {snap.uwagi}"

    payload = {
        "typ": snap.typ,
        "ostatni_krok": snap.ostatni_krok,
        "nastepny_krok": snap.nastepny_krok,
        "git_status": snap.git_status,
        "uwagi": snap.uwagi,
        "timestamp": timestamp,
        **{k: v for k, v in snap.meta.items()},
    }

    try:
        embedding_result = get_text_embedder().run(text=tekst)
        embedding = embedding_result.get("embedding")

        doc = Document(
            id=snap_id,
            content=tekst,
            meta=payload,
            embedding=embedding,
        )

        store = _get_store()
        store.write_documents([doc])

        logger.info(
            "[supervisor_memory] Snapshot zapisany id=%s typ=%s",
            snap_id,
            snap.typ,
        )
        return SnapshotSaveResponse(id=snap_id, message="Snapshot zapisany")

    except Exception as e:
        logger.exception("[supervisor_memory] Błąd zapisu: %s", e)
        raise HTTPException(status_code=500, detail=f"Błąd zapisu snapshotu: {e}")


# ---------------------------------------------------------------------------
# GET /v1/supervisor/memory/search — szukaj semantycznie
# ---------------------------------------------------------------------------


@router.get("/memory/search", response_model=SnapshotSearchResponse)
async def search_snapshots(
    q: str = Query(..., min_length=1, description="Zapytanie semantyczne"),
    limit: int = Query(5, ge=1, le=50),
    typ: Optional[str] = Query(None, description="Filtr po typie wpisu"),
    _: None = Depends(require_api_key),
) -> SnapshotSearchResponse:
    """Wyszukuje snapshoty z pamięci nadzorcy semantycznie (cosine similarity)."""
    from ..services import get_text_embedder
    from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever

    try:
        query_embedding = get_text_embedder().run(text=q)

        retriever = QdrantEmbeddingRetriever(
            document_store=_get_store(),
            top_k=limit * 2 if typ else limit,
        )
        result = retriever.run(query_embedding=query_embedding["embedding"])
        docs = result.get("documents", [])

        if typ:
            docs = [d for d in docs if d.meta.get("typ") == typ]

        docs = docs[:limit]

        results = [
            _payload_to_result(
                payload=doc.meta,
                score=float(getattr(doc, "score", 0.0) or doc.meta.get("score", 0.0)),
                doc_id=doc.id or "",
            )
            for doc in docs
        ]

        logger.info("[supervisor_memory] Szukano: '%s' → %d wyników", q[:60], len(results))
        return SnapshotSearchResponse(data=results, total=len(results))

    except Exception as e:
        logger.exception("[supervisor_memory] Błąd wyszukiwania: %s", e)
        raise HTTPException(status_code=500, detail=f"Błąd wyszukiwania: {e}")


# ---------------------------------------------------------------------------
# GET /v1/supervisor/memory/recent — ostatnie N snapshotów
# ---------------------------------------------------------------------------


@router.get("/memory/recent", response_model=SnapshotSearchResponse)
async def recent_snapshots(
    limit: int = Query(10, ge=1, le=100),
    typ: Optional[str] = Query(None, description="Filtr po typie wpisu"),
    _: None = Depends(require_api_key),
) -> SnapshotSearchResponse:
    """Zwraca ostatnie snapshoty z pamięci nadzorcy (posortowane po timestamp malejąco)."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue

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
            _payload_to_result(
                payload=r.payload,
                score=0.0,
                doc_id=str(r.id),
            )
            for r in records
        ]

        logger.info("[supervisor_memory] Recent %d snapshotów (typ=%s)", len(results), typ)
        return SnapshotSearchResponse(data=results, total=len(results))

    except Exception as e:
        logger.exception("[supervisor_memory] Błąd recent: %s", e)
        raise HTTPException(status_code=500, detail=f"Błąd pobierania snapshotów: {e}")
