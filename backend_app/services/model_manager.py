"""
services/model_manager.py — Zarządzanie modelami LLM/VLM
=========================================================

Funkcje:
- Przełączanie między modelami LLM i VLM
- Zatrzymianie/startowanie serwera llama.cpp
- Odczyt/zapis konfiguracji modeli
"""

import subprocess
import os
import json
import time
import glob
from typing import Optional, Dict, Any

try:
    from ..config import settings
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from config import settings
    except ImportError:
        settings = None

# ---------------------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------------------


def _detect_base():
    from pathlib import Path

    env = os.environ.get("KLIMTECH_BASE_PATH", "").strip()
    if env and Path(env).exists():
        return env
    h = Path.home() / "KlimtechRAG"
    if h.exists():
        return str(h)
    return "/media/lobo/BACKUP/KlimtechRAG"


BASE_DIR = _detect_base()
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LLM_COMMAND_FILE = os.path.join(LOG_DIR, "llm_command.txt")
MODELS_CONFIG_FILE = os.path.join(LOG_DIR, "models_config.json")

LLAMA_PORT = "8082"

# Katalogi modeli
MODEL_CATEGORIES = {
    "llm": ["model_thinking", "model_reasoning"],
    "vlm": ["model_video", "model_vision"],
    "audio": ["model_audio"],
    "embedding": ["model_embedding"],
}


# ---------------------------------------------------------------------------
# FUNKCJE POMOCNICZE
# ---------------------------------------------------------------------------


