#!/bin/bash
# =============================================================================
# KlimtechRAG — Faza 4: AMD Instinct MI50 (gfx906) — ROCm 7.2.1 + llama.cpp
# =============================================================================
# Referencje:
#   https://rocm.docs.amd.com/projects/install-on-linux/en/latest/install/quick-start.html
#   https://rocm.docs.amd.com/projects/install-on-linux/en/latest/install/prerequisites.html
#   https://countryboycomputersbg.com/dual-instinct-mi50-32gb-running-moe-models-with-self-built-llama-cpp-gpt-oss20b-qwen330b-and-gpt-oss120b/
#
# Uruchomienie:
#   bash server_setup/04_amd_instinct_rocm7.sh
#
# Kolejność kroków:
#   1. Sprawdzenie prerequisitów (kernel, distro)
#   2. amdgpu-install 7.2.1 + python wheels
#   3. linux-headers + amdgpu-dkms
#   4. usermod render/video
#   5. sudo apt install rocm
#   6. rocblas 7.1.1 z lokalnej paczki
#   7. [RĘCZNIE] Skopiuj pliki tensor gfx906 z Google Drive → PRZED REBOOTEM
#   8. Reboot
#   9. llama.cpp build z -DGPU_TARGETS=gfx906
#   10. Test GPU
# =============================================================================

set -euo pipefail

# ── Zmienne ──────────────────────────────────────────────────────────────────
USERNAME="${LOGNAME:-lobo}"
AMD_GFX="gfx906"
ROCM_VERSION="7.2.1"
AMDGPU_DEB="amdgpu-install_7.2.1.70201-1_all.deb"
AMDGPU_URL="https://repo.radeon.com/amdgpu-install/7.2.1/ubuntu/noble/${AMDGPU_DEB}"
ROCBLAS_PKG="$(dirname "$0")/rocblas-7.1.1-1-x86_64.pkg.tar.zst"
LLAMA_DIR="/home/${USERNAME}/builds/llama.cpp"
LOG="$HOME/install_rocm7_$(date +%Y%m%d_%H%M%S).log"

# ── Kolory ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()      { echo -e "${GREEN}[OK]${NC}    $1" | tee -a "$LOG"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $1" | tee -a "$LOG"; }
fail()    { echo -e "${RED}[FAIL]${NC}  $1" | tee -a "$LOG"; exit 1; }
info()    { echo -e "${CYAN}[INFO]${NC}  $1" | tee -a "$LOG"; }
section() { echo "" | tee -a "$LOG"; echo "══════════════════════════════════════════════════" | tee -a "$LOG"; echo "  $1" | tee -a "$LOG"; echo "══════════════════════════════════════════════════" | tee -a "$LOG"; }

echo "KlimtechRAG — AMD Instinct ROCm ${ROCM_VERSION} — $(date '+%Y-%m-%d %H:%M:%S')" | tee "$LOG"
echo "User: $USERNAME | GFX: $AMD_GFX | Log: $LOG" | tee -a "$LOG"

[ "$EUID" -eq 0 ] && fail "Nie uruchamiaj jako root. Uruchom jako użytkownik: bash $0"

# =============================================================================
section "1. Prerequisity — sprawdzenie systemu"
# =============================================================================
# Ref: https://rocm.docs.amd.com/projects/install-on-linux/en/latest/install/prerequisites.html

ARCH=$(uname -m)
KERNEL=$(uname -srmv)
DISTRO=$(grep DISTRIB_RELEASE /etc/lsb-release 2>/dev/null | cut -d= -f2 || echo "unknown")
CODENAME=$(lsb_release -cs 2>/dev/null || echo "unknown")

info "Architektura: $ARCH"
info "Kernel: $KERNEL"
info "Ubuntu: $DISTRO ($CODENAME)"

[ "$ARCH" != "x86_64" ] && fail "Wymagana architektura x86_64. Masz: $ARCH"
[ "$CODENAME" != "noble" ] && warn "Skrypt testowany na Ubuntu 24.04 (noble). Masz: $CODENAME — kontynuuj ostrożnie."

# Sprawdź czy GPU widoczne
if ls /dev/kfd /dev/dri/renderD* &>/dev/null; then
    ok "GPU devices widoczne: /dev/kfd, /dev/dri/renderD*"
