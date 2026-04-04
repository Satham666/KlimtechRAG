#!/bin/bash
# =============================================================================
# KlimtechRAG — Faza 1: Instalacja systemu na świeżym Ubuntu Server
# =============================================================================
# Uruchom po pierwszym restarcie Ubuntu Server jako użytkownik lobo:
#   bash 01_system_install.sh
#
# Co robi:
#   1. Aktualizacja systemu
#   2. Pakiety systemowe (git, nginx, fish, podman, python3, build tools)
#   3. AMD ROCm + HIP (sterowniki GPU dla gfx906 / MI50)
#   4. Budowa llama.cpp z obsługą ROCm
#   5. Konfiguracja fish shell + zmiennych AMD GPU
#   6. Struktura katalogów projektu
# =============================================================================

set -euo pipefail

# ── Zmienne ──────────────────────────────────────────────────────────────────
USERNAME="lobo"
NEW_BASE="/home/lobo/KlimtechRAG"
LLAMA_BUILD_DIR="/home/lobo/builds/llama.cpp"
AMD_GFX="gfx906"                     # AMD Instinct / Vega20 (HSA_OVERRIDE=9.0.6)
ROCM_VERSION="6.3"                   # ROCm 6.3.x (Ubuntu 22.04/24.04)
LOG="$HOME/install_phase1.log"

# ── Kolory ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $1" | tee -a "$LOG"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG"; }
fail() { echo -e "${RED}[FAIL]${NC} $1" | tee -a "$LOG"; exit 1; }
section() { echo "" | tee -a "$LOG"; echo "══════════════════════════════════════" | tee -a "$LOG"; echo "  $1" | tee -a "$LOG"; echo "══════════════════════════════════════" | tee -a "$LOG"; }

echo "KlimtechRAG — Faza 1 — $(date '+%Y-%m-%d %H:%M:%S')" | tee "$LOG"

# ── Sprawdź czy nie root ──────────────────────────────────────────────────────
if [ "$EUID" -eq 0 ]; then
    fail "Nie uruchamiaj jako root. Użyj: bash 01_system_install.sh (sudo będzie pytać w razie potrzeby)"
fi

# Sprawdź Ubuntu version
UBUNTU_CODENAME=$(lsb_release -cs 2>/dev/null || echo "jammy")
ok "Ubuntu: $UBUNTU_CODENAME"

# =============================================================================
section "1. Aktualizacja systemu"
# =============================================================================
sudo apt-get update -y 2>&1 | tee -a "$LOG"
sudo apt-get upgrade -y 2>&1 | tee -a "$LOG"
ok "System zaktualizowany"

# =============================================================================
section "2. Pakiety systemowe"
# =============================================================================
sudo apt-get install -y \
    git curl wget htop tmux vim nano unzip rsync \
    python3 python3-pip python3-venv python3-dev \
    build-essential cmake ninja-build ccache pkg-config \
    libssl-dev libffi-dev libmagic1 \
    nginx \
    fish \
    podman \
    openssl \
    ffmpeg \
    poppler-utils \
    tesseract-ocr tesseract-ocr-pol \
    lsb-release software-properties-common \
    net-tools iproute2 \
    2>&1 | tee -a "$LOG"
ok "Pakiety systemowe zainstalowane"

# =============================================================================
section "3. AMD ROCm $ROCM_VERSION (sterowniki GPU gfx906)"
# =============================================================================
# Sprawdź czy ROCm już zainstalowany
if command -v rocm-smi &>/dev/null; then
    warn "ROCm już zainstalowany — pomijam"
