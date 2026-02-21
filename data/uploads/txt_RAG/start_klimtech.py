#!/usr/bin/env python3
"""
KlimtechRAG - Automatyczny starter modeli LLM z optymalizacją parametrów
Dla karty AMD Instinct 16GB

Autor: KlimtechRAG Team
Wersja: 6.0 - Automatyczne obliczanie parametrów VRAM
"""

import subprocess
import os
import time
import signal
import sys
import glob
import fcntl
import math

# --- KONFIGURACJA SPRZĘTOWA ---
VRAM_TOTAL_GB = 16.0              # AMD Instinct 16GB
SAFE_VRAM_LIMIT_GB = 15.0         # Bezpieczny limit (zapas na system/sterownik)
THREADS = 32                      # Ilość wątków CPU

# Parametry docelowe
TARGET_CONTEXT = 98304            # Cel kontekstu (~96k tokenów)
DEFAULT_BATCH = 512
DEFAULT_N_PREDICT = 2048

# Ścieżki
BASE_DIR = os.path.expanduser("~/KlimtechRAG")
BACKEND_DIR = os.path.join(BASE_DIR, "backend_app")
LLAMA_DIR = os.path.join(BASE_DIR, "llama.cpp")
ENV_FILE = os.path.join(BASE_DIR, ".env")
PYTHON_VENV = os.path.join(BASE_DIR, "venv", "bin", "python")
CONTAINERS = ["qdrant", "nextcloud", "postgres_nextcloud", "n8n"]

# Globalna lista procesów
PROCESSES = []


def get_file_size_gb(filepath):
    """Zwraca rozmiar pliku w GB."""
    size_bytes = os.path.getsize(filepath)
    return size_bytes / (1024 ** 3)


def estimate_model_layers(model_size_gb, context_size):
    """
    Szacuje optymalną liczbę warstw do przeniesienia na GPU.
    
    Logika:
    1. Model zajmuje VRAM (wielkość pliku)
    2. Kontekst (KV Cache) zajmuje dodatkowy VRAM
    3. Jeśli Model + Kontekst > VRAM, zmniejszamy -ngl
    
    Zwraca:
        dict: Parametry dla llama-server
    """
    print(f"\n{'='*60}")
    print("   ANALIZA ZASOBÓW VRAM")
    print(f"{'='*60}")
    print(f"📦 Model: {model_size_gb:.2f} GB")
    print(f"🎯 Docelowy kontekst: {context_size} tokenów")
    
    # Szacunkowe zużycie pamięci przez kontekst (KV Cache) w GB
    # Dla kontekstu 96k (98304 tokenów) w formacie F16:
    # - Około 8-10 GB dla modeli 7B-11B
    # - Flash Attention nieco zmniejsza to zapotrzebowanie
    # Heurystyka: ~0.085 GB na 1000 tokenów (bezpieczna wartość)
    context_memory_per_1k = 0.085  # GB na 1000 tokenów
    context_memory_gb = (context_size / 1000) * context_memory_per_1k
    
    # Całkowite zapotrzebowanie na VRAM
    total_vram_needed = model_size_gb + context_memory_gb
    
    print(f"💾 Szacowany KV Cache: {context_memory_gb:.2f} GB")
    print(f"📊 Łączne zapotrzebowanie: {total_vram_needed:.2f} GB")
    print(f"🖥️  Dostępny VRAM: {SAFE_VRAM_LIMIT_GB:.2f} GB")
    print(f"{'='*60}")
    
    params = {
        "ngl": -1,              # Domyślnie wszystkie warstwy na GPU
        "context": context_size,
        "batch": DEFAULT_BATCH,
        "cache_type_k": "f16",  # Domyślny format cache
        "cache_type_v": "f16",
        "strategy": "",
        "vram_used_gb": 0,
        "fits_in_vram": True
    }
    
    # SCENARIUSZ 1: Wszystko mieści się w VRAM
    if total_vram_needed <= SAFE_VRAM_LIMIT_GB:
        params["strategy"] = "✅ PEŁNY GPU - Wszystko w VRAM"
        params["vram_used_gb"] = total_vram_needed
        params["fits_in_vram"] = True
        print(f"\n✅ DECYZJA: Model mieści się w całości w VRAM!")
        print(f"   Strategia: Maksymalna wydajność GPU")
        print(f"   -ngl = -1 (wszystkie warstwy na GPU)")
        
    # SCENARIUSZ 2: Kompresja KV Cache (Q8_0)
    elif total_vram_needed <= SAFE_VRAM_LIMIT_GB * 1.5:
        # Kompresja Q8 zmniejsza KV Cache o ~50%
        compressed_context_gb = context_memory_gb * 0.5
        compressed_total = model_size_gb + compressed_context_gb
        
        if compressed_total <= SAFE_VRAM_LIMIT_GB:
            params["cache_type_k"] = "q8_0"
            params["cache_type_v"] = "q8_0"
            params["strategy"] = "⚡ GPU + KOMPRESJA CACHE (Q8_0)"
            params["vram_used_gb"] = compressed_total
            params["fits_in_vram"] = True
            print(f"\n⚡ DECYZJA: Włączam kompresję KV Cache (Q8_0)")
            print(f"   KV Cache po kompresji: {compressed_context_gb:.2f} GB")
            print(f"   Oszczędność: {context_memory_gb - compressed_context_gb:.2f} GB")
            print(f"   -ngl = -1 (wszystkie warstwy na GPU)")
        else:
            # Przejdź do scenariusza 3
            params = _hybrid_mode(model_size_gb, context_memory_gb, params)
            
    # SCENARIUSZ 3: Tryb hybrydowy (część modelu w RAM)
    else:
        params = _hybrid_mode(model_size_gb, context_memory_gb, params)
    
    return params


