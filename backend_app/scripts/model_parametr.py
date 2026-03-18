#!/usr/bin/env python3
"""
model_parametr.py - Obliczanie optymalnych parametrów dla llama-server
na podstawie rozmiaru modelu i dostępnego VRAM.

Dla karty AMD Instinct 16GB
"""

import os
import subprocess
import glob

DEFAULT_MODELS_DIR = os.path.expanduser("~/.cache/llama.cpp")
VRAM_TOTAL_GB = 16.0
SAFE_VRAM_LIMIT_GB = 14.0
SAFE_VRAM_OVERHEAD_GB = 0.5
THREADS = 32

CONTEXT_LEVELS = [98304, 81920, 65536, 49152, 32768, 16384, 8192, 4096]
DEFAULT_BATCH = 512
DEFAULT_N_PREDICT = 4096
DEFAULT_TEMP = 0.3
DEFAULT_REPEAT_PENALTY = 1.1

KV_CACHE_PER_1K_TOKENS_F16_GB = 0.008
KV_CACHE_PER_1K_TOKENS_Q8_GB = 0.004


def get_file_size_gb(filepath):
    """Zwraca rozmiar pliku w GB."""
    size_bytes = os.path.getsize(filepath)
    return size_bytes / (1024**3)


def estimate_model_layers(model_path):
    """
    Szacuje liczbę warstw modelu na podstawie rozmiaru pliku.

    Zasady empiryczne:
    - ~7B params: ~32-36 warstw, ~0.22 GB/layer (Q5_K)
    - ~11B params: ~40-50 warstw, ~0.15 GB/layer (Q5_K)
    - ~2.6B params: ~32 warstw, ~0.15 GB/layer (F16)
    """
    model_size_gb = get_file_size_gb(model_path)

    if model_size_gb > 6.0:
        estimated_layers = 50
    elif model_size_gb > 4.0:
        estimated_layers = 40
    elif model_size_gb > 2.0:
        estimated_layers = 32
    else:
        estimated_layers = 24

    return estimated_layers


def estimate_kv_cache_size(context_tokens, num_layers=32):
    """
    Szacuje rozmiar KV cache na podstawie kontekstu i liczby warstw.

    Obliczone z logów dla Bielik-11B (50 warstw):
    - 19200 MiB dla 98304 tokenów = 3.8 MB na 1k tokenów na warstwę (F16)
    - Dla Q8: ~50% mniej = 1.9 MB na 1k tokenów na warstwę

    Dla 50 warstw, 32k kontekstu: ~6 GB F16, ~3 GB Q8
    Dla 50 warstw, 65k kontekstu: ~12 GB F16, ~6 GB Q8
    """
    context_k = context_tokens / 1000.0

    kv_per_layer_f16_mb = 3.8
    kv_per_layer_q8_mb = 1.9

    kv_cache_f16_gb = (context_k * kv_per_layer_f16_mb * num_layers) / 1024
    kv_cache_q8_gb = (context_k * kv_per_layer_q8_mb * num_layers) / 1024

    return kv_cache_f16_gb, kv_cache_q8_gb


def get_real_vram_usage():
    """Próbuje pobrać aktualne zużycie VRAM przez rocm-smi (GPU 0 = Instinct)."""
    try:
        result = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--csv"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            # Format CSV: device,VRAM Total Memory (B),VRAM Total Used Memory (B)
            lines = [l for l in result.stdout.strip().split("\n") if l and not l.startswith("WARNING")]
            for line in lines[1:]:  # skip header
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3 and "card0" in parts[0]:
                    vram_total = float(parts[1]) / (1024**3)
                    vram_used = float(parts[2]) / (1024**3)
                    return vram_used, vram_total
    except Exception:
        pass
    return 0.0, VRAM_TOTAL_GB


def get_available_models(models_dir):
    """Zwraca listę dostępnych modeli GGUF w katalogu."""
    if not os.path.exists(models_dir):
        return []
    models = glob.glob(os.path.join(models_dir, "**", "*.gguf"), recursive=True)
    models.sort(key=lambda x: os.path.getsize(x), reverse=True)
    return models


