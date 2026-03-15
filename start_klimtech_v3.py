#!/usr/bin/env python3
"""
KlimtechRAG v7.0 — Start Script
=================================
Uruchamia TYLKO:
  ✅ kontenery Podman (qdrant, nextcloud, postgres_nextcloud, n8n)
  ✅ Backend FastAPI

Modele LLM/VLM → uruchamiane z panelu UI
"""
import subprocess, os, time, signal, sys

# ─── KONFIGURACJA ───────────────────────────────────────────────────
BASE_DIR     = "/media/lobo/BACKUP/KlimtechRAG"
LOG_DIR      = os.path.join(BASE_DIR, "logs")
PYTHON_VENV  = "/media/lobo/BACKUP/KlimtechRAG/venv/bin/python3"
INTERFACE    = "enp9s0"
BACKEND_PORT = "8000"
QDRANT_PORT  = "6333"
CONTAINERS   = ["qdrant", "nextcloud", "postgres_nextcloud", "n8n"]
PROCESSES    = []

def get_ip(iface=INTERFACE):
    try:
        out = subprocess.check_output(["ip","-4","addr","show",iface],text=True,stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            line=line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    print(f"⚠️  Nie można pobrać IP z {iface} — używam localhost")
    return "localhost"

LOCAL_IP = get_ip()

def start_containers(containers):
    print("\n🐳 Uruchamianie kontenerów Podman...")
    for name in containers:
        try:
            r = subprocess.run(["podman","start",name],capture_output=True,text=True,timeout=30)
            print(f"   {'✅' if r.returncode==0 else '⚪'} {name}" + (f": {r.stderr.strip()[:80]}" if r.returncode!=0 else ""))
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  {name}: timeout")
        except Exception as e:
            print(f"   ⚠️  {name}: {e}")
        time.sleep(0.4)

def start_backend():
    print("\n🚀 Uruchamianie: Backend FastAPI...")
    os.makedirs(LOG_DIR, exist_ok=True)
    cmd = [PYTHON_VENV, "-m", "backend_app.main"]
    env = os.environ.copy()
    env.update({"HIP_VISIBLE_DEVICES":"0","HSA_OVERRIDE_GFX_VERSION":"9.0.6",
                "KLIMTECH_EMBEDDING_DEVICE":"cuda:0","KLIMTECH_BASE_PATH":BASE_DIR})
    log_out = open(os.path.join(LOG_DIR,"backend_stdout.log"),"a")
    log_err = open(os.path.join(LOG_DIR,"backend_stderr.log"),"a")
    proc = subprocess.Popen(cmd,cwd=BASE_DIR,stdout=log_out,stderr=log_err,start_new_session=True,env=env)
    PROCESSES.append(proc)
    print("   ⏳ Czekam 5s na inicjalizację...")
    time.sleep(5)
    if proc.poll() is not None:
        print("   ❌ Backend padł! Sprawdź logs/backend_stderr.log")
        return False
    print(f"   ✅ Backend FastAPI działa (PID: {proc.pid})")
    return True

def signal_handler(sig,frame):
    print("\n🛑 Zatrzymywanie procesów...")
    for proc in PROCESSES:
        try: proc.terminate(); proc.wait(timeout=3)
        except subprocess.TimeoutExpired: proc.kill()
        except Exception: pass
    print("👋 Do widzenia!")
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT,signal_handler)
    os.makedirs(LOG_DIR,exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR,"data","uploads"),exist_ok=True)

    print("\n"+"="*65)
    print("   KlimtechRAG v7.0")
    print("="*65)
    print(f"   Baza: {BASE_DIR}   IP: {LOCAL_IP}")

    start_containers(CONTAINERS)
    time.sleep(2)

    if not start_backend():
        sys.exit(1)

    # Wyczyść stary progress log przy każdym starcie
    progress_log = os.path.join(LOG_DIR,"llm_progress.log")
    try:
        if os.path.exists(progress_log): os.remove(progress_log)
    except Exception: pass

    print("\n"+"="*65)
    print("🎉 KlimtechRAG gotowy!")
    print("="*65)
    print(f"   🔧 API Backend:    http://{LOCAL_IP}:{BACKEND_PORT}")
    print(f"   📦 Qdrant:         http://{LOCAL_IP}:{QDRANT_PORT}")
    print(f"   💡 UI:             http://{LOCAL_IP}:{BACKEND_PORT}")
    print("   💡 Modele LLM/VLM → z panelu UI")
    print("   CTRL+C aby zatrzymać")
    print("="*65)

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None,None)

if __name__=="__main__":
    main()
