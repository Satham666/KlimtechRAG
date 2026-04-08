#!/bin/bash
# =============================================================================
# KlimtechRAG — Faza 3: Migracja danych z dysków USB
# =============================================================================
# Uruchom gdy oba dyski są podłączone przez USB:
#   bash 03_data_migrate.sh
#
# Dyski USB:
#   - Stary dysk BACKUP (label: BACKUP) → /media/lobo/BACKUP lub /media/lobo/BACKUP1
#   - Stary dysk systemowy (label: systemowy) → /media/lobo/... (sprawdzamy)
#
# Co kopiuje:
#   1. data/uploads/    — dokumenty, pliki użytkownika
#   2. modele_LLM/      — modele GGUF (duże pliki!)
#   3. data/ssl/        — stary certyfikat SSL i konfiguracja nginx
#   4. .env             — stara konfiguracja środowiska
#   5. Podman volumes   — Qdrant vectors, Nextcloud data, PostgreSQL data
# =============================================================================

set -euo pipefail

# ── Zmienne ──────────────────────────────────────────────────────────────────
USERNAME="lobo"
NEW_BASE="/home/lobo/KlimtechRAG"
OLD_BASE_NAME="KlimtechRAG"
OLD_PATH_ON_BACKUP="/media/lobo/BACKUP/$OLD_BASE_NAME"    # stary dysk BACKUP
LOG="$HOME/install_phase3.log"

# Nazwy Podman volumes na starym systemie
VOL_QDRANT="klimtech_qdrant_data"
VOL_NEXTCLOUD="klimtech_nextcloud_data"
VOL_POSTGRES="klimtech_postgres_data"

# Podman volumes storage rootless: ~/.local/share/containers/storage/volumes/
OLD_PODMAN_VOLUMES_PATH=""   # wykrywane automatycznie poniżej

# ── Kolory ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}  $1" | tee -a "$LOG"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG"; }
fail() { echo -e "${RED}[FAIL]${NC} $1" | tee -a "$LOG"; exit 1; }
info() { echo -e "${CYAN}[INFO]${NC} $1" | tee -a "$LOG"; }
section() { echo "" | tee -a "$LOG"; echo "══════════════════════════════════════" | tee -a "$LOG"; echo "  $1" | tee -a "$LOG"; echo "══════════════════════════════════════" | tee -a "$LOG"; }

echo "KlimtechRAG — Faza 3: Migracja danych — $(date '+%Y-%m-%d %H:%M:%S')" | tee "$LOG"

# =============================================================================
section "0. Wykrywanie podłączonych dysków USB"
# =============================================================================
echo "" | tee -a "$LOG"
echo "  Dostępne zamontowane partycje:" | tee -a "$LOG"
lsblk -f 2>/dev/null | grep -E "(BACKUP|lobo|media|mnt)" | tee -a "$LOG" || true
echo "" | tee -a "$LOG"
echo "  Media w /media/lobo/:" | tee -a "$LOG"
ls /media/lobo/ 2>/dev/null | tee -a "$LOG" || warn "/media/lobo/ jest puste — czy dyski są podłączone?"
echo "" | tee -a "$LOG"

# Znajdź dysk BACKUP (może być BACKUP, BACKUP1 jeśli nowy dysk też miałby podobną nazwę)
BACKUP_DISK=""
for candidate in /media/lobo/BACKUP /media/lobo/BACKUP1 /media/lobo/backup; do
    if [ -d "$candidate/$OLD_BASE_NAME" ]; then
        BACKUP_DISK="$candidate"
        ok "Znaleziono dysk BACKUP: $BACKUP_DISK"
        break
    fi
done