else
    warn "/dev/kfd lub /dev/dri/renderD* niewidoczne — GPU może nie być zamontowane lub brak passthrough"
fi

# =============================================================================
section "2. amdgpu-install 7.2.1 (pomij jeśli już zainstalowany)"
# =============================================================================
# Te kroki mogą być już wykonane — skrypt sprawdza stan

if dpkg -l | grep -q "amdgpu-install"; then
    ok "amdgpu-install już zainstalowany — pomijam krok 2"
else
    info "Pobieranie: $AMDGPU_URL"
    cd /tmp
    wget -q --show-progress "$AMDGPU_URL" -O "$AMDGPU_DEB" 2>&1 | tee -a "$LOG"
    sudo apt install -y "./$AMDGPU_DEB" 2>&1 | tee -a "$LOG"
    sudo apt update 2>&1 | tee -a "$LOG"
    ok "amdgpu-install 7.2.1 zainstalowany"
fi

# Python wheels (wymagane przez ROCm)
info "Instalacja python3-setuptools, python3-wheel..."
sudo apt install -y python3-setuptools python3-wheel 2>&1 | tee -a "$LOG"
ok "Python wheels gotowe"

# =============================================================================
section "3. linux-headers + amdgpu-dkms (sterownik kernela)"
# =============================================================================
KERN_VER=$(uname -r)
info "Kernel: $KERN_VER"

if dpkg -l | grep -q "amdgpu-dkms"; then
    ok "amdgpu-dkms już zainstalowany — pomijam"
else
    info "Instalacja linux-headers i amdgpu-dkms (może potrwać kilka minut)..."
    sudo apt install -y \
        "linux-headers-${KERN_VER}" \
        "linux-modules-extra-${KERN_VER}" \
        2>&1 | tee -a "$LOG"
    sudo apt install -y amdgpu-dkms 2>&1 | tee -a "$LOG"
    ok "amdgpu-dkms zainstalowany"
fi

# =============================================================================
section "4. Dodanie użytkownika do grup render i video"
# =============================================================================
if groups "$USERNAME" | grep -q "render"; then
    ok "Użytkownik $USERNAME już w grupie render,video"
else
    sudo usermod -a -G render,video "$USERNAME"
    ok "Dodano $USERNAME do grup render i video — WYMAGANE przelogowanie!"
fi

# =============================================================================
section "5. Instalacja ROCm"
# =============================================================================
if command -v rocm-smi &>/dev/null; then
    ok "ROCm już zainstalowany: $(rocm-smi --version 2>/dev/null || echo 'OK')"
else
    info "Instalacja ROCm (może potrwać 20-30 minut)..."
    sudo apt install -y rocm 2>&1 | tee -a "$LOG"
    ok "ROCm zainstalowany"
fi

# ROCm do PATH (jeśli nie jest)
if ! echo "$PATH" | grep -q "/opt/rocm/bin"; then
    warn "/opt/rocm/bin nie w PATH — dodaj do ~/.bashrc lub ~/.config/fish/conf.d/amd_gpu.fish:"
    warn '  export PATH="/opt/rocm/bin:$PATH"  # bash/zsh'
    warn '  fish_add_path /opt/rocm/bin         # fish'
fi

# =============================================================================
section "6. rocblas 7.1.1 z lokalnej paczki"
# =============================================================================
# Plik: server_setup/rocblas-7.1.1-1-x86_64.pkg.tar.zst
# Źródło: pendrive FILMY_PROJE/Serwer_instalatory/

if [ -f "$ROCBLAS_PKG" ]; then
    info "Rozpakowywanie $ROCBLAS_PKG..."
    ROCBLAS_TMP="/tmp/rocblas_install"
    mkdir -p "$ROCBLAS_TMP"
    tar --use-compress-program=zstd -xf "$ROCBLAS_PKG" -C "$ROCBLAS_TMP" 2>&1 | tee -a "$LOG"

    # Skopiuj biblioteki do /opt/rocm (jeśli istnieje) lub /usr/lib
    if [ -d "$ROCBLAS_TMP/usr" ]; then
        sudo cp -r "$ROCBLAS_TMP/usr/"* /usr/ 2>&1 | tee -a "$LOG"
        ok "rocblas 7.1.1 zainstalowany z lokalnej paczki"
    elif [ -d "$ROCBLAS_TMP/opt" ]; then
        sudo cp -r "$ROCBLAS_TMP/opt/"* /opt/ 2>&1 | tee -a "$LOG"
        ok "rocblas 7.1.1 zainstalowany w /opt"
    else
        warn "Nieznana struktura paczki — sprawdź ręcznie: ls $ROCBLAS_TMP"
    fi

    rm -rf "$ROCBLAS_TMP"
