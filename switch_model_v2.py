#!/usr/bin/env python3
"""
switch_model.py — Przełączanie modeli LLM ↔ VLM
===============================================

Ten skrypt służy do przełączania między modelami z poziomu backendu/UI.
Można go wywołać przez:
- API endpoint: POST /switch_model?type=llm lub type=vlm
- Bezpośrednio: python switch_model.py --type llm

Wymaga zapisanego pliku models_config.json z informacjami o wybranych modelach.
"""
import subprocess
import os
import sys
import json
import time
import argparse

# ---------------------------------------------------------------------------
# KONFIGURACJA
# ---------------------------------------------------------------------------

BASE_DIR = "/media/lobo/BACKUP/KlimtechRAG"
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LLM_COMMAND_FILE = os.path.join(LOG_DIR, "llm_command.txt")
MODELS_CONFIG_FILE = os.path.join(LOG_DIR, "models_config.json")

LLAMA_PORT = "8082"

# ---------------------------------------------------------------------------
# FUNKCJE
# ---------------------------------------------------------------------------

def load_models_config():
    """Wczytuje konfigurację wybranych modeli."""
    if not os.path.exists(MODELS_CONFIG_FILE):
        print(f"❌ Brak pliku konfiguracyjnego: {MODELS_CONFIG_FILE}")
        print("   Uruchom najpierw start_klimtech_v3.py")
        return None
    
    with open(MODELS_CONFIG_FILE, "r") as f:
        return json.load(f)


def stop_llm_server():
    """Zatrzymuje serwer LLM/VLM."""
    print("   🛑 Zatrzymuję serwer LLM/VLM...")
    
    # Zabij przez pkill
    subprocess.run(["pkill", "-f", "llama-server"], capture_output=True)
    subprocess.run(["pkill", "-f", "llama-cli"], capture_output=True)
    
    # Zabij port
    try:
        subprocess.run(["fuser", "-k", f"{LLAMA_PORT}/tcp"], capture_output=True, timeout=5)
    except Exception:
        pass
    
    time.sleep(3)
    print("   ✅ VRAM zwolniony")


def start_llm_server(model_path: str, model_type: str = "llm") -> bool:
    """Uruchamia serwer LLM lub VLM."""
    model_label = "VLM (Vision)" if model_type == "vlm" else "LLM (Czat)"
    print(f"\n   🚀 Uruchamianie {model_label}...")
    print(f"   Model: {os.path.basename(model_path)}")
    
    # AMD GPU env
    amd_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "GPU_MAX_ALLOC_PERCENT": "100",
        "HSA_ENABLE_SDMA": "0",
        "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
    }
    
    # Znajdź binarkę llama-server
    llama_binary = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
    if not os.path.exists(llama_binary):
        llama_binary = os.path.join(LLAMA_DIR, "llama-server")
    
    if not os.path.exists(llama_binary):
        print(f"   ❌ Nie znaleziono llama-server: {llama_binary}")
        return False
    
    # Parametry modelu
    llama_cmd = [
        llama_binary, "-m", model_path,
        "--host", "0.0.0.0",
        "--port", LLAMA_PORT,
        "-ngl", "99",
        "-c", "8192",
    ]
    
    # Dla VLM dodaj specjalne flagi
    if model_type == "vlm":
        model_dir = os.path.dirname(model_path)
        mmproj_files = []
        for f in os.listdir(model_dir):
            if "mmproj" in f.lower():
                mmproj_files.append(os.path.join(model_dir, f))
        
        if mmproj_files:
            llama_cmd.extend(["--mmproj", mmproj_files[0]])
            print(f"   📷 Znaleziono mmproj: {os.path.basename(mmproj_files[0])}")
        else:
            print("   ⚠️  Nie znaleziono mmproj - VLM może nie działać poprawnie")
    
    # Zapisz komendę do pliku
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LLM_COMMAND_FILE, "w") as f:
        json.dump({
            "command": llama_cmd, 
            "cwd": LLAMA_DIR, 
            "env_vars": amd_env,
            "model_type": model_type,
            "model_path": model_path
        }, f, indent=2)
    
    # Uruchom proces
    process_env = os.environ.copy()
    process_env.update(amd_env)
    
    try:
        log_stdout = open(os.path.join(LOG_DIR, "llm_server_stdout.log"), "a")
        log_stderr = open(os.path.join(LOG_DIR, "llm_server_stderr.log"), "a")
        
        proc = subprocess.Popen(
            llama_cmd,
            cwd=LLAMA_DIR,
            stdout=log_stdout,
            stderr=log_stderr,
            start_new_session=True,
            env=process_env,
        )
        
        print("   ⏳ Czekam 15s na załadowanie modelu...")
        time.sleep(15)
        
        if proc.poll() is not None:
            print(f"   ❌ Serwer padł przy starcie! Kod: {proc.returncode}")
            return False
        
        print(f"   ✅ {model_label} Server działa (PID: {proc.pid})")
        
        # Zapisz PID
        with open(os.path.join(LOG_DIR, "llm_server.pid"), "w") as f:
            f.write(str(proc.pid))
        
        return True
        
    except Exception as e:
        print(f"   ❌ Błąd startu serwera: {e}")
        return False


