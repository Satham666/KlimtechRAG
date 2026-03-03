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
