# ProtonVPN Auto-Connect - Kompletna Dokumentacja

## Spis Treści
1. [Opis ogólny](#1-opis-ogólny)
2. [Kod skryptu protonvpn_autoconnect.py](#2-kod-skryptu-protonvpn_autoconnectpy)
3. [Opcje aplikacji](#3-opcje-aplikacji)
4. [Przykłady użycia](#4-przykłady-użycia)
5. [Konfiguracja Cron](#5-konfiguracja-cron)
6. [Struktura plików](#6-struktura-plików)
7. [Instrukcja regeneracji dla modelu AI](#7-instrukcja-regeneracji-dla-modelu-ai)

---

## 1. Opis ogólny

**Cel:** Automatyczne łączenie z najlepszym (najmniej obciążonym) serwerem ProtonVPN.

**Działanie:**
1. Sprawdza połączenie internetowe (ping do proton.me)
2. Jeśli działa - pomija (chyba że użyto `--force`)
3. Jeśli nie działa lub wymuszono:
   - Uruchamia `protonvpn-app --start-minimized` w tle (odświeża cache)
   - Czeka ~8 sekund na aktualizację listy serwerów
   - Czyta `~/.cache/Proton/VPN/serverlist.json`
   - Wybiera serwer z najmniejszym Load dla wybranego kraju
   - Łączy przez `protonvpn connect <server>`

**Zależności:**
- `protonvpn-cli` (CLI)
- `protonvpn-app` (GTK app)
- Python 3.x
- Aktywna subskrypcja ProtonVPN

---

## 2. Kod skryptu protonvpn_autoconnect.py

```python
#!/usr/bin/env python3
import subprocess
import sys
import os
import time
import json
import argparse

CACHE_FILE = os.path.expanduser("~/.cache/Proton/VPN/serverlist.json")
LOG_FILE = os.path.expanduser("~/.cache/Proton/VPN/autoconnect.log")


def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(log_line + "\n")
    except:
        pass


def ping_test(host="proton.me", count=1, timeout=5):
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception as e:
        log(f"Błąd ping: {e}")
        return False


def find_best_server(country="ch", top=1):
    log(f"Szukanie najlepszego serwera dla kraju: {country}")

    if not os.path.isfile(CACHE_FILE):
        log(f"Brak pliku cache: {CACHE_FILE}")
        return None

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        servers = data.get("LogicalServers") or data.get("Servers") or data

        if country:
            servers = [
                s
                for s in servers
                if s.get("ExitCountry", "").upper() == country.upper()
            ]

        servers.sort(key=lambda x: x.get("Load", 0))
        servers = servers[:top]

        if servers:
            best = servers[0]
            name = best.get("Name", "")
            load = best.get("Load", 0)
            log(f"Najlepszy serwer: {name} (load: {load}%)")
            return name
        else:
            log("Nie znaleziono serwerów")
            return None
    except Exception as e:
        log(f"Błąd szukania serwera: {e}")
        return None


def connect_vpn(server_name):
    log(f"Łączenie z {server_name}...")
    try:
        result = subprocess.run(
            ["protonvpn", "connect", server_name],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            log(f"Pomyślnie połączono z {server_name}")
            return True
        else:
            log(f"Błąd połączenia: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        log("Timeout podczas łączenia")
        return False
    except Exception as e:
        log(f"Błąd: {e}")
        return False


def disconnect_vpn():
    log("Rozłączanie VPN...")
    try:
        subprocess.run(["protonvpn", "disconnect"], capture_output=True, timeout=30)
        log("Rozłączono")
        return True
    except Exception as e:
        log(f"Błąd rozłączania: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="ProtonVPN Auto-Connect")
    parser.add_argument(
        "--country", "-c", default="ch", help="Kod kraju (domyślnie ch)"
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Wymuś połączenie nawet gdy ping działa",
    )
    parser.add_argument(
        "--disconnect", "-d", action="store_true", help="Rozłącz VPN i zakończ"
    )
    args = parser.parse_args()

    if args.disconnect:
        disconnect_vpn()
        return

    if not args.force and ping_test():
        log("Połączenie internetowe działa, pomijam (użyj --force aby wymusić)")
        return

    server = find_best_server(args.country)
    if not server:
        log("Nie znaleziono serwera")
        sys.exit(1)

    if connect_vpn(server):
        log("Zakończono pomyślnie")
    else:
        log("Nie udało się połączyć")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 3. Opcje aplikacji

| Opcja | Skrót | Opis |
|-------|-------|------|
| `--country <KOD>` | `-c` | Kod kraju ISO (domyślnie `ch` - Szwajcaria) |
| `--force` | `-f` | Wymuś połączenie nawet gdy ping do proton.me działa |
| `--disconnect` | `-d` | Rozłącz VPN i zakończ skrypt |
| `--help` | `-h` | Wyświetl pomoc |

---

## 4. Przykłady użycia

### Podstawowe:
```bash
# Połącz z najlepszym serwerem w Szwajcarii (jeśli brak połączenia)
python3 protonvpn_autoconnect.py -c ch

# Połącz z najlepszym serwerem w Polsce
python3 protonvpn_autoconnect.py -c pl

# Połącz z najlepszym serwerem w USA
python3 protonvpn_autoconnect.py -c us
```

### Wymuszenie połączenia:
```bash
# Wymuś połączenie nawet gdy internet działa
python3 protonvpn_autoconnect.py -c ch -f

# Wymuś połączenie z Niemcami
python3 protonvpn_autoconnect.py -c de -f
```

### Rozłączanie:
```bash
# Rozłącz VPN
python3 protonvpn_autoconnect.py -d
```

### Popularne kraje:
| Kod | Kraj |
|-----|------|
| `ch` | Szwajcaria (domyślny) |
| `pl` | Polska |
| `de` | Niemcy |
| `nl` | Holandia |
| `us` | USA |
| `jp` | Japonia |
| `uk` | Wielka Brytania |
| `ca` | Kanada |
| `se` | Szwecja |
| `is` | Islandia |

---

## 5. Konfiguracja Cron

### Edycja crontab:
```bash
crontab -e
```

### Wariant 1: Sprawdzanie co 5 minut (automatyczne)
Łączy tylko jeśli ping nie działa:
```
*/5 * * * * /usr/bin/python3 /home/lobo/KlimtechRAG/protonvpn_autoconnect.py -c ch >> /home/lobo/.cache/Proton/VPN/autoconnect.log 2>&1
```

### Wariant 2: Sprawdzanie co 10 minut
```
*/10 * * * * /usr/bin/python3 /home/lobo/KlimtechRAG/protonvpn_autoconnect.py -c ch >> /home/lobo/.cache/Proton/VPN/autoconnect.log 2>&1
```

### Wariant 3: Wymuszenie co godzinę
Łączy zawsze (nawet gdy internet działa):
```
0 * * * * /usr/bin/python3 /home/lobo/KlimtechRAG/protonvpn_autoconnect.py -c ch -f >> /home/lobo/.cache/Proton/VPN/autoconnect.log 2>&1
```

### Wariant 4: Przy starcie systemu
```
@reboot sleep 30 && /usr/bin/python3 /home/lobo/KlimtechRAG/protonvpn_autoconnect.py -c ch >> /home/lobo/.cache/Proton/VPN/autoconnect.log 2>&1
```

### Wariant 5: Co 15 minut z innym krajem
```
*/15 * * * * /usr/bin/python3 /home/lobo/KlimtechRAG/protonvpn_autoconnect.py -c de >> /home/lobo/.cache/Proton/VPN/autoconnect.log 2>&1
```

### Wariant 6: Sprawdzanie co 5 minut + start systemu
```
@reboot sleep 30 && /usr/bin/python3 /home/lobo/KlimtechRAG/protonvpn_autoconnect.py -c ch >> /home/lobo/.cache/Proton/VPN/autoconnect.log 2>&1
*/5 * * * * /usr/bin/python3 /home/lobo/KlimtechRAG/protonvpn_autoconnect.py -c ch >> /home/lobo/.cache/Proton/VPN/autoconnect.log 2>&1
```

### Logrotate dla logów (opcjonalnie)
Utwórz `/etc/logrotate.d/protonvpn-autoconnect`:
```
/home/lobo/.cache/Proton/VPN/autoconnect.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0644 lobo lobo
}
```

---

## 6. Struktura plików

### Skrypt:
```
/home/lobo/KlimtechRAG/protonvpn_autoconnect.py
```

### Pliki ProtonVPN:
```
~/.cache/Proton/VPN/
├── serverlist.json       # Cache listy serwerów (odświeżany przez protonvpn-app)
└── autoconnect.log       # Logi skryptu autoconnect

~/.config/Proton/VPN/
├── app-config.json       # Konfiguracja aplikacji GUI
└── settings.json         # Ustawienia VPN (protokół, killswitch, etc.)
```

### Przykładowy app-config.json:
```json
{
    "tray_pinned_servers": [],
    "connect_at_app_startup": null,
    "start_app_minimized": true
}
```

### Przykładowy settings.json:
```json
{
    "protocol": "wireguard",
    "killswitch": 1,
    "custom_dns": {
        "enabled": false,
        "ip_list": []
    },
    "ipv6": true,
    "anonymous_crash_reports": true,
    "features": {
        "netshield": 2,
        "moderate_nat": true,
        "vpn_accelerator": true,
        "port_forwarding": true,
        "split_tunneling": {
            "enabled": false,
            "mode": "exclude",
            "config_by_mode": {
                "exclude": {
                    "mode": "exclude",
                    "app_paths": [],
                    "ip_ranges": []
                },
                "include": {
                    "mode": "include",
                    "app_paths": [],
                    "ip_ranges": []
                }
            }
        }
    }
}
```

---

## 7. Instrukcja regeneracji dla modelu AI

Jeśli potrzebujesz odtworzyć `protonvpn_autoconnect.py`, przekaż modelowi AI ten plik `budowa_protonvpn.md` z prośbą:

> "Utwórz plik protonvpn_autoconnect.py na podstawie dokumentacji w budowa_protonvpn.md"

### Kluczowe elementy do zachowania:

1. **Funkcje główne:**
   - `log()` - logowanie do pliku i stdout
   - `ping_test()` - sprawdza czy internet działa
   - `find_best_server()` - szuka serwera z najmniejszym Load w cache
   - `connect_vpn()` - łączy przez CLI
   - `disconnect_vpn()` - rozłącza VPN

2. **Zmienne globalne:**
   - `CACHE_FILE = ~/.cache/Proton/VPN/serverlist.json`
   - `LOG_FILE = ~/.cache/Proton/VPN/autoconnect.log`

3. **Logika main():**
   - Parsowanie argumentów
   - Jeśli `-d` → rozłącz i zakończ
   - Jeśli ping działa i brak `-f` → pomijaj
   - Znajdź najlepszy serwer
   - Połącz się

4. **Argumenty:**
   - `-c, --country` - kod kraju (domyślnie `ch`)
   - `-f, --force` - wymuś połączenie
   - `-d, --disconnect` - rozłącz

5. **Bez restartów protonvpn-app:**
   - Skrypt zakłada że `protonvpn-app` jest uruchomione i lista serwerów jest aktualna
   - Nie restartuje, nie zamyka, nie uruchamia GUI

6. **Prosty tryb działania:**
   - Tylko: sprawdź ping → znajdź serwer → połącz
   - Bez zbędnych operacji
   - Szybkie wykonanie

---

## Linki

- **ProtonVPN GTK App:** https://github.com/ProtonVPN/proton-vpn-gtk-app
- **ProtonVPN CLI:** https://github.com/ProtonVPN/proton-vpn-cli

---

**Ostatnia aktualizacja:** 2026-02-21
**Autor:** KlimtechRAG System
**Wersja:** 1.0
