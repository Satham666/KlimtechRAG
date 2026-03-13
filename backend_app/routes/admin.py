import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse

from ..config import settings
from ..services import doc_store
from ..file_registry import (
    init_db as init_file_registry,
    sync_with_filesystem,
    get_stats as get_file_stats,
    list_files,
    get_pending_files,
)

router = APIRouter(tags=["admin"])
logger = logging.getLogger("klimtechrag")

metrics = {
    "ingest_requests": 0,
    "query_requests": 0,
    "code_query_requests": 0,
}


@router.get("/health")
async def health_check():
    qdrant_ok = False
    llm_ok = False

    try:
        count = doc_store.count_documents()
        qdrant_ok = count >= 0
    except Exception:
        qdrant_ok = False

    llm_ok = True

    status = qdrant_ok and llm_ok
    return {
        "status": "ok" if status else "degraded",
        "qdrant": qdrant_ok,
        "llm": llm_ok,
    }


@router.get("/metrics")
async def metrics_endpoint():
    return {
        "ingest_requests": metrics["ingest_requests"],
        "query_requests": metrics["query_requests"],
        "code_query_requests": metrics["code_query_requests"],
    }


@router.delete("/documents")
async def delete_documents(
    source: Optional[str] = None,
    doc_id: Optional[str] = None,
):
    if not source and not doc_id:
        raise HTTPException(
            status_code=400, detail="Provide at least source or doc_id filter"
        )

    filters = {}
    if source:
        filters = {"field": "meta.source", "operator": "==", "value": source}
    if doc_id:
        filters = {"field": "id", "operator": "==", "value": doc_id}
    if source and doc_id:
        filters = {
            "operator": "AND",
            "conditions": [
                {"field": "meta.source", "operator": "==", "value": source},
                {"field": "id", "operator": "==", "value": doc_id},
            ],
        }

    doc_store.delete_by_filter(filters)
    return {"status": "ok"}


@router.websocket("/ws/health")
async def websocket_health(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            health = await health_check()
            await ws.send_json(health)
            await ws.receive_text()
    except Exception:
        await ws.close()

@router.get("/files/stats")
async def files_stats():
    return get_file_stats()


@router.get("/files/list")
async def files_list(
    ext: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
):
    files = list_files(extension=ext, status=status, limit=limit)
    return {
        "count": len(files),
        "files": [
            {
                "filename": f.filename,
                "extension": f.extension,
                "size_kb": round(f.size_bytes / 1024, 1),
                "status": f.status,
                "chunks": f.chunks_count,
                "indexed_at": f.indexed_at,
            }
            for f in files
        ],
    }


@router.post("/files/sync")
async def files_sync():
    count = sync_with_filesystem()
    return {"registered": count, "message": f"Zsynchronizowano {count} plików"}


@router.get("/files/pending")
async def files_pending():
    files = get_pending_files()
    return {
        "count": len(files),
        "files": [
            {
                "path": f.path,
                "filename": f.filename,
                "extension": f.extension,
                "size_kb": round(f.size_bytes / 1024, 1),
            }
            for f in files
        ],
    }
# --- ENDPOINTY DO DODANIA DO ROUTERA ---

# Dodaj te endpointy do istniejącego router w admin.py
# Przykład: router = APIRouter(tags=["Admin"])



@router.get("/model/ui")
async def model_switch_ui():
    """
    Prosty interfejs HTML do przełączania modeli.
    Dostępny pod: http://localhost:8000/model/ui
    """
    config = _get_models_config() or {}
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <title>Przełączanie Modeli</title>
        <style>
            body {{ font-family: system-ui; background: #1a1a2e; color: #eee; padding: 20px; text-align: center; }}
            .container {{ max-width: 500px; margin: 0 auto; }}
            h1 {{ color: #4ecca3; }}
            .status {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin: 20px 0; }}
            button {{ padding: 15px 30px; font-size: 16px; margin: 10px; cursor: pointer; border: none; border-radius: 8px; }}
            .btn-llm {{ background: #4ecca3; color: #1a1a2e; }}
            .btn-vlm {{ background: #ff6b6b; color: #fff; }}
            .btn-llm:hover {{ background: #38a3a5; }}
            .btn-vlm:hover {{ background: #ee5a5a; }}
            .loading {{ display: none; color: #4ecca3; padding: 20px; }}
            .model {{ background: rgba(0,0,0,0.2); padding: 10px; margin: 5px 0; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Przełączanie Modeli</h1>
            <div class="status" id="status">Ładowanie...</div>
            <div class="loading" id="loading">⏳ Przełączanie... (~20s)</div>
            <div>
                <button class="btn-llm" onclick="switchModel('llm')">💬 LLM (Czat)</button>
                <button class="btn-vlm" onclick="switchModel('vlm')">📷 VLM (Vision)</button>
            </div>
            <div style="margin-top:20px">
                <div class="model">💬 LLM: {config.get('llm_model', 'brak').split('/')[-1] if config.get('llm_model') else 'brak'}</div>
                <div class="model">📷 VLM: {config.get('vlm_model', 'brak').split('/')[-1] if config.get('vlm_model') else 'brak'}</div>
            </div>
        </div>
        <script>
            async function refresh() {{
                const r = await fetch('/model/status');
                const d = await r.json();
                document.getElementById('status').innerHTML = 
                    `<b>Status:</b> ${{d.running ? '✅ ' + d.model_type.toUpperCase() : '❌ Zatrzymany'}}`;
            }}
            async function switchModel(type) {{
                document.getElementById('loading').style.display = 'block';
                try {{
                    const r = await fetch(`/model/switch/${{type}}`, {{method: 'POST'}});
                    const d = await r.json();
                    alert(d.message);
                }} catch(e) {{ alert('Błąd: ' + e); }}
                document.getElementById('loading').style.display = 'none';
                refresh();
            }}
            refresh();
            setInterval(refresh, 10000);
        </script>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)
