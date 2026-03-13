#!/usr/bin/env python3
"""
KlimtechRAG v7.0 — Unified Start Script
=========================================
Funkcje:
- Dwie listy modeli: LLM (czat) + VLM (vision/obrazy)
- Przełączanie między modelami podczas pracy
- Automatyczne zarządzanie VRAM (zabijanie/startowanie procesów)
- Rozpoznawanie modeli na podstawie katalogów

Struktura katalogów modeli:
  modele_LLM/
  ├── model_thinking/    ← LLM (czat)
  ├── model_video/       ← VLM (vision)
  ├── model_audio/       ← Audio
  └── model_embedding/   ← Embedding

Uruchamia: LLM/VLM Server, Podman kontenery, FastAPI backend, Watchdog, Open WebUI
"""
import subprocess
import os
import time
import signal
import sys
import glob
import json
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from backend_app.scripts.model_parametr import calculate_params
except ImportError:
    # Fallback jeśli moduł nie jest dostępny
    def calculate_params(model_path):
        return "-ngl 99 -c 8192"

# ---------------------------------------------------------------------------
# KONFIGURACJA — dostosuj do swojego środowiska
# ---------------------------------------------------------------------------

BASE_DIR = "/media/lobo/BACKUP/KlimtechRAG"
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
ENV_FILE = os.path.join(BASE_DIR, ".env")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LLM_COMMAND_FILE = os.path.join(LOG_DIR, "llm_command.txt")
MODELS_CONFIG_FILE = os.path.join(LOG_DIR, "models_config.json")

PYTHON_VENV = "/home/lobo/klimtech_venv/bin/python3"

# Katalogi modeli (relatywne do models_dir)
MODEL_CATEGORIES = {
    "llm": ["model_thinking", "model_reasoning"],      # LLM do czatu
    "vlm": ["model_video", "model_vision"],            # Vision-Language
    "audio": ["model_audio"],                           # Audio/TTS/STT
    "embedding": ["model_embedding"],                   # Embedding
}

# Kontenery Podman (w kolejności startu)
CONTAINERS = ["qdrant", "nextcloud", "postgres_nextcloud", "n8n", "open-webui"]

PROCESSES = []
CURRENT_LLM_PROCESS = None
CURRENT_MODEL_TYPE = None  # "llm" lub "vlm"
SELECTED_LLM_MODEL = None
SELECTED_VLM_MODEL = None

# ---------------------------------------------------------------------------
# Pobierz IP z interfejsu sieciowego
# ---------------------------------------------------------------------------

def get_interface_ip(interface: str = "enp9s0") -> str:
    """Zwraca adres IPv4 podanego interfejsu. Fallback: localhost."""
    try:
        result = subprocess.check_output(
            ["ip", "-4", "addr", "show", interface],
            text=True, stderr=subprocess.DEVNULL
        )
        for line in result.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    print(f"⚠️  Nie można pobrać IP z {interface} — używam localhost")
    return "localhost"

LOCAL_IP = get_interface_ip("enp9s0")

# ---------------------------------------------------------------------------
# Konfiguracja z .env
# ---------------------------------------------------------------------------

def load_env_file(env_path: str) -> dict:
    defaults = {
        "LLAMA_MODELS_DIR": os.path.join(BASE_DIR, "modele_LLM"),
        "LLAMA_API_PORT": "8082",
        "BACKEND_PORT": "8000",
        "OWUI_PORT": "3000",
        "OWUI_DATA_DIR": os.path.join(BASE_DIR, "data", "open-webui"),
    }
    if not os.path.exists(env_path):
        print(f"⚠️  Brak pliku .env ({env_path}). Używam domyślnych.")
        return defaults
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                defaults[key.strip()] = value.strip().strip('"').strip("'")
    return defaults


