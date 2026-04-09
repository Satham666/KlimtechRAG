#!/bin/bash
# KlimtechRAG — wrapper startowy backendu
# Używany przez systemd unit klimtech-backend.service

set -e

BASE_DIR="/home/lobo/KlimtechRAG"
VENV_UVICORN="$BASE_DIR/venv/bin/uvicorn"
ENV_FILE="$BASE_DIR/.env"

cd "$BASE_DIR"

# Wczytaj zmienne z .env (pominięcie pustych linii i komentarzy)
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$')
    set +a
fi

exec "$VENV_UVICORN" backend_app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info \
    --no-access-log
