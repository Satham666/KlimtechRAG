#!/usr/bin/env python3
"""
KlimtechRAG — GPU Ingest Mode
Zatrzymuje LLM, uruchamia backend z GPU embedding do masowego indeksowania.
Po zakończeniu restartuje LLM z wybranym modelem.

Użycie: python3 start_backend_gpu.py
"""
import subprocess
import os
import time
import signal
import sys
import glob
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend_app.scripts.model_parametr import calculate_params

# ---------------------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------------------

BASE_DIR         = "/media/lobo/BACKUP/KlimtechRAG"
LLAMA_DIR        = os.path.join(BASE_DIR, "llama.cpp")
LOG_DIR          = os.path.join(BASE_DIR, "logs")
LLM_COMMAND_FILE = os.path.join(LOG_DIR, "llm_command.txt")
MODELS_DIR       = os.path.join(BASE_DIR, "modele_LLM")
PYTHON_VENV      = "/home/lobo/klimtech_venv/bin/python3"
LLAMA_BINARY     = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
LLAMA_PORT       = "8082"
BACKEND_PORT     = "8000"

AMD_ENV = {
    "HIP_VISIBLE_DEVICES":      "0",
    "GPU_MAX_ALLOC_PERCENT":    "100",
    "HSA_ENABLE_SDMA":          "0",
    "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
}

BACKEND_PROC = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_interface_ip(interface: str = "enp9s0") -> str:
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


def get_available_models() -> list:
    if not os.path.exists(MODELS_DIR):
        print(f"❌ Katalog modeli nie istnieje: {MODELS_DIR}")
        sys.exit(1)
    models = glob.glob(os.path.join(MODELS_DIR, "**", "*.gguf"), recursive=True)
    if not models:
        print(f"❌ Nie znaleziono .gguf w {MODELS_DIR}")
        sys.exit(1)
    models.sort()
    return models


def select_model(models: list) -> str:
    print("\n" + "=" * 55)
    print("   DOSTĘPNE MODELE (GGUF)")
    print("=" * 55)
    for i, path in enumerate(models, 1):
        size_gb = os.path.getsize(path) / (1024 ** 3)
        print(f"[{i}] {os.path.basename(path)}  ({size_gb:.1f} GB)")
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


def signal_handler(sig, frame):
    print("\n🛑 Przerywanie — zatrzymuję backend GPU...")
    stop_backend()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Zarządzanie procesami
# ---------------------------------------------------------------------------

def stop_llm():
    print("\n🔻 Zatrzymuję LLM server (zwalnianie VRAM)...")
    subprocess.run(["pkill", "-f", "llama-server"],       capture_output=True)
    subprocess.run(["fuser", "-k", f"{LLAMA_PORT}/tcp"],  capture_output=True)
    time.sleep(2)
    print(f"   ✅ Port {LLAMA_PORT} wolny — VRAM zwolniony dla GPU embedding")


def stop_backend():
    global BACKEND_PROC
    print("🔻 Zatrzymuję backend GPU...")
    subprocess.run(["pkill", "-f", "uvicorn backend_app"],    capture_output=True)
    subprocess.run(["fuser", "-k", f"{BACKEND_PORT}/tcp"],    capture_output=True)
    if BACKEND_PROC:
        try:
            BACKEND_PROC.terminate()
            BACKEND_PROC.wait(timeout=5)
        except Exception:
            try:
                BACKEND_PROC.kill()
            except Exception:
                pass
        BACKEND_PROC = None
    time.sleep(2)
    print(f"   ✅ Backend zatrzymany, port {BACKEND_PORT} wolny")


def start_backend_gpu():
    global BACKEND_PROC
    print("\n🚀 Uruchamianie Backend FastAPI (GPU embedding)...")
    os.makedirs(LOG_DIR, exist_ok=True)

    backend_env = os.environ.copy()
    backend_env.update({
        "HIP_VISIBLE_DEVICES":      "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
        "KLIMTECH_EMBEDDING_DEVICE": "cuda:0",
        "KLIMTECH_BASE_PATH":       BASE_DIR,
    })

    log_out = open(os.path.join(LOG_DIR, "backend_gpu_stdout.log"), "a")
    log_err = open(os.path.join(LOG_DIR, "backend_gpu_stderr.log"), "a")

    BACKEND_PROC = subprocess.Popen(
        [PYTHON_VENV, "-m", "backend_app.main"],
        cwd=BASE_DIR,
        stdout=log_out,
        stderr=log_err,
        start_new_session=True,
        env=backend_env,
    )

    print("   ⏳ Czekam 8s na inicjalizację...")
    time.sleep(8)

    if BACKEND_PROC.poll() is not None:
        print("❌ Backend GPU padł! Sprawdź logs/backend_gpu_stderr.log")
        sys.exit(1)

    print(f"✅ Backend GPU działa (PID: {BACKEND_PROC.pid})")
    print(f"   🔧 API:              http://{LOCAL_IP}:{BACKEND_PORT}")
    print(f"   ⚡ Embedding device: cuda:0")