else
    warn "Plik $ROCBLAS_PKG nie istnieje — pomijam instalację rocblas"
    warn "Skopiuj plik do server_setup/ i uruchom ten krok ręcznie"
fi

# =============================================================================
section "7. [WAŻNE — RĘCZNIE] Pliki tensor gfx906 przed rebootem"
# =============================================================================
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  KROK RĘCZNY — PRZED REBOOTEM                               ║${NC}"
echo -e "${YELLOW}║                                                              ║${NC}"
echo -e "${YELLOW}║  Pobierz pliki tensor dla gfx906 z Google Drive (link        ║${NC}"
echo -e "${YELLOW}║  z artykułu countryboycomputersbg.com) i skopiuj je do:      ║${NC}"
echo -e "${YELLOW}║    /opt/rocm/lib/rocblas/library/                            ║${NC}"
echo -e "${YELLOW}║                                                              ║${NC}"
echo -e "${YELLOW}║  BEZ TYCH PLIKÓW rocblas nie będzie działać na gfx906!       ║${NC}"
echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Czy skopiowałeś pliki tensor gfx906? [t/N]: " TENSOR_DONE
if [[ "$TENSOR_DONE" =~ ^[tTyY]$ ]]; then
    ok "Pliki tensor gfx906 potwierdzone"
else
    warn "Pamiętaj o plikach tensor przed restartem!"
fi

# =============================================================================
section "8. [OPCJONALNIE] Zmienne środowiskowe AMD GPU do fish"
# =============================================================================
FISH_AMD="/home/${USERNAME}/.config/fish/conf.d/amd_gpu.fish"
if [ ! -f "$FISH_AMD" ]; then
    mkdir -p "$(dirname "$FISH_AMD")"
    cat > "$FISH_AMD" << 'FISHEOF'
# AMD GPU environment — KlimtechRAG (MI50 gfx906)
# Ref: wiki/lessons.md, CLAUDE.md sekcja 7
set -gx HIP_VISIBLE_DEVICES 0
set -gx GPU_MAX_ALLOC_PERCENT 100
set -gx HSA_ENABLE_SDMA 0
set -gx HSA_OVERRIDE_GFX_VERSION 9.0.6
fish_add_path /opt/rocm/bin
FISHEOF
    ok "Fish: zmienne AMD GPU zapisane w $FISH_AMD"
else
    ok "Fish AMD GPU config już istnieje: $FISH_AMD"
fi

# Wersja bash/.bashrc
if ! grep -q "HSA_OVERRIDE_GFX_VERSION" /home/"${USERNAME}"/.bashrc 2>/dev/null; then
    cat >> /home/"${USERNAME}"/.bashrc << 'BASHEOF'

# AMD GPU environment — KlimtechRAG (MI50 gfx906)
export HIP_VISIBLE_DEVICES=0
export GPU_MAX_ALLOC_PERCENT=100
export HSA_ENABLE_SDMA=0
export HSA_OVERRIDE_GFX_VERSION=9.0.6
export PATH="/opt/rocm/bin:$PATH"
BASHEOF
    ok "~/.bashrc: zmienne AMD GPU dodane"
fi

# =============================================================================
section "9. Budowa llama.cpp z HIP/ROCm dla gfx906"
# =============================================================================
# UWAGA: uruchom TEN KROK dopiero PO restarcie i weryfikacji ROCm (rocm-smi)

