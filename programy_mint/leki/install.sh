#!/bin/bash
# Skrypt instalacyjny dla pobierz_leki.py

echo "=========================================="
echo "  Instalacja zależności dla pobierz_leki.py"
echo "=========================================="

# Sprawdź czy Python 3 jest zainstalowany
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 nie jest zainstalowany!"
    echo "  Zainstaluj Python 3: sudo apt install python3 python3-pip"
    exit 1
fi

echo "✓ Python 3: $(python3 --version)"

# Instaluj zależności
echo ""
echo "Instalowanie zależności..."

pip3 install -r requirements.txt --break-system-packages

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  Instalacja zakończona pomyślnie!"
    echo "=========================================="
    echo ""
    echo "Uruchomienie:"
    echo "  python3 pobierz_leki.py              # Tryb interaktywny"
    echo "  python3 pobierz_leki.py -n 'Apap'    # Wyszukaj lek"
    echo "  python3 pobierz_leki.py --help       # Pomoc"
else
    echo ""
    echo "✗ Wystąpił błąd podczas instalacji"
    exit 1
fi