else
    cd /tmp

    # Pobierz amdgpu-install dla Ubuntu
    if [ "$UBUNTU_CODENAME" = "noble" ]; then
        # Ubuntu 24.04
        AMDGPU_DEB="amdgpu-install_6.3.60300-1_all.deb"
        AMDGPU_URL="https://repo.radeon.com/amdgpu-install/6.3/ubuntu/noble/$AMDGPU_DEB"
    else
        # Ubuntu 22.04 (domyślnie)
        AMDGPU_DEB="amdgpu-install_6.3.60300-1_all.deb"
        AMDGPU_URL="https://repo.radeon.com/amdgpu-install/6.3/ubuntu/jammy/$AMDGPU_DEB"
    fi

    echo "Pobieranie: $AMDGPU_URL" | tee -a "$LOG"
    wget -q --show-progress "$AMDGPU_URL" -O "$AMDGPU_DEB" 2>&1 | tee -a "$LOG" || \
        fail "Nie można pobrać amdgpu-install. Sprawdź: https://repo.radeon.com/amdgpu-install/"

    sudo apt-get install -y "./$AMDGPU_DEB" 2>&1 | tee -a "$LOG"
    sudo apt-get update -y 2>&1 | tee -a "$LOG"

    # Instalacja ROCm + HIP (bez DKMS - nie potrzebujemy kernel module dla compute)
    sudo amdgpu-install -y --usecase=rocm,hip --no-dkms 2>&1 | tee -a "$LOG"

    # Dodaj użytkownika do grup GPU
    sudo usermod -aG render,video "$USERNAME"
    ok "ROCm zainstalowany. UWAGA: wymagany LOGOUT/LOGIN żeby grupy działały!"
fi

# =============================================================================
section "4. Budowa llama.cpp z ROCm/HIP"
# =============================================================================
if [ -f "/usr/local/bin/llama-server" ]; then
    warn "llama-server już istnieje w /usr/local/bin — pomijam budowę"
    warn "Aby przebudować: rm /usr/local/bin/llama-server i uruchom ponownie"
else
    mkdir -p "$(dirname "$LLAMA_BUILD_DIR")"

    if [ -d "$LLAMA_BUILD_DIR" ]; then
        echo "Aktualizacja llama.cpp..." | tee -a "$LOG"
        cd "$LLAMA_BUILD_DIR" && git pull 2>&1 | tee -a "$LOG"
    else
        echo "Klonowanie llama.cpp..." | tee -a "$LOG"
        git clone https://github.com/ggerganov/llama.cpp "$LLAMA_BUILD_DIR" 2>&1 | tee -a "$LOG"
    fi

    cd "$LLAMA_BUILD_DIR"

    # Sprawdź czy hipconfig dostępny (ROCm musi być zainstalowany)
    if ! command -v hipconfig &>/dev/null; then
        fail "hipconfig nie znaleziono. ROCm musi być zainstalowany przed budową llama.cpp. Uruchom skrypt ponownie po instalacji ROCm."
    fi

    HIP_LIB=$(hipconfig -l)
    HIP_ROOT=$(hipconfig -R)
    echo "HIP: $HIP_ROOT" | tee -a "$LOG"

    # Budowa z HIP/ROCm
    HIPCXX="${HIP_LIB}/clang" HIP_PATH="$HIP_ROOT" \
    cmake -S . -B build \
        -DGGML_HIP=ON \
        -DAMDGPU_TARGETS="$AMD_GFX" \
        -DCMAKE_BUILD_TYPE=Release \
        -DLLAMA_BUILD_SERVER=ON \
        -GNinja \
        2>&1 | tee -a "$LOG"

    cmake --build build --config Release -j"$(nproc)" 2>&1 | tee -a "$LOG"

    # Instalacja binariów
    sudo cp build/bin/llama-server /usr/local/bin/
    sudo cp build/bin/llama-cli /usr/local/bin/ 2>/dev/null || true
    sudo chmod +x /usr/local/bin/llama-server

    ok "llama-server zainstalowany: $(llama-server --version 2>/dev/null || echo 'OK')"
fi

# =============================================================================
section "5. Konfiguracja Fish Shell"
# =============================================================================
FISH_BIN=$(which fish)

