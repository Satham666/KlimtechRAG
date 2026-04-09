# Proxmox VE 9.1 — Plan Instalacji dla KlimtechRAG
**Data opracowania:** 2026-04-08  
**Sprzęt docelowy:** GIGABYTE X870 EAGLE WIFI7 + AMD Instinct 16 GB  
**Cel:** Proxmox VE jako hypervisor → Ubuntu 24.04 LXC → KlimtechRAG + Claude Code CLI

---

## Sprzęt

| Komponent | Model | Uwagi |
|-----------|-------|-------|
| Płyta główna | GIGABYTE X870 EAGLE WIFI7 | AM5, DDR5, M.2 PCIe 5.0, Wi-Fi 7 |
| GPU (obecna) | AMD Instinct 16 GB VRAM | gfx906, HSA_OVERRIDE=9.0.6 |
| GPU (przyszła) | AMD Instinct 32 GB VRAM | GPU1 dla Qwen3-Coder |
| LAN | Intel I226-V 2.5GbE | sterownik `igc` — znane problemy |
| WiFi | MediaTek MT7925 | WiFi 7, sterownik `mt7925e` |

---

## Faza 0 — Przygotowanie (na laptopie, przed instalacją)

### 0.1 Pobierz Proxmox VE ISO
```
https://www.proxmox.com/en/downloads/proxmox-virtual-environment/iso
Pobierz: proxmox-ve_9.1-*.iso
```

### 0.2 Nagraj na USB (min. 8 GB)
```bash
# Linux (laptop):
lsblk  # znajdź nazwę USB np. /dev/sdb
sudo dd if=proxmox-ve_9.1-*.iso of=/dev/sdb bs=4M status=progress oflag=sync

# Windows: użyj Rufus lub Balena Etcher
# WAŻNE: tryb DD/Raw write — NIE ISO mode
```

### 0.3 BIOS — ustawienia przed instalacją
```
1. Włącz AMD-Vi (IOMMU):
   AMD CBS → NBIO → IOMMU → Enabled

2. Boot order: USB first

3. Secure Boot: Disabled (Proxmox tego wymaga)

4. CSM (Compatibility Support Module): Disabled

5. Zapis ustawień i restart
```

---

## Faza 1 — Instalacja Proxmox VE

### 1.1 Instalator Proxmox
```
1. Boot z USB → wybierz "Install Proxmox VE (Graphical)"

2. Dysk docelowy:
   - Wybierz SSD systemowy (min. 60 GB — Proxmox host)
   - Filesystem: ext4 (lub ZFS jeśli masz RAM > 32 GB)

3. Strefa czasowa: Europe/Warsaw

4. Hasło root + email (do alertów)

5. Sieć:
   - Management Interface: wybierz LAN (Intel I226-V)
   - Hostname: hall9000.local
   - IP: 192.168.31.70/24
   - Gateway: 192.168.31.1
   - DNS: 192.168.31.1 (lub 8.8.8.8)

6. Install → czekaj ~5-10 min → Reboot
```

### 1.2 Dostęp do web UI
```
Po restarcie otwórz w przeglądarce (z laptopa):
https://192.168.31.70:8006

Login: root
Hasło: to co ustawiłeś w instalatorze
```

---

## Faza 2 — Post-install Proxmox Host

### 2.1 SSH na Proxmox host
```bash
ssh root@192.168.31.70
```

### 2.2 GRUB — pokaż menu przy bootowaniu
```bash
nano /etc/default/grub
# Zmień:
# GRUB_TIMEOUT=5
# GRUB_TIMEOUT_STYLE=menu

update-grub
```

### 2.3 Aktualizacja bez płatnej subskrypcji
```bash
# Wyłącz enterprise repo (wymaga płatnej licencji)
sed -i 's/^deb/# deb/' /etc/apt/sources.list.d/pve-enterprise.list
sed -i 's/^deb/# deb/' /etc/apt/sources.list.d/ceph.list

# Dodaj darmowe community repo
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" \
  > /etc/apt/sources.list.d/pve-no-subscription.list

apt update && apt dist-upgrade -y
```

### 2.4 Fix LAN — Intel I226-V (Energy Efficient Ethernet)
```bash
# Wyłącz EEE na interfejsie LAN (fix losowych resetów połączenia)
apt install ethtool -y

# Sprawdź nazwę interfejsu
ip link show | grep -v lo | grep -v vmbr

# Wyłącz EEE (podmień enp*s0 na aktualną nazwę)
ethtool -s enp2s0 eee off

# Żeby było trwałe — dodaj do /etc/network/interfaces post-up:
nano /etc/network/interfaces
# W bloku iface enp2s0 inet manual dodaj:
# post-up ethtool -s enp2s0 eee off
```

