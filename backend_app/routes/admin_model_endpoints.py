# ---------------------------------------------------------------------------
# DODAJ DO PLIKU backend_app/routes/admin.py
# ---------------------------------------------------------------------------
# Te endpointy można dodać na końcu pliku admin.py
# Nie wymagają tworzenia nowych plików
# ---------------------------------------------------------------------------

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import subprocess
import os
import json
import time
import glob

# Konfiguracja
BASE_DIR = os.environ.get("KLIMTECH_BASE_PATH", "/media/lobo/BACKUP/KlimtechRAG")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
LLAMA_PORT = "8082"
MODELS_CONFIG_FILE = os.path.join(LOG_DIR, "models_config.json")


# --- Modele Pydantic ---

class ModelStatusResponse(BaseModel):
    running: bool
    model_type: str
    llm_model: Optional[str] = None
    vlm_model: Optional[str] = None
    message: str = ""


class SwitchModelResponse(BaseModel):
    success: bool
    message: str
    previous_type: Optional[str] = None
    new_type: Optional[str] = None
    model: Optional[str] = None


# --- Funkcje pomocnicze ---

def _get_models_config():
    """Wczytuje konfigurację modeli."""
    if not os.path.exists(MODELS_CONFIG_FILE):
        return None
    try:
        with open(MODELS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return None


def _save_models_config(config):
    """Zapisuje konfigurację modeli."""
    os.makedirs(LOG_DIR, exist_ok=True)
    config["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(MODELS_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def _stop_llm_server():
    """Zatrzymuje serwer LLM."""
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
    subprocess.run(["fuser", "-k", f"{LLAMA_PORT}/tcp"], capture_output=True)
    time.sleep(3)


def _start_llm_server(model_path: str, model_type: str = "llm"):
    """Uruchamia serwer LLM/VLM."""
    
    llama_binary = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
    if not os.path.exists(llama_binary):
        llama_binary = os.path.join(LLAMA_DIR, "llama-server")
    
    if not os.path.exists(llama_binary) or not os.path.exists(model_path):
        return None
    
    amd_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "GPU_MAX_ALLOC_PERCENT": "100",
        "HSA_ENABLE_SDMA": "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
    }
    
    cmd = [llama_binary, "-m", model_path, "--host", "0.0.0.0", "--port", LLAMA_PORT, "-ngl", "99", "-c", "8192"]
    
    # VLM mmproj
    if model_type == "vlm":
        model_dir = os.path.dirname(model_path)
        mmproj = glob.glob(os.path.join(model_dir, "*mmproj*"))
        if mmproj:
            cmd.extend(["--mmproj", mmproj[0]])
    
    env = os.environ.copy()
    env.update(amd_env)
    
    log_out = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
    log_err = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")
    
    proc = subprocess.Popen(cmd, cwd=LLAMA_DIR, stdout=log_out, stderr=log_err, 
                           start_new_session=True, env=env)
    
    time.sleep(15)
    return proc if proc.poll() is None else None


# --- ENDPOINTY DO DODANIA DO ROUTERA ---

# Dodaj te endpointy do istniejącego router w admin.py
# Przykład: router = APIRouter(tags=["Admin"])

@router.get("/model/status", response_model=ModelStatusResponse)
async def get_model_status():
    """
    Pobiera status aktualnego modelu LLM/VLM.
    
    Sprawdza:
    - Czy serwer działa
    - Jaki typ modelu jest uruchomiony (llm/vlm)
    - Skonfigurowane modele
    """
    result = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True)
    running = result.returncode == 0
    
    config = _get_models_config()
    model_type = config.get("current_model_type", "unknown") if config else "unknown"
    
    return ModelStatusResponse(
        running=running,
        model_type=model_type if running else "stopped",
        llm_model=config.get("llm_model") if config else None,
        vlm_model=config.get("vlm_model") if config else None,
        message="Serwer działa" if running else "Serwer zatrzymany"
    )


@router.post("/model/switch/llm", response_model=SwitchModelResponse)
async def api_switch_to_llm():
    """
    Przełącza na model LLM (do czatu).
    
    Zabija obecny model, zwalnia VRAM, uruchamia LLM.
    Czas operacji: ~20-25 sekund.
    
    Wymaga wcześniejszego uruchomienia start_klimtech_v3.py
    """
    config = _get_models_config()
    if not config:
        raise HTTPException(status_code=400, detail="Brak konfiguracji. Uruchom start_klimtech_v3.py")
    
    llm_model = config.get("llm_model")
    if not llm_model:
        raise HTTPException(status_code=400, detail="Brak skonfigurowanego modelu LLM")
    
    previous = config.get("current_model_type", "unknown")
    
    if previous == "llm":
        return SwitchModelResponse(success=True, message="LLM już działa", 
                                  previous_type=previous, new_type="llm",
                                  model=os.path.basename(llm_model))
    
    # Zatrzymaj i uruchom
    _stop_llm_server()
    time.sleep(5)
    
    proc = _start_llm_server(llm_model, "llm")
    
    if proc:
        config["current_model_type"] = "llm"
        _save_models_config(config)
        return SwitchModelResponse(
            success=True,
            message=f"Przełączono na LLM: {os.path.basename(llm_model)}",
            previous_type=previous,
            new_type="llm",
            model=os.path.basename(llm_model)
        )
    else:
        raise HTTPException(status_code=500, detail="Błąd startu serwera LLM")


@router.post("/model/switch/vlm", response_model=SwitchModelResponse)
async def api_switch_to_vlm():
    """
    Przełącza na model VLM (do obrazków).
    
    Zabija obecny model, zwalnia VRAM, uruchamia VLM.
    Czas operacji: ~20-25 sekund.
    
    Wymaga wcześniejszego uruchomienia start_klimtech_v3.py
    """
    config = _get_models_config()
    if not config:
        raise HTTPException(status_code=400, detail="Brak konfiguracji. Uruchom start_klimtech_v3.py")
    
    vlm_model = config.get("vlm_model")
    if not vlm_model:
        raise HTTPException(status_code=400, detail="Brak skonfigurowanego modelu VLM")
    
    previous = config.get("current_model_type", "unknown")
    
    if previous == "vlm":
        return SwitchModelResponse(success=True, message="VLM już działa",
                                  previous_type=previous, new_type="vlm",
                                  model=os.path.basename(vlm_model))
    
    # Zatrzymaj i uruchom
    _stop_llm_server()
    time.sleep(5)
    
    proc = _start_llm_server(vlm_model, "vlm")
    
    if proc:
        config["current_model_type"] = "vlm"
        _save_models_config(config)
        return SwitchModelResponse(
            success=True,
            message=f"Przełączono na VLM: {os.path.basename(vlm_model)}",
            previous_type=previous,
            new_type="vlm",
            model=os.path.basename(vlm_model)
        )
    else:
        raise HTTPException(status_code=500, detail="Błąd startu serwera VLM")


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
