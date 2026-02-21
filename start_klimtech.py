#!/usr/bin/env python3
import subprocess
import os
import time
import signal
import sys
import glob
import select
import fcntl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend_app.scripts.model_parametr import calculate_params

# --- KONFIGURACJA ---
BASE_DIR = os.path.expanduser("~/KlimtechRAG")
BACKEND_DIR = os.path.join(BASE_DIR, "backend_app")
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
ENV_FILE = os.path.join(BASE_DIR, ".env")
LLM_COMMAND_FILE = os.path.join(BASE_DIR, "logs", "llm_command.txt")

PYTHON_VENV = os.path.join(BASE_DIR, "venv", "bin", "python")
CONTAINERS = ["qdrant", "nextcloud", "postgres_nextcloud", "n8n"]
PROCESSES = []


def load_env_file(env_path):
    env_vars = {
        "LLAMA_MODELS_DIR": "/home/lobo/.cache/llama.cpp",
        "LLAMA_API_PORT": "8082",
    }
    if not os.path.exists(env_path):
        print(f"⚠️  Brak pliku .env. Używam domyślnych.")
        return env_vars
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.strip().split("=", 1)
                env_vars[key] = value.strip('"').strip("'")
    return env_vars


def get_available_models(models_dir):
    if not os.path.exists(models_dir):
        print(f"❌ Katalog modeli nie istnieje: {models_dir}")
        sys.exit(1)
    models = glob.glob(os.path.join(models_dir, "**", "*.gguf"), recursive=True)
    if not models:
        print(f"❌ Nie znaleziono .gguf w {models_dir}")
        sys.exit(1)
    models.sort()
    return models


def select_user_model(models):
    print("\n" + "=" * 50)
    print("   DOSTĘPNE MODELE (GGUF)")
    print("=" * 50)
    for i, model_path in enumerate(models, 1):
        print(f"[{i}] {os.path.basename(model_path)}")
    print("=" * 50)
    while True:
        try:
            choice = input("\nWybierz numer modelu: ")
            index = int(choice) - 1
            if 0 <= index < len(models):
                return models[index]
            print("❌ Nieprawidłowy numer.")
        except ValueError:
            print("❌ To nie jest liczba.")


def start_process(name, command, cwd, env_vars=None, wait_seconds=5):
    """Uruchamia proces i sprawdza czy wystartował."""
    print(f"🚀 Uruchamianie: {name}...")
    print(f"   -> Komenda: {' '.join(command)}")
    if env_vars:
        print(f"   -> Zmienne środowiskowe: {env_vars}")

    if name == "LLM Server":
        os.makedirs(os.path.dirname(LLM_COMMAND_FILE), exist_ok=True)
        import json

        with open(LLM_COMMAND_FILE, "w") as f:
            json.dump(
                {
                    "command": command,
                    "cwd": cwd,
                    "env_vars": env_vars,
                },
                f,
            )
        print(f"   -> Komenda zapisana do: {LLM_COMMAND_FILE}")

    process_env = os.environ.copy()
    if env_vars:
        process_env.update(env_vars)

    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=process_env,
        )

        PROCESSES.append(proc)
        if wait_seconds > 0:
            print(f"   ⏳ Czekam {wait_seconds} sekund na inicjalizację...")
            time.sleep(wait_seconds)

        if proc.poll() is not None:
            print(f"❌ {name} padł przy starcie!")
            stdout, stderr = proc.communicate()
            if stderr:
                print(f"   👉 STDERR:\n{stderr.decode('utf-8', errors='ignore')}")
            if stdout:
                print(f"   👉 STDOUT:\n{stdout.decode('utf-8', errors='ignore')}")
            if name == "LLM Server" and os.path.exists(LLM_COMMAND_FILE):
                os.remove(LLM_COMMAND_FILE)
            return False
        else:
            print(f"✅ {name} działa (PID: {proc.pid})")
            return True

    except Exception as e:
        print(f"❌ Błąd: {e}")
        if name == "LLM Server" and os.path.exists(LLM_COMMAND_FILE):
            os.remove(LLM_COMMAND_FILE)
        return False


def restart_podman_containers():
    print("\n🐳 Uruchamianie kontenerów...")
    for container in CONTAINERS:
        try:
            subprocess.run(["podman", "start", container], check=False)
            time.sleep(1)
        except:
            pass
    print("✅ Kontenery startują.")