def _hybrid_mode(model_size_gb, context_memory_gb, params):
    """
    Oblicza parametry dla trybu hybrydowego (GPU + RAM).
    """
    # Szacujemy ile warstw zostawić na GPU
    # Przyjmujemy średnio 40 warstw dla modeli 7B-11B
    estimated_total_layers = 40
    
    # Ile VRAM mamy dostępne na model?
    vram_for_model = SAFE_VRAM_LIMIT_GB - context_memory_gb * 0.5  # Z kompresją Q8
    
    if vram_for_model < model_size_gb * 0.3:
        # Bardzo mało miejsca - minimalny offload
        ngl = 10
    elif vram_for_model < model_size_gb * 0.5:
        # Umiarkowanie - około połowa warstw na GPU
        ngl = 20
    elif vram_for_model < model_size_gb * 0.75:
        # Większość na GPU
        ngl = 30
    else:
        # Prawie wszystko na GPU
        ngl = 35
    
    params["ngl"] = ngl
    params["cache_type_k"] = "q8_0"
    params["cache_type_v"] = "q8_0"
    params["strategy"] = f"🔄 HYBRYDOWY (GPU {ngl} warstw + RAM)"
    params["fits_in_vram"] = False
    params["vram_used_gb"] = SAFE_VRAM_LIMIT_GB
    
    print(f"\n🔄 DECYZJA: Tryb hybrydowy GPU+RAM")
    print(f"   VRAM wystarcza tylko na {ngl} warstw modelu")
    print(f"   Reszta warstw będzie przetwarzana przez CPU (wolniej)")
    print(f"   Kompresja KV Cache: Q8_0 włączona")
    print(f"   -ngl = {ngl}")
    
    return params


def load_env_file(env_path):
    """Wczytuje zmienne środowiskowe z pliku .env"""
    env_vars = {}
    if not os.path.exists(env_path):
        print(f"⚠️  Brak pliku .env. Używam domyślnych wartości.")
        env_vars["LLAMA_MODELS_DIR"] = "/home/lobo/.cache/llama.cpp"
        env_vars["LLAMA_API_PORT"] = "8082"
        return env_vars
    
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.strip().split("=", 1)
                env_vars[key] = value.strip('"').strip("'")
    return env_vars


def get_available_models(models_dir):
    """Pobiera listę dostępnych modeli GGUF."""
    if not os.path.exists(models_dir):
        print(f"❌ Katalog modeli nie istnieje: {models_dir}")
        sys.exit(1)
    
    models = glob.glob(os.path.join(models_dir, "**", "*.gguf"), recursive=True)
    
    if not models:
        print(f"❌ Nie znaleziono plików .gguf w: {models_dir}")
        sys.exit(1)
    
    models.sort(key=lambda x: os.path.getsize(x), reverse=True)
    return models


def select_user_model(models):
    """Wyświetla listę modeli i pozwala użytkownikowi wybrać jeden."""
    print("\n" + "=" * 70)
    print("   📚 DOSTĘPNE MODELE GGUF")
    print("=" * 70)
    print(f"{'Nr':<4} {'Nazwa modelu':<45} {'Rozmiar':>12}")
    print("-" * 70)
    
    for i, model_path in enumerate(models, 1):
        model_name = os.path.basename(model_path)
        size_gb = get_file_size_gb(model_path)
        
        # Skróć nazwę jeśli za długa
        if len(model_name) > 43:
            model_name = model_name[:40] + "..."
        
        print(f"[{i:<2}] {model_name:<45} {size_gb:>8.2f} GB")
    
    print("=" * 70)
    
    while True:
        try:
            choice = input("\n🎯 Wybierz numer modelu [1-{}]: ".format(len(models)))
            index = int(choice) - 1
            if 0 <= index < len(models):
                selected = models[index]
                print(f"\n✅ Wybrano: {os.path.basename(selected)}")
                return selected
            print(f"❌ Nieprawidłowy numer. Wybierz 1-{len(models)}.")
        except ValueError:
            print("❌ To nie jest liczba. Wpisz numer modelu.")


