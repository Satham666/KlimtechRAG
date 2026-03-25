#!/usr/bin/env python3
"""
Skrypt do indeksowania plików na GPU.
Zatrzymuje LLM, indeksuje na GPU, przywraca LLM.

Użycie:
    python backend_app/scripts/ingest_gpu.py              # indeksuj wszystkie pending
    python backend_app/scripts/ingest_gpu.py --limit 5    # tylko 5 plików
    python backend_app/scripts/ingest_gpu.py --no-restart # nie restartuj LLM po zakończeniu
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

LLAMA_DIR = os.path.join(str(Path(__file__).parent.parent.parent), "llama.cpp")
LLAMA_BINARY = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
LLAMA_PORT = 8082

BASE_DIR = str(Path(__file__).parent.parent.parent)
LLM_COMMAND_FILE = os.path.join(BASE_DIR, "logs", "llm_command.txt")
BACKEND_PORT = 8000

HIP_ENV = {
    "HIP_VISIBLE_DEVICES": "0",
    "GPU_MAX_ALLOC_PERCENT": "100",
    "HSA_ENABLE_SDMA": "0",
    "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
    "KLIMTECH_EMBEDDING_DEVICE": "cuda:0",
}


def get_backend_pid():
    """Pobiera PID działającego backendu."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "backend_app.main"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            if pids and pids[0]:
                return int(pids[0])
    except Exception:
        pass
    return None