### 2.5 WiFi — MediaTek MT7925 (opcjonalnie, jeśli potrzebne)
```bash
# Firmware może być brakujące w Proxmox (Debian base)
apt install firmware-linux firmware-linux-nonfree -y

# Sprawdź czy MT7925 jest widoczny
lspci | grep -i network
dmesg | grep mt7925

# Jeśli brakuje firmware:
# Pobierz ręcznie z linux-firmware repo do /lib/firmware/mediatek/
```

### 2.6 AMD Instinct — sterownik kernela (amdgpu) na hoście
```bash
# WAŻNE: Kernel module musi być NA HOŚCIE Proxmox
# User-space ROCm będzie w kontenerze LXC
# Proxmox jest Debian-based — używamy unofficjalnej metody

# Metoda 1: przez amdgpu-dkms z repo AMD
wget https://repo.radeon.com/amdgpu-install/6.3/ubuntu/focal/amdgpu-install_6.3.60300-1_all.deb
# UWAGA: dla Proxmox/Debian użyj wersji dla jammy/focal

# Alternatywnie — sprawdź czy amdgpu już w kernelu:
lspci | grep -i amd
lspci | grep -i display
dmesg | grep amdgpu

# Jeśli karta jest widoczna w dmesg — sterownik działa (Proxmox 9.x kernel 6.8+)
# AMD Instinct jest compute card — może nie mieć wyjścia video, to normalne

# Sprawdź /dev/kfd (wymagane dla ROCm):
ls -la /dev/kfd
ls -la /dev/dri/

# Dodaj roota do grup GPU:
usermod -aG render,video root
```

---

## Faza 3 — Tworzenie LXC Ubuntu 24.04

### 3.1 Pobierz template Ubuntu 24.04
```bash
# W terminalu Proxmox lub przez web UI: Datacenter → pve → local → CT Templates
pveam update
pveam download local ubuntu-24.04-standard_*.tar.zst
```

### 3.2 Utwórz kontener LXC
```bash
# Przez CLI (lub przez web UI — patrz 3.3)
pct create 100 local:vztmpl/ubuntu-24.04-standard_*.tar.zst \
  --hostname hall9000 \
  --cores 8 \
  --memory 32768 \
  --swap 8192 \
  --rootfs local-lvm:100 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.31.71/24,gw=192.168.31.1 \
  --unprivileged 0 \
  --features nesting=1,keyctl=1 \
  --password TwojeHaslo123 \
  --ostype ubuntu \
  --start 1
```

### 3.3 Przez web UI (alternatywa dla CLI)
```
1. Datacenter → Create CT
2. General: CT ID=100, Hostname=hall9000, Password=...
3. Template: ubuntu-24.04-standard
4. Disks: 100 GB na local-lvm
5. CPU: 8 cores
6. Memory: 32768 MB RAM, 8192 MB SWAP
7. Network: vmbr0, IP 192.168.31.71/24, GW 192.168.31.1
8. Confirm → Finish

WAŻNE po stworzeniu — przed startem:
Options → Features → Nesting: YES, keyctl: YES
Options → Unprivileged: NO (privileged — wymagane dla GPU)
```

### 3.4 GPU Passthrough do LXC — konfiguracja
```bash
# Na hoście Proxmox (nie w kontenerze!)
nano /etc/pve/lxc/100.conf

# Dodaj na końcu pliku:
lxc.cgroup2.devices.allow: c 226:* rwm
lxc.cgroup2.devices.allow: c 235:* rwm
lxc.mount.entry: /dev/dri dev/dri none bind,optional,create=dir
lxc.mount.entry: /dev/kfd dev/kfd none bind,optional,create=file

# Sprawdź numery urządzeń (mogą się różnić):
ls -la /dev/dri/
ls -la /dev/kfd
# c 226:* — DRI (renderD128 itp.)
# c 235:* — KFD (AMD Kernel Fusion Driver)
```

### 3.5 Start kontenera
```bash
pct start 100
pct enter 100
# lub przez web UI: kliknij kontener → Console
```

---

## Faza 4 — Setup Ubuntu 24.04 w LXC

### 4.1 Podstawowa konfiguracja
```bash
# W kontenerze LXC:
apt update && apt upgrade -y
apt install -y sudo curl wget git nano fish htop tmux net-tools

# Utwórz użytkownika lobo
useradd -m -s /usr/bin/fish -G sudo,render,video lobo
passwd lobo

# SSH
apt install -y openssh-server
systemctl enable ssh
```

