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
BASE_DIR = "/home/lobo/KlimtechRAG"
LOG_DIR = os.path.join(BASE_DIR, "logs")
PYTHON_VENV = "/home/lobo/KlimtechRAG/venv/bin/python3"
INTERFACE = "enp9s0"

# Porty HTTP (wewnetrzne)
BACKEND_PORT = "8000"
QDRANT_PORT = "6333"

# Porty HTTPS (nginx reverse proxy)
HTTPS_BACKEND = "8443"
HTTPS_NEXTCLOUD = "8444"
HTTPS_N8N = "5679"
HTTPS_QDRANT = "6334"

# Pod i kontenery
POD_NAME = "klimtech_pod"
CONTAINERS_STANDALONE = ["qdrant", "n8n"]

# Konfiguracja Podman
BASE_PATH = BASE_DIR
NEXTCLOUD_DATA_DIR = os.path.join(BASE_DIR, "data", "nextcloud")
NEXTCLOUD_USER_DATA = os.path.join(BASE_DIR, "data", "nextcloud_data")

# Dane dostępowe do bazy
DB_NAME = "nextcloud"
DB_USER = "nextcloud"
DB_PASS = "klimtech123"

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


def cleanup_podman():
    """Czyści nieużywane obrazy i warstwy overlay."""
    print("\n   Czyszczenie Podman storage...")
    try:
        result = subprocess.run(
            ["podman", "system", "prune", "-a", "-f"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            # Wyświetl ile zwolniono
            for line in result.stderr.splitlines():
                if "Total reclaimed space" in line:
                    print(f"   [OK] {line.strip()}")
                    break
            else:
                print("   [OK] Storage oczyszczony")
        else:
            print(f"   [WARN] Cleanup: {result.stderr[:100]}")
    except Exception as e:
        print(f"   [WARN] Cleanup error: {e}")


def start_pod():
    """Uruchamia Pod z Nextcloud + PostgreSQL. Tworzy tylko jeśli nie istnieje."""
    print("\n   Pod 'klimtech'...")

    # Sprawdź czy pod już istnieje
    check = subprocess.run(
        ["podman", "pod", "exists", POD_NAME],
        capture_output=True,
        timeout=10,
    )

    if check.returncode == 0:
        # Pod istnieje — tylko uruchom
        print(f"   [SKIP] Pod {POD_NAME} już istnieje, uruchamiam...")
        subprocess.run(
            ["podman", "pod", "start", POD_NAME],
            capture_output=True,
            text=True,
            timeout=30,
        )
        time.sleep(5)
        return True

    # Pod nie istnieje — utwórz od zera
    print(f"   Tworzenie nowego Pod {POD_NAME}...")

    # Utwórz nowy pod z mapowaniem portu 8081
    result = subprocess.run(
        ["podman", "pod", "create", "--name", POD_NAME, "-p", "8081:80"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 0:
        print(f"   [OK] Pod {POD_NAME} utworzony")
    else:
        print(f"   [FAIL] Pod: {result.stderr}")
        return False

    # Utwórz katalogi dla Nextcloud
    os.makedirs(NEXTCLOUD_DATA_DIR, exist_ok=True)
    os.makedirs(NEXTCLOUD_USER_DATA, exist_ok=True)

    # Uruchom PostgreSQL w Pod
    print("   Uruchamianie PostgreSQL w Pod...")
    pg_result = subprocess.run(
        [
            "podman",
            "run",
            "-d",
            "--name",
            "postgres_nextcloud",
            "--restart",
            "always",
            "--pod",
            POD_NAME,
            "-e",
            f"POSTGRES_DB={DB_NAME}",
            "-e",
            f"POSTGRES_USER={DB_USER}",
            "-e",
            f"POSTGRES_PASSWORD={DB_PASS}",
            "-v",
            "klimtech_postgres_data:/var/lib/postgresql/data",
            "docker.io/library/postgres:16",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if pg_result.returncode == 0:
        print("   [OK] PostgreSQL uruchomiony")
    else:
        print(f"   [FAIL] PostgreSQL: {pg_result.stderr[:100]}")
        return False

    time.sleep(3)

    # Uruchom Nextcloud w Pod (Named Volume dla danych, NIE exFAT!)
    print("   Uruchamianie Nextcloud w Pod...")
    nc_result = subprocess.run(
        [
            "podman",
            "run",
            "-d",
            "--name",
            "nextcloud",
            "--restart",
            "always",
            "--pod",
            POD_NAME,
            "-e",
            "POSTGRES_HOST=localhost",
            "-e",
            f"POSTGRES_DB={DB_NAME}",
            "-e",
            f"POSTGRES_USER={DB_USER}",
            "-e",
            f"POSTGRES_PASSWORD={DB_PASS}",
            "-e",
            "NEXTCLOUD_TRUSTED_DOMAINS=192.168.31.70 localhost 127.0.0.1",
            "-e",
            "NEXTCLOUD_ADMIN_USER=admin",
            "-e",
            "NEXTCLOUD_ADMIN_PASSWORD=klimtech123",
            "-v",
            "klimtech_nextcloud_data:/var/www/html/data",
            "docker.io/library/nextcloud:32",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if nc_result.returncode == 0:
        print("   [OK] Nextcloud uruchomiony")
    else:
        print(f"   [FAIL] Nextcloud: {nc_result.stderr[:100]}")
        return False

    print("   Czekam 45s na instalację Nextcloud...")
    time.sleep(45)

    return True


def create_standalone_containers():
    """Tworzy standalone kontenery (qdrant, n8n) jeśli nie istnieją."""
    print("\n   Tworzenie standalone kontenerów...")

    # Sprawdź czy kontenery istnieją
    existing = subprocess.run(
        ["podman", "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    existing_names = set(existing.stdout.strip().split("\n"))

    # Utwórz qdrant jeśli nie istnieje
    if "qdrant" not in existing_names:
        print("   Tworzenie kontenera qdrant...")
        try:
            result = subprocess.run(
                [
                    "podman",
                    "run",
                    "-d",
                    "--name",
                    "qdrant",
                    "--restart",
                    "always",
                    "-p",
                    "6333:6333",
                    "-v",
                    "klimtech_qdrant_data:/qdrant/storage",
                    "docker.io/qdrant/qdrant:latest",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("   [OK] qdrant utworzony")
            else:
                print(f"   [WARN] qdrant: {result.stderr[:100]}")
        except Exception as e:
            print(f"   [ERR] qdrant: {e}")
    else:
        print("   [SKIP] qdrant już istnieje")

    # Utwórz n8n jeśli nie istnieje
    if "n8n" not in existing_names:
        print("   Tworzenie kontenera n8n...")
        try:
            result = subprocess.run(
                [
                    "podman",
                    "run",
                    "-d",
                    "--name",
                    "n8n",
                    "--restart",
                    "always",
                    "-p",
                    "5678:5678",
                    "-e",
                    "N8N_PORT=5678",
                    "-e",
                    "N8N_HOST=0.0.0.0",
                    "-e",
                    "N8N_PROTOCOL=http",
                    "docker.io/n8nio/n8n:latest",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                print("   [OK] n8n utworzony")
            else:
                print(f"   [WARN] n8n: {result.stderr[:100]}")
        except Exception as e:
            print(f"   [ERR] n8n: {e}")
    else:
        print("   [SKIP] n8n już istnieje")


def start_containers():
    print("\n   Uruchamianie kontenerów Podman...")

    # Uruchom Pod z Nextcloud i PostgreSQL
    pod_ok = start_pod()
    if not pod_ok:
        print("   [WARN] Pod nie został uruchomiony poprawnie")

    # Utwórz standalone kontenery jeśli nie istnieją
    create_standalone_containers()

    # Uruchom standalone kontenery
    for name in CONTAINERS_STANDALONE:
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
            "KLIMTECH_EMBEDDING_DEVICE": "cpu",
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
    print("   KlimtechRAG v7.4 (HTTPS)")
    print("=" * 65)
    print(f"   Baza: {BASE_DIR}   IP: {LOCAL_IP}")

    cleanup_podman()  # Czyść stare overlay layers przed startem
    start_containers()
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