def get_models_by_category(models_dir: str) -> dict:
    """
    Pobiera modele z katalogów tematycznych.
    
    Struktura:
      modele_LLM/
      ├── model_thinking/    → LLM
      ├── model_video/       → VLM
      ├── model_audio/       → Audio
      └── model_embedding/   → Embedding
    """
    if not os.path.exists(models_dir):
        print(f"❌ Katalog modeli nie istnieje: {models_dir}")
        sys.exit(1)
    
    models = {
        "llm": [],
        "vlm": [],
        "audio": [],
        "embedding": [],
        "other": []
    }
    
    # Przeskanuj wszystkie podkatalogi
    for category, folder_names in MODEL_CATEGORIES.items():
        for folder in folder_names:
            folder_path = os.path.join(models_dir, folder)
            if os.path.exists(folder_path):
                gguf_files = glob.glob(os.path.join(folder_path, "*.gguf"))
                gguf_files.sort()
                models[category].extend(gguf_files)
    
    # Sprawdź czy są modele bezpośrednio w models_dir (bez podkatalogów)
    direct_models = glob.glob(os.path.join(models_dir, "*.gguf"))
    for model in direct_models:
        models["other"].append(model)
    
    # Sortuj wszystkie listy
    for key in models:
        models[key].sort()
    
    return models


def print_model_list(models: list, title: str, start_idx: int = 1) -> None:
    """Wyświetla listę modeli z numerami."""
    print(f"\n{'='*65}")
    print(f"   {title}")
    print("="*65)
    
    if not models:
        print("   (brak modeli)")
        print("="*65)
        return
    
    for i, model_path in enumerate(models, start_idx):
        size_gb = os.path.getsize(model_path) / (1024 ** 3)
        name = os.path.basename(model_path)
        # Pokaż też nazwę katalogu
        parent_dir = os.path.basename(os.path.dirname(model_path))
        print(f"[{i:2d}] {name}  ({size_gb:.1f} GB)  [{parent_dir}/]")
    
    print("="*65)


