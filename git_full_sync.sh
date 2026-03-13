#!/bin/bash

# Skrypt do pełnej synchronizacji lokalnego repo z GitHub
# Użycie: ./git_full_sync.sh [opcjonalna wiadomość commit]

set -e  # Zatrzymaj przy błędzie

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Git Full Sync ===${NC}"

# Sprawdź czy jesteś w repo git
if [ ! -d .git ]; then
    echo -e "${RED}Błąd: Nie jesteś w katalogu git repo${NC}"
    exit 1
fi

# Sprawdź czy są zmiany
if [ -z "$(git status --porcelain)" ]; then
    echo -e "${GREEN}Brak zmian do synchronizacji${NC}"
    exit 0
fi

# Pokaż status
echo -e "${YELLOW}Zmiany do zsynchronizowania:${NC}"
git status --short

# Dodaj wszystkie zmiany
echo -e "${YELLOW}Dodawanie wszystkich zmian...${NC}"
git add -A

# Wiadomość commit
if [ -z "$1" ]; then
    COMMIT_MSG="Full sync: $(date +%Y-%m-%d_%H:%M:%S)"
else
    COMMIT_MSG="$1"
fi

# Commit
echo -e "${YELLOW}Commit: $COMMIT_MSG${NC}"
git commit -m "$COMMIT_MSG"

# Push
echo -e "${YELLOW}Wysyłanie na GitHub...${NC}"
git push --force

echo -e "${GREEN}✓ Synchronizacja zakończona pomyślnie!${NC}"

# Pokaż ostatni commit
echo -e "${YELLOW}Ostatni commit:${NC}"
git log -1 --oneline
