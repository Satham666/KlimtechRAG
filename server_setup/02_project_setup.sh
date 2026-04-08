#!/bin/bash
# =============================================================================
# KlimtechRAG — Faza 2: Konfiguracja projektu
# =============================================================================
# Uruchom PO migracji danych (03_data_migrate.sh) lub gdy dane już są w miejscu:
#   bash 02_project_setup.sh
#
# Co robi:
#   1. Clone repo z GitHub (lub pull jeśli istnieje)
#   2. Python venv + pip install
#   3. Generowanie certyfikatu SSL
#   4. Konfiguracja nginx (HTTPS na 8443/8444/5679/6334)
#   5. Pull obrazów Podman
#   6. Plik .env (jeśli nie ma)
#   7. Test uruchomienia backendu
# =============================================================================

set -euo pipefail

# ── Zmienne ──────────────────────────────────────────────────────────────────
USERNAME="lobo"
NEW_BASE="/home/lobo/KlimtechRAG"
GITHUB_REPO="git@github.com:Satham666/KlimtechRAG.git"
VENV="$NEW_BASE/venv"
CERTS_DIR="$NEW_BASE/data/ssl"
LOG="$HOME/install_phase2.log"

# Sieć — sprawdź interfejs po instalacji serwera (może być inna nazwa niż enp9s0)
# ip link show — żeby sprawdzić aktualną nazwę interfejsu
INTERFACE="${KLIMTECH_IFACE:-enp9s0}"

# ── Kolory ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $1" | tee -a "$LOG"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG"; }
fail() { echo -e "${RED}[FAIL]${NC} $1" | tee -a "$LOG"; exit 1; }
section() { echo "" | tee -a "$LOG"; echo "══════════════════════════════════════" | tee -a "$LOG"; echo "  $1" | tee -a "$LOG"; echo "══════════════════════════════════════" | tee -a "$LOG"; }

echo "KlimtechRAG — Faza 2 — $(date '+%Y-%m-%d %H:%M:%S')" | tee "$LOG"

# Pobierz aktualne IP serwera
SERVER_IP=$(ip -4 addr show "$INTERFACE" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || echo "192.168.31.70")
echo "  IP serwera: $SERVER_IP (interfejs: $INTERFACE)" | tee -a "$LOG"
echo "  Jeśli IP jest błędne, uruchom: KLIMTECH_IFACE=eth0 bash 02_project_setup.sh" | tee -a "$LOG"

# =============================================================================
section "1. Clone / Pull repozytorium"
# =============================================================================
if [ -d "$NEW_BASE/.git" ]; then
    warn "Repo już istnieje — git pull"
    cd "$NEW_BASE"
    git pull 2>&1 | tee -a "$LOG"
    ok "Repo zaktualizowane"
else
    echo "Klonowanie z GitHub..." | tee -a "$LOG"
    # Sprawdź czy SSH key jest skonfigurowany
    if ! ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        warn "SSH key dla GitHub nie jest skonfigurowany lub brak połączenia"
        warn "Próbuję HTTPS jako fallback..."
        GITHUB_REPO_HTTPS="https://github.com/Satham666/KlimtechRAG.git"
        git clone "$GITHUB_REPO_HTTPS" "$NEW_BASE" 2>&1 | tee -a "$LOG" || \
            fail "Nie można sklonować repo. Skonfiguruj SSH key: ssh-keygen && cat ~/.ssh/id_rsa.pub → GitHub Settings → SSH keys"
    else
        git clone "$GITHUB_REPO" "$NEW_BASE" 2>&1 | tee -a "$LOG"
    fi
    ok "Repo sklonowane do $NEW_BASE"
fi

cd "$NEW_BASE"

# =============================================================================
section "2. Python virtualenv + pip install"
# =============================================================================
if [ ! -d "$VENV" ]; then
    echo "Tworzenie venv..." | tee -a "$LOG"
    python3 -m venv "$VENV" 2>&1 | tee -a "$LOG"
fi

source "$VENV/bin/activate"
pip install --upgrade pip 2>&1 | tee -a "$LOG"