def switch_to_llm():
    """Przełącza na model LLM (do czatu)."""
    config = load_models_config()
    if not config:
        return False
    
    llm_model = config.get("llm_model")
    if not llm_model:
        print("❌ Brak skonfigurowanego modelu LLM")
        return False
    
    print(f"\n{'='*60}")
    print("   🔄 PRZEŁĄCZANIE NA LLM (CZAT)")
    print("="*60)
    print(f"   Model: {os.path.basename(llm_model)}")
    
    stop_llm_server()
    success = start_llm_server(llm_model, "llm")
    
    if success:
        # Aktualizuj status
        config["current_model_type"] = "llm"
        config["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(MODELS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Przełączono na LLM: {os.path.basename(llm_model)}")
    
    return success


def switch_to_vlm():
    """Przełącza na model VLM (do obrazków)."""
    config = load_models_config()
    if not config:
        return False
    
    vlm_model = config.get("vlm_model")
    if not vlm_model:
        print("❌ Brak skonfigurowanego modelu VLM")
        return False
    
    print(f"\n{'='*60}")
    print("   🔄 PRZEŁĄCZANIE NA VLM (VISION)")
    print("="*60)
    print(f"   Model: {os.path.basename(vlm_model)}")
    
    stop_llm_server()
    success = start_llm_server(vlm_model, "vlm")
    
    if success:
        # Aktualizuj status
        config["current_model_type"] = "vlm"
        config["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(MODELS_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Przełączono na VLM: {os.path.basename(vlm_model)}")
    
    return success


def get_current_model():
    """Zwraca aktualnie uruchomiony model."""
    config = load_models_config()
    if config:
        return config.get("current_model_type", "unknown")
    return "unknown"


def show_status():
    """Wyświetla status modeli."""
    config = load_models_config()
    
    print("\n" + "="*60)
    print("   📊 STATUS MODELÓW")
    print("="*60)
    
    if config:
        print(f"   Aktualny typ: {config.get('current_model_type', 'nieznany').upper()}")
        print(f"   LLM: {os.path.basename(config.get('llm_model', 'brak'))}")
        print(f"   VLM: {os.path.basename(config.get('vlm_model', 'brak'))}")
        print(f"   Ostatnia zmiana: {config.get('timestamp', 'nieznana')}")
    else:
        print("   Brak konfiguracji")
    
    print("="*60)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Przełączanie modeli LLM ↔ VLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  python switch_model.py --type llm    # Przełącz na model do czatu
  python switch_model.py --type vlm    # Przełącz na model do obrazków
  python switch_model.py --status      # Pokaż aktualny model
  python switch_model.py -t llm        # Krótka wersja
        """
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["llm", "vlm"],
        help="Typ modelu do uruchomienia"
    )
    
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Pokaż aktualny model"
    )
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if not args.type:
        parser.print_help()
        print("\n")
        show_status()
        return
    
    if args.type == "llm":
        success = switch_to_llm()
        sys.exit(0 if success else 1)
    elif args.type == "vlm":
        success = switch_to_vlm()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
