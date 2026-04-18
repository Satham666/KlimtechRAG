"""Szablony promptów — strukturalne brief dla Qwen od Claude.

Workflow:
    1. Claude składa prompt: template + specyfikacja
    2. Zapis do robotnik_tasks/NNN_<slug>.md
    3. python -m robotnik.runner robotnik_tasks/NNN_<slug>.md --out robotnik_output/NNN.py
    4. Claude review wygenerowanego pliku
"""

from __future__ import annotations

CODE_TASK = """\
Jesteś ekspertem programistą Python z wieloletnim doświadczeniem w pisaniu
produkcyjnego kodu zgodnego z PEP 8. Twoim zadaniem jest napisanie kompletnego,
gotowego do użycia skryptu realizującego poniższą specyfikację.

**OGRANICZENIA TECHNICZNE:**
{constraints}

**SPECYFIKACJA:**
{spec}

**STRUKTURA ODPOWIEDZI:**
- Rozpocznij od docstringa nagłówkowego z opisem modułu.
- Dodaj `from __future__ import annotations` jeśli używasz type hints.
- Zapewnij type hints na wszystkich publicznych funkcjach.
- Użyj centralnej funkcji `run_cmd(cmd_list)` dla wywołań subprocess (jeśli dotyczy).
- Zapewnij obsługę błędów (try/except z sensownymi komunikatami).
- Kod musi być kompletny — jeden plik, działający od razu.

Rozpocznij od kodu.
"""

REFACTOR_TASK = """\
Jesteś ekspertem Python refaktoryzującym kod. Poniżej znajduje się plik do
refaktoryzacji oraz wymagania dotyczące kierunku zmian.

**PLIK DO REFAKTORYZACJI:**
```python
{source}
```

**KIERUNEK REFAKTORYZACJI:**
{direction}

**ZASADY:**
- Zachowaj 100% funkcjonalność — żadnych regresji.
- Poprawiaj czytelność, nie dodawaj nowych funkcji.
- Dodaj type hints tam, gdzie ich brakuje.
- Nie zmieniaj publicznego API bez wyraźnego wskazania.

Zwróć sam zrefaktoryzowany kod.
"""

TEST_TASK = """\
Jesteś ekspertem testowania Python (pytest). Napisz kompletny zestaw testów
jednostkowych dla poniższego modułu.

**MODUŁ:**
```python
{source}
```

**WYMAGANIA:**
- Użyj pytest (bez unittest).
- Pokryj szczęśliwą ścieżkę + min. 2 przypadki brzegowe.
- Użyj fixtures dla powtarzalnego setupu.
- Każdy test to jedna asercja (AAA: arrange/act/assert).
- Nazwy testów w formacie `test_<co>_<kiedy>_<oczekiwane>`.

Zwróć sam plik testowy gotowy do zapisu jako test_<nazwa>.py.
"""

DOCSTRING_TASK = """\
Jesteś ekspertem dokumentacji Python. Dodaj docstrings w stylu Google do
poniższego modułu tam, gdzie ich brakuje lub są niekompletne.

**MODUŁ:**
```python
{source}
```

**ZASADY:**
- Styl Google: Args, Returns, Raises.
- Nie zmieniaj logiki kodu — TYLKO docstrings.
- Istniejące, poprawne docstrings zostaw bez zmian.

Zwróć cały moduł z dodanymi docstringami.
"""


def render_code_task(spec: str, constraints: str = "Standard library only.") -> str:
    return CODE_TASK.format(spec=spec.strip(), constraints=constraints.strip())


def render_refactor_task(source: str, direction: str) -> str:
    return REFACTOR_TASK.format(source=source.strip(), direction=direction.strip())


def render_test_task(source: str) -> str:
    return TEST_TASK.format(source=source.strip())


def render_docstring_task(source: str) -> str:
    return DOCSTRING_TASK.format(source=source.strip())