def signal_handler(sig, frame):
    print("\n🛑 Zatrzymywanie...")
    for proc in PROCESSES:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except:
            pass
    if os.path.exists(LLM_COMMAND_FILE):
        os.remove(LLM_COMMAND_FILE)
        print("   -> Usunięto plik komendy LLM")
    sys.exit(0)


def make_non_blocking(fd):
    """Ustawia deskryptor pliku na tryb nieblokujący."""
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    config = load_env_file(ENV_FILE)
    models_dir = config.get("LLAMA_MODELS_DIR")

    print("=" * 50)
    print("   KlimtechRAG v5.4 (Auto VRAM)")
    print("=" * 50)

    selected_model_path = select_user_model(get_available_models(models_dir))

    amd_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "GPU_MAX_ALLOC_PERCENT": "100",
        "HSA_ENABLE_SDMA": "0",
    }

    llama_binary = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
    if not os.path.exists(llama_binary):
        llama_binary = os.path.join(LLAMA_DIR, "llama-server")

    # Oblicz parametry automatycznie na podstawie rozmiaru modelu
    llama_args = calculate_params(selected_model_path).split()
    port = config.get("LLAMA_API_PORT", "8082")

    llama_cmd = [
        llama_binary,
        "-m",
        selected_model_path,
        "--host",
        "0.0.0.0",
        "--port",
        port,
    ] + llama_args

    if not start_process("LLM Server", llama_cmd, LLAMA_DIR, env_vars=amd_env):
        print("\n⛔ Start LLM nieudany.")
        sys.exit(1)

    restart_podman_containers()
    time.sleep(2)

    backend_cmd = [PYTHON_VENV, "-m", "backend_app.main"]
    backend_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
        "KLIMTECH_EMBEDDING_DEVICE": "cpu",
    }
    if not start_process(
        "Backend (FastAPI)", backend_cmd, BASE_DIR, env_vars=backend_env, wait_seconds=3
    ):
        print("\n⛔ Start Backend nieudany.")
        sys.exit(1)

    watchdog_cmd = [PYTHON_VENV, "backend_app/scripts/watch_nextcloud.py"]
    watchdog_proc = subprocess.Popen(
        watchdog_cmd,
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    PROCESSES.append(watchdog_proc)
    print(f"✅ Watchdog działa (PID: {watchdog_proc.pid})")

    print("\n" + "=" * 50)
    print("🎉 System KlimtechRAG gotowy!")
    print(f"📡 API LLM: http://localhost:{port}")
    print(f"📡 API Backend: http://localhost:8000")
    print("=" * 50)
    print("👂 Nasłuchiwanie logów LLM + Backend (CTRL+C by przerwać):\n")

    try:
        llm_proc = PROCESSES[0]
        backend_proc = PROCESSES[1]

        make_non_blocking(llm_proc.stdout)
        make_non_blocking(llm_proc.stderr)
        make_non_blocking(backend_proc.stdout)
        make_non_blocking(backend_proc.stderr)

        dead_processes = set()
        while True:
            for proc_info in [
                (llm_proc, "[LLM]"),
                (backend_proc, "[BACKEND]"),
            ]:
                proc, prefix = proc_info

                if proc.poll() is not None and prefix not in dead_processes:
                    dead_processes.add(prefix)
                    print(
                        f"\n❌ Proces {prefix} zakończył się (kod: {proc.returncode})"
                    )
                    while True:
                        chunk = proc.stdout.read(1024)
                        if not chunk:
                            break
                        print(
                            f"{prefix} {chunk.decode('utf-8', errors='ignore')}", end=""
                        )
                    while True:
                        chunk = proc.stderr.read(1024)
                        if not chunk:
                            break
                        print(
                            f"{prefix} ERR: {chunk.decode('utf-8', errors='ignore')}",
                            end="",
                        )

                if prefix in dead_processes:
                    continue

                try:
                    chunk = proc.stdout.read(4096)
                    if chunk:
                        for line in chunk.decode("utf-8", errors="ignore").splitlines():
                            print(f"{prefix} {line}")
                except (BlockingIOError, Exception):
                    pass

                try:
                    chunk = proc.stderr.read(4096)
                    if chunk:
                        for line in chunk.decode("utf-8", errors="ignore").splitlines():
                            print(f"{prefix} ERR: {line}")
                except (BlockingIOError, Exception):
                    pass

            if len(dead_processes) == 2:
                print("\n🛑 Wszystkie procesy zakończone. Wyjście...")
                break

            time.sleep(0.1)

    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