### 4.2 Hardening SSH
```bash
nano /etc/ssh/sshd_config
# Ustaw:
# Port 2222
# PasswordAuthentication no      # po skonfigurowaniu kluczy SSH!
# PermitRootLogin no
# PubkeyAuthentication yes

systemctl restart ssh
```

### 4.3 Firewall
```bash
apt install -y ufw fail2ban
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp    # SSH (nowy port)
ufw allow 8000/tcp    # KlimtechRAG backend
ufw allow 8443/tcp    # KlimtechRAG HTTPS
ufw allow 6333/tcp    # Qdrant (tylko z sieci lokalnej!)
ufw allow from 192.168.31.0/24 to any port 6333
ufw enable
```

### 4.4 AMD ROCm w kontenerze LXC
```bash
# Użyj istniejącego skryptu server_setup/01_system_install.sh
# (sklonuj repo najpierw lub uruchom manualnie kroki ROCm)

# Sprawdź czy /dev/kfd jest dostępny w kontenerze:
ls -la /dev/kfd
ls -la /dev/dri/

# Zainstaluj ROCm (Ubuntu 24.04 / noble)
cd /tmp
wget https://repo.radeon.com/amdgpu-install/6.3/ubuntu/noble/amdgpu-install_6.3.60300-1_all.deb
apt install ./amdgpu-install_6.3.60300-1_all.deb -y
apt update
amdgpu-install -y --usecase=rocm,hip --no-dkms

# Dodaj lobo do grup GPU
usermod -aG render,video lobo

# Test ROCm (po relogowaniu):
rocm-smi
rocminfo | grep "gfx"
```

---

## Faza 5 — Instalacja KlimtechRAG w LXC

### 5.1 Pakiety systemowe
```bash
# Uruchom istniejący skrypt (jako użytkownik lobo):
su - lobo
bash /home/lobo/KlimtechRAG/server_setup/01_system_install.sh
```

### 5.2 Klonowanie repozytorium
```bash
su - lobo
git clone https://github.com/Satham666/KlimtechRAG.git /home/lobo/KlimtechRAG
cd /home/lobo/KlimtechRAG
```

### 5.3 Setup projektu
```bash
# Uruchom skrypt setup (jako lobo):
bash server_setup/02_project_setup.sh

# Sprawdź i uzupełnij .env:
nano /home/lobo/KlimtechRAG/.env
# KLIMTECH_BASE_PATH=/home/lobo/KlimtechRAG
# KLIMTECH_API_KEY=sk-local-ZMIEN
# HSA_OVERRIDE_GFX_VERSION=9.0.6
```

### 5.4 Qdrant w Podman (LXC)
```bash
# Podman działa w privileged LXC z nesting=1
systemctl --user enable qdrant.service
systemctl --user start qdrant.service
curl http://localhost:6333/healthz
```

### 5.5 Test backendu
```bash
cd /home/lobo/KlimtechRAG
source venv/bin/activate.fish
python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000 &
curl http://localhost:8000/health
```

---

## Faza 6 — Claude Code CLI w LXC

### 6.1 Instalacja Node.js i Claude Code
```bash
# W kontenerze LXC jako lobo:
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Zainstaluj Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Weryfikacja
claude --version
```

### 6.2 Pierwsza konfiguracja
```bash
cd /home/lobo/KlimtechRAG
claude
# Przy pierwszym uruchomieniu: zaloguj się przez link w przeglądarce
# (lub przez API key: claude --api-key sk-ant-...)
```

### 6.3 Sprawdź CLAUDE.md i wiki
```bash
# Claude Code automatycznie załaduje CLAUDE.md przy starcie
# Przeczytaj wiki/status.md żeby wiedzieć gdzie skończyliśmy:
cat wiki/status.md
```

---

## Faza 7 — Przyszłość: GPU1 (32 GB AMD Instinct)

```bash
# Po zamontowaniu drugiej karty na hoście Proxmox:

# 1. Sprawdź czy karta widoczna na hoście:
lspci | grep -i amd
ls /dev/dri/  # renderD128 (GPU0), renderD129 (GPU1)?

# 2. Dodaj do /etc/pve/lxc/100.conf lub nowego kontenera 101:
lxc.cgroup2.devices.allow: c 226:129 rwm  # renderD129
lxc.mount.entry: /dev/dri/renderD129 dev/dri/renderD129 none bind,optional,create=file

# 3. W kontenerze GPU1 ustaw HIP_VISIBLE_DEVICES=1
# 4. Start llama-server Qwen3-Coder na porcie 8083

# SZCZEGÓŁY: patrz Plan_Wdrożenia_Architektury_Agentowej.md Faza 2
```

