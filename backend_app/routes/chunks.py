import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from ..models.schemas import ChunkResult, ChunksRequest, ChunksResponse
from ..utils.dependencies import require_api_key

logger = logging.getLogger("klimtechrag")

router = APIRouter(prefix="/v1", tags=["chunks"])

# ---------------------------------------------------------------------------
# B7: /v1/chunks — Low-level retrieval bez LLM
# Zwraca chunki z Qdrant (score, source, content) bez odpowiedzi LLM.
# Używany przez F2 (podgląd źródeł) i zewnętrznych klientów.
# ---------------------------------------------------------------------------


@router.post("/chunks", response_model=ChunksResponse)
async def get_chunks(
    request: ChunksRequest,
    _: str = Depends(require_api_key),
) -> ChunksResponse:
    """Pobiera chunki z Qdrant dla danego zapytania tekstowego.

    Nie wywołuje LLM — zwraca surowe chunki z metadanymi i score.
    """
    from ..services import get_text_embedder
    from ..services.qdrant import get_qdrant_retriever

    if not request.text or not request.text.strip():
        raise HTTPException(status_code=422, detail="Pole 'text' nie może być puste")

    try:
        query_embedding = get_text_embedder().run(text=request.text)
        retriever = get_qdrant_retriever()

        # Pobieramy limit * 2 aby mieć margines po filtrze context_filter
        fetch_k = max(request.limit * 2, 20)
        result = retriever.run(
            query_embedding=query_embedding["embedding"],
            top_k=fetch_k,
        )
        raw_docs = result.get("documents", [])

        # Filtr context_filter (np. {"source": "raport.pdf"})
        if request.context_filter:
            filtered = []
            for doc in raw_docs:
                match = all(
                    doc.meta.get(k) == v for k, v in request.context_filter.items()
                )
                if match:
                    filtered.append(doc)
            raw_docs = filtered

        # Ogranicz do limit
        raw_docs = raw_docs[: request.limit]

        chunks: List[ChunkResult] = []
        for doc in raw_docs:
            score = float(getattr(doc, "score", 0.0) or doc.meta.get("score", 0.0))
            chunks.append(
                ChunkResult(
                    id=doc.id or "",
                    content=doc.content or "",
                    score=round(score, 4),
                    source=doc.meta.get("source", "unknown"),
                    meta={k: v for k, v in doc.meta.items() if k != "source"},
                )
            )

        logger.info(
            "[/v1/chunks] %d chunków dla: %s",
            len(chunks),
            request.text[:60],
        )
        return ChunksResponse(data=chunks, total=len(chunks))

    except Exception as e:
        logger.exception("[/v1/chunks] Błąd: %s", e)
        raise HTTPException(status_code=500, detail=f"Błąd retrieval: {e}")