# Znajdź requirements.txt
if [ -f "$NEW_BASE/requirements.txt" ]; then
    pip install -r "$NEW_BASE/requirements.txt" 2>&1 | tee -a "$LOG"
    ok "requirements.txt zainstalowany"
else
    # Zainstaluj znane pakiety projektu
    warn "Brak requirements.txt — instaluję podstawowe pakiety projektu"
    pip install \
        fastapi uvicorn[standard] \
        pydantic pydantic-settings \
        qdrant-client \
        sentence-transformers \
        openai \
        pypdf python-docx python-magic \
        pillow \
        colpali-engine \
        haystack-ai \
        httpx aiofiles \
        python-multipart \
        2>&1 | tee -a "$LOG"
    ok "Podstawowe pakiety zainstalowane"
fi

deactivate

# =============================================================================
section "3. Certyfikat SSL (self-signed)"
# =============================================================================
mkdir -p "$CERTS_DIR"

if [ -f "$CERTS_DIR/server.crt" ] && [ -f "$CERTS_DIR/server.key" ]; then
    warn "Certyfikat SSL już istnieje — pomijam"
else
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$CERTS_DIR/server.key" \
        -out "$CERTS_DIR/server.crt" \
        -subj "/CN=klimtech-server/O=Klimtech/C=PL" \
        -addext "subjectAltName=IP:$SERVER_IP,IP:127.0.0.1,DNS:localhost" \
        2>&1 | tee -a "$LOG"
    ok "Certyfikat SSL wygenerowany (ważny 10 lat)"
fi

# =============================================================================
section "4. Konfiguracja nginx"
# =============================================================================
# Wygeneruj konfigurację nginx (zastępuje stary plik ze starego serwera)
NGINX_CONF="$CERTS_DIR/klimtech-nginx.conf"

cat > "$NGINX_CONF" << NGINXEOF
# KlimtechRAG — nginx reverse proxy (HTTPS)
# Generowany przez 02_project_setup.sh

server {
    listen 8443 ssl;
    server_name $SERVER_IP localhost;

    ssl_certificate     $CERTS_DIR/server.crt;
    ssl_certificate_key $CERTS_DIR/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    client_max_body_size 210M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}

server {
    listen 8444 ssl;
    server_name $SERVER_IP localhost;

    ssl_certificate     $CERTS_DIR/server.crt;
    ssl_certificate_key $CERTS_DIR/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    client_max_body_size 512M;

    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s;
    }
}

server {
    listen 5679 ssl;
    server_name $SERVER_IP localhost;

    ssl_certificate     $CERTS_DIR/server.crt;
    ssl_certificate_key $CERTS_DIR/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 300s;
    }
}

server {
    listen 6334 ssl;
    server_name $SERVER_IP localhost;

    ssl_certificate     $CERTS_DIR/server.crt;
    ssl_certificate_key $CERTS_DIR/server.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:6333;
        proxy_set_header Host \$host;
        proxy_read_timeout 120s;
    }
}
NGINXEOF

ok "Konfiguracja nginx wygenerowana: $NGINX_CONF"

# Zainstaluj konfigurację
sudo cp "$NGINX_CONF" /etc/nginx/sites-available/klimtech
sudo ln -sf /etc/nginx/sites-available/klimtech /etc/nginx/sites-enabled/klimtech

# Usuń domyślną stronę nginx (blokuje port 80/443)
sudo rm -f /etc/nginx/sites-enabled/default

# Test i restart
sudo nginx -t 2>&1 | tee -a "$LOG"
sudo systemctl enable nginx
sudo systemctl restart nginx
ok "nginx uruchomiony z konfiguracją KlimtechRAG"

# =============================================================================
section "5. Pull obrazów Podman"
# =============================================================================
echo "Pobieranie obrazów kontenerów (może chwilę potrwać)..." | tee -a "$LOG"

podman pull docker.io/library/postgres:16 2>&1 | tee -a "$LOG" && ok "postgres:16"
podman pull docker.io/library/nextcloud:32 2>&1 | tee -a "$LOG" && ok "nextcloud:32"
podman pull docker.io/qdrant/qdrant:latest 2>&1 | tee -a "$LOG" && ok "qdrant:latest"
podman pull docker.io/n8nio/n8n:latest 2>&1 | tee -a "$LOG" && ok "n8n:latest"

