#!/usr/bin/env python3
"""
KlimtechRAG v7.1 — Start Script (HTTPS)
=========================================
Uruchamia:
  - kontenery Podman (qdrant, nextcloud, postgres_nextcloud, n8n)
  - Backend FastAPI (:8000)
  - nginx reverse proxy (HTTPS :8443, :8444, :5679, :6334)

Modele LLM/VLM -> uruchamiane z panelu UI
"""

import subprocess, os, time, signal, sys

# --- KONFIGURACJA -----------------------------------------------------------
BASE_DIR = "/media/lobo/BACKUP/KlimtechRAG"
LOG_DIR = os.path.join(BASE_DIR, "logs")
PYTHON_VENV = "/media/lobo/BACKUP/KlimtechRAG/venv/bin/python3"
INTERFACE = "enp9s0"

# Porty HTTP (wewnetrzne)
BACKEND_PORT = "8000"
QDRANT_PORT = "6333"

# Porty HTTPS (nginx reverse proxy)
HTTPS_BACKEND = "8443"
HTTPS_NEXTCLOUD = "8444"
HTTPS_N8N = "5679"
HTTPS_QDRANT = "6334"

CONTAINERS = ["qdrant", "nextcloud", "postgres_nextcloud", "n8n"]
PROCESSES = []