def save_models_config(llm_model: str, vlm_model: str, current_type: str):
    """Zapisuje konfigurację wybranych modeli do pliku JSON."""
    config = {
        "llm_model": llm_model,
        "vlm_model": vlm_model,
        "current_model_type": current_type,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(MODELS_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"   💾 Konfiguracja zapisana: {MODELS_CONFIG_FILE}")


def select_models(models: dict) -> tuple:
    """
    Wyświetla dwie listy modeli i pozwala wybrać:
    - Model LLM do czatu (z model_thinking/)
    - Model VLM do obrazków (z model_video/)
    
    Zwraca: (selected_llm_path, selected_vlm_path)
    """
    llm_models = models["llm"]
    vlm_models = models["vlm"]
    
    # =========================================
    # LISTA 1: Modele LLM do czatu
    # =========================================
    if not llm_models:
        print("❌ Brak modeli LLM do czatu w katalogu model_thinking/!")
        sys.exit(1)
    
    print_model_list(llm_models, "📦 LISTA 1: MODELE LLM DO CZATU (model_thinking/)", start_idx=1)
    
    # Wybór modelu LLM
    while True:
        try:
            choice = input("\n👉 Wybierz numer modelu LLM do czatu: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(llm_models):
                selected_llm = llm_models[idx]
                print(f"   ✅ Wybrano LLM: {os.path.basename(selected_llm)}")
                break
            print("   ❌ Nieprawidłowy numer.")
        except ValueError:
            print("   ❌ To nie jest liczba.")
        except KeyboardInterrupt:
            print("\n   Anulowano.")
            sys.exit(0)
    
    # =========================================
    # LISTA 2: Modele VLM (Vision-Language)
    # =========================================
    selected_vlm = None
    if vlm_models:
        print_model_list(vlm_models, "📷 LISTA 2: MODELE VLM - VISION (model_video/)", start_idx=1)
        print("\n   [0] Pomiń - nie używaj modelu VLM")
        
        while True:
            try:
                choice = input("\n👉 Wybierz numer modelu VLM (0 = pomiń): ").strip()
                idx = int(choice) - 1
                if idx == -1:
                    print("   ⏭️  Pominięto model VLM")
                    break
                if 0 <= idx < len(vlm_models):
                    selected_vlm = vlm_models[idx]
                    print(f"   ✅ Wybrano VLM: {os.path.basename(selected_vlm)}")
                    break
                print("   ❌ Nieprawidłowy numer.")
            except ValueError:
                print("   ❌ To nie jest liczba.")
            except KeyboardInterrupt:
                print("\n   Anulowano.")
                sys.exit(0)
    else:
        print("\n   ⚠️  Brak modeli VLM w katalogu model_video/")
    
    return selected_llm, selected_vlm


# ---------------------------------------------------------------------------
# Uruchamianie procesów
# ---------------------------------------------------------------------------

def stop_llm_server():
    """Zatrzymuje serwer LLM/VLM."""
    global CURRENT_LLM_PROCESS
    print("\n   🛑 Zatrzymuję serwer LLM/VLM...")
    
    # Zabij przez pkill
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
    subprocess.run(["pkill", "-f", "llama-cli"], capture_output=True)
    
    # Zabij port
    try:
        subprocess.run(["fuser", "-k", "8082/tcp"], capture_output=True, timeout=5)
    except Exception:
        pass
    
    # Zabij proces jeśli mamy referencję
    if CURRENT_LLM_PROCESS:
        try:
            CURRENT_LLM_PROCESS.terminate()
            CURRENT_LLM_PROCESS.wait(timeout=5)
        except Exception:
            try:
                CURRENT_LLM_PROCESS.kill()
            except Exception:
                pass
        CURRENT_LLM_PROCESS = None
    
    time.sleep(2)  # Czekamy na zwolnienie VRAM
    print("   ✅ VRAM zwolniony")


def ensure_mmproj(model_path: str) -> Optional[str]:
    """
    Sprawdza czy VLM ma mmproj w katalogu.
    Jeśli nie ma - próbuje pobrać automatycznie.
    
    Returns:
        Ścieżka do mmproj lub None
    """
    model_dir = os.path.dirname(model_path)
    model_name = os.path.basename(model_path).lower()
    
    # Szukaj mmproj w katalogu
    mmproj_files = glob.glob(os.path.join(model_dir, "*mmproj*"))
    if mmproj_files:
        return mmproj_files[0]
    
    # Jeśli nie ma - spróbuj pobrać
    print("\n   ⚠️  Nie znaleziono mmproj - próbuję pobrać...")
    
    # Mapa modeli do mmproj
    mmproj_urls = {
        "qwen2-vl": "https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2-VL-7B-Instruct-f16.gguf",
        "qwen2.5-vl": "https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct-GGUF/resolve/main/mmproj-Qwen2.5-VL-7B-Instruct-f16.gguf",
    }
    
    # Znajdź odpowiedni URL
    mmproj_url = None
    for key, url in mmproj_urls.items():
        if key in model_name:
            mmproj_url = url
            break
    
    if not mmproj_url:
        print("   ❌ Nie znaleziono mmproj dla tego modelu")
        print("   Pobierz ręcznie z HuggingFace i umieść w katalogu modelu")
        return None
    
    # Pobierz mmproj
    mmproj_path = os.path.join(model_dir, "mmproj.gguf")
    print(f"   📥 Pobieranie: {mmproj_url}")
    
    try:
        import urllib.request
        urllib.request.urlretrieve(mmproj_url, mmproj_path)
        print(f"   ✅ Pobrano: {mmproj_path}")
        return mmproj_path
    except Exception as e:
        print(f"   ❌ Błąd pobierania: {e}")
        return None


def start_llm_server(model_path: str, model_type: str = "llm", port: str = "8082") -> bool:
    """
    Uruchamia serwer LLM lub VLM.
    
    Args:
        model_path: Ścieżka do modelu GGUF
        model_type: "llm" lub "vlm"
        port: Port serwera
    
    Returns:
        True jeśli sukces
    """
    global CURRENT_LLM_PROCESS, CURRENT_MODEL_TYPE
    
    model_label = "VLM (Vision)" if model_type == "vlm" else "LLM (Czat)"
    print(f"\n{'='*65}")
    print(f"   🚀 URUCHAMIANIE {model_label.upper()} SERVER")
    print("="*65)
    print(f"   Model: {os.path.basename(model_path)}")
    print(f"   Ścieżka: {model_path}")
    
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
        print(f"   ❌ Nie znaleziono llama-server!")
        return False
    
    # Parametry modelu
    try:
        llama_args = calculate_params(model_path).split()
    except Exception:
        llama_args = ["-ngl", "99", "-c", "8192"]
    
    llama_cmd = [
        llama_binary, "-m", model_path,
        "--host", "0.0.0.0",
        "--port", port,
    ] + llama_args
    
    # Dla VLM dodaj specjalne flagi
    if model_type == "vlm":
        # Sprawdź/pobierz mmproj
        mmproj_path = ensure_mmproj(model_path)
        if mmproj_path:
            llama_cmd.extend(["--mmproj", mmproj_path])
            print(f"   📷 mmproj: {os.path.basename(mmproj_path)}")
        else:
            print("   ⚠️  Nie znaleziono mmproj - VLM może nie działać poprawnie")
            print("   Pobierz mmproj z HuggingFace i umieść w katalogu modelu")
    
    # Zapisz komendę do pliku (dla debugowania)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LLM_COMMAND_FILE, "w") as f:
        json.dump({
            "command": llama_cmd, 
            "cwd": LLAMA_DIR, 
            "env_vars": amd_env,
            "model_type": model_type,
            "model_path": model_path
        }, f, indent=2)
    
    # Uruchom proces
    process_env = os.environ.copy()
    process_env.update(amd_env)
    
    try:
        log_stdout = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
        log_stderr = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")
        
        proc = subprocess.Popen(
            llama_cmd,
            cwd=LLAMA_DIR,
            stdout=log_stdout,
            stderr=log_stderr,
            start_new_session=True,
            env=process_env,
        )
        CURRENT_LLM_PROCESS = proc
        CURRENT_MODEL_TYPE = model_type
        PROCESSES.append(proc)
        
        print(f"   ⏳ Czekam 15s na załadowanie modelu...")
        time.sleep(15)
        
        if proc.poll() is not None:
            print(f"   ❌ Serwer padł przy starcie! Kod: {proc.returncode}")
            print(f"   Sprawdź: {LOG_DIR}/llm_server_stderr.log")
            return False
        
        print(f"   ✅ {model_label} Server działa (PID: {proc.pid})")
        return True
        
    except Exception as e:
        print(f"   ❌ Błąd startu serwera: {e}")
        return False


def switch_model(new_model_path: str, new_model_type: str) -> bool:
    """
    Przełącza z jednego modelu na drugi.
    Zabija obecny model, czeka na zwolnienie VRAM, startuje nowy.
    """
    global CURRENT_MODEL_TYPE
    
    print(f"\n{'='*65}")
    print(f"   🔄 PRZEŁĄCZANIE MODELU")
    print("="*65)
    print(f"   Z: {CURRENT_MODEL_TYPE.upper() if CURRENT_MODEL_TYPE else 'brak'}")
    print(f"   Na: {new_model_type.upper()} ({os.path.basename(new_model_path)})")
    print("="*65)
    
    # 1. Zatrzymaj obecny model
    stop_llm_server()
    
    # 2. Czekaj na zwolnienie VRAM
    print("   ⏳ Czekam na zwolnienie VRAM (5s)...")
    time.sleep(5)
    
    # 3. Uruchom nowy model
    success = start_llm_server(new_model_path, new_model_type)
    
    if success:
        # Aktualizuj konfigurację
        CURRENT_MODEL_TYPE = new_model_type
        save_models_config(SELECTED_LLM_MODEL, SELECTED_VLM_MODEL, new_model_type)
        print(f"\n   ✅ Przełączono na: {os.path.basename(new_model_path)}")
    else:
        print(f"\n   ❌ Błąd przełączania!")
    
    return success


def start_process(name: str, command: list, cwd: str,
                  env_vars: dict = None, wait_seconds: int = 5) -> bool:
    print(f"\n🚀 Uruchamianie: {name}...")
    print(f"   Komenda: {' '.join(str(c) for c in command)}")
    if env_vars:
        print(f"   Env: {env_vars}")

    process_env = os.environ.copy()
    if env_vars:
        process_env.update(env_vars)

    try:
        log_stdout = open(os.path.join(LOG_DIR, f"{name.lower().replace(' ', '_')}_stdout.log"), "a")
        log_stderr = open(os.path.join(LOG_DIR, f"{name.lower().replace(' ', '_')}_stderr.log"), "a")

        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=log_stdout,
            stderr=log_stderr,
            start_new_session=True,
            env=process_env,
        )
        PROCESSES.append(proc)

        if wait_seconds > 0:
            print(f"   ⏳ Czekam {wait_seconds}s na inicjalizację...")
            time.sleep(wait_seconds)

        if proc.poll() is not None:
            print(f"❌ {name} padł przy starcie! Sprawdź logi: logs/")
            return False

        print(f"✅ {name} działa (PID: {proc.pid})")
        return True

    except Exception as e:
        print(f"❌ Błąd startu {name}: {e}")
        return False


def restart_podman_containers(containers: list) -> None:
    print("\n🐳 Uruchamianie kontenerów Podman...")
    for container in containers:
        try:
            result = subprocess.run(
                ["podman", "start", container],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                print(f"   ✅ {container}")
            else:
                print(f"   ⚪ {container}: {result.stderr.strip()[:80]}")
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  {container}: timeout")
        except Exception as e:
            print(f"   ⚠️  {container}: {e}")
        time.sleep(0.5)


def start_owui(config: dict) -> None:
    """Uruchamia Open WebUI jako kontener Podman."""
    owui_port = config.get("OWUI_PORT", "3000")
    owui_data = config.get("OWUI_DATA_DIR", os.path.join(BASE_DIR, "data", "open-webui"))
    backend_port = config.get("BACKEND_PORT", "8000")
    api_key = config.get("KLIMTECH_API_KEY", "sk-dummy")
    embedding_model = config.get("KLIMTECH_EMBEDDING_MODEL", "intfloat/multilingual-e5-large")

    os.makedirs(owui_data, exist_ok=True)

    # Sprawdź czy kontener już istnieje
    result = subprocess.run(
        ["podman", "inspect", "open-webui"],
        capture_output=True
    )

    if result.returncode == 0:
        subprocess.run(["podman", "start", "open-webui"], capture_output=True)
        print(f"✅ Open WebUI uruchomiony → http://{LOCAL_IP}:{owui_port}")
        return

    print(f"   Tworzę nowy kontener Open WebUI...")
    cmd = [
        "podman", "run", "-d",
        "--name", "open-webui",
        "--network", "host",
        "-v", f"{owui_data}:/app/backend/data",
        "-e", f"OPENAI_API_BASE_URLS=http://localhost:{backend_port}",
        "-e", f"OPENAI_API_KEYS={api_key}",
        "-e", "ENABLE_OLLAMA_API=False",
        "-e", "VECTOR_DB=qdrant",
        "-e", "QDRANT_URI=http://localhost:6333",
        "-e", "RAG_EMBEDDING_ENGINE=openai",
        "-e", f"RAG_EMBEDDING_MODEL={embedding_model}",
        "-e", f"RAG_OPENAI_API_BASE_URL=http://localhost:{backend_port}/v1",
        "-e", f"RAG_OPENAI_API_KEY={api_key}",
        "-e", "CHUNK_SIZE=500",
        "-e", "CHUNK_OVERLAP=50",
        "-e", f"PORT={owui_port}",
        "-e", "WEBUI_NAME=KlimtechRAG",
        "ghcr.io/open-webui/open-webui:main",
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"✅ Open WebUI uruchomiony → http://{LOCAL_IP}:{owui_port}")
    else:
        print(f"❌ Open WebUI — błąd startu: {proc.stderr[:200]}")


# ---------------------------------------------------------------------------
# Menu interaktywne
# ---------------------------------------------------------------------------

def show_menu() -> str:
    """Wyświetla menu operacji i zwraca wybór użytkownika."""
    current = CURRENT_MODEL_TYPE.upper() if CURRENT_MODEL_TYPE else "BRAK"
    
    print("\n" + "="*65)
    print("   📋 MENU OPERACJI")
    print("="*65)
    print(f"   Aktualny model: {current}")
    print("-"*65)
    print(f"   [1] 💬 Przełącz na LLM (czat)")
    print(f"   [2] 📷 Przełącz na VLM (obrazki)")
    print(f"   [3] 🔄 Przełącz model LLM ↔ VLM")
    print(f"   [4] 📊 Status systemu")
    print(f"   [5] 🛑 Zatrzymaj wszystko")
    print(f"   [q] ❌ Wyjście")
    print("="*65)
    
    choice = input("\n👉 Wybierz opcję: ").strip().lower()
    return choice


def show_status():
    """Wyświetla status systemu."""
    print("\n" + "="*65)
    print("   📊 STATUS SYSTEMU")
    print("="*65)
    
    # Sprawdź proces LLM
    result = subprocess.run(["pgrep", "-f", "llama-server"], capture_output=True)
    if result.returncode == 0:
        print(f"   🤖 LLM/VLM: Działa (typ: {CURRENT_MODEL_TYPE or 'nieznany'})")
    else:
        print("   🤖 LLM/VLM: Zatrzymany")
    
    # Sprawdź backend
    result = subprocess.run(["pgrep", "-f", "backend_app"], capture_output=True)
    if result.returncode == 0:
        print("   🔧 Backend: Działa")
    else:
        print("   🔧 Backend: Zatrzymany")
    
    # Sprawdź Qdrant
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:6333/collections", timeout=2)
        print("   📦 Qdrant: Działa")
    except Exception:
        print("   📦 Qdrant: Niedostępny")
    
    # Sprawdź Open WebUI
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:3000", timeout=2)
        print("   💬 Open WebUI: Działa")
    except Exception:
        print("   💬 Open WebUI: Niedostępny")
    
    # VRAM
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("\n   📊 VRAM:")
            for line in result.stdout.splitlines():
                if "VRAM" in line or "Total" in line or "Used" in line:
                    print(f"      {line.strip()}")
    except Exception:
        pass
    
    # Wybrane modele
    print(f"\n   📝 Wybrany LLM: {os.path.basename(SELECTED_LLM_MODEL) if SELECTED_LLM_MODEL else 'brak'}")
    print(f"   📷 Wybrany VLM: {os.path.basename(SELECTED_VLM_MODEL) if SELECTED_VLM_MODEL else 'brak'}")
    
    print("="*65)


# ---------------------------------------------------------------------------
# Signal handler
# ---------------------------------------------------------------------------

def signal_handler(sig, frame):
    print("\n🛑 Zatrzymywanie procesów...")
    for proc in PROCESSES:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass
    if os.path.exists(LLM_COMMAND_FILE):
        os.remove(LLM_COMMAND_FILE)
    print("👋 Do widzenia!")
    sys.exit(0)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    global SELECTED_LLM_MODEL, SELECTED_VLM_MODEL, CURRENT_MODEL_TYPE
    
    signal.signal(signal.SIGINT, signal_handler)

    # Utwórz katalogi
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "uploads"), exist_ok=True)

    config = load_env_file(ENV_FILE)
    models_dir = config.get("LLAMA_MODELS_DIR")
    backend_port = config.get("BACKEND_PORT", "8000")
    llama_port = config.get("LLAMA_API_PORT", "8082")

    print("\n" + "=" * 65)
    print("   KlimtechRAG v7.0 — Dual Model Selection")
    print("=" * 65)
    print(f"   Baza: {BASE_DIR}")
    print(f"   Modele: {models_dir}")

    # 1. Pobierz modele z kategorii
    models = get_models_by_category(models_dir)
    
    print("\n" + "=" * 65)
    print("   📚 ZNALEZIONE MODELE (wg katalogów)")
    print("=" * 65)
    print(f"   LLM (model_thinking/):  {len(models['llm'])} modeli")
    print(f"   VLM (model_video/):     {len(models['vlm'])} modeli")
    print(f"   Audio (model_audio/):   {len(models['audio'])} modeli")
    print(f"   Embed (model_embedding/): {len(models['embedding'])} modeli")
    
    # 2. Wybór modeli
    SELECTED_LLM_MODEL, SELECTED_VLM_MODEL = select_models(models)
    
    # 3. Zapytaj jaki model uruchomić na początek
    print("\n" + "=" * 65)
    print("   🚀 TRYB STARTOWY")
    print("=" * 65)
    print("   [1] 💬 Czat — uruchom model LLM")
    if SELECTED_VLM_MODEL:
        print("   [2] 📷 VLM Ingest — uruchom model VLM (PDF z obrazkami)")
    print("=" * 65)
    
    start_mode = input("\n👉 Wybierz tryb startowy: ").strip()
    
    if start_mode == "2" and SELECTED_VLM_MODEL:
        initial_model = SELECTED_VLM_MODEL
        initial_type = "vlm"
    else:
        initial_model = SELECTED_LLM_MODEL
        initial_type = "llm"
    
    # Zapisz konfigurację modeli
    save_models_config(SELECTED_LLM_MODEL, SELECTED_VLM_MODEL, initial_type)
    
    # 4. Uruchom LLM/VLM Server
    if not start_llm_server(initial_model, initial_type):
        print("\n⛔ Start serwera nieudany. Sprawdź logi/llm_server_stderr.log")
        sys.exit(1)

    # 5. Kontenery Podman
    restart_podman_containers(["qdrant", "nextcloud", "postgres_nextcloud", "n8n"])
    time.sleep(3)

    # 6. Backend FastAPI
    backend_cmd = [PYTHON_VENV, "-m", "backend_app.main"]
    backend_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
        "KLIMTECH_EMBEDDING_DEVICE": "cuda:0",
        "KLIMTECH_BASE_PATH": BASE_DIR,
    }
    if not start_process("Backend FastAPI", backend_cmd, BASE_DIR,
                         env_vars=backend_env, wait_seconds=5):
        print("\n⛔ Start Backend nieudany. Sprawdź logi/backend_fastapi_stderr.log")
        sys.exit(1)

    # 7. Watchdog
    watchdog_cmd = [PYTHON_VENV, "backend_app/scripts/watch_nextcloud.py"]
    watchdog_log_out = open(os.path.join(LOG_DIR, "watchdog_stdout.log"), "a")
    watchdog_log_err = open(os.path.join(LOG_DIR, "watchdog_stderr.log"), "a")
    watchdog_proc = subprocess.Popen(
        watchdog_cmd,
        cwd=BASE_DIR,
        stdout=watchdog_log_out,
        stderr=watchdog_log_err,
        start_new_session=True,
    )
    PROCESSES.append(watchdog_proc)
    print(f"\n✅ Watchdog działa (PID: {watchdog_proc.pid})")

    # 8. Open WebUI
    time.sleep(2)
    start_owui(config)

    # Podsumowanie
    def get_container_port(name):
        try:
            w = subprocess.run(["podman", "port", name], capture_output=True, text=True, timeout=5)
            for linia in w.stdout.strip().splitlines():
                if "->" in linia:
                    return linia.split(":")[-1].strip()
        except Exception:
            pass
        return "???"

    print("\n" + "=" * 65)
    print("🎉 KlimtechRAG gotowy!")
    print("=" * 65)
    print(f"   💬 Open WebUI:     http://{LOCAL_IP}:{config.get('OWUI_PORT', 3000)}")
    print(f"   🔧 API Backend:    http://{LOCAL_IP}:{backend_port}")
    print(f"   🤖 LLM/VLM:        http://{LOCAL_IP}:{llama_port}")
    print(f"   📦 Qdrant:         http://{LOCAL_IP}:{get_container_port('qdrant')}")
    print("-"*65)
    print(f"   📝 Model LLM: {os.path.basename(SELECTED_LLM_MODEL)}")
    if SELECTED_VLM_MODEL:
        print(f"   📷 Model VLM: {os.path.basename(SELECTED_VLM_MODEL)}")
    print(f"   📊 RAG debug: http://{LOCAL_IP}:{backend_port}/rag/debug")
    print("-"*65)
    print("   CTRL+C aby zatrzymać, lub użyj menu")
    print("=" * 65)

    # Menu główne
    try:
        while True:
            choice = show_menu()
            
            if choice == "1":
                # Przełącz na LLM
                if CURRENT_MODEL_TYPE != "llm" and SELECTED_LLM_MODEL:
                    switch_model(SELECTED_LLM_MODEL, "llm")
                else:
                    print("\n   ✅ Już działasz na modelu LLM")
            
            elif choice == "2" and SELECTED_VLM_MODEL:
                # Przełącz na VLM
                if CURRENT_MODEL_TYPE != "vlm":
                    switch_model(SELECTED_VLM_MODEL, "vlm")
                else:
                    print("\n   ✅ Już działasz na modelu VLM")
            
            elif choice == "3":
                # Przełącz LLM ↔ VLM
                if CURRENT_MODEL_TYPE == "llm" and SELECTED_VLM_MODEL:
                    switch_model(SELECTED_VLM_MODEL, "vlm")
                elif CURRENT_MODEL_TYPE == "vlm" and SELECTED_LLM_MODEL:
                    switch_model(SELECTED_LLM_MODEL, "llm")
                else:
                    print("\n   ⚠️  Nie można przełączyć - brak drugiego modelu")
            
            elif choice == "4":
                show_status()
            
            elif choice == "5":
                signal_handler(None, None)
            
            elif choice == "q":
                signal_handler(None, None)
            
            else:
                print("\n   ⚠️  Nieznana opcja")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
