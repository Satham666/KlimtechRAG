#!/bin/bash
# KlimtechRAG - Trust self-signed certificate system-wide
# ======================================================
# WERSJA DLA LAPTOPA: Pobiera certyfikat z serwera i dodaje do systemu
# Po wykonaniu: zamknij i otwórz WaveTerm ponownie

set -e

# === KONFIGURACJA ===
SERVER_IP="192.168.31.70"
SERVER_USER="lobo"
SERVER_CERT_PATH="/home/lobo/KlimtechRAG/data/ssl/klimtech.crt"
LOCAL_CERT="/tmp/klimtech.crt"
TARGET_DIR="/usr/local/share/ca-certificates"

echo "=== KlimtechRAG: Trusting self-signed certificate ==="
echo ""

# === KROK 1: Pobierz certyfikat z serwera ===
echo "[1/4] Pobieranie certyfikatu z serwera $SERVER_IP..."
echo "      Źródło: $SERVER_USER@$SERVER_IP:$SERVER_CERT_PATH"
echo "      Cel: $LOCAL_CERT"
echo ""

if ! scp "$SERVER_USER@$SERVER_IP:$SERVER_CERT_PATH" "$LOCAL_CERT" 2>/dev/null; then
    echo "ERROR: Nie udało się pobrać certyfikatu przez SCP."
    echo "      Sprawdź czy:"
    echo "      - SSH działa na serwerze"
    echo "      - Masz dostęp SSH do $SERVER_USER@$SERVER_IP"
    echo "      - Plik istnieje na serwerze"
    exit 1
fi

echo "      Certyfikat pobrany pomyślnie."
echo ""

# === KROK 2: Sprawdź certyfikat ===
echo "[2/4] Weryfikacja certyfikatu..."
openssl x509 -in "$LOCAL_CERT" -noout -subject -issuer
echo ""

# === KROK 3: Kopiuj do systemowego store'a ===
echo "[3/4] Kopiowanie certyfikatu do $TARGET_DIR..."
sudo cp "$LOCAL_CERT" "$TARGET_DIR/klimtech.crt"

# === KROK 4: Aktualizuj CA certificates ===
echo "[4/4] Aktualizacja magazynu certyfikatów..."
sudo update-ca-certificates

echo ""
echo "=== SUKCES ==="
echo "Certyfikat '$SERVER_IP' dodany do systemu."
echo ""
echo "UWAGA: Zamknij WaveTerm i otwórz ponownie!"
echo ""

# === SPRZĄTANIE ===
echo "Usuwam tymczasowy certyfikat z /tmp..."
rm -f "$LOCAL_CERT"
echo "Gotowe."
echo ""
echo "Jeśli nadal nie działa, spróbuj:"
echo "  sudo apt install ca-certificates"
echo "  sudo update-ca-certificates --fresh"
echo "  # lub uruchom ponownie system"
