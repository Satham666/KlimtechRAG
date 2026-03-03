#!/bin/bash
cd /home/lobo/KlimtechRAG
source venv/bin/activate

export HIP_VISIBLE_DEVICES=0
export HSA_OVERRIDE_GFX_VERSION=9.0.6
export KLIMTECH_EMBEDDING_DEVICE=cuda:0

exec python -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000
pkill -f "uvicorn backend_app" 2>/dev/null; fuser -k 8000/tcp 2>/dev/null; sleep 2; ss -tlnp | grep 8000 || echo "Port 8000 wolny"