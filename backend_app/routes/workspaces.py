import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..utils.dependencies import require_api_key

logger = logging.getLogger("klimtechrag")

# ---------------------------------------------------------------------------
# W1: Workspaces — izolowane konteksty RAG
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nazwa workspace'a")
    description: str = Field(default="", max_length=500)


class WorkspaceInfo(BaseModel):
    name: str
    description: str = ""
    points_count: int = 0
    vectors_count: int = 0


def _get_qdrant_client():
    try:
        from qdrant_client import QdrantClient

        from ..config import settings

        return QdrantClient(url=str(settings.qdrant_url))
    except Exception as e:
        logger.error("[Workspaces] Qdrant client error: %s", e)
        return None


def _get_embedding_dim() -> int:
    from ..config import settings

    try:
        dim = settings.embedding_dim
        if dim and dim > 0:
            return dim
    except Exception:
        pass
    return 1024


def _collection_name(workspace: str) -> str:
    return f"workspace_{workspace.lower().replace(' ', '_').replace('-', '_')}"


@router.post("", response_model=WorkspaceInfo)
async def create_workspace(
    data: WorkspaceCreate,
    _: str = Depends(require_api_key),
):
    """Tworzy nowy workspace (kolekcje Qdrant)."""
    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    collection = _collection_name(data.name)

    try:
        existing = client.get_collection(collection)
        return WorkspaceInfo(
            name=data.name,
            description=data.description,
            points_count=existing.points_count,
            vectors_count=existing.vectors_count or 0,
        )
    except Exception:
        pass

    from qdrant_client import models

    try:
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=_get_embedding_dim(),
                distance=models.Distance.COSINE,
            ),
        )
        logger.info("[Workspaces] Utworzono: %s (%d dim)", collection, _get_embedding_dim())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blad tworzenia kolekcji: {e}")

    return WorkspaceInfo(name=data.name, description=data.description)


@router.get("", response_model=list[WorkspaceInfo])
async def list_workspaces(
    _: str = Depends(require_api_key),
):
    """Zwraca liste workspace'ow."""
    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    collections = client.get_collections().collections
    workspaces = []

    for c in collections:
        name = c.name
        if name.startswith("workspace_"):
            ws_name = name[len("workspace_"):]
            workspaces.append(WorkspaceInfo(
                name=ws_name,
                points_count=c.points_count,
                vectors_count=c.vectors_count or 0,
            ))

    return workspaces


@router.delete("/{workspace_name}")
async def delete_workspace(
    workspace_name: str,
    force: bool = Query(False, description="Wymusza usuniecie"),
    _: str = Depends(require_api_key),
):
    """Usuwa workspace (kolekcje Qdrant)."""
    if workspace_name.lower().replace(" ", "_") == "klimtech_docs":
        if not force:
            raise HTTPException(
                status_code=403,
                detail="Nie mozna usunac domyslnego workspace'u bez flagi ?force=true",
            )

    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    collection = _collection_name(workspace_name)

    try:
        client.delete_collection(collection)
        logger.info("[Workspaces] Usunieto: %s", collection)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Workspace nie istnieje: {e}")

    return {"status": "ok", "workspace": workspace_name, "collection": collection}


@router.get("/{workspace_name}/stats")
async def workspace_stats(
    workspace_name: str,
    _: str = Depends(require_api_key),
):
    """Zwraca statystyki workspace'a."""
    client = _get_qdrant_client()
    if not client:
        raise HTTPException(status_code=503, detail="Qdrant niedostepny")

    collection = _collection_name(workspace_name)

    try:
        info = client.get_collection(collection)
        return {
            "name": workspace_name,
            "collection": collection,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count or 0,
            "status": "ok",
        }
    except Exception:
        raise HTTPException(status_code=404, detail="Workspace nie istnieje")
