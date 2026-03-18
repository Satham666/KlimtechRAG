#!/bin/bash
# ==============================================================================
# KLIMTECHRAG - FIX NEXTCLOUD HYBRID STORAGE (Wersja Poprawna)
# ==============================================================================
# Rozwiązuje problem: PostgreSQL nie działa na exFAT.
# Rozwiązanie: Baza danych na Named Volume (ext4), pliki userów na exFAT.
# Kontenery wewnątrz Poda (wspólne localhost).
# ==============================================================================

set -e

# --- KONFIGURACJA ---
BASE_PATH="/media/lobo/BACKUP/KlimtechRAG"
NEXTCLOUD_DATA_DIR="${BASE_PATH}/data/nextcloud"
NEXTCLOUD_USER_DATA="${BASE_PATH}/data/nextcloud_data"

# Dane dostępowe do bazy
DB_NAME="nextcloud"
DB_USER="nextcloud"
DB_PASS="klimtech123"

# Nazwy
C_POSTGRES="postgres_nextcloud"
C_NEXTCLOUD="nextcloud"
POD_NAME="klimtech_pod"

# --- START ---

if [ ! -d "$BASE_PATH" ]; then
    echo "BŁĄD: Nie znaleziono katalogu projektu: $BASE_PATH"
    exit 1
fi

podman rm -f postgres_nextcloud nextcloud
podman pod ls
podman pod rm -f klimtech



echo "=== ZATRZYMANIE I CZYSZCZENIE STARYCH KONTENERÓW ==="
# Zatrzymujemy kontenery (mogą być poza podem)
podman stop $C_NEXTCLOUD 2>/dev/null || true
podman rm $C_NEXTCLOUD 2>/dev/null || true
podman stop $C_POSTGRES 2>/dev/null || true
podman rm $C_POSTGRES 2>/dev/null || true
# Usuwamy stary Pod (jeśli istnieje)
podman pod rm -f $POD_NAME 2>/dev/null || true
echo "   Czyszczenie zakończone."

echo ""
echo "=== PRZYGOTOWANIE WOLUMENU DLA POSTGRES (ext4) ==="
if ! podman volume exists klimtech_postgres_data; then
    podman volume create klimtech_postgres_data
    echo "   Utworzono wolumen 'klimtech_postgres_data'"
else
    echo "   Wolumen 'klimtech_postgres_data' już istnieje"
fi

echo ""
echo "=== TWORZENIE PODA '$POD_NAME' ==="
# Tworzymy Pod z mapowaniem portu 8081 na hosta
podman pod create --name $POD_NAME -p 8081:80
echo "   Pod utworzony."

echo ""
echo "=== URUCHAMIANIE POSTGRESQL (W PODZIE) ==="
# Uruchamiamy w Podzie (--pod $POD_NAME)
# Dzięki temu Nextcloud zobaczy go na localhost
podman run -d \
    --name $C_POSTGRES \
    --pod $POD_NAME \
    --restart always \
    -e POSTGRES_DB=$DB_NAME \
    -e POSTGRES_USER=$DB_USER \
    -e POSTGRES_PASSWORD=$DB_PASS \
    -v klimtech_postgres_data:/var/lib/postgresql/data \
    docker.io/library/postgres:16

if [ $? -ne 0 ]; then
    echo "BŁĄD: Nie udało się uruchomić Postgres."
    exit 1
fi
echo "   PostgreSQL uruchomiony w Podzie."
sleep 5

echo ""
echo "=== PRZYGOTOWANIE KATALOGÓW NA exFAT ==="
mkdir -p "$NEXTCLOUD_DATA_DIR"
mkdir -p "$NEXTCLOUD_USER_DATA"

# Backup konfiguracji, żeby wymusić czystą instalację
if [ -f "$NEXTCLOUD_DATA_DIR/config/config.php" ]; then
    echo "   Backup config.php -> config.php.bak_hybrid_fix"
    mv "$NEXTCLOUD_DATA_DIR/config/config.php" "$NEXTCLOUD_DATA_DIR/config/config.php.bak_hybrid_fix"
fi

echo ""
echo "=== URUCHAMIANIE NEXTCLOUD (W PODZIE) ==="
# Uruchamiamy w tym samym Podzie
# Łączymy się z Postgresem przez 'localhost'
podman run -d \
    --name $C_NEXTCLOUD \
    --pod $POD_NAME \
    --restart always \
    -e POSTGRES_HOST="localhost" \
    -e POSTGRES_DB=$DB_NAME \
    -e POSTGRES_USER=$DB_USER \
    -e POSTGRES_PASSWORD=$DB_PASS \
    -e NEXTCLOUD_TRUSTED_DOMAINS="192.168.31.70 localhost" \
    -v "$NEXTCLOUD_DATA_DIR:/var/www/html" \
    -v "$NEXTCLOUD_USER_DATA:/var/www/html/data" \
    docker.io/library/nextcloud:32

if [ $? -ne 0 ]; then
    echo "BŁĄD: Nie udało się uruchomić Nextcloud."
    exit 1
fi
echo "   Nextcloud uruchomiony w Podzie."

echo ""
echo "=== KONFIGURACJA NEXTCLOUD (PO INICJALIZACJI) ==="
echo "   Czekam 20 sekund na start aplikacji..."
sleep 20

# Instalacja aplikacji
echo "   Instalacja integration_openai..."
podman exec $C_NEXTCLOUD occ app:install integration_openai 2>/dev/null || echo "   (już zainstalowane)"
echo "   Instalacja assistant..."
podman exec $C_NEXTCLOUD occ app:install assistant 2>/dev/null || echo "   (już zainstalowane)"

# Konfiguracja systemowa
echo "   Ustawienia systemowe..."
podman exec $C_NEXTCLOUD occ config:system:set check_data_directory_permissions --value=false --type=boolean
podman exec $C_NEXTCLOUD occ config:system:set filelocking.enabled --value=false --type=boolean
podman exec $C_NEXTCLOUD occ config:system:set allow_local_remote_servers --value=true --type=boolean

# HTTPS
podman exec $C_NEXTCLOUD occ config:system:set overwriteprotocol --value="https"
podman exec $C_NEXTCLOUD occ config:system:set overwritehost --value="192.168.31.70:8444"

echo ""
echo "======================================================================"
echo "SUKCES! Nextcloud działa w trybie HYBRYDOWYM."
echo "======================================================================"
echo "  HTTP:  http://192.168.31.70:8081"
echo "  HTTPS: https://192.168.31.70:8444"
echo "  Login: admin / klimtech123"
echo ""
echo "  Baza danych: Wolumen 'klimtech_postgres_data' (ext4 - bezpieczna)"
echo "  Pliki:       $NEXTCLOUD_USER_DATA (exFAT)"
echo ""
echo "  Konfiguracja AI w panelu admina:"
echo "    URL: http://192.168.31.70:8000"
echo "    Key: sk-local"
echo "======================================================================"