# =============================================================================
section "6. Plik .env"
# =============================================================================
if [ -f "$NEW_BASE/.env" ]; then
    warn ".env już istnieje (skopiowany przez 03_data_migrate.sh?) — sprawdź ścieżki!"
    grep "KLIMTECH_BASE_PATH" "$NEW_BASE/.env" | tee -a "$LOG"
else
    cat > "$NEW_BASE/.env" << ENVEOF
# KlimtechRAG — konfiguracja środowiska
# Wygenerowany przez 02_project_setup.sh — UZUPEŁNIJ przed uruchomieniem!

KLIMTECH_BASE_PATH=$NEW_BASE
KLIMTECH_EMBEDDING_DEVICE=cpu

# API key (zmień na unikalny!)
KLIMTECH_API_KEY=sk-local-ZMIEN-MNIE

# LLM (llama-server)
KLIMTECH_LLM_BASE_URL=http://localhost:8082/v1
KLIMTECH_LLM_API_KEY=sk-dummy

# Qdrant
KLIMTECH_QDRANT_URL=http://localhost:6333

# Nextcloud
NEXTCLOUD_ADMIN_USER=admin
NEXTCLOUD_ADMIN_PASSWORD=klimtech123

# AMD GPU
HIP_VISIBLE_DEVICES=0
HSA_OVERRIDE_GFX_VERSION=9.0.6
GPU_MAX_ALLOC_PERCENT=100
HSA_ENABLE_SDMA=0
ENVEOF
    warn ".env wygenerowany z domyślnymi wartościami — ZMIEŃ KLIMTECH_API_KEY!"
fi

# =============================================================================
section "7. Aktualizacja ścieżek w start_klimtech_v3.py"
# =============================================================================
# start_klimtech_v3.py ma hardcoded ścieżkę /home/lobo/KlimtechRAG
OLD_PATH="/home/lobo/KlimtechRAG"
START_SCRIPT="$NEW_BASE/start_klimtech_v3.py"

if grep -q "$OLD_PATH" "$START_SCRIPT" 2>/dev/null; then
    sed -i "s|$OLD_PATH|$NEW_BASE|g" "$START_SCRIPT"
    ok "Ścieżki zaktualizowane w start_klimtech_v3.py ($OLD_PATH → $NEW_BASE)"
else
    warn "start_klimtech_v3.py — stara ścieżka nie znaleziona (już zaktualizowana?)"
fi

# Zaktualizuj też interfejs sieciowy jeśli podano inny niż enp9s0
if [ "$INTERFACE" != "enp9s0" ] && grep -q "enp9s0" "$START_SCRIPT" 2>/dev/null; then
    sed -i "s|enp9s0|$INTERFACE|g" "$START_SCRIPT"
    warn "Interfejs sieciowy zmieniony: enp9s0 → $INTERFACE w start_klimtech_v3.py"
fi

# =============================================================================
section "PODSUMOWANIE"
# =============================================================================
echo ""
echo "  ✓ Repo: $NEW_BASE"
echo "  ✓ Python venv: $VENV"
echo "  ✓ SSL cert: $CERTS_DIR/server.crt"
echo "  ✓ nginx: HTTPS 8443/8444/5679/6334"
echo "  ✓ Obrazy Podman pobrane"
echo "  ✓ .env: $NEW_BASE/.env"
echo ""
echo "  ★ NASTĘPNE KROKI:"
echo "    1. Podłącz dysk BACKUP i systemowy przez USB (jeśli jeszcze nie)"
echo "    2. Uruchom: bash 03_data_migrate.sh"
echo "    3. Sprawdź .env: nano $NEW_BASE/.env"
echo "    4. Uruchom backend: cd $NEW_BASE && python3 start_klimtech_v3.py"
echo ""
echo "  IP serwera:  https://$SERVER_IP:8443"
echo "  Nextcloud:   https://$SERVER_IP:8444"
echo "  n8n:         https://$SERVER_IP:5679"
echo ""
echo "Log: $LOG"