def stop_backend():
    """Zatrzymuje backend."""
    pid = get_backend_pid()
    if not pid:
        print("Backend nie działa")
        return False

    print(f"Zatrzymuję backend (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("✅ Backend zatrzymany")
                return True
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
        print("✅ Backend zatrzymany (SIGKILL)")
        return True
    except ProcessLookupError:
        print("Backend już nie działa")
        return True


def start_backend():
    """Uruchamia backend ze zmiennymi HIP dla GPU."""
    if get_backend_pid():
        print("Backend już działa")
        return

    start_script = os.path.join(BASE_DIR, "start_backend_gpu.sh")
    if os.path.exists(start_script):
        print("🚀 Uruchamianie backendu przez start_backend_gpu.sh...")
        subprocess.Popen(
            [start_script],
            cwd=BASE_DIR,
            stdout=open(os.path.join(BASE_DIR, "logs", "backend_stdout.log"), "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    else:
        env = os.environ.copy()
        env.update(HIP_ENV)
        python_venv = os.path.join(BASE_DIR, "venv", "bin", "python")
        cmd = [
            python_venv,
            "-m",
            "uvicorn",
            "backend_app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(BACKEND_PORT),
        ]
        print("🚀 Uruchamianie backendu z HIP...")
        print(f"   -> HIP_VISIBLE_DEVICES=0")
        print(f"   -> KLIMTECH_EMBEDDING_DEVICE=cuda:0")
        subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )

    for _ in range(30):
        time.sleep(1)
        try:
            import requests

            r = requests.get(f"http://localhost:{BACKEND_PORT}/health", timeout=1)
            if r.status_code == 200:
                print(f"✅ Backend działa na GPU")
                return
        except Exception:
            pass

    print("❌ Timeout - backend nie wystartował")


def get_llm_pid():
    """Pobiera PID działającego LLM."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"llama-server.*{LLAMA_PORT}"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            if pids and pids[0]:
                return int(pids[0])
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.split("\n"):
            if f":{LLAMA_PORT}" in line:
                parts = line.split()
                for p in parts:
                    if "pid=" in p:
                        return int(p.split("pid=")[1].split(",")[0])
    except Exception:
        pass

    return None


def load_llm_command():
    """Wczytuje zapisaną komendę LLM z pliku."""
    import json

    try:
        with open(LLM_COMMAND_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def save_llm_command(data):
    """Zapisuje komendę LLM do pliku."""
    import json

    os.makedirs(os.path.dirname(LLM_COMMAND_FILE), exist_ok=True)
    with open(LLM_COMMAND_FILE, "w") as f:
        json.dump(data, f)


def stop_llm():
    """Zatrzymuje LLM i zapisuje jego komendę do pliku."""
    pid = get_llm_pid()
    llm_cmd = load_llm_command()

    if not pid:
        print("LLM nie działa")
        return None

    print(f"Zatrzymuję LLM (PID: {pid})...")
    if llm_cmd:
        cmd_str = " ".join(llm_cmd.get("command", []))
        print(f"   -> Komenda: {cmd_str[:80]}...")

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("✅ LLM zatrzymany")
                return llm_cmd
        print("LLM nie zatrzymał się, wysyłam SIGKILL...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(1)
        print("✅ LLM zatrzymany (SIGKILL)")
        return llm_cmd
    except ProcessLookupError:
        print("LLM już nie działa")
        return llm_cmd


def start_llm():
    """Uruchamia LLM używając zapisanej komendy."""
    pid = get_llm_pid()
    if pid:
        print(f"LLM już działa (PID: {pid})")
        return

    llm_cmd = load_llm_command()
    if not llm_cmd:
        print("❌ Brak zapisanej komendy LLM!")
        print("   Najpierw uruchom system przez ./start_klimtech.py")
        return

    command = llm_cmd.get("command", [])
    cwd = llm_cmd.get("cwd", LLAMA_DIR)
    env_vars = llm_cmd.get("env_vars", {})

    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    print("🚀 Uruchamianie: LLM Server...")
    print(f"   -> Komenda: {' '.join(command)}")

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        start_new_session=True,
    )

    for _ in range(60):
        time.sleep(1)
        try:
            import requests

            r = requests.get(f"http://localhost:{LLAMA_PORT}/health", timeout=1)
            if r.status_code == 200:
                print(f"✅ LLM Server działa (PID: {proc.pid})")
                return
        except Exception:
            pass

    print("❌ Timeout - LLM nie wystartował w 60s")


def ingest_on_gpu(limit=None):
    print("\n" + "=" * 50)
    print("  Indeksowanie na GPU")
    print("=" * 50 + "\n")

    import requests

    url = "http://localhost:8000/ingest_all"
    if limit:
        url += f"?limit={limit}"

    print(f"Wywołuję: POST {url}")
    print("To może potrwać kilka minut...\n")

    try:
        response = requests.post(url, timeout=7200)
        if response.status_code == 200:
            result = response.json()
            print(f"\nZindeksowano: {result.get('indexed', 0)} plików")
            for r in result.get("results", []):
                status = r.get("status", "unknown")
                filename = r.get("filename", "?")
                chunks = r.get("chunks", 0)
                error = r.get("error", "")
                if status == "ok":
                    print(f"  ✅ {filename} -> {chunks} chunków")
                elif status == "empty":
                    print(f"  ⚠️  {filename} -> pusty")
                else:
                    print(f"  ❌ {filename} -> {error}")
        else:
            print(f"Błąd: HTTP {response.status_code}")
            print(response.text[:500])
    except requests.exceptions.Timeout:
        print("Timeout - indeksowanie trwa dalej w tle")
    except Exception as e:
        print(f"Błąd: {e}")


def main():
    parser = argparse.ArgumentParser(description="Indeksowanie na GPU")
    parser.add_argument("--limit", type=int, help="Maks. liczba plików")
    parser.add_argument(
        "--no-restart", action="store_true", help="Nie restartuj LLM po zakończeniu"
    )
    parser.add_argument(
        "--keep-backend",
        action="store_true",
        help="Nie restartuj backendu (jeśli już działa z HIP)",
    )
    args = parser.parse_args()

    llm_was_running = get_llm_pid() is not None

    print("\n" + "=" * 60)
    print("  KLIMTECHRAG - Indeksowanie na GPU")
    print("=" * 60)

    # 1. Zatrzymaj LLM
    if llm_was_running:
        print("\n[1/4] Zatrzymuję LLM...")
        stop_llm()
        time.sleep(2)
    else:
        print("\n[1/4] LLM nie działa - OK")

    # 2. Zatrzymaj backend
    if not args.keep_backend:
        print("\n[2/4] Restartuję backend z HIP...")
        stop_backend()
        time.sleep(1)
        start_backend()
        time.sleep(3)
    else:
        print("\n[2/4] Backend zostawiam bez zmian")

    # 3. Indeksuj na GPU
    print("\n[3/4] Indeksowanie na GPU...")
    try:
        ingest_on_gpu(limit=args.limit)
    except Exception as e:
        print(f"Błąd indeksowania: {e}")

    # 4. Przywróć LLM
    if llm_was_running and not args.no_restart:
        print("\n[4/4] Przywracanie LLM...")
        time.sleep(2)
        start_llm()
    else:
        print("\n[4/4] LLM nie będzie uruchomiony (--no-restart)")

    print("\n" + "=" * 60)
    print("  Zakończono")
    print("=" * 60)


if __name__ == "__main__":
    main()
