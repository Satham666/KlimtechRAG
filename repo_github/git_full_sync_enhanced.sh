#!/bin/bash

# Skrypt do pełnej synchronizacji lokalnego repo z GitHub
# Wersja z diagnostyką
# Użycie: ./git_full_sync.sh [opcjonalna wiadomość commit]

set -e  # Zatrzymaj przy błędzie

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Git Full Sync (Enhanced) ===${NC}"

# Sprawdź czy jesteś w repo git
if [ ! -d .git ]; then
    echo -e "${RED}Błąd: Nie jesteś w katalogu git repo${NC}"
    exit 1
fi

# Pobierz info z remote
echo -e "${BLUE}Sprawdzam status z GitHub...${NC}"
git fetch

# Sprawdź WSZYSTKIE różnice (local vs remote)
UNPUSHED=$(git log origin/main..HEAD --oneline | wc -l)
UNCOMMITTED=$(git status --porcelain | wc -l)

echo -e "${BLUE}Diagnostyka:${NC}"
echo -e "  Niezacommitowane zmiany: ${UNCOMMITTED}"
echo -e "  Zacommitowane ale niewypushowane: ${UNPUSHED}"

# Jeśli są JAKIEKOLWIEK zmiany
if [ "$UNCOMMITTED" -gt 0 ] || [ "$UNPUSHED" -gt 0 ]; then
    
    # Najpierw zacommituj niezacommitowane
    if [ "$UNCOMMITTED" -gt 0 ]; then
        echo -e "${YELLOW}Znalezione niezacommitowane zmiany:${NC}"
        git status --short
        
        echo -e "${YELLOW}Dodawanie wszystkich zmian...${NC}"
        git add -A
        
        # Wiadomość commit
        if [ -z "$1" ]; then
            COMMIT_MSG="Full sync: $(date +%Y-%m-%d_%H:%M:%S)"
        else
            COMMIT_MSG="$1"
        fi
        
        echo -e "${YELLOW}Commit: $COMMIT_MSG${NC}"
        git commit -m "$COMMIT_MSG"
    fi
    
    # Push (z force jak użytkownik ustawił)
    echo -e "${YELLOW}Wysyłanie na GitHub (--force)...${NC}"
    git push --force
    
    echo -e "${GREEN}✓ Synchronizacja zakończona pomyślnie!${NC}"
    
else
    echo -e "${GREEN}✓ Wszystko jest już zsynchronizowane z GitHub${NC}"
    echo -e "${BLUE}Local i remote są identyczne.${NC}"
fi

# Pokaż ostatni commit
echo -e "${YELLOW}Ostatni commit:${NC}"
git log -1 --oneline

# Pokaż status
echo -e "${YELLOW}Status końcowy:${NC}"
git status
