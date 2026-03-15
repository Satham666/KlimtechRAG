#!/usr/bin/env python3
"""
KlimtechRAG v6.0 — Start Script
Uruchamia: LLM Server, Podman kontenery, FastAPI backend, Watchdog, Open WebUI
Kompatybilny z fish shell (uruchamiaj jako: python start_klimtech.py)
"""
import subprocess
import os
import time
import signal
import sys
import glob
import fcntl
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend_app.scripts.model_parametr import calculate_params

# ---------------------------------------------------------------------------
# KONFIGURACJA — dostosuj do swojego środowiska
# ---------------------------------------------------------------------------

BASE_DIR = "/media/lobo/BACKUP/KlimtechRAG"
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
ENV_FILE = os.path.join(BASE_DIR, ".env")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LLM_COMMAND_FILE = os.path.join(LOG_DIR, "llm_command.txt")

PYTHON_VENV = os.path.join(BASE_DIR, "venv", "bin", "python")

# Kontenery Podman (w kolejności startu)
CONTAINERS = ["qdrant", "nextcloud", "postgres_nextcloud", "n8n", "open-webui"]

PROCESSES = []

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


def get_available_models(models_dir: str) -> list:
    if not os.path.exists(models_dir):
        print(f"❌ Katalog modeli nie istnieje: {models_dir}")
        sys.exit(1)
    models = glob.glob(os.path.join(models_dir, "**", "*.gguf"), recursive=True)
    if not models:
        print(f"❌ Nie znaleziono .gguf w {models_dir}")
        sys.exit(1)
    models.sort()
    return models


def select_user_model(models: list) -> str:
    print("\n" + "=" * 55)
    print("   DOSTĘPNE MODELE (GGUF)")
    print("=" * 55)
    for i, model_path in enumerate(models, 1):
        size_gb = os.path.getsize(model_path) / (1024 ** 3)
        print(f"[{i}] {os.path.basename(model_path)}  ({size_gb:.1f} GB)")
    print("=" * 55)
    while True:
        try:
            choice = input("\nWybierz numer modelu: ").strip()
            index = int(choice) - 1
            if 0 <= index < len(models):
                return models[index]
            print("❌ Nieprawidłowy numer.")
        except ValueError:
            print("❌ To nie jest liczba.")
        except KeyboardInterrupt:
            print("\nAnulowano.")
            sys.exit(0)


# ---------------------------------------------------------------------------
# Uruchamianie procesów
# ---------------------------------------------------------------------------

def start_process(name: str, command: list, cwd: str,
                  env_vars: dict = None, wait_seconds: int = 5) -> bool:
    print(f"\n🚀 Uruchamianie: {name}...")
    print(f"   Komenda: {' '.join(str(c) for c in command)}")
    if env_vars:
        print(f"   Env: {env_vars}")

    # Zapisz komendę LLM do pliku (używane przez ingest_gpu.py)
    if name == "LLM Server":
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LLM_COMMAND_FILE, "w") as f:
            json.dump({"command": command, "cwd": cwd, "env_vars": env_vars or {}}, f, indent=2)
        print(f"   Komenda zapisana: {LLM_COMMAND_FILE}")

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
                # Kontener może nie istnieć — to ok przy pierwszym uruchomieniu
                print(f"   ⚪ {container}: {result.stderr.strip()[:80]}")
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  {container}: timeout")
        except Exception as e:
            print(f"   ⚠️  {container}: {e}")
        time.sleep(0.5)


