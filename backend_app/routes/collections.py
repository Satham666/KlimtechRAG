import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..utils.dependencies import require_api_key

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# E3: Multi-collection management — niskopoziomowe CRUD kolekcji Qdrant
# Uzupełnia W1 Workspaces (E3 jest bardziej generyczny, bez prefixu workspace_)
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/collections", tags=["collections"])

PROTECTED_COLLECTIONS = {"klimtech_docs", "klimtech_colpali"}


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    vector_size: int = Field(default=1024, ge=1, le=4096)


class CollectionInfo(BaseModel):
    name: str
    points_count: int = 0
    vectors_count: int = 0
    vector_size: int = 0
    protected: bool = False


def _get_qdrant_client():
    try:
        from qdrant_client import QdrantClient

        from ..config import settings

        return QdrantClient(url=str(settings.qdrant_url))
    except Exception as e:
        logger.error("[Collections] Qdrant client error: %s", e)
        return None


@router.post("", response_model=CollectionInfo)
async def create_collection(
    data: CollectionCreate,
    _: str = Depends(require_api_key),
):
    """Tworzy nowa kolekcje Qdrant."""
    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    try:
        existing = client.get_collection(data.name)
        return CollectionInfo(
            name=data.name,
            points_count=existing.points_count,
            vectors_count=existing.vectors_count or 0,
            protected=data.name in PROTECTED_COLLECTIONS,
        )
    except Exception:
        pass

    from qdrant_client import models

    try:
        client.create_collection(
            collection_name=data.name,
            vectors_config=models.VectorParams(
                size=data.vector_size,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info("[Collections] Utworzono: %s (dim=%d)", data.name, data.vector_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blad tworzenia: {e}")

    return CollectionInfo(name=data.name, vector_size=data.vector_size)


@router.get("", response_model=list[CollectionInfo])
async def list_collections(
    _: str = Depends(require_api_key),
):
    """Zwraca wszystkie kolekcje Qdrant z statystykami."""
    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    collections = client.get_collections().collections
    return [
        CollectionInfo(
            name=c.name,
            points_count=c.points_count,
            vectors_count=c.vectors_count or 0,
            protected=c.name in PROTECTED_COLLECTIONS,
        )
        for c in collections
    ]


@router.delete("/{collection_name}")
async def delete_collection(
    collection_name: str,
    force: bool = Query(False),
    _: str = Depends(require_api_key),
):
    """Usuwa kolekcje Qdrant. Chronione kolekcje wymagaja ?force=true."""
    if collection_name in PROTECTED_COLLECTIONS and not force:
        raise HTTPException(
            status_code=403,
            detail=f"Kolekcja '{collection_name}' jest chroniona. Uzyj ?force=true.",
        )

    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    try:
        client.delete_collection(collection_name)
        logger.info("[Collections] Usunieto: %s", collection_name)
    except Exception:
        raise HTTPException(status_code=404, detail="Kolekcja nie istnieje")

    return {"status": "ok", "collection": collection_name}


@router.get("/{collection_name}")
async def collection_info(
    collection_name: str,
    _: str = Depends(require_api_key),
):
    """Zwraca szczegolowe informacje o kolekcji."""
    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    try:
        info = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count or 0,
            "protected": collection_name in PROTECTED_COLLECTIONS,
            "status": "ok",
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Kolekcja nie istnieje")