def get_ip(iface=INTERFACE):
    try:
        out = subprocess.check_output(
            ["ip", "-4", "addr", "show", iface], text=True, stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    print("   Nie mozna pobrac IP z %s -- uzywam localhost" % iface)
    return "localhost"


LOCAL_IP = get_ip()


def start_containers(containers):
    print("\n   Uruchamianie kontenerow Podman...")
    for name in containers:
        try:
            r = subprocess.run(
                ["podman", "start", name], capture_output=True, text=True, timeout=30
            )
            status = "OK" if r.returncode == 0 else "SKIP"
            extra = ": " + r.stderr.strip()[:80] if r.returncode != 0 else ""
            print(f"   [{status}] {name}{extra}")
        except subprocess.TimeoutExpired:
            print(f"   [TIMEOUT] {name}")
        except Exception as e:
            print(f"   [ERR] {name}: {e}")
        time.sleep(0.4)


def start_backend():
    print("\n   Uruchamianie: Backend FastAPI...")
    os.makedirs(LOG_DIR, exist_ok=True)
    cmd = [PYTHON_VENV, "-m", "backend_app.main"]
    env = os.environ.copy()
    env.update(
        {
            "HIP_VISIBLE_DEVICES": "0",
            "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
            "KLIMTECH_EMBEDDING_DEVICE": "cuda:0",
            "KLIMTECH_BASE_PATH": BASE_DIR,
        }
    )
    log_out = open(os.path.join(LOG_DIR, "backend_stdout.log"), "a")
    log_err = open(os.path.join(LOG_DIR, "backend_stderr.log"), "a")
    proc = subprocess.Popen(
        cmd,
        cwd=BASE_DIR,
        stdout=log_out,
        stderr=log_err,
        start_new_session=True,
        env=env,
    )
    PROCESSES.append(proc)
    print("   Czekam 5s na inicjalizacje...")
    time.sleep(5)
    if proc.poll() is not None:
        print("   [FAIL] Backend padl! Sprawdz logs/backend_stderr.log")
        return False

    try:
        import urllib.request

        req = urllib.request.Request(f"http://127.0.0.1:{BACKEND_PORT}/health")
        response = urllib.request.urlopen(req, timeout=5)
        if response.status == 200:
            print(f"   [OK] Backend FastAPI (PID: {proc.pid})")
            return True
    except Exception:
        pass
    print(f"   [OK] Backend uruchomiony (PID: {proc.pid})")
    return True


def start_nginx():
    """Uruchamia nginx HTTPS reverse proxy."""
    print("\n   Uruchamianie: nginx HTTPS reverse proxy...")

    nginx_bin = subprocess.run(["which", "nginx"], capture_output=True, text=True)
    if nginx_bin.returncode != 0:
        print("   [FAIL] nginx nie jest zainstalowany!")
        print("          Uruchom: sudo apt-get install -y nginx")
        return False

    # Sprawdz czy nginx juz dziala na portach HTTPS
    try:
        ss = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        https_ports = [HTTPS_BACKEND, HTTPS_NEXTCLOUD, HTTPS_N8N, HTTPS_QDRANT]
        ok_count = sum(1 for p in https_ports if f":{p}" in ss.stdout)
        if ok_count == len(https_ports):
            print(
                f"   [OK] nginx HTTPS juz dziala ({ok_count}/{len(https_ports)} portow)"
            )
            return True
    except Exception:
        pass

    # Nginx nie dziala -probujemy uruchomic
    if not os.path.exists("/etc/nginx/sites-enabled/klimtech"):
        print("   [WARN] Brak /etc/nginx/sites-enabled/klimtech")
        print("          Kopiuje konfiguracje...")
        src = os.path.join(BASE_DIR, "data", "ssl", "klimtech-nginx.conf")
        if os.path.exists(src):
            try:
                subprocess.run(
                    ["sudo", "-n", "cp", src, "/etc/nginx/sites-available/klimtech"],
                    capture_output=True,
                    timeout=10,
                )
                subprocess.run(
                    [
                        "sudo",
                        "-n",
                        "ln",
                        "-sf",
                        "/etc/nginx/sites-available/klimtech",
                        "/etc/nginx/sites-enabled/klimtech",
                    ],
                    capture_output=True,
                    timeout=10,
                )
            except Exception as e:
                print(f"   [FAIL] Nie mozna skopiowac konfiguracji: {e}")
                return False
        else:
            print(f"   [FAIL] Brak pliku: {src}")
            return False

    # Usun merecat jesli blokuje port 80
    subprocess.run(
        ["sudo", "-n", "pkill", "-9", "merecat"], capture_output=True, timeout=3
    )
    time.sleep(0.5)

    # Usun domyslna strone nginx
    if os.path.exists("/etc/nginx/sites-enabled/default"):
        try:
            subprocess.run(
                ["sudo", "-n", "rm", "/etc/nginx/sites-enabled/default"],
                capture_output=True,
                timeout=3,
            )
        except Exception:
            pass

    # Test konfiguracji
    test = subprocess.run(
        ["sudo", "-n", "nginx", "-t"], capture_output=True, text=True, timeout=10
    )
    if test.returncode != 0:
        print(f"   [FAIL] nginx -t: {test.stderr.strip()[:200]}")
        return False

    # Start nginx
    result = subprocess.run(
        ["sudo", "-n", "nginx"], capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        print(f"   [FAIL] nginx start: {result.stderr.strip()[:200]}")
        return False

    time.sleep(1)
    try:
        ss = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        https_ports = [HTTPS_BACKEND, HTTPS_NEXTCLOUD, HTTPS_N8N, HTTPS_QDRANT]
        ok_count = sum(1 for p in https_ports if f":{p}" in ss.stdout)
        if ok_count == len(https_ports):
            print(f"   [OK] nginx HTTPS ({ok_count}/{len(https_ports)} portow)")
            return True
        else:
            print(f"   [WARN] nginx HTTPS ({ok_count}/{len(https_ports)} portow)")
            return True
    except Exception:
        pass

    print("   [OK] nginx uruchomiony")
    return True


def signal_handler(sig, frame):
    print("\n   Zatrzymywanie procesow...")
    for proc in PROCESSES:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception:
            pass
    # nginx zostaje uruchomiony — zatrzymaj go przez stop_klimtech.py
    # NIE uzywamy sudo tutaj (blokuje terminal, wycieka haslo)
    print("   Backend zatrzymany. nginx HTTPS nadal dziala.")
    print("   Aby zatrzymac nginx: sudo nginx -s stop")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "uploads"), exist_ok=True)

    print("\n" + "=" * 65)
    print("   KlimtechRAG v7.1 (HTTPS)")
    print("=" * 65)
    print(f"   Baza: {BASE_DIR}   IP: {LOCAL_IP}")

    start_containers(CONTAINERS)
    time.sleep(2)

    if not start_backend():
        sys.exit(1)

    nginx_ok = start_nginx()

    progress_log = os.path.join(LOG_DIR, "llm_progress.log")
    try:
        if os.path.exists(progress_log):
            os.remove(progress_log)
    except Exception:
        pass

    print("\n" + "=" * 65)
    print("   KlimtechRAG gotowy!")
    print("=" * 65)
    if nginx_ok:
        print(f"   Backend + UI:   https://{LOCAL_IP}:{HTTPS_BACKEND}")
        print(f"   Nextcloud:      https://{LOCAL_IP}:{HTTPS_NEXTCLOUD}")
        print(f"   n8n:            https://{LOCAL_IP}:{HTTPS_N8N}")
        print(f"   Qdrant:         https://{LOCAL_IP}:{HTTPS_QDRANT}")
    else:
        print("   [WARN] nginx nie wystartowal -- adresy HTTP:")
        print(f"   Backend + UI:   http://{LOCAL_IP}:{BACKEND_PORT}")
        print(f"   Nextcloud:      http://{LOCAL_IP}:8081")
        print(f"   n8n:            http://{LOCAL_IP}:5678")
        print(f"   Qdrant:         http://{LOCAL_IP}:{QDRANT_PORT}")
    print("   Modele LLM/VLM -> z panelu UI")
    print("   CTRL+C aby zatrzymac")
    print("=" * 65)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