def calculate_params(model_path):
    """
    Oblicza optymalne parametry dla llama-server na podstawie rozmiaru modelu.

    Zwraca string z argumentami dla llama-server.
    """
    model_size_gb = get_file_size_gb(model_path)
    num_layers = estimate_model_layers(model_path)

    current_vram_used, current_vram_total = get_real_vram_usage()
    available_vram = current_vram_total - current_vram_used - SAFE_VRAM_OVERHEAD_GB
    available_vram = max(available_vram, 2.0)  # minimum 2 GB zeby w ogole cos uruchomic

    print(f"\n{'=' * 60}")
    print("   ANALIZA ZASOBÓW VRAM")
    print(f"{'=' * 60}")
    print(f"📦 Model: {os.path.basename(model_path)}")
    print(f"📊 Rozmiar modelu: {model_size_gb:.2f} GB")
    print(f"📊 Szacowana liczba warstw: {num_layers}")
    print(f"🖥️  Całkowity VRAM: {current_vram_total:.1f} GB")
    print(f"📊 Aktualnie używane: {current_vram_used:.2f} GB")
    print(f"✅ Dostępne dla modelu: {available_vram:.2f} GB")
    print(f"{'=' * 60}")

    ngl = -1
    selected_context = None
    use_q8_cache = False

    for context in CONTEXT_LEVELS:
        kv_f16, kv_q8 = estimate_kv_cache_size(context, num_layers)

        total_f16 = model_size_gb + kv_f16 + SAFE_VRAM_OVERHEAD_GB
        total_q8 = model_size_gb + kv_q8 + SAFE_VRAM_OVERHEAD_GB

        print(f"\n🔍 Test kontekstu {context} tokenów:")
        print(f"   KV Cache F16: {kv_f16:.2f} GB")
        print(f"   KV Cache Q8:  {kv_q8:.2f} GB")
        print(f"   Łącznie F16: {total_f16:.2f} GB")
        print(f"   Łącznie Q8:  {total_q8:.2f} GB")

        if total_f16 <= available_vram:
            selected_context = context
            use_q8_cache = False
            print(f"   ✅ MIEŚCI SIĘ bez kompresji!")
            break
        elif total_q8 <= available_vram:
            selected_context = context
            use_q8_cache = True
            print(f"   ⚡ MIEŚCI SIĘ z Q8 cache!")
            break
        else:
            print(f"   ❌ Za dużo VRAM potrzebne")

    if selected_context is None:
        kv_f16_min, kv_q8_min = estimate_kv_cache_size(CONTEXT_LEVELS[-1], num_layers)
        vram_for_model = available_vram - kv_q8_min - SAFE_VRAM_OVERHEAD_GB
        ratio = vram_for_model / model_size_gb

        if ratio < 0.2:
            ngl = 5
            print(f"\n⚠️  Tryb CPU-dominant (model za duży)")
        elif ratio < 0.4:
            ngl = 10
        elif ratio < 0.6:
            ngl = 20
        elif ratio < 0.8:
            ngl = 30
        else:
            ngl = 40

        selected_context = CONTEXT_LEVELS[-1]
        use_q8_cache = True
        print(f"\n🔄 Tryb hybrydowy GPU+RAM (-ngl = {ngl})")

    args = f"-ngl {ngl} -c {selected_context} -b {DEFAULT_BATCH} -t {THREADS} --flash-attn on --n-predict {DEFAULT_N_PREDICT}"

    if use_q8_cache:
        args += " --cache-type-k q8_0 --cache-type-v q8_0"

    args += f" --repeat-penalty {DEFAULT_REPEAT_PENALTY} --temp {DEFAULT_TEMP}"

    print(f"\n{'=' * 60}")
    print("📋 WYBRANE PARAMETRY:")
    print(f"   Kontekst: {selected_context} tokenów")
    print(f"   Warstwy GPU: {'wszystkie' if ngl == -1 else ngl}")
    print(f"   Kompresja cache: {'Q8_0' if use_q8_cache else 'brak (F16)'}")
    print(f"\n   {args}")
    print(f"{'=' * 60}\n")

    return args


if __name__ == "__main__":
    import sys

    models_dir = DEFAULT_MODELS_DIR
    if len(sys.argv) > 2:
        models_dir = os.path.expanduser(sys.argv[2])
    elif len(sys.argv) > 1:
        arg = os.path.expanduser(sys.argv[1])
        if os.path.isdir(arg):
            models_dir = arg
        elif os.path.exists(arg):
            calculate_params(arg)
            sys.exit(0)
        else:
            print(f"❌ Nie znaleziono: {arg}")
            sys.exit(1)

    models = get_available_models(models_dir)
    if not models:
        print(f"❌ Brak modeli .gguf w: {models_dir}")
        sys.exit(1)

    print(f"\n📁 Katalog modeli: {models_dir}")
    print(f"📋 Znalezione modele ({len(models)}):\n")

    for i, model_path in enumerate(models, 1):
        size_gb = get_file_size_gb(model_path)
        name = os.path.basename(model_path)
        print(f"  [{i:2d}] {name} ({size_gb:.2f} GB)")

    print()
    try:
        choice = input("Wybierz numer modelu (lub wpisz ścieżkę): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
            else:
                print("❌ Nieprawidłowy numer")
                sys.exit(1)
        else:
            selected = os.path.expanduser(choice)
            if not os.path.exists(selected):
                print(f"❌ Plik nie istnieje: {selected}")
                sys.exit(1)

        calculate_params(selected)
    except KeyboardInterrupt:
        print("\n⛔ Anulowano")
        sys.exit(1)
