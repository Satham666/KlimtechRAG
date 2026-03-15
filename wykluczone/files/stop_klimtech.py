#!/usr/bin/env python3
"""
KlimtechRAG — Stop Script
Zatrzymuje wszystkie procesy i kontenery.
"""
import os
import subprocess
import sys
import time

BASE_DIR = "/media/lobo/BACKUP/KlimtechRAG"
LOG_DIR = os.path.join(BASE_DIR, "logs")

# MUSI być zgodne z watch_nextcloud.py (logs/klimtech_watchdog.pid)
WATCHDOG_PID_FILE = os.path.join(LOG_DIR, "klimtech_watchdog.pid")

CONTAINERS = ["open-webui", "n8n", "nextcloud", "postgres_nextcloud", "qdrant"]


def kill_by_pid_file(pid_file: str, name: str) -> bool:
    """Zabija proces przez PID file. Zwraca True jeśli się udało."""
    if not os.path.exists(pid_file):
        return False
    try:
        with open(pid_file) as f:
            pid = int(f.read().strip())
        os.kill(pid, 9)
        os.remove(pid_file)
        print(f"   ✅ {name} zabity (PID: {pid})")
        return True
    except (ProcessLookupError, ProcessError := Exception) as e:
        # Proces już nie istnieje — usuń stary PID file
        try:
            os.remove(pid_file)
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"   ⚠️  {name} PID file błąd: {e}")
        return False


def pkill(pattern: str, name: str) -> None:
    """Fallback: pkill po nazwie procesu."""
    try:
        result = subprocess.run(
            ["pkill", "-9", "-f", pattern],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            print(f"   ✅ {name} zatrzymany (pkill)")
        else:
            print(f"   ⚪ {name}: brak procesów")
    except subprocess.TimeoutExpired:
        print(f"   ⏱️  {name}: timeout")
    except Exception as e:
        print(f"   ⚠️  {name}: {e}")


def kill_watchdog() -> None:
    print("⚡ Watchdog...")
    if not kill_by_pid_file(WATCHDOG_PID_FILE, "Watchdog"):
        pkill("watch_nextcloud", "Watchdog")


def kill_backend() -> None:
    print("⚡ Backend FastAPI...")
    pkill("backend_app.main", "Backend")
    # Zwolnij port jeśli coś zostało
    try:
        subprocess.run(["fuser", "-k", "8000/tcp"], capture_output=True, timeout=5)
    except Exception:
        pass


def kill_llama() -> None:
    print("⚡ LLM Server (llama.cpp)...")
    pkill("llama-server", "llama-server")


def kill_venv_python() -> None:
    print("⚡ Pozostałe procesy venv...")
    pkill("KlimtechRAG/venv/bin/python", "venv python")


def stop_containers() -> None:
    print("\n🐳 Zatrzymywanie kontenerów Podman...")
    for container in CONTAINERS:
        try:
            result = subprocess.run(
                ["podman", "stop", "-t", "5", container],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                print(f"   ✅ {container}")
            else:
                print(f"   ⚪ {container}: nie działał")
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  {container}: timeout — wymuszam...")
            subprocess.run(["podman", "kill", container], capture_output=True)
        except Exception as e:
            print(f"   ⚠️  {container}: {e}")


def cleanup_pid_files() -> None:
    """Usuń stare PID files."""
    for pid_file in [WATCHDOG_PID_FILE]:
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
                print(f"   🧹 Usunięto: {pid_file}")
            except Exception:
                pass


def check_ports() -> None:
    print("\n📋 Sprawdzanie portów...")
    ports_to_check = {
        "8000": "Backend",
        "8082": "LLM",
        "6333": "Qdrant",
        "3000": "Open WebUI",
    }
    try:
        result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        for port, name in ports_to_check.items():
            if f":{port}" in result.stdout:
                print(f"   ⚠️  Port {port} ({name}) nadal zajęty!")
            else:
                print(f"   ✅ Port {port} ({name}) wolny")
    except Exception:
        pass


def main():
    print("\n" + "=" * 50)
    print("   🛑 KLIMTECHRAG STOP 🛑")
    print("=" * 50 + "\n")

    kill_watchdog()
    kill_backend()
    kill_llama()
    kill_venv_python()

    time.sleep(1)

    stop_containers()
    cleanup_pid_files()
    check_ports()

    # Usuń LLM command file
    llm_cmd_file = os.path.join(LOG_DIR, "llm_command.txt")
    if os.path.exists(llm_cmd_file):
        os.remove(llm_cmd_file)
        print(f"\n🧹 Usunięto: {llm_cmd_file}")

    print("\n" + "=" * 50)
    print("✅ System zatrzymany.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