---

## Checklist — Szybki Start

```
PRZED INSTALACJĄ:
[ ] ISO pobrane i nagrane na USB (tryb DD)
[ ] BIOS: AMD-Vi ON, Secure Boot OFF, CSM OFF, USB boot first

INSTALACJA PROXMOX:
[ ] Hostname: hall9000.local, IP: 192.168.31.70
[ ] Dysk: SSD systemowy, ext4

POST-INSTALL PROXMOX HOST:
[ ] Enterprise repo wyłączone, community repo dodane
[ ] apt dist-upgrade
[ ] GRUB: TIMEOUT=5, STYLE=menu
[ ] LAN fix: ethtool -s enp*s0 eee off
[ ] /dev/kfd i /dev/dri/ widoczne
[ ] AMD ROCm kernel module: dmesg | grep amdgpu ✓

LXC KONTENER:
[ ] Ubuntu 24.04, privileged, nesting=1, keyctl=1
[ ] GPU passthrough w /etc/pve/lxc/100.conf
[ ] Użytkownik lobo w grupach render,video
[ ] ROCm zainstalowany: rocm-smi ✓
[ ] KlimtechRAG: curl http://localhost:8000/health ✓
[ ] Qdrant: curl http://localhost:6333/healthz ✓
[ ] Claude Code CLI: claude --version ✓
[ ] CLAUDE.md załadowany, wiki/status.md przeczytany ✓

BEZPIECZEŃSTWO:
[ ] SSH key dodany, PasswordAuthentication no
[ ] ufw aktywny, porty 2222/8443 otwarte
[ ] fail2ban aktywny
[ ] Proxmox web UI (8006) dostępny TYLKO z 192.168.31.0/24
```

---

## Znane Problemy i Rozwiązania

### Problem: /dev/kfd nie istnieje w LXC
```bash
# Na hoście Proxmox sprawdź:
ls -la /dev/kfd
# Jeśli brak — amdgpu kernel module nie jest załadowany
modprobe amdgpu
# Jeśli błąd — sprawdź czy karta jest w PCIe:
lspci | grep -i amd
```

### Problem: rocm-smi nie widzi karty w LXC
```bash
# Sprawdź grupy użytkownika:
groups lobo  # musi być render i video
# Jeśli nie — usermod -aG render,video lobo && logout/login
# Sprawdź czy /dev/kfd ma odpowiednie uprawnienia:
ls -la /dev/kfd  # powinno być crw-rw---- root render
```

### Problem: LAN (igc) — przerwy w połączeniu
```bash
# Trwałe wyłączenie EEE przez /etc/network/interfaces:
nano /etc/network/interfaces
# W bloku iface enp2s0:
# post-up ethtool -s enp2s0 eee off
```

### Problem: WiFi MT7925 — brak sieci
```bash
apt install firmware-linux firmware-linux-nonfree -y
# Jeśli nadal brak:
dmesg | grep mt7925
# Pobierz firmware ręcznie z: https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git
```

### Problem: Podman w LXC — Permission denied
```bash
# Kontener MUSI być privileged (unprivileged=0)
# I mieć features: nesting=1,keyctl=1
# Sprawdź w /etc/pve/lxc/100.conf:
grep -E "unprivileged|features" /etc/pve/lxc/100.conf
# unprivileged: 0
# features: nesting=1,keyctl=1
```

---

## Porty i Usługi

| Port | Usługa | Gdzie |
|------|---------|-------|
| 8006 | Proxmox Web UI (HTTPS) | host Proxmox |
| 22 | SSH Proxmox host | host Proxmox |
| 2222 | SSH LXC container | LXC |
| 8000 | KlimtechRAG backend | LXC |
| 8443 | KlimtechRAG HTTPS (nginx) | LXC |
| 8082 | llama-server (LLM) | LXC |
| 8083 | llama-server Qwen3 (GPU1) | LXC [PRZYSZŁOŚĆ] |
| 6333 | Qdrant REST | LXC |
| 6334 | Qdrant gRPC | LXC |

---

## Historia Zmian

| Data | Co dodano |
|------|-----------|
| 2026-04-08 | Opracowanie planu na podstawie istniejących skryptów server_setup/ i specyfiki sprzętu |
