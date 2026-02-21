#!/usr/bin/env python3
import subprocess
import sys
import os

CONTAINERS = ["qdrant", "nextcloud", "postgres_nextcloud", "n8n"]


def kill_all_venv_python():
    """Zabija wszystkie procesy używające venv/bin/python."""
    print(
        "⚡ Zatrzymywanie wszystkich procesów venv/bin/python...", end=" ", flush=True
    )
    try:
        result = subprocess.run(
            ["pkill", "-9", "-f", "KlimtechRAG/venv/bin/python"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("✅ ZABITO")
        else:
            print("⚪ Brak procesów")
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout")
    except Exception as e:
        print(f"⚠️ Błąd: {e}")


def kill_llama_server():
    """Zabija llama-server."""
    print("⚡ Zatrzymywanie llama-server...", end=" ", flush=True)
    try:
        result = subprocess.run(
            ["pkill", "-9", "-f", "llama-server"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("✅ ZABITO")
        else:
            print("⚪ Nie działał")
    except subprocess.TimeoutExpired:
        print("⏱️ Timeout")
    except Exception as e:
        print(f"⚠️ Błąd: {e}")


def stop_containers():
    """Zatrzymuje kontenery Podmana."""
    print("\n🐳 Zatrzymywanie kontenerów Podman...")
    for container in CONTAINERS:
        try:
            subprocess.run(
                ["podman", "stop", "-t", "5", container],
                capture_output=True,
                timeout=15,
            )
            print(f"   -> {container}: OK")
        except subprocess.TimeoutExpired:
            print(f"   -> {container}: Timeout")
        except Exception as e:
            print(f"   -> {container}: Błąd ({e})")


def check_port_8000():
    """Sprawdza czy port 8000 jest wolny."""
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if ":8000" in result.stdout:
            print("⚠️  Port 8000 nadal zajęty!")
            return False
    except Exception:
        pass
    return True

def kill_watchdog():
    print("⚡ Zatrzymywanie watchdog...", end=" ", flush=True)
    try:
        # Najpierw przez PID file
        pid_file = "/tmp/klimtech_watchdog.pid"
        if os.path.exists(pid_file):
            with open(pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 9)
            os.remove(pid_file)
            print("✅ ZABITO (PID file)")
            return
    except Exception:
        pass
    
    # Fallback: pkill
    try:
        result = subprocess.run(
            ["pkill", "-9", "-f", "watch_nextcloud"],
            capture_output=True, timeout=10,
        )
        if result.returncode == 0:
            print("✅ ZABITO (pkill)")
        else:
            print("⚪ Nie działał")
    except Exception as e:
        print(f"⚠️ Błąd: {e}")


def main():
    print("\n" + "=" * 50)
    print("   🛑 KLIMTECHRAG HARD STOP 🛑")
    print("=" * 50 + "\n")

    kill_watchdog()
    kill_all_venv_python()
    kill_llama_server()
    stop_containers()

    print("\n📋 Sprawdzanie portów...")
    check_port_8000()

    print("\n" + "=" * 50)
    print("🧹 Gotowe.")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
