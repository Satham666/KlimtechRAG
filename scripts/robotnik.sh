#!/usr/bin/env bash
# Robotnik CLI — Złota Komenda v1.0 dla Qwen2.5-Coder-3B-Q8_0 na Quadro P1000
# Użycie: ./scripts/robotnik.sh <prompt_file>
# Parametry ustalono eksperymentalnie (GPU_LAPTOPT_TEST.md):
#   Prompt: 286 t/s, Generation: 14.1 t/s, EOS natural, bez OOM
set -euo pipefail

PROMPT_FILE="${1:?Usage: $0 <prompt_file>}"

if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "Error: prompt file not found: $PROMPT_FILE" >&2
    exit 1
fi

LLAMA_CLI="${LLAMA_CLI:-/home/tamiel/programy/llama.cpp/build/bin/llama-cli}"
MODEL="${ROBOTNIK_MODEL:-/home/tamiel/.cache/llama.cpp/lmstudio-community_Qwen2.5-Coder-3B-GGUF_Qwen2.5-Coder-3B-Q8_0.gguf}"

exec "$LLAMA_CLI" -m "$MODEL" -c 4096 -n -1 -b 64 -ngl 99 -t 8 -tb 12 -fa on -ctk q8_0 -ctv q8_0 --temp 0.6 --top-k 40 --top-p 0.9 --repeat-penalty 1.1 -f "$PROMPT_FILE"