def start_llm(model_path: str) -> bool:
    llama_bin = LLAMA_BINARY
    if not os.path.exists(llama_bin):
        llama_bin = os.path.join(LLAMA_DIR, "llama-server")

    llama_args = calculate_params(model_path).split()
    llama_cmd = [
        llama_bin, "-m", model_path,
        "--host", "0.0.0.0",
        "--port", LLAMA_PORT,
    ] + llama_args

    model_name = os.path.basename(model_path)
    print(f"\n🚀 Uruchamianie LLM Server: {model_name}...")
    print(f"   Komenda: {' '.join(llama_cmd)}")

    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LLM_COMMAND_FILE, "w") as f:
        json.dump({"command": llama_cmd, "cwd": LLAMA_DIR, "env_vars": AMD_ENV}, f, indent=2)

    llm_env = os.environ.copy()
    llm_env.update(AMD_ENV)

    log_out = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
    log_err = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")

    proc = subprocess.Popen(
        llama_cmd,
        cwd=LLAMA_DIR,
        stdout=log_out,
        stderr=log_err,
        start_new_session=True,
        env=llm_env,
    )

    print("   ⏳ Czekam 10s na inicjalizację...")
    time.sleep(10)

    if proc.poll() is not None:
        print("❌ LLM Server padł! Sprawdź logs/llm_server_stderr.log")
        return False

    print(f"✅ LLM Server działa (PID: {proc.pid})")
    print(f"   🤖 http://{LOCAL_IP}:{LLAMA_PORT}")
    return True


def run_ingest():
    print("\n" + "=" * 55)
    try:
        raw = input("Ile plików zaindeksować? (Enter = 50): ").strip()
        limit = int(raw) if raw else 50
    except (ValueError, KeyboardInterrupt):
        limit = 50

    print(f"\n📥 Indeksowanie (limit={limit}) — może potrwać kilka minut...")
    print(f"   Postęp na żywo: tail -f {LOG_DIR}/backend_gpu_stdout.log")

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"http://localhost:{BACKEND_PORT}/ingest_all?limit={limit}"],
            capture_output=True, text=True, timeout=7200
        )
        if result.returncode == 0:
            print(f"   ✅ Zakończono: {result.stdout[:300]}")
        else:
            print(f"   ⚠️  Błąd curl: {result.stderr[:100]}")
    except subprocess.TimeoutExpired:
        print("   ⏱️  Timeout — indeksowanie nadal trwa w tle (sprawdź logi)")
    except Exception as e:
        print(f"   ❌ Błąd: {e}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    signal.signal(signal.SIGINT, signal_handler)
    os.makedirs(LOG_DIR, exist_ok=True)

    print("\n" + "=" * 55)
    print("   KlimtechRAG — GPU Ingest Mode")
    print("=" * 55)
    print(f"   Baza:   {BASE_DIR}")
    print(f"   Modele: {MODELS_DIR}")

    # 1. Wybór modelu LLM — wróci po zakończeniu indeksowania
    models = get_available_models()
    print("\n📌 Wybierz model LLM do uruchomienia PO indeksowaniu:")
    selected_model = select_model(models)
    model_name = os.path.basename(selected_model)
    print(f"\n   ✅ Zapamiętano: {model_name}")

    # 2. Zatrzymaj LLM — zwolnij VRAM
    stop_llm()

    # 3. Zatrzymaj ewentualny stary backend
    stop_backend()

    # 4. Uruchom backend z GPU embedding
    start_backend_gpu()

    # 5. Indeksowanie
    run_ingest()

    # 6. Statystyki po indeksowaniu
    print("\n" + "=" * 55)
    print("📊 Statystyki po indeksowaniu:")
    try:
        result = subprocess.run(
            ["curl", "-s", f"http://localhost:{BACKEND_PORT}/files/stats"],
            capture_output=True, text=True, timeout=10
        )
        print(f"   {result.stdout[:400]}")
    except Exception:
        print("   (nie można pobrać statystyk)")

    # 7. Zatrzymaj backend GPU
    stop_backend()

    # 8. Uruchom LLM z wybranym modelem
    print("\n" + "=" * 55)
    print(f"🔄 Przywracam LLM: {model_name}")
    print("=" * 55)

    if not start_llm(selected_model):
        print("\n⛔ Start LLM nieudany. Sprawdź logs/llm_server_stderr.log")
        sys.exit(1)

    # Podsumowanie
    print("\n" + "=" * 55)
    print("🎉 GPU Ingest zakończony!")
    print(f"   🤖 LLM (llama):   http://{LOCAL_IP}:{LLAMA_PORT}")
    print(f"   📝 Model:         {model_name}")
    print(f"\n   ℹ️  Aby uruchomić pełny system: python3 start_klimtech.py")
    print("=" * 55)


if __name__ == "__main__":
    main()