def get_models_config() -> Optional[Dict[str, Any]]:
    """Wczytuje konfigurację wybranych modeli."""
    if not os.path.exists(MODELS_CONFIG_FILE):
        return None
    try:
        with open(MODELS_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_models_config(config: Dict[str, Any]) -> bool:
    """Zapisuje konfigurację modeli."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        config["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(MODELS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Błąd zapisu konfiguracji: {e}")
        return False


def get_server_status() -> Dict[str, Any]:
    """Sprawdza status serwera LLM/VLM."""
    result = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True)
    running = result.returncode == 0

    config = get_models_config()
    current_type = config.get("current_model_type", "unknown") if config else "unknown"

    return {"running": running, "model_type": current_type, "port": LLAMA_PORT}


# ---------------------------------------------------------------------------
# ZARZĄDZANIE SERWEREM
# ---------------------------------------------------------------------------


def stop_llm_server() -> Dict[str, Any]:
    """Zatrzymuje serwer LLM/VLM."""
    result = {"success": True, "message": "Serwer zatrzymany"}

    try:
        # Zabij przez pkill
        subprocess.run(["pkill", "-f", "llama-server"], capture_output=True, timeout=10)
        subprocess.run(["pkill", "-f", "llama-cli"], capture_output=True, timeout=10)

        # Zabij port
        subprocess.run(
            ["fuser", "-k", f"{LLAMA_PORT}/tcp"], capture_output=True, timeout=5
        )

        # Czekaj na zwolnienie
        time.sleep(3)

    except subprocess.TimeoutExpired:
        result["success"] = False
        result["message"] = "Timeout przy zatrzymywaniu serwera"
    except Exception as e:
        result["success"] = False
        result["message"] = f"Błąd: {str(e)}"

    return result


def start_llm_server(model_path: str, model_type: str = "llm") -> Dict[str, Any]:
    """
    Uruchamia serwer LLM lub VLM.

    Args:
        model_path: Ścieżka do modelu GGUF
        model_type: "llm" lub "vlm"

    Returns:
        Dict z wynikiem operacji
    """
    result = {
        "success": False,
        "message": "",
        "pid": None,
        "model": os.path.basename(model_path),
        "model_type": model_type,
    }

    if not os.path.exists(model_path):
        result["message"] = f"Model nie istnieje: {model_path}"
        return result

    # AMD GPU env
    amd_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "GPU_MAX_ALLOC_PERCENT": "100",
        "HSA_ENABLE_SDMA": "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
    }

    # Znajdź binarkę llama-server
    llama_binary = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
    if not os.path.exists(llama_binary):
        llama_binary = os.path.join(LLAMA_DIR, "llama-server")

    if not os.path.exists(llama_binary):
        result["message"] = f"Nie znaleziono llama-server"
        return result

    # Oblicz optymalne parametry używając model_parametr.py
    try:
        import sys

        sys.path.insert(0, BASE_DIR)
        from backend_app.scripts.model_parametr import calculate_params

        params = calculate_params(model_path)
    except Exception as e:
        # Fallback do domyślnych parametrów
        params = "-ngl -1 -c 8192"

    # Parametry modelu
    model_alias = (
        getattr(settings, "llm_model_name", None) or "klimtech-bielik"
        if settings
        else "klimtech-bielik"
    )

    # Parsuj params string na listę argumentów
    param_list = params.split() if params else ["-ngl", "-1", "-c", "8192"]

    llama_cmd = [
        llama_binary,
        "-m",
        model_path,
        "--host",
        "0.0.0.0",
        "--port",
        LLAMA_PORT,
        "--alias",
        model_alias,
    ] + param_list

    # Dla VLM dodaj mmproj
    if model_type == "vlm":
        model_dir = os.path.dirname(model_path)
        mmproj_files = glob.glob(os.path.join(model_dir, "*mmproj*"))
        if mmproj_files:
            llama_cmd.extend(["--mmproj", mmproj_files[0]])
            result["mmproj"] = os.path.basename(mmproj_files[0])

    # Zapisz komendę do pliku
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LLM_COMMAND_FILE, "w") as f:
            json.dump(
                {
                    "command": llama_cmd,
                    "cwd": LLAMA_DIR,
                    "env_vars": amd_env,
                    "model_type": model_type,
                    "model_path": model_path,
                },
                f,
                indent=2,
            )
    except Exception as e:
        result["message"] = f"Błąd zapisu komendy: {e}"
        return result

    # Uruchom proces
    try:
        log_stdout = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
        log_stderr = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")

        process_env = os.environ.copy()
        process_env.update(amd_env)

        proc = subprocess.Popen(
            llama_cmd,
            cwd=LLAMA_DIR,
            stdout=log_stdout,
            stderr=log_stderr,
            start_new_session=True,
            env=process_env,
        )

        # Czekaj na inicjalizację
        time.sleep(15)

        if proc.poll() is not None:
            result["message"] = f"Serwer padł przy starcie (kod: {proc.returncode})"
            return result

        result["success"] = True
        result["message"] = f"Serwer {model_type.upper()} uruchomiony"
        result["pid"] = proc.pid

        # Zapisz PID
        with open(os.path.join(LOG_DIR, "llm_server.pid"), "w") as f:
            f.write(str(proc.pid))

    except Exception as e:
        result["message"] = f"Błąd startu serwera: {e}"

    return result


# ---------------------------------------------------------------------------
# PRZEŁĄCZANIE MODELÓW
# ---------------------------------------------------------------------------


def switch_model(model_type: str) -> Dict[str, Any]:
    """
    Przełącza na wybrany typ modelu.

    Args:
        model_type: "llm" lub "vlm"

    Returns:
        Dict z wynikiem operacji
    """
    result = {
        "success": False,
        "message": "",
        "previous_type": None,
        "new_type": model_type,
        "model": None,
    }

    # Pobierz konfigurację
    config = get_models_config()
    if not config:
        result["message"] = "Brak konfiguracji modeli. Uruchom start_klimtech_v3.py"
        return result

    result["previous_type"] = config.get("current_model_type", "unknown")

    # Pobierz ścieżkę do modelu
    model_path = config.get(f"{model_type}_model")
    if not model_path:
        result["message"] = f"Brak skonfigurowanego modelu {model_type.upper()}"
        return result

    result["model"] = os.path.basename(model_path)

    # Sprawdź czy już działa ten typ
    if result["previous_type"] == model_type:
        result["success"] = True
        result["message"] = f"Model {model_type.upper()} już działa"
        return result

    # Zatrzymaj obecny serwer
    stop_result = stop_llm_server()
    if not stop_result["success"]:
        result["message"] = f"Błąd zatrzymywania: {stop_result['message']}"
        return result

    # Czekaj na zwolnienie VRAM
    time.sleep(5)

    # Uruchom nowy model
    start_result = start_llm_server(model_path, model_type)
    if not start_result["success"]:
        result["message"] = f"Błąd startu: {start_result['message']}"
        return result

    # Aktualizuj konfigurację
    config["current_model_type"] = model_type
    save_models_config(config)

    result["success"] = True
    result["message"] = f"Przełączono na {model_type.upper()}: {result['model']}"
    result["pid"] = start_result.get("pid")

    return result


def switch_to_llm() -> Dict[str, Any]:
    """Przełącza na model LLM (do czatu)."""
    return switch_model("llm")


def switch_to_vlm() -> Dict[str, Any]:
    """Przełącza na model VLM (do obrazków)."""
    return switch_model("vlm")


# ---------------------------------------------------------------------------
# LISTA MODELI
# ---------------------------------------------------------------------------


def get_available_models() -> Dict[str, list]:
    """Pobiera listę dostępnych modeli z katalogów."""
    models_dir = os.environ.get(
        "LLAMA_MODELS_DIR", os.path.join(BASE_DIR, "modele_LLM")
    )

    models = {"llm": [], "vlm": [], "audio": [], "embedding": []}

    if not os.path.exists(models_dir):
        return models

    for category, folders in MODEL_CATEGORIES.items():
        for folder in folders:
            folder_path = os.path.join(models_dir, folder)
            if os.path.exists(folder_path):
                gguf_files = glob.glob(os.path.join(folder_path, "*.gguf"))
                for f in sorted(gguf_files):
                    models[category].append(
                        {
                            "path": f,
                            "name": os.path.basename(f),
                            "size_gb": round(os.path.getsize(f) / (1024**3), 2),
                            "folder": folder,
                        }
                    )

    # ── ColPali — model HuggingFace (nie GGUF, dodawany na stałe) ──
    models["embedding"].append(
        {
            "path": "vidore/colpali-v1.3-hf",
            "name": "ColPali v1.3 — PDF wizualny (obrazy stron)",
            "size_gb": 5.0,
            "folder": "huggingface",
            "type": "colpali",
        }
    )

    return models


# ─── PROGRESS LOG ────────────────────────────────────────────────────────────
PROGRESS_LOG = os.path.join(LOG_DIR, "llm_progress.log")


def _log(msg: str) -> None:
    """Zapisuje linię do progress logu (z timestampem)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(PROGRESS_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def clear_progress_log() -> None:
    """Czyści log postępu."""
    try:
        if os.path.exists(PROGRESS_LOG):
            os.remove(PROGRESS_LOG)
    except Exception:
        pass


def get_progress_lines(since: int = 0) -> dict:
    """Zwraca linie logu od indeksu `since`."""
    if not os.path.exists(PROGRESS_LOG):
        return {"lines": [], "total": 0}
    try:
        with open(PROGRESS_LOG, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        new_lines = [l.rstrip() for l in all_lines[since:]]
        return {"lines": new_lines, "total": len(all_lines)}
    except Exception:
        return {"lines": [], "total": 0}


def start_model_with_progress(
    model_path: str, model_type: str = "llm", llama_port: str = "8082"
) -> dict:
    """
    Uruchamia llama-server w tle, pisząc postęp do PROGRESS_LOG.
    Zwraca natychmiast: {"ok": True, "pid": None} — PID jest logowany.
    """
    import threading

    def _run():
        clear_progress_log()

        _log("=" * 60)
        _log("KlimtechRAG v7.0 — Dual Model Selection")
        _log("=" * 60)

        model_name = os.path.basename(model_path)
        size_gb = 0
        try:
            size_gb = os.path.getsize(model_path) / (1024**3)
        except Exception:
            pass

        label = "VLM (Vision)" if model_type == "vlm" else "LLM (Czat)"

        _log(f"📚 ZNALEZIONE MODELE (wg katalogów)")
        models = get_available_models()
        _log(f"   LLM  (model_thinking/): {len(models['llm'])} modeli")
        _log(f"   VLM  (model_video/):    {len(models['vlm'])} modeli")
        _log(f"   Emb  (model_embedding/): {len(models['embedding'])} modeli")

        _log(f"")
        if model_type == "llm":
            _log(f"📦 LISTA 1: MODELE LLM DO CZATU (model_thinking/)")
            for m in models["llm"]:
                marker = "➤" if m["path"] == model_path else " "
                _log(f"   {marker} {m['name']}  ({m['size_gb']:.1f} GB)")
        else:
            _log(f"📷 LISTA 2: MODELE VLM - VISION (model_video/)")
            for m in models["vlm"]:
                marker = "➤" if m["path"] == model_path else " "
                _log(f"   {marker} {m['name']}  ({m['size_gb']:.1f} GB)")

        _log(f"")
        _log(f"🚀 URUCHAMIANIE {label.upper()} SERVER")
        _log(f"   Model: {model_name}  ({size_gb:.1f} GB)")
        _log(f"   Port:  {llama_port}")

        # Sprawdź VRAM
        _log(f"")
        _log("ANALIZA ZASOBÓW VRAM")
        try:
            r = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0:
                for line in r.stdout.splitlines():
                    if any(k in line for k in ["VRAM", "Total", "Used", "Free"]):
                        _log(f"   {line.strip()}")
            else:
                _log("   (brak rocm-smi lub GPU niedostępne)")
        except Exception:
            _log("   (nie można pobrać info VRAM)")

        # Parametry
        _log(f"")
        _log("🔍 Test kontekstu — obliczanie parametrów...")
        try:
            sys.path.insert(0, BASE_DIR)
            from backend_app.scripts.model_parametr import calculate_params

            params = calculate_params(model_path)
        except Exception:
            params = "-ngl 99 -c 8192"
        _log(f"📋 WYBRANE PARAMETRY: {params}")

        # Stop istniejącego serwera
        stop_llm_server()

        # Znajdź binarkę
        llama_bin = os.path.join(BASE_DIR, "llama.cpp", "build", "bin", "llama-server")
        if not os.path.exists(llama_bin):
            llama_bin = os.path.join(BASE_DIR, "llama.cpp", "llama-server")
        if not os.path.exists(llama_bin):
            _log(f"❌ Nie znaleziono llama-server!")
            return

        model_alias = (
            getattr(settings, "llm_model_name", None) or "klimtech-bielik"
            if settings
            else "klimtech-bielik"
        )
        cmd = [
            llama_bin,
            "-m",
            model_path,
            "--host",
            "0.0.0.0",
            "--port",
            llama_port,
            "--alias",
            model_alias,
        ] + params.split()

        # VLM: mmproj
        if model_type == "vlm":
            model_dir = os.path.dirname(model_path)
            mmp = glob.glob(os.path.join(model_dir, "*mmproj*"))
            if mmp:
                cmd += ["--mmproj", mmp[0]]
                _log(f"   📷 mmproj: {os.path.basename(mmp[0])}")

        amd_env = os.environ.copy()
        amd_env.update(
            {
                "HIP_VISIBLE_DEVICES": "0",
                "GPU_MAX_ALLOC_PERCENT": "100",
                "HSA_ENABLE_SDMA": "0",
                "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
            }
        )

        log_out = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
        log_err = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=os.path.join(BASE_DIR, "llama.cpp"),
                stdout=log_out,
                stderr=log_err,
                start_new_session=True,
                env=amd_env,
            )

            # Zapisz konfigurację
            config = get_models_config() or {}
            if model_type == "llm":
                config["llm_model"] = model_path
            else:
                config["vlm_model"] = model_path
            config["current_model_type"] = model_type
            save_models_config(config)

            _log(f"⏳ Czekam 15s na załadowanie modelu...")
            time.sleep(15)

            if proc.poll() is not None:
                _log(f"❌ Serwer padł (kod: {proc.returncode})")
                _log(f"   Sprawdź: {LOG_DIR}/llm_server_stderr.log")
            else:
                _log(f"✅ {label} Server działa (PID: {proc.pid})")

        except Exception as e:
            _log(f"❌ Błąd uruchamiania: {e}")

        _log("")
        _log("=" * 60)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return {"ok": True}