def start_process(name, command, cwd, env_vars=None, wait_seconds=5):
    """Uruchamia proces i sprawdza czy wystartował poprawnie."""
    print(f"\n🚀 Uruchamianie: {name}...")
    print(f"   📁 Katalog: {cwd}")
    
    process_env = os.environ.copy()
    if env_vars:
        process_env.update(env_vars)
    
    try:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=process_env,
        )
        
        PROCESSES.append(proc)
        
        if wait_seconds > 0:
            print(f"   ⏳ Czekam {wait_seconds}s na inicjalizację...")
            time.sleep(wait_seconds)
        
        if proc.poll() is not None:
            print(f"❌ {name} zakończył się nieoczekiwanie!")
            stdout, stderr = proc.communicate()
            if stderr:
                print(f"   👉 STDERR:\n{stderr.decode('utf-8', errors='ignore')}")
            if stdout:
                print(f"   👉 STDOUT:\n{stdout.decode('utf-8', errors='ignore')}")
            return False
        else:
            print(f"✅ {name} działa (PID: {proc.pid})")
            return True
            
    except Exception as e:
        print(f"❌ Błąd uruchamiania {name}: {e}")
        return False


def restart_podman_containers():
    """Restartuje kontenery podman."""
    print("\n🐳 Uruchamianie kontenerów Podman...")
    for container in CONTAINERS:
        try:
            result = subprocess.run(
                ["podman", "start", container],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"   ✅ {container}")
            else:
                print(f"   ⚠️  {container} - już działa lub nie istnieje")
            time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️  {container}: {e}")
    print("✅ Kontenery gotowe.")


def signal_handler(sig, frame):
    """Obsługuje sygnał CTRL+C."""
    print("\n\n🛑 Zatrzymywanie procesów...")
    for i, proc in enumerate(PROCESSES):
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"   ✅ Zatrzymano proces {i+1}")
        except:
            try:
                proc.kill()
                print(f"   ⚡ Wymuszono zatrzymanie procesu {i+1}")
            except:
                pass
    print("👋 Do widzenia!")
    sys.exit(0)


def make_non_blocking(fd):
    """Ustawia deskryptor pliku na tryb nieblokujący."""
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)


def print_params_summary(params, model_path):
    """Wyświetla podsumowanie parametrów."""
    print("\n" + "=" * 70)
    print("   ⚙️  WYNIKOWE PARAMETRY")
    print("=" * 70)
    print(f"📦 Model: {os.path.basename(model_path)}")
    print(f"📊 Rozmiar: {get_file_size_gb(model_path):.2f} GB")
    print("-" * 70)
    print(f"🎯 Strategia: {params['strategy']}")
    print(f"💾 Zużycie VRAM: {params['vram_used_gb']:.2f} GB / {SAFE_VRAM_LIMIT_GB:.2f} GB")
    print("-" * 70)
    print("   PARAMETRY LLAMA-SERVER:")
    print(f"   -ngl {params['ngl']}")
    print(f"   -c {params['context']}")
    print(f"   -b {params['batch']}")
    print(f"   --flash-attn on")
    print(f"   --n-predict {DEFAULT_N_PREDICT}")
    print(f"   -t {THREADS}")
    print(f"   --cache-type-k {params['cache_type_k']}")
    print(f"   --cache-type-v {params['cache_type_v']}")
    print("=" * 70)


def build_llama_command(llama_binary, model_path, params, port):
    """Buduje komendę uruchomieniową dla llama-server."""
    cmd = [
        llama_binary,
        "-m", model_path,
        "--host", "0.0.0.0",
        "--port", str(port),
        "-ngl", str(params["ngl"]),
        "-c", str(params["context"]),
        "-b", str(params["batch"]),
        "-t", str(THREADS),
        "--flash-attn", "on",
        "--n-predict", str(DEFAULT_N_PREDICT),
        "--cache-type-k", params["cache_type_k"],
        "--cache-type-v", params["cache_type_v"],
        "--repeat-penalty", "1.2",
        "--temp", "0.2",
    ]
    return cmd


