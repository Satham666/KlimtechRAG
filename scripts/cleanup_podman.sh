#!/bin/bash
# KlimtechRAG - Podman Cleanup Script
# Usuwa nieużywane kontenery i obrazy

echo "=========================================="
echo "  Podman Cleanup - KlimtechRAG"
echo "=========================================="

# Lista kontenerów do usunięcia (nieaktywne/nieużywane)
KONTENERE_USUN="open-webui postgres_nextcloud nextcloud"

# Kolejność usunięcia: kontenery → obrazy → cleanup systemu

echo ""
echo "[1/4] Zatrzymywanie i usuwanie kontenerów..."

for nazwa in $KONTENERE_USUN; do
    if podman ps -a --format "{{.Names}}" | grep -q "^${nazwa}$"; then
        echo "   - Zatrzymuję: $nazwa"
        podman stop "$nazwa" 2>/dev/null
        echo "   - Usuwam: $nazwa"
        podman rm "$nazwa" 2>/dev/null
        echo "   ✓ $nazwa usunięty"
    else
        echo "   - $nazwa nie istnieje (pominięto)"
    fi
done

echo ""
echo "[2/4] Usuwanie nieużywanych obrazów..."

# Usuń konkretne nieużywane obrazy
OBRAZY_USUN="ghcr.io/open-webui/open-webui docker.io/library/postgres"

for obraz in $OBRAZY_USUN; do
    if podman images --format "{{.Repository}}" | grep -q "^${obraz}$"; then
        echo "   - Usuwam obraz: $obraz"
        podman rmi "$obraz" 2>/dev/null && echo "   ✓ $obraz usunięty" || echo "   ! $obraz - błąd lub w użyciu"
    else
        echo "   - $obraz nie istnieje (pominięto)"
    fi
done

echo ""
echo "[3/4] Prune dangling images..."
podman image prune -f 2>/dev/null
echo "   ✓ Dangling images usunięte"

echo ""
echo "[4/4] Podman system prune..."
podman system prune -f 2>/dev/null
echo "   ✓ System cleanup wykonany"

echo ""
echo "=========================================="
echo "  STATUS PO CLEANUP"
echo "=========================================="

echo ""
echo "Aktywne kontenery:"
podman ps --format "   {{.Names}} ({{.Status}})"

echo ""
echo "Obrazy:"
podman images --format "   {{.Repository}}:{{.Tag}} ({{.Size}})"

echo ""
echo "Rozmiar storage:"
du -sh ~/.local/share/containers/storage/ 2>/dev/null || echo "   (brak dostępu)"

echo ""
echo "=========================================="
echo "  GOTOWE!"
echo "=========================================="
