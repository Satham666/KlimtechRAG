# security.md — Hardening i Bezpieczeństwo Serwera KlimtechRAG
*Zasady bezpieczeństwa dla Proxmox host + LXC container.*

---

## Powierzchnia Ataku — Porównanie

| | Proxmox VE | Ubuntu Server | Ubuntu Desktop |
|--|------------|---------------|----------------|
| Uruchomione usługi domyślnie | ~15 | ~20 | ~60+ |
| Środowisko graficzne | ❌ | ❌ | ✅ (X11/Wayland) |
| Bluetooth daemon | ❌ | ❌ | ✅ |
| Avahi (mDNS) | ❌ | ❌ | ✅ |
| CUPS (drukarka) | ❌ | ❌ | ✅ |
| Izolacja workloadów | ✅ LXC/VM | ❌ | ❌ |
| Ocena security | ✅✅ | ✅✅ | ⚠️ |

**Ubuntu Desktop jako serwer = NIE RÓB TEGO** — zbyt duża powierzchnia ataku.  
Znane przykłady: CUPS CVE-2024-47176 (RCE), X11 historyczne podatności.

---

## Izolacja przez Proxmox LXC

```
Internet/Sieć lokalna
    ↓
Proxmox host (Debian minimal, tylko SSH + port 8006)
    ↓
LXC Container (Ubuntu 24.04)
    ↓
KlimtechRAG / llama-server

Jeśli KlimtechRAG zostanie zhackowany:
  → atakujący jest WEWNĄTRZ kontenera
  → host Proxmox jest częściowo chroniony
  → bez eskalacji uprawnień nie wyjdzie z kontenera
```

---

## SSH — Hardening (LXC i host Proxmox)

```bash
nano /etc/ssh/sshd_config
```

```
Port 2222                     # zmień domyślny port 22
PasswordAuthentication no     # tylko klucze SSH (ustaw PO dodaniu klucza!)
PermitRootLogin no            # zakaz logowania jako root
PubkeyAuthentication yes
MaxAuthTries 3
LoginGraceTime 30
```

```bash
systemctl restart ssh
```

### Dodaj klucz SSH (z laptopa)
```bash
# Na laptopie:
ssh-copy-id -i ~/.ssh/id_rsa.pub -p 2222 lobo@192.168.31.71

# Lub ręcznie:
cat ~/.ssh/id_rsa.pub  # skopiuj zawartość
# Na serwerze:
mkdir -p ~/.ssh && nano ~/.ssh/authorized_keys  # wklej klucz
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
```

---

## Firewall — ufw (LXC container)

```bash
apt install ufw -y

ufw default deny incoming
ufw default allow outgoing

# Porty do otwarcia:
ufw allow 2222/tcp                              # SSH (nowy port)
ufw allow 8443/tcp                              # KlimtechRAG HTTPS

# Qdrant — TYLKO z sieci lokalnej (nie eksponuj na internet!):
ufw allow from 192.168.31.0/24 to any port 6333

# Opcjonalnie jeśli potrzebujesz:
# ufw allow 8082/tcp  # llama-server
# ufw allow 8083/tcp  # Qwen3 (przyszłość)

ufw enable
ufw status verbose
```

---

## Fail2ban — ochrona przed brute force

```bash
apt install fail2ban -y

# Konfiguracja SSH jail:
nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 3

[sshd]
enabled  = true
port     = 2222
logpath  = %(sshd_log)s
backend  = systemd
```

```bash
systemctl enable fail2ban
systemctl start fail2ban

# Sprawdź status:
fail2ban-client status sshd
```

---

## Proxmox Web UI — ograniczenie dostępu

Proxmox web UI działa na porcie **8006** — powinien być dostępny TYLKO z sieci lokalnej.

```bash
# Na hoście Proxmox — Firewall (przez web UI lub CLI):
# Datacenter → Firewall → Add rule:
# Direction: IN, Action: ACCEPT, Source: 192.168.31.0/24, Dest port: 8006

# Blokuj 8006 z zewnątrz:
# Direction: IN, Action: DROP, Source: !192.168.31.0/24, Dest port: 8006
```

### Dodaj 2FA do Proxmox
```
Proxmox web UI → Datacenter → Permissions → Two Factor
→ Add TOTP (Google Authenticator / Aegis)
```

---

## Zmienne środowiskowe — sekrety

```bash
# NIGDY nie commituj .env do git!
echo ".env" >> /home/lobo/KlimtechRAG/.gitignore

# API key — zmień domyślny:
nano /home/lobo/KlimtechRAG/.env
# KLIMTECH_API_KEY=sk-local-ZMIEN-NA-LOSOWY-STRING

# Generuj losowy klucz:
python3 -c "import secrets; print('sk-local-' + secrets.token_hex(16))"
```

---

## Qdrant — nie eksponuj na internet

```bash
# Qdrant NIE powinien być dostępny z zewnątrz sieci lokalnej
# Domyślnie słucha na 0.0.0.0:6333 — ogranicz przez ufw:
ufw allow from 192.168.31.0/24 to any port 6333
ufw deny 6333  # blokuj resztę

# Lub ogranicz bind address w konfiguracji Qdrant:
# W /home/lobo/qdrant_storage/config/config.yaml:
# service:
#   host: 127.0.0.1  # tylko localhost
```

---

## Aktualizacje — harmonogram

```bash
# Proxmox host — raz w tygodniu:
apt update && apt dist-upgrade -y

# LXC container — raz w tygodniu:
apt update && apt upgrade -y

# Sprawdź podatności w Python packages:
cd /home/lobo/KlimtechRAG
source venv/bin/activate
pip audit  # wymaga: pip install pip-audit
```

---

## Monitoring — co sprawdzać

```bash
# Logowane próby logowania SSH:
journalctl -u ssh | grep "Failed\|Invalid" | tail -20

# Aktywne blokady fail2ban:
fail2ban-client status sshd

# Otwarte porty:
ss -tlnp

# Podejrzane procesy:
ps aux | grep -v "root\|lobo\|systemd" | head -20

# Miejsca na dysku (logs mogą rosnąć):
du -sh /var/log/* | sort -h | tail -10
```

---

## Zakazy Bezwzględne (z CLAUDE.md)

```
❌ eval() / exec() / pickle.loads() na danych od użytkownika
❌ shell=True w subprocess
❌ Commit .env lub kluczy API do git
❌ Nowy endpoint bez require_api_key()
❌ Qdrant na publicznym IP bez auth
❌ Hasło SSH — tylko klucze
❌ Proxmox web UI dostępny z internetu bez VPN/tunelu
```

---

## Ranking Bezpieczeństwa (rekomendacja)

```
1. Proxmox VE + Ubuntu LXC + ufw + SSH keys + fail2ban + 2FA
   → Najlepsza izolacja, snapshoty, minimalna powierzchnia ataku

2. Ubuntu Server 24.04 + ufw + SSH keys + fail2ban
   → Dobre, prostsze, brak izolacji kontenerów

3. Ubuntu Desktop jako serwer
   → NIE — zbyt duża powierzchnia ataku
```
