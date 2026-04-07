---
name: klimtech-atomic
description: Protokół atomowych zadań i komunikacji dla KlimtechRAG — jeden krok na raz, format raportowania, tryby pracy (Planowanie vs Budowanie). Użyj gdy zaczynasz implementację nowej funkcji lub gdy sesja wymaga precyzyjnego podziału na etapy.
compatibility: opencode
metadata:
  project: KlimtechRAG
  phase: implementation
---

# klimtech-atomic — Atomowe Zadania i Protokół Komunikacji

## Tryby Pracy

| Tryb | Opis |
|---|---|
| **Planowanie** | NIE wykonujesz żadnych rzeczywistych zmian. Wyłącznie analizujesz, proponujesz kroki i planujesz. |
| **Budowanie** (domyślny) | Wprowadzasz zmiany zgodnie z protokołem poniżej. |

**Jeśli nie wiesz w którym trybie jesteś → ZAPYTAJ użytkownika na początku.**

---

## Zasada atomowych zadań (KLUCZOWE)

- ZAWSZE dziel pracę na **najmniejsze możliwe logiczne etapy**
- NIGDY nie proponuj więcej niż **jednej zmiany technicznej** w jednym kroku
- Wyjątek: trywialne, oczywiste poprawki w jednej linii (np. literówka)

**Jeden krok = jedna akcja.** Przykłady:
- „utwórz pusty katalog"
- „dodaj plik z szablonem"
- „zmień nazwę funkcji X w pliku Y"
- „dodaj linię importu w pliku Z"

---

## Protokół Komunikacji

### Propozycja kroku

Format:
```
Krok N/TOTAL: [opis akcji].
Planowany diff/opis: [krótko, co się zmieni]
Czy mam wykonać ten krok?
```

### Po wykonaniu

Format:
```
Krok N wykonany. [co się zmieniło].
Spójność: [składnia OK / importy OK / type hints OK]
```

### Kolejny krok

Zaproponuj **jeden** kolejny krok. Powtarzaj cykl.

---

## Analiza przed działaniem

1. Dokładnie przeanalizuj powiązane pliki i ich zależności
2. Po analizie sprawdź czy CLAUDE.md nie został zaktualizowany od początku sesji
3. Jeśli potrzebujesz więcej kontekstu → poproś wprost, wymień co już przeanalizowałeś
4. Plik > 500 linii → nie wklejaj całego, czytaj fragmenty z zakresem linii
5. Wiele plików → analizuj sekwencyjnie z informacją o postępie

---

## Bezpieczeństwo przed edycją

Przed edycją istniejącego pliku:
- Podaj dokładny plan w formie **minidiffu** (przed/po)
- Nie usuwaj istniejącego kodu bez absolutnej konieczności
- Preferuj: dodawanie nowych linii, refaktoryzację z zachowaniem starej funkcji
- Tymczasowe wyłączenie: `# TODO: do usunięcia po weryfikacji`

Po każdej zmianie: sprawdź składnię, importy, type hints.

---

## Zakazy bezwzględne w kodzie

```
❌ eval() / exec() / pickle.loads() na danych użytkownika
❌ shell=True w subprocess — zawsze lista argumentów
❌ Logowanie treści dokumentów użytkownika
❌ Commit pliku .env lub kluczy API
❌ Nowy endpoint bez require_api_key()
❌ Ścieżka pliku z user input bez Path.resolve() + walidacji base_path
❌ Zmiana lazy → eager loading w embeddings.py / rag.py
❌ Hardcoded hasła/tokeny — zawsze os.getenv()
❌ Edycja plików bezpośrednio na serwerze
```

---

## Konwencje kodu KlimtechRAG

```python
# Nazewnictwo
snake_case           # pliki, funkcje, zmienne

# Zawsze wymagane
def func(arg: str) -> dict:   # type hints na argumentach i return
    """Docstring dla każdej publicznej funkcji."""

# Importy (kolejność)
# 1. stdlib
# 2. third-party
# 3. local (backend_app.*)

# Nowe endpointy — obowiązkowa struktura
from backend_app.utils.dependencies import require_api_key
from fastapi import Depends

@router.post("/nowy_endpoint")
async def nowy_endpoint(
    data: PydanticSchema,
    _: str = Depends(require_api_key)   # auth ZAWSZE
):
    ...
```

---

## JavaScript w Python strings

```python
# DOBRZE — concatenation, var
html = "<script>var x = " + str(value) + "; var y = " + str(other) + ";</script>"

# ŹLE — backtick → SyntaxWarning w Python + SyntaxError w przeglądarce
html = f"<script>var x = `{value}`;</script>"

# ŹLE — const/let problematyczne w niektórych kontekstach
html = "<script>const x = 1;</script>"
```

---

## Shell na serwerze (fish) — ważne

```bash
# Fish shell nie obsługuje heredoc!
# ŹLE:
cat << 'EOF'
  kod
EOF

# DOBRZE — zawsze używaj python3 -c:
python3 -c "print('kod')"
```

---

## Dokumentacja zmian

- W kodzie: komentarz **dlaczego** zmiana, nie tylko co
- Po znaczącej zmianie: zaproponuj aktualizację `PROJEKT_OPIS.md` i `postep.md` jako osobny atomowy krok
- `postep.md`: aktualizuj po każdej sesji (co zrobiono, co nierozwiązane, rekomendacja)