# Ustaw fish jako domyślny shell
if [ "$(getent passwd "$USERNAME" | cut -d: -f7)" != "$FISH_BIN" ]; then
    sudo chsh -s "$FISH_BIN" "$USERNAME"
    ok "Fish ustawiony jako domyślny shell"
else
    warn "Fish już jest domyślnym shellem"
fi

# Konfiguracja fish: zmienne AMD GPU
FISH_CONF_DIR="/home/$USERNAME/.config/fish"
mkdir -p "$FISH_CONF_DIR"

cat > "$FISH_CONF_DIR/conf.d/amd_gpu.fish" << 'EOF'
# AMD GPU environment — KlimtechRAG
set -gx HIP_VISIBLE_DEVICES 0
set -gx GPU_MAX_ALLOC_PERCENT 100
set -gx HSA_ENABLE_SDMA 0
set -gx HSA_OVERRIDE_GFX_VERSION 9.0.6
# ROCm bin w PATH
fish_add_path /opt/rocm/bin
EOF

ok "Fish: zmienne AMD GPU skonfigurowane (~/.config/fish/conf.d/amd_gpu.fish)"

# =============================================================================
section "6. Podman — konfiguracja rootless"
# =============================================================================
# Ustaw subuid/subgid dla rootless podman
if ! grep -q "^$USERNAME:" /etc/subuid 2>/dev/null; then
    echo "$USERNAME:100000:65536" | sudo tee -a /etc/subuid
    echo "$USERNAME:100000:65536" | sudo tee -a /etc/subgid
    ok "subuid/subgid dla rootless Podman dodane"
else
    warn "subuid/subgid już istnieje"
fi

# Inicjalizacja rootless Podman
podman system migrate 2>/dev/null || true
ok "Podman rootless gotowy"

# =============================================================================
section "7. Nginx — sudoers (bez hasła dla reload)"
# =============================================================================
SUDOERS_FILE="/etc/sudoers.d/klimtech-nginx"
if [ ! -f "$SUDOERS_FILE" ]; then
    cat << EOF | sudo tee "$SUDOERS_FILE" > /dev/null
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx
$USERNAME ALL=(ALL) NOPASSWD: /usr/sbin/nginx -t
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/cp /home/$USERNAME/KlimtechRAG/data/ssl/klimtech-nginx.conf /etc/nginx/sites-available/klimtech
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/ln -sf /etc/nginx/sites-available/klimtech /etc/nginx/sites-enabled/klimtech
$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/pkill -9 merecat
EOF
    ok "Sudoers dla nginx skonfigurowany"
else
    warn "Sudoers dla nginx już istnieje"
fi

# =============================================================================
section "8. Struktura katalogów projektu"
# =============================================================================
mkdir -p "$NEW_BASE"/{data,logs,certs,modele_LLM}
mkdir -p "$NEW_BASE"/data/{uploads,ssl}
ok "Katalogi projektu: $NEW_BASE"

# =============================================================================
section "PODSUMOWANIE"
# =============================================================================
echo ""
echo "  ✓ Pakiety systemowe"
echo "  ✓ AMD ROCm (sprawdź: rocm-smi po relogowaniu)"
echo "  ✓ llama-server ($(llama-server --version 2>/dev/null || echo 'sprawdź po relogu'))"
echo "  ✓ Fish shell + zmienne AMD GPU"
echo "  ✓ Podman rootless"
echo "  ✓ Nginx + sudoers"
echo "  ✓ Katalogi: $NEW_BASE"
echo ""
echo "  ★ NASTĘPNY KROK:"
echo "    1. Podłącz dysk BACKUP i dysk systemowy przez USB"
echo "    2. Uruchom: bash 02_project_setup.sh"
echo ""
warn "WAŻNE: Wyloguj się i zaloguj ponownie żeby grupy render/video działały z GPU!"
echo ""
echo "Log: $LOG"