if [ -z "$BACKUP_DISK" ]; then
    echo "" | tee -a "$LOG"
    warn "Nie znaleziono automatycznie dysku BACKUP z katalogiem KlimtechRAG"
    echo "  Dostępne katalogi w /media/lobo/:" | tee -a "$LOG"
    ls /media/lobo/ 2>/dev/null | tee -a "$LOG"
    echo ""
    read -r -p "  Podaj ścieżkę do katalogu KlimtechRAG na dysku BACKUP (np. /home/lobo/KlimtechRAG): " MANUAL_PATH
    if [ -d "$MANUAL_PATH" ]; then
        OLD_BACKUP_PROJECT="$MANUAL_PATH"
        BACKUP_DISK=$(dirname "$MANUAL_PATH")
        ok "Ścieżka: $OLD_BACKUP_PROJECT"
    else
        fail "Katalog nie istnieje: $MANUAL_PATH"
    fi
else
    OLD_BACKUP_PROJECT="$BACKUP_DISK/$OLD_BASE_NAME"
fi

# Znajdź dysk systemowy (stary system Ubuntu) — szukamy katalogu home/lobo
OLD_SYSTEM_DISK=""
OLD_SYSTEM_HOME=""
for mount_point in /media/lobo/*; do
    if [ -d "$mount_point/home/lobo" ]; then
        OLD_SYSTEM_DISK="$mount_point"
        OLD_SYSTEM_HOME="$mount_point/home/lobo"
        ok "Znaleziono stary dysk systemowy: $OLD_SYSTEM_DISK"
        break
    fi
done

if [ -z "$OLD_SYSTEM_DISK" ]; then
    warn "Nie znaleziono automatycznie starego dysku systemowego (z /home/lobo)"
    echo "  Wolumeny Podman (Qdrant, Nextcloud, PostgreSQL) są na dysku systemowym."
    echo "  Dostępne katalogi w /media/lobo/:" | tee -a "$LOG"
    ls /media/lobo/ 2>/dev/null | tee -a "$LOG"
    echo ""
    read -r -p "  Podaj ścieżkę do /home/lobo na starym dysku systemowym (lub Enter aby pominąć wolumeny): " OLD_SYSTEM_HOME_INPUT
    if [ -n "$OLD_SYSTEM_HOME_INPUT" ] && [ -d "$OLD_SYSTEM_HOME_INPUT" ]; then
        OLD_SYSTEM_HOME="$OLD_SYSTEM_HOME_INPUT"
        ok "Stary home: $OLD_SYSTEM_HOME"
    else
        warn "Dysk systemowy pominięty — wolumeny Podman nie zostaną zmigrowane"
        OLD_SYSTEM_HOME=""
    fi
fi

# Ścieżka do Podman volumes na starym systemie
if [ -n "$OLD_SYSTEM_HOME" ]; then
    OLD_PODMAN_VOLUMES_PATH="$OLD_SYSTEM_HOME/.local/share/containers/storage/volumes"
    if [ -d "$OLD_PODMAN_VOLUMES_PATH" ]; then
        ok "Wolumeny Podman znalezione: $OLD_PODMAN_VOLUMES_PATH"
    else
        warn "Nie znaleziono wolumenów Podman w $OLD_PODMAN_VOLUMES_PATH"
        OLD_PODMAN_VOLUMES_PATH=""
    fi
fi

# =============================================================================
section "1. Kopiowanie data/uploads/ (dokumenty RAG)"
# =============================================================================
OLD_UPLOADS="$OLD_BACKUP_PROJECT/data/uploads"
NEW_UPLOADS="$NEW_BASE/data/uploads"

if [ -d "$OLD_UPLOADS" ]; then
    mkdir -p "$NEW_UPLOADS"
    echo "Kopiowanie uploads (może chwilę potrwać)..." | tee -a "$LOG"
    rsync -av --progress "$OLD_UPLOADS/" "$NEW_UPLOADS/" 2>&1 | tee -a "$LOG"
    ok "uploads/ skopiowany"
    du -sh "$NEW_UPLOADS" | tee -a "$LOG"
else
    warn "Brak katalogu: $OLD_UPLOADS — pomijam"
fi

# =============================================================================
section "2. Kopiowanie modeli GGUF (modele_LLM/)"
# =============================================================================
# Modele mogą być na dysku BACKUP w katalogu projektu lub osobno
OLD_MODELS="$OLD_BACKUP_PROJECT/modele_LLM"
NEW_MODELS="$NEW_BASE/modele_LLM"

if [ -d "$OLD_MODELS" ]; then
    mkdir -p "$NEW_MODELS"
    echo "Kopiowanie modeli GGUF (DUŻE pliki — może trwać długo)..." | tee -a "$LOG"
    du -sh "$OLD_MODELS" | tee -a "$LOG"
    rsync -av --progress "$OLD_MODELS/" "$NEW_MODELS/" 2>&1 | tee -a "$LOG"
    ok "modele_LLM/ skopiowany"
else
    warn "Brak katalogu: $OLD_MODELS — pomijam (sprawdź czy modele są gdzie indziej)"
    info "Jeśli modele są w innym miejscu: rsync -av /ścieżka/do/modeli/ $NEW_MODELS/"
fi

# =============================================================================
section "3. Kopiowanie konfiguracji SSL i nginx"
# =============================================================================
OLD_SSL="$OLD_BACKUP_PROJECT/data/ssl"
NEW_SSL="$NEW_BASE/data/ssl"

if [ -d "$OLD_SSL" ]; then
    mkdir -p "$NEW_SSL"
    rsync -av "$OLD_SSL/" "$NEW_SSL/" 2>&1 | tee -a "$LOG"
    ok "data/ssl/ skopiowany (certyfikaty, nginx.conf)"
else
    warn "Brak $OLD_SSL — 02_project_setup.sh wygenerował nowy certyfikat SSL"
fi

# =============================================================================
section "4. Kopiowanie .env"
# =============================================================================
OLD_ENV="$OLD_BACKUP_PROJECT/.env"
NEW_ENV="$NEW_BASE/.env"

if [ -f "$OLD_ENV" ]; then
    if [ -f "$NEW_ENV" ]; then
        cp "$NEW_ENV" "${NEW_ENV}.backup_$(date +%Y%m%d_%H%M%S)"
        warn ".env już istnieje — backup zrobiony, nadpisuję starym"
    fi
    cp "$OLD_ENV" "$NEW_ENV"
    ok ".env skopiowany"

    # Zaktualizuj starą ścieżkę bazową na nową
    OLD_PATH_IN_ENV="/home/lobo/KlimtechRAG"
    if grep -q "$OLD_PATH_IN_ENV" "$NEW_ENV"; then
        sed -i "s|$OLD_PATH_IN_ENV|$NEW_BASE|g" "$NEW_ENV"
        ok ".env: ścieżka zaktualizowana ($OLD_PATH_IN_ENV → $NEW_BASE)"
    fi

    # Upewnij się że KLIMTECH_BASE_PATH jest ustawiony
    if ! grep -q "KLIMTECH_BASE_PATH" "$NEW_ENV"; then
        echo "KLIMTECH_BASE_PATH=$NEW_BASE" >> "$NEW_ENV"
        ok ".env: dodano KLIMTECH_BASE_PATH=$NEW_BASE"
    fi
else
    warn "Brak .env na starym dysku — użyj pliku wygenerowanego przez 02_project_setup.sh"
fi

# =============================================================================
section "5. Migracja wolumenów Podman"
# =============================================================================
if [ -z "$OLD_PODMAN_VOLUMES_PATH" ]; then
    warn "Pomijam migrację wolumenów Podman (dysk systemowy niedostępny)"
    echo ""
    info "Aby zmigrować wolumeny ręcznie gdy dysk będzie dostępny:"
    info "  bash 03_data_migrate.sh --volumes-only /media/lobo/<dysk>/home/lobo"
else
    # Funkcja migracji jednego wolumenu
    migrate_volume() {
        local VOL_NAME="$1"
        local OLD_VOL_PATH="$OLD_PODMAN_VOLUMES_PATH/$VOL_NAME/_data"
        local DESC="$2"

        if [ ! -d "$OLD_VOL_PATH" ]; then
            warn "Wolumin $VOL_NAME nie znaleziony: $OLD_VOL_PATH"
            return
        fi

        echo "Migracja: $VOL_NAME ($DESC)..." | tee -a "$LOG"
        du -sh "$OLD_VOL_PATH" | tee -a "$LOG"

        # Utwórz wolumin na nowym systemie jeśli nie istnieje
        if ! podman volume inspect "$VOL_NAME" &>/dev/null; then
            podman volume create "$VOL_NAME" 2>&1 | tee -a "$LOG"
        fi

        # Pobierz ścieżkę docelową woluminu
        NEW_VOL_PATH=$(podman volume inspect "$VOL_NAME" --format "{{.Mountpoint}}" 2>/dev/null)

        if [ -z "$NEW_VOL_PATH" ]; then
            warn "Nie można pobrać ścieżki woluminu $VOL_NAME"
            return
        fi

        # Kopiuj dane
        rsync -av --progress "$OLD_VOL_PATH/" "$NEW_VOL_PATH/" 2>&1 | tee -a "$LOG"
        ok "Wolumin $VOL_NAME zmigrowany → $NEW_VOL_PATH"
    }

    migrate_volume "$VOL_QDRANT"    "baza wektorów RAG"
    migrate_volume "$VOL_NEXTCLOUD" "pliki Nextcloud"
    migrate_volume "$VOL_POSTGRES"  "baza danych PostgreSQL"
fi

# =============================================================================
section "6. Kopiowanie workflow n8n"
# =============================================================================
OLD_N8N="$OLD_BACKUP_PROJECT/n8n_workflows"
NEW_N8N="$NEW_BASE/n8n_workflows"

if [ -d "$OLD_N8N" ]; then
    mkdir -p "$NEW_N8N"
    rsync -av "$OLD_N8N/" "$NEW_N8N/" 2>&1 | tee -a "$LOG"
    ok "n8n_workflows/ skopiowany"
fi

# =============================================================================
section "7. Kopiowanie MD_files i agentów"
# =============================================================================
for dir in MD_files agents; do
    OLD_DIR="$OLD_BACKUP_PROJECT/$dir"
    NEW_DIR="$NEW_BASE/$dir"
    if [ -d "$OLD_DIR" ]; then
        mkdir -p "$NEW_DIR"
        rsync -av "$OLD_DIR/" "$NEW_DIR/" 2>&1 | tee -a "$LOG"
        ok "$dir/ skopiowany"
    fi
done

# =============================================================================
section "WERYFIKACJA"
# =============================================================================
echo "" | tee -a "$LOG"
echo "  Rozmiar katalogów po migracji:" | tee -a "$LOG"
du -sh "$NEW_BASE/data/uploads" 2>/dev/null | tee -a "$LOG" || echo "  data/uploads: brak" | tee -a "$LOG"
du -sh "$NEW_BASE/modele_LLM" 2>/dev/null | tee -a "$LOG" || echo "  modele_LLM: brak" | tee -a "$LOG"
du -sh "$NEW_BASE" 2>/dev/null | tee -a "$LOG"
echo "" | tee -a "$LOG"

echo "  Wolumeny Podman:" | tee -a "$LOG"
podman volume ls 2>/dev/null | tee -a "$LOG"

# =============================================================================
section "PODSUMOWANIE"
# =============================================================================
echo ""
echo "  ✓ Dane zmigrowane do $NEW_BASE"
echo ""
echo "  ★ NASTĘPNE KROKI:"
echo "    1. Sprawdź .env: nano $NEW_BASE/.env"
echo "       (upewnij się że IP serwera jest aktualne)"
echo ""
echo "    2. Uruchom system:"
echo "       cd $NEW_BASE"
echo "       source venv/bin/activate.fish   # w fish"
echo "       python3 start_klimtech_v3.py"
echo ""
echo "    3. Weryfikacja:"
echo "       curl -k https://localhost:8443/health"
echo "       curl http://localhost:6333/healthz"
echo ""
echo "    4. Sprawdź skrypt health check:"
echo "       bash $NEW_BASE/scripts/check_project.sh"
echo ""
echo "Log: $LOG"