def start_owui(config: dict) -> None:
    """Uruchamia Open WebUI jako kontener Podman (jeśli nie startuje przez podman start)."""
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
        # Kontener istnieje — po prostu go uruchom
        subprocess.run(["podman", "start", "open-webui"], capture_output=True)
        print(f"✅ Open WebUI uruchomiony (istniejący kontener) → http://localhost:{owui_port}")
        return

    # Tworzenie nowego kontenera (pierwsze uruchomienie)
    print(f"   Tworzę nowy kontener Open WebUI...")
    cmd = [
        "podman", "run", "-d",
        "--name", "open-webui",
        "--network", "host",
        "-v", f"{owui_data}:/app/backend/data",
        # === LLM — KlimtechRAG backend (ma wbudowany RAG) ===
        "-e", f"OPENAI_API_BASE_URLS=http://localhost:{backend_port}",
        "-e", f"OPENAI_API_KEYS={api_key}",
        "-e", "ENABLE_OLLAMA_API=False",
        # === RAG — Qdrant przez KlimtechRAG embeddingi ===
        "-e", "VECTOR_DB=qdrant",
        "-e", "QDRANT_URI=http://localhost:6333",
        "-e", "RAG_EMBEDDING_ENGINE=openai",
        "-e", f"RAG_EMBEDDING_MODEL={embedding_model}",
        "-e", f"RAG_OPENAI_API_BASE_URL=http://localhost:{backend_port}/v1",
        "-e", f"RAG_OPENAI_API_KEY={api_key}",
        "-e", "CHUNK_SIZE=500",
        "-e", "CHUNK_OVERLAP=50",
        # === UI ===
        "-e", f"PORT={owui_port}",
        "-e", "WEBUI_NAME=KlimtechRAG",
        "ghcr.io/open-webui/open-webui:main",
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        print(f"✅ Open WebUI uruchomiony (nowy kontener) → http://localhost:{owui_port}")
    else:
        print(f"❌ Open WebUI — błąd startu: {proc.stderr[:200]}")
        print("   Sprawdź: podman pull ghcr.io/open-webui/open-webui:main")


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


def make_non_blocking(fd):
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    signal.signal(signal.SIGINT, signal_handler)

    # Utwórz katalogi
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "uploads"), exist_ok=True)

    config = load_env_file(ENV_FILE)
    models_dir = config.get("LLAMA_MODELS_DIR")
    backend_port = config.get("BACKEND_PORT", "8000")
    llama_port = config.get("LLAMA_API_PORT", "8082")

    print("\n" + "=" * 55)
    print("   KlimtechRAG v6.0 (OWUI + Nextcloud RAG)")
    print("=" * 55)
    print(f"   Baza: {BASE_DIR}")
    print(f"   Modele: {models_dir}")

    # 1. Wybór modelu LLM
    selected_model_path = select_user_model(get_available_models(models_dir))
    model_name = os.path.basename(selected_model_path)

    # 2. AMD GPU env (dla 1 karty; przyszłe 2 karty: HIP_VISIBLE_DEVICES=0,1)
    amd_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "GPU_MAX_ALLOC_PERCENT": "100",
        "HSA_ENABLE_SDMA": "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",   # dla AMD Instinct MI50/MI60
    }

    # 3. Uruchom LLM Server
    llama_binary = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
    if not os.path.exists(llama_binary):
        llama_binary = os.path.join(LLAMA_DIR, "llama-server")

    llama_args = calculate_params(selected_model_path).split()
    llama_cmd = [
        llama_binary, "-m", selected_model_path,
        "--host", "0.0.0.0",
        "--port", llama_port,
    ] + llama_args

    if not start_process("LLM Server", llama_cmd, LLAMA_DIR, env_vars=amd_env, wait_seconds=10):
        print("\n⛔ Start LLM nieudany. Sprawdź logi/llm_server_stderr.log")
        sys.exit(1)

    # 4. Kontenery Podman (Qdrant, Nextcloud, n8n — BEZ open-webui, startujemy osobno)
    restart_podman_containers(["qdrant", "nextcloud", "postgres_nextcloud", "n8n"])
    time.sleep(3)   # daj Qdrant chwilę na start

    # 5. Backend FastAPI (embedding na CPU, żeby nie kolidować z LLM na GPU)
    backend_cmd = [PYTHON_VENV, "-m", "backend_app.main"]
    backend_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
        "KLIMTECH_EMBEDDING_DEVICE": "cpu",   # embedding na CPU
        "KLIMTECH_BASE_PATH": BASE_DIR,
    }
    if not start_process("Backend FastAPI", backend_cmd, BASE_DIR,
                         env_vars=backend_env, wait_seconds=5):
        print("\n⛔ Start Backend nieudany. Sprawdź logi/backend_fastapi_stderr.log")
        sys.exit(1)

    # 6. Watchdog
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
    print(f"\n✅ Watchdog działa (PID: {watchdog_proc.pid}) → logs/watchdog.log")

    # 7. Open WebUI
    time.sleep(2)
    start_owui(config)

    # Podsumowanie
    print("\n" + "=" * 55)
    print("🎉 KlimtechRAG gotowy!")
    print(f"   💬 Open WebUI:     http://localhost:{config.get('OWUI_PORT', 3000)}")
    print(f"   🔧 API Backend:    http://localhost:{backend_port}")
    print(f"   🤖 LLM (llama):   http://localhost:{llama_port}")
    print(f"   📦 Qdrant:        http://localhost:6333")
    print(f"   ☁️  Nextcloud:     http://localhost:8443")
    print(f"   🔗 n8n:           http://localhost:5678")
    print(f"\n   📝 Model: {model_name}")
    print(f"   📊 RAG debug: http://localhost:{backend_port}/rag/debug")
    print("\n   CTRL+C aby zatrzymać\n")
    print("=" * 55)

    # Czekaj na SIGINT
    try:
        while True:
            time.sleep(5)
            # Sprawdź czy backend żyje
            for proc in PROCESSES:
                if proc.poll() is not None:
                    print(f"\n⚠️  Proces (PID: {proc.pid}) zakończył się (kod: {proc.returncode})")
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