def main():
    """Główna funkcja programu."""
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wczytaj konfigurację
    config = load_env_file(ENV_FILE)
    models_dir = config.get("LLAMA_MODELS_DIR", "/home/lobo/.cache/llama.cpp")
    port = config.get("LLAMA_API_PORT", "8082")
    
    print("\n" + "=" * 70)
    print("   🤖 KlimtechRAG v6.0 - Automatyczna Optymalizacja VRAM")
    print("   Karta: AMD Instinct 16GB")
    print("=" * 70)
    
    # Pobierz i wyświetl modele
    models = get_available_models(models_dir)
    selected_model = select_user_model(models)
    
    # Oblicz parametry na podstawie rozmiaru modelu
    model_size_gb = get_file_size_gb(selected_model)
    params = estimate_model_layers(model_size_gb, TARGET_CONTEXT)
    
    # Wyświetl podsumowanie
    print_params_summary(params, selected_model)
    
    # Potwierdzenie od użytkownika
    print("\n❓ Czy chcesz uruchomić model z tymi parametrami? [T/n]: ", end="")
    try:
        confirm = input().strip().lower()
        if confirm in ['n', 'nie', 'no']:
            print("👋 Anulowano.")
            sys.exit(0)
    except:
        pass
    
    # Zmienne środowiskowe dla AMD ROCm
    amd_env = {
        "HIP_VISIBLE_DEVICES": "0",
        "GPU_MAX_ALLOC_PERCENT": "100",
        "HSA_ENABLE_SDMA": "0",
    }
    
    # Znajdź binarkę llama-server
    llama_binary = os.path.join(LLAMA_DIR, "build", "bin", "llama-server")
    if not os.path.exists(llama_binary):
        llama_binary = os.path.join(LLAMA_DIR, "llama-server")
    
    if not os.path.exists(llama_binary):
        print(f"❌ Nie znaleziono llama-server w: {LLAMA_DIR}")
        sys.exit(1)
    
    # Zbuduj komendę
    llama_cmd = build_llama_command(llama_binary, selected_model, params, port)
    
    print(f"\n{' '.join(llama_cmd[:8])}...")
    
    # Uruchom LLM server
    if not start_process("LLM Server", llama_cmd, LLAMA_DIR, env_vars=amd_env):
        print("\n⛔ Nie udało się uruchomić LLM Server.")
        sys.exit(1)
    
    # Uruchom kontenery
    restart_podman_containers()
    time.sleep(2)
    
    # Uruchom backend (opcjonalnie)
    if os.path.exists(PYTHON_VENV):
        backend_cmd = [PYTHON_VENV, "-m", "backend_app.main"]
        if not start_process("Backend (FastAPI)", backend_cmd, BASE_DIR, wait_seconds=3):
            print("⚠️  Backend nie wystartował, ale LLM działa.")
    
    # Uruchom watchdog (opcjonalnie)
    watchdog_path = os.path.join(BASE_DIR, "watch_nextcloud.py")
    if os.path.exists(watchdog_path) and os.path.exists(PYTHON_VENV):
        watchdog_cmd = [PYTHON_VENV, "watch_nextcloud.py"]
        subprocess.Popen(
            watchdog_cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        print("✅ Watchdog uruchomiony.")
    
    # Wyświetl informacje końcowe
    print("\n" + "=" * 70)
    print("   🎉 SYSTEM KLIMTECHRAG GOTOWY!")
    print("=" * 70)
    print(f"📡 API LLM:     http://localhost:{port}")
    print(f"📡 API Backend: http://localhost:8000")
    print(f"📊 Strategia:   {params['strategy']}")
    print("=" * 70)
    print("👂 Nasłuchiwanie logów (CTRL+C by przerwać)...\n")
    
    # Monitorowanie logów
    try:
        if len(PROCESSES) >= 1:
            llm_proc = PROCESSES[0]
            make_non_blocking(llm_proc.stdout)
            make_non_blocking(llm_proc.stderr)
        
        if len(PROCESSES) >= 2:
            backend_proc = PROCESSES[1]
            make_non_blocking(backend_proc.stdout)
            make_non_blocking(backend_proc.stderr)
        
        while True:
            # Sprawdź LLM process
            if len(PROCESSES) >= 1:
                llm_proc = PROCESSES[0]
                
                if llm_proc.poll() is not None:
                    print(f"\n❌ LLM zakończył się (kod: {llm_proc.returncode})")
                    break
                
                try:
                    chunk = llm_proc.stdout.read(4096)
                    if chunk:
                        for line in chunk.decode("utf-8", errors="ignore").splitlines():
                            print(f"[LLM] {line}")
                except:
                    pass
                
                try:
                    chunk = llm_proc.stderr.read(4096)
                    if chunk:
                        for line in chunk.decode("utf-8", errors="ignore").splitlines():
                            print(f"[LLM] ERR: {line}")
                except:
                    pass
            
            # Sprawdź Backend process
            if len(PROCESSES) >= 2:
                backend_proc = PROCESSES[1]
                
                if backend_proc.poll() is not None:
                    print(f"\n⚠️  Backend zakończył się (kod: {backend_proc.returncode})")
                
                try:
                    chunk = backend_proc.stdout.read(4096)
                    if chunk:
                        for line in chunk.decode("utf-8", errors="ignore").splitlines():
                            print(f"[BACKEND] {line}")
                except:
                    pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
