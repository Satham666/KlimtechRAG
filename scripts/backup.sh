#!/bin/bash
# KlimtechRAG — backup baz danych SQLite
# Użycie: bash scripts/backup.sh [katalog_docelowy]
# Domyślnie zapisuje do: {BASE}/backups/YYYY-MM-DD_HH-MM/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data"
BACKUP_ROOT="${1:-$PROJECT_DIR/backups}"
TIMESTAMP="$(date +%Y-%m-%d_%H-%M)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"

mkdir -p "$BACKUP_DIR"

echo "KlimtechRAG Backup — $TIMESTAMP"
echo "Cel: $BACKUP_DIR"
echo ""

backup_db() {
    local src="$1"
    local name="$(basename "$src")"
    if [ ! -f "$src" ]; then
        echo "  [SKIP] $name — brak pliku"
        return
    fi
    local dst="$BACKUP_DIR/$name"
    sqlite3 "$src" ".backup '$dst'" 2>/dev/null || cp "$src" "$dst"
    local size=$(du -h "$dst" 2>/dev/null | cut -f1)
    echo "  [OK]   $name → $dst ($size)"
}

echo "── Bazy SQLite ──────────────────────────────"
backup_db "$DATA_DIR/file_registry.db"
backup_db "$DATA_DIR/sessions.db"

echo ""
echo "── Czyszczenie starych backupów (> 7 dni) ───"
find "$BACKUP_ROOT" -maxdepth 1 -type d -mtime +7 -exec echo "  Usuwam: {}" \; -exec rm -rf {} \; 2>/dev/null || true

echo ""
TOTAL=$(ls "$BACKUP_DIR" | wc -l)
echo "Backup zakończony: $TOTAL plików w $BACKUP_DIR"
