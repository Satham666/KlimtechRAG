#!/bin/bash
# KlimtechRAG — przywracanie baz SQLite z backupu
# Użycie: bash scripts/restore.sh <katalog_backupu>
# Przykład: bash scripts/restore.sh backups/2026-04-06_14-30

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data"

if [ -z "$1" ]; then
    echo "Użycie: bash scripts/restore.sh <katalog_backupu>"
    echo ""
    echo "Dostępne backupy:"
    ls -1t "$PROJECT_DIR/backups/" 2>/dev/null || echo "  (brak backupów)"
    exit 1
fi

BACKUP_DIR="$1"
if [ ! -d "$BACKUP_DIR" ]; then
    BACKUP_DIR="$PROJECT_DIR/backups/$1"
fi
if [ ! -d "$BACKUP_DIR" ]; then
    echo "BŁĄD: katalog backupu nie istnieje: $BACKUP_DIR"
    exit 1
fi

echo "KlimtechRAG Restore — $(date '+%Y-%m-%d %H:%M:%S')"
echo "Źródło: $BACKUP_DIR"
echo ""
echo "UWAGA: Ta operacja NADPISZE aktualne bazy danych!"
echo "Wpisz 'tak' aby kontynuować:"
read -r CONFIRM
if [ "$CONFIRM" != "tak" ]; then
    echo "Anulowano."
    exit 0
fi

restore_db() {
    local name="$1"
    local src="$BACKUP_DIR/$name"
    local dst="$DATA_DIR/$name"
    if [ ! -f "$src" ]; then
        echo "  [SKIP] $name — brak w backupie"
        return
    fi
    # Backup aktualnej bazy przed nadpisaniem
    if [ -f "$dst" ]; then
        cp "$dst" "${dst}.pre_restore"
        echo "  [BAK]  Kopia bezpieczeństwa: ${dst}.pre_restore"
    fi
    cp "$src" "$dst"
    echo "  [OK]   $name przywrócony ($(du -h "$dst" | cut -f1))"
}

echo "── Przywracanie baz SQLite ──────────────────"
restore_db "file_registry.db"
restore_db "sessions.db"

echo ""
echo "Restore zakończony. Uruchom ponownie backend aby załadować zmiany."
