#!/usr/bin/env python3
"""
KlimtechRAG — GPU Ingest Mode
==============================
1. Zatrzymuje LLM (zwalnia VRAM)
2. Uruchamia backend z GPU embedding
3. Czeka — Ty ładujesz pliki przez przeglądarkę

   👉  http://192.168.31.70:8000/

4. CTRL+C = zatrzymaj backend
5. Potem uruchom: python3 start_klimtech.py
"""
import subprocess, os, time, signal, sys, json

# ---------------------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------------------
BASE_DIR         = "/media/lobo/BACKUP/KlimtechRAG"
LLAMA_DIR        = os.path.join(BASE_DIR, "llama.cpp")
LOG_DIR          = os.path.join(BASE_DIR, "logs")
LLM_COMMAND_FILE = os.path.join(LOG_DIR, "llm_command.txt")
PYTHON_VENV      = "/home/lobo/klimtech_venv/bin/python3"
LLAMA_PORT       = "8082"
BACKEND_PORT     = "8000"
INTERFACE        = "enp9s0"

AMD_ENV = {
    "HIP_VISIBLE_DEVICES":      "0",
    "GPU_MAX_ALLOC_PERCENT":    "100",
    "HSA_ENABLE_SDMA":          "0",
    "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
}

BACKEND_PROC = None

# ---------------------------------------------------------------------------

def get_ip(interface: str = INTERFACE) -> str:
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
    print("\n🔻 Zatrzymuję LLM (zwalniam VRAM dla GPU embedding)...")
    subprocess.run(["pkill", "-f", "llama-server"],      capture_output=True)
    subprocess.run(["fuser", "-k", f"{LLAMA_PORT}/tcp"], capture_output=True)
    time.sleep(2)
    print("   ✅ VRAM wolny")

def stop_backend():
    global BACKEND_PROC
    print("\n🔻 Zatrzymuję backend...")
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
    print(f"   ✅ Port {BACKEND_PORT} wolny")

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

    # 1. Zatrzymaj LLM
    stop_llm()

    # 2. Zatrzymaj stary backend
    stop_backend()

    # 3. Start backend GPU
    start_backend_gpu()

    # 4. Instrukcje
    print("\n" + "=" * 60)
    print("🎉 Backend gotowy — otwórz przeglądarkę:")
    print()
    print(f"   👉  http://{LOCAL_IP}:{BACKEND_PORT}/")
    print()
    print("   Możesz tam:")
    print("   • Wgrywać pliki (PDF, TXT, DOCX...)")
    print("   • Wybrać tryb: normalny  lub  VLM (PDF z grafikami)")
    print("   • Śledzić postęp i statystyki")
    print()
    print("   Logi na żywo:")
    print(f"   tail -f {LOG_DIR}/backend_gpu_stdout.log")
    print()
    print("   CTRL+C = zatrzymaj i wróć do czatu")
    print("=" * 60 + "\n")

    # 5. Czekaj
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
