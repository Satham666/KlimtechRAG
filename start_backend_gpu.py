#!/usr/bin/env python3
"""
KlimtechRAG — GPU Ingest Mode
1. Zatrzymuje LLM (zwalnia VRAM)
2. Startuje Qdrant (jeśli nie działa)
3. Uruchamia backend z GPU embedding
4. Czeka — Ty ładujesz pliki przez przeglądarkę: http://<IP>:8000/
5. CTRL+C = zatrzymaj backend, potem uruchom start_klimtech.py
"""
import subprocess, os, time, signal, sys, json

# ---------------------------------------------------------------------------
BASE_DIR         = "/media/lobo/BACKUP/KlimtechRAG"
LLAMA_DIR        = os.path.join(BASE_DIR, "llama.cpp")
LOG_DIR          = os.path.join(BASE_DIR, "logs")
LLM_COMMAND_FILE = os.path.join(LOG_DIR, "llm_command.txt")
PYTHON_VENV      = "/media/lobo/BACKUP/KlimtechRAG/venv/bin/python3"
LLAMA_PORT       = "8082"
BACKEND_PORT     = "8000"
QDRANT_PORT      = "6333"
INTERFACE        = "enp9s0"

AMD_ENV = {
    "HIP_VISIBLE_DEVICES":      "0",
    "GPU_MAX_ALLOC_PERCENT":    "100",
    "HSA_ENABLE_SDMA":          "0",
    "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
}

BACKEND_PROC = None

# ---------------------------------------------------------------------------

def get_ip(interface=INTERFACE):
    try:
        out = subprocess.check_output(["ip", "-4", "addr", "show", interface],
                                      text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return "localhost"

LOCAL_IP = get_ip()

# ---------------------------------------------------------------------------

def stop_llm():
    print("\n🔻 Zatrzymuję LLM (zwalniam VRAM)...")
    subprocess.run(["pkill", "-f", "llama-server"],      capture_output=True)
    subprocess.run(["fuser", "-k", f"{LLAMA_PORT}/tcp"], capture_output=True)
    time.sleep(2)
    print("   ✅ VRAM wolny")


def ensure_qdrant():
    """Sprawdza czy Qdrant działa, jeśli nie — startuje kontener."""
    import urllib.request, urllib.error

    def qdrant_ok():
        try:
            urllib.request.urlopen(f"http://localhost:{QDRANT_PORT}/collections", timeout=2)
            return True
        except Exception:
            return False

    if qdrant_ok():
        print(f"\n✅ Qdrant już działa (port {QDRANT_PORT})")
        return

    print(f"\n🐳 Uruchamiam Qdrant...")
    subprocess.run(["podman", "start", "qdrant"], capture_output=True)

    print("   ⏳ Czekam na Qdrant...")
    for i in range(20):
        time.sleep(1)
        if qdrant_ok():
            print(f"   ✅ Qdrant gotowy ({i+1}s)")
            return

    print("   ❌ Qdrant nie odpowiada po 20s!")
    print("   Sprawdź: podman logs qdrant")
    sys.exit(1)


def stop_backend():
    global BACKEND_PROC
    subprocess.run(["pkill", "-f", "uvicorn backend_app"],   capture_output=True)
    subprocess.run(["pkill", "-f", "backend_app.main"],       capture_output=True)
    subprocess.run(["fuser", "-k", f"{BACKEND_PORT}/tcp"],   capture_output=True)
    if BACKEND_PROC:
        try:
            BACKEND_PROC.terminate()
            BACKEND_PROC.wait(timeout=5)
        except Exception:
            try: BACKEND_PROC.kill()
            except Exception: pass
        BACKEND_PROC = None
    time.sleep(2)


def start_backend_gpu():
    global BACKEND_PROC
    print("\n🚀 Uruchamianie Backend (GPU embedding)...")
    os.makedirs(LOG_DIR, exist_ok=True)

    env = os.environ.copy()
    env.update({
        "HIP_VISIBLE_DEVICES":       "0",
        "HSA_OVERRIDE_GFX_VERSION":  "9.0.6",
        "KLIMTECH_EMBEDDING_DEVICE": "cuda:0",
        "KLIMTECH_BASE_PATH":        BASE_DIR,
    })

    log_out = open(os.path.join(LOG_DIR, "backend_gpu_stdout.log"), "a")
    log_err = open(os.path.join(LOG_DIR, "backend_gpu_stderr.log"), "a")

    BACKEND_PROC = subprocess.Popen(
        [PYTHON_VENV, "-m", "backend_app.main"],
        cwd=BASE_DIR, stdout=log_out, stderr=log_err,
        start_new_session=True, env=env,
    )

    print("   ⏳ Czekam 10s na inicjalizację...")
    time.sleep(10)

    if BACKEND_PROC.poll() is not None:
        print("❌ Backend padł! Sprawdź logs/backend_gpu_stderr.log")
        sys.exit(1)

    print(f"✅ Backend GPU działa (PID: {BACKEND_PROC.pid})")


def signal_handler(sig, frame):
    print("\n\n🛑 Zatrzymuję backend GPU...")
    stop_backend()
    print("\n✅ Gotowe. Teraz uruchom:")
    print("   python3 start_klimtech.py")
    sys.exit(0)

# ---------------------------------------------------------------------------

def main():
    signal.signal(signal.SIGINT, signal_handler)
    os.makedirs(LOG_DIR, exist_ok=True)

    print("\n" + "=" * 60)
    print("   KlimtechRAG — Tryb ładowania plików (GPU)")
    print("=" * 60)

    stop_llm()

    print("\n🔻 Zatrzymuję poprzedni backend...")
    stop_backend()

    ensure_qdrant()

    start_backend_gpu()

    print("\n" + "=" * 60)
    print("🎉 Gotowe — otwórz przeglądarkę:")
    print()
    print(f"   👉  http://{LOCAL_IP}:{BACKEND_PORT}/")
    print()
    print("   • Wgraj pliki (PDF, TXT, DOCX...)")
    print("   • Wybierz tryb: normalny lub VLM (PDF z grafikami)")
    print("   • Śledź postęp i statystyki")
    print()
    print(f"   Logi: tail -f {LOG_DIR}/backend_gpu_stdout.log")
    print()
    print("   CTRL+C = zatrzymaj i przejdź do czatu")
    print("=" * 60 + "\n")

    try:
        while True:
            time.sleep(10)
            if BACKEND_PROC and BACKEND_PROC.poll() is not None:
                print(f"\n⚠️  Backend zakończył się (kod: {BACKEND_PROC.returncode})")
                print(f"   Sprawdź: {LOG_DIR}/backend_gpu_stderr.log")
                break
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