if command -v rocm-smi &>/dev/null && rocm-smi 2>/dev/null | grep -q "GPU"; then
    if [ -f "/usr/local/bin/llama-server" ]; then
        warn "llama-server już istnieje — pomijam budowę"
        warn "Aby przebudować: sudo rm /usr/local/bin/llama-server i uruchom ponownie"
    else
        mkdir -p "$(dirname "$LLAMA_DIR")"

        if [ -d "$LLAMA_DIR" ]; then
            info "Aktualizacja llama.cpp..."
            cd "$LLAMA_DIR" && git pull 2>&1 | tee -a "$LOG"
        else
            info "Klonowanie llama.cpp..."
            git clone https://github.com/ggml-org/llama.cpp "$LLAMA_DIR" 2>&1 | tee -a "$LOG"
        fi

        cd "$LLAMA_DIR"

        command -v hipconfig &>/dev/null || fail "hipconfig nie znaleziono. ROCm musi być widoczny (sprawdź PATH i czy po restarcie)."

        HIP_LIB=$(hipconfig -l)
        HIP_ROOT=$(hipconfig -R)
        info "HIP_LIB: $HIP_LIB"
        info "HIP_ROOT: $HIP_ROOT"

        HIPCXX="${HIP_LIB}/clang" HIP_PATH="$HIP_ROOT" \
        cmake -S . -B build \
            -DGGML_HIP=ON \
            -DAMDGPU_TARGETS="${AMD_GFX}" \
            -DCMAKE_BUILD_TYPE=Release \
            -DLLAMA_BUILD_SERVER=ON \
            -GNinja \
            2>&1 | tee -a "$LOG"

        cmake --build build --config Release -j"$(nproc)" 2>&1 | tee -a "$LOG"

        sudo cp build/bin/llama-server /usr/local/bin/
        sudo cp build/bin/llama-cli /usr/local/bin/ 2>/dev/null || true
        sudo chmod +x /usr/local/bin/llama-server /usr/local/bin/llama-cli

        ok "llama-server zbudowany dla ${AMD_GFX}: $(llama-server --version 2>/dev/null || echo 'OK')"
    fi
else
    warn "rocm-smi nie wykrywa GPU — pomiń krok 9 teraz, uruchom po restarcie i weryfikacji ROCm"
    warn "Komenda do ręcznego uruchomienia po restarcie:"
    warn "  bash server_setup/04_amd_instinct_rocm7.sh"
fi

# =============================================================================
section "10. Test GPU (po restarcie)"
# =============================================================================
echo ""
if command -v rocm-smi &>/dev/null; then
    info "rocm-smi:"
    rocm-smi 2>&1 | tee -a "$LOG" || warn "rocm-smi error — sprawdź po restarcie"

    info "rocminfo (GPU architecture):"
    rocminfo 2>/dev/null | grep -E "Name|gfx|Marketing" | head -10 | tee -a "$LOG" || warn "rocminfo niedostępne"
else
    warn "rocm-smi niedostępne — uruchom test po restarcie:"
    warn "  rocm-smi"
    warn "  rocminfo | grep -E 'Name|gfx'"
fi

# =============================================================================
section "PODSUMOWANIE"
# =============================================================================
echo ""
echo "  ✓ Prerequisity sprawdzone (x86_64, Ubuntu noble)"
echo "  ✓ amdgpu-install 7.2.1"
echo "  ✓ linux-headers + amdgpu-dkms"
echo "  ✓ usermod render,video"
echo "  ✓ ROCm zainstalowany"
echo "  ✓ rocblas 7.1.1 (lokalny package)"
echo "  ✓ Zmienne AMD GPU (fish + bash)"
echo ""
echo -e "${YELLOW}  ★ NASTĘPNE KROKI RĘCZNE:${NC}"
echo "  1. [JEŚLI NIE ZROBIONE] Skopiuj pliki tensor gfx906 → /opt/rocm/lib/rocblas/library/"
echo "  2. sudo reboot"
echo "  3. Po restarcie: rocm-smi  # sprawdź czy GPU widoczne"
echo "  4. Po weryfikacji: bash server_setup/04_amd_instinct_rocm7.sh  # buduje llama.cpp"
echo ""
echo "  Log: $LOG"
echo ""
echo -e "${CYAN}  Ref: https://rocm.docs.amd.com/projects/install-on-linux/en/latest/install/quick-start.html${NC}"
echo -e "${CYAN}  Ref: https://countryboycomputersbg.com/dual-instinct-mi50-32gb-running-moe-models-with-self-built-llama-cpp-gpt-oss20b-qwen330b-and-gpt-oss120b/${NC}"
