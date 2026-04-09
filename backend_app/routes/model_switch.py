"""
routes/model_switch.py — Endpointy API do przełączania modeli
=============================================================

Endpoints:
- GET  /model/status         - Status aktualnego modelu
- POST /model/switch/llm     - Przełącz na LLM (czat)
- POST /model/switch/vlm     - Przełącz na VLM (obrazki)
- POST /model/switch         - Przełącz na wybrany typ (?type=llm lub ?type=vlm)
- GET  /model/list           - Lista dostępnych modeli
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from ..utils.dependencies import require_api_key
from ..services.model_manager import (
    get_server_status,
    switch_to_llm,
    switch_to_vlm,
    switch_model,
    get_available_models,
    get_models_config,
    start_model_with_progress,
    get_progress_lines,
    stop_llm_server,
    clear_progress_log,
    _log,
    LLAMA_PORT,
    BASE_DIR,
)
from ..utils.dependencies import require_api_key


router = APIRouter(
    prefix="/model",
    tags=["Model Management"],
    dependencies=[Depends(require_api_key)],
)


# ---------------------------------------------------------------------------
# MODELE PYDANTIC
# ---------------------------------------------------------------------------


class ModelStatus(BaseModel):
    running: bool
    model_type: str
    port: str
    llm_model: Optional[str] = None
    vlm_model: Optional[str] = None


class SwitchResult(BaseModel):
    success: bool
    message: str
    previous_type: Optional[str] = None
    new_type: Optional[str] = None
    model: Optional[str] = None
    pid: Optional[int] = None


class ModelInfo(BaseModel):
    path: str
    name: str
    size_gb: float
    folder: str


class ModelsList(BaseModel):
    llm: List[ModelInfo]
    vlm: List[ModelInfo]
    audio: List[ModelInfo]
    embedding: List[ModelInfo]


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------


@router.get("/status", response_model=ModelStatus)
async def get_model_status():
    """
    Pobiera status aktualnego modelu.

    Returns:
        - running: czy serwer działa
        - model_type: typ aktualnego modelu (llm/vlm/unknown)
        - port: port serwera
        - llm_model: ścieżka do wybranego modelu LLM
        - vlm_model: ścieżka do wybranego modelu VLM
    """
    status = get_server_status()
    config = get_models_config()

    if config:
        status["llm_model"] = config.get("llm_model")
        status["vlm_model"] = config.get("vlm_model")

    return ModelStatus(**status)


@router.post("/switch/llm", response_model=SwitchResult)
async def api_switch_to_llm(req: Request):
    require_api_key(req)
    """
    Przełącza na model LLM (do czatu).

    Zabija obecny model, czeka na zwolnienie VRAM, uruchamia LLM.
    Czas operacji: ~20-25 sekund.
    """
    result = switch_to_llm()
    return SwitchResult(**result)


@router.post("/switch/vlm", response_model=SwitchResult)
async def api_switch_to_vlm(req: Request):
    require_api_key(req)
    """
    Przełącza na model VLM (do obrazków).

    Zabija obecny model, czeka na zwolnienie VRAM, uruchamia VLM.
    Czas operacji: ~20-25 sekund.
    """
    result = switch_to_vlm()
    return SwitchResult(**result)


@router.post("/switch", response_model=SwitchResult)
async def api_switch_model(
    req: Request,
    model_type: str = Query(
        ..., pattern="^(llm|vlm)$", description="Typ modelu: llm lub vlm"
    ),
):
    require_api_key(req)
    """
    Przełącza na wybrany typ modelu.

    Args:
        model_type: "llm" dla czatu, "vlm" dla obrazków

    Czas operacji: ~20-25 sekund.
    """
    result = switch_model(model_type)
    return SwitchResult(**result)


@router.get("/list", response_model=ModelsList)
async def api_list_models():
    """
    Pobiera listę dostępnych modeli z katalogów.

    Modele są kategoryzowane na podstawie katalogów:
    - model_thinking/ → LLM
    - model_video/ → VLM
    - model_audio/ → Audio
    - model_embedding/ → Embedding
    """
    models = get_available_models()
    return ModelsList(**models)


@router.get("/config")
async def api_get_config():
    """
    Pobiera pełną konfigurację modeli.
    """
    config = get_models_config()
    if not config:
        raise HTTPException(status_code=404, detail="Brak konfiguracji modeli")
    return config


# ---------------------------------------------------------------------------
# ENDPOINT HTML DLA UI
# ---------------------------------------------------------------------------


@router.get("/ui")
async def model_switch_ui():
    """
    Prosty interfejs HTML do przełączania modeli.
    """
    status = get_server_status()
    config = get_models_config() or {}

    html = f"""
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Przełączanie Modeli - KlimtechRAG</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #eee;
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
            }}
            h1 {{
                text-align: center;
                margin-bottom: 30px;
                color: #4ecca3;
            }}
            .card {{
                background: rgba(255,255,255,0.1);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
            }}
            .status {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                background: rgba(0,0,0,0.2);
                border-radius: 8px;
                margin-bottom: 15px;
            }}
            .status-label {{ color: #888; }}
            .status-value {{
                font-weight: bold;
                font-size: 1.2em;
            }}
            .status-value.llm {{ color: #4ecca3; }}
            .status-value.vlm {{ color: #ff6b6b; }}
            .status-value.stopped {{ color: #888; }}
            .buttons {{
                display: flex;
                gap: 15px;
                justify-content: center;
                flex-wrap: wrap;
            }}
            button {{
                padding: 15px 30px;
                font-size: 16px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: bold;
            }}
            button:disabled {{
                opacity: 0.5;
                cursor: not-allowed;
            }}
            .btn-llm {{
                background: linear-gradient(135deg, #4ecca3, #38a3a5);
                color: #1a1a2e;
            }}
            .btn-llm:hover:not(:disabled) {{
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(78, 204, 163, 0.4);
            }}
            .btn-vlm {{
                background: linear-gradient(135deg, #ff6b6b, #ee5a5a);
                color: #fff;
            }}
            .btn-vlm:hover:not(:disabled) {{
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(255, 107, 107, 0.4);
            }}
            .btn-refresh {{
                background: #333;
                color: #fff;
                padding: 10px 20px;
            }}
            .models {{
                margin-top: 20px;
            }}
            .model-item {{
                display: flex;
                justify-content: space-between;
                padding: 10px;
                background: rgba(0,0,0,0.2);
                border-radius: 6px;
                margin-bottom: 8px;
            }}
            .model-name {{ font-weight: 500; }}
            .model-size {{ color: #888; }}
            .loading {{
                display: none;
                text-align: center;
                padding: 20px;
            }}
            .loading.active {{ display: block; }}
            .spinner {{
                border: 4px solid rgba(255,255,255,0.3);
                border-top: 4px solid #4ecca3;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 15px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .message {{
                padding: 15px;
                border-radius: 8px;
                margin-top: 15px;
                display: none;
            }}
            .message.success {{
                background: rgba(78, 204, 163, 0.2);
                border: 1px solid #4ecca3;
                color: #4ecca3;
            }}
            .message.error {{
                background: rgba(255, 107, 107, 0.2);
                border: 1px solid #ff6b6b;
                color: #ff6b6b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Przełączanie Modeli</h1>
            
            <div class="card">
                <div class="status">
                    <span class="status-label">Status serwera:</span>
                    <span id="server-status" class="status-value {"llm" if status["model_type"] == "llm" else "vlm" if status["model_type"] == "vlm" else "stopped"}">
                        {"LLM (Czat)" if status["model_type"] == "llm" else "VLM (Vision)" if status["model_type"] == "vlm" else "Zatrzymany"}
                    </span>
                </div>
                
                <div class="status">
                    <span class="status-label">Aktualny model:</span>
                    <span id="current-model" class="status-value">
                        {status.get("model_type", "brak").upper()}
                    </span>
                </div>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Przełączanie modelu... (~20s)</p>
                </div>
                
                <div class="buttons" id="buttons">
                    <button class="btn-llm" id="btn-llm" onclick="switchToLLM()">
                        💬 Przełącz na LLM (Czat)
                    </button>
                    <button class="btn-vlm" id="btn-vlm" onclick="switchToVLM()">
                        📷 Przełącz na VLM (Vision)
                    </button>
                    <button class="btn-refresh" onclick="refreshStatus()">
                        🔄 Odśwież
                    </button>
                </div>
                
                <div id="message" class="message"></div>
            </div>
            
            <div class="card models">
                <h3>📚 Skonfigurowane modele</h3>
                <div class="model-item">
                    <span class="model-name">💬 LLM:</span>
                    <span class="model-size">{config.get("llm_model", "brak").split("/")[-1] if config.get("llm_model") else "brak"}</span>
                </div>
                <div class="model-item">
                    <span class="model-name">📷 VLM:</span>
                    <span class="model-size">{config.get("vlm_model", "brak").split("/")[-1] if config.get("vlm_model") else "brak"}</span>
                </div>
            </div>
        </div>
        
        <script>
            async function switchToLLM() {{
                await switchModel('llm');
            }}
            
            async function switchToVLM() {{
                await switchModel('vlm');
            }}
            
            async function switchModel(type) {{
                const loading = document.getElementById('loading');
                const buttons = document.getElementById('buttons');
                const message = document.getElementById('message');
                
                loading.classList.add('active');
                buttons.style.opacity = '0.5';
                message.style.display = 'none';
                
                try {{
                    const response = await fetch(`/model/switch/${{type}}`, {{
                        method: 'POST'
                    }});
                    const data = await response.json();
                    
                    if (data.success) {{
                        message.className = 'message success';
                        message.textContent = `✅ ${{data.message}}`;
                    }} else {{
                        message.className = 'message error';
                        message.textContent = `❌ ${{data.message}}`;
                    }}
                    message.style.display = 'block';
                    
                }} catch (error) {{
                    message.className = 'message error';
                    message.textContent = `❌ Błąd: ${{error.message}}`;
                    message.style.display = 'block';
                }}
                
                loading.classList.remove('active');
                buttons.style.opacity = '1';
                
                refreshStatus();
            }}
            
            async function refreshStatus() {{
                try {{
                    const response = await fetch('/model/status');
                    const data = await response.json();
                    
                    const statusEl = document.getElementById('server-status');
                    const modelEl = document.getElementById('current-model');
                    
                    if (data.running) {{
                        statusEl.className = 'status-value ' + data.model_type;
                        statusEl.textContent = data.model_type === 'llm' ? 'LLM (Czat)' : 'VLM (Vision)';
                    }} else {{
                        statusEl.className = 'status-value stopped';
                        statusEl.textContent = 'Zatrzymany';
                    }}
                    
                    modelEl.textContent = data.model_type.toUpperCase();
                    
                }} catch (error) {{
                    console.error('Błąd:', error);
                }}
            }}
            
            // Odświeżaj status co 10 sekund
            setInterval(refreshStatus, 10000);
        </script>
    </body>
    </html>
    """

    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=html)


# ─── START / PROGRESS ─────────────────────────────────────────────────────────

from pydantic import BaseModel as _BM


class StartModelRequest(_BM):
    model_path: str
    model_type: str = "llm"  # "llm" | "vlm"


@router.post("/start")
async def start_model(body: StartModelRequest):
    """
    Uruchamia llama-server dla podanego modelu w tle.
    Postep logowany do llm_progress.log — pobieraj przez /model/progress-log
    """
    from pathlib import Path
    allowed = Path(BASE_DIR).resolve()
    target = Path(body.model_path).resolve()
    if not str(target).startswith(str(allowed)):
        raise HTTPException(status_code=403, detail="Model path outside allowed directory")
    result = start_model_with_progress(body.model_path, body.model_type, LLAMA_PORT)
    return result


@router.get("/progress-log")
async def progress_log(since: int = 0):
    """
    Zwraca linie progress logu od indeksu `since`.
    Uzyj do pollingu z UI (co 500ms).
    """
    data = get_progress_lines(since)
    status = get_server_status()
    data["server_running"] = status.get("running", False)
    return data


@router.post("/stop")
async def stop_model(req: Request):
    require_api_key(req)
    """Zatrzymuje aktualnie dzialajacy serwer LLM/VLM."""
    clear_progress_log()
    _log("Zatrzymywanie serwera LLM/VLM...")
    result = stop_llm_server()
    _log("VRAM zwolniony")
    return result
