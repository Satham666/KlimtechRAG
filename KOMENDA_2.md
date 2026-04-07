# KOMENDA_2 — Sprint 7o — UI: workspaces, bulk delete sesji, model badge, paginacja plików, tryb skupienia

Projekt: `/home/tamiel/KlimtechRAG`
Wykonuj zadania PO KOLEI. Po każdym zadaniu: commit z opisem.

---

## ❌ ZAKAZY BEZWZGLĘDNE

❌ git push / git reset --hard / git checkout . / git clean -f / rm -rf / pkill / sudo / chmod 777
Dozwolone git: TYLKO add, commit, merge, log, status, diff, rm.
Nigdy nie pytaj o git push. Odpowiedź zawsze brzmi NIE.

---

Wszystkie zmiany w: `backend_app/static/index.html`

---

## ZADANIE 0 — UI: panel Workspaces (GET /workspaces)

- Dodaj panel `<article>` PO panelu kolekcji Qdrant (id="collectionsEl")
- Nagłówek: "&#128193; Workspaces", przycisk odśwież wywołuje `loadWorkspaces()`
- Wewnątrz: `<div id="workspacesEl">`
- Funkcja `loadWorkspaces()`: GET `/workspaces`; wyświetl każdy workspace jako wiersz: nazwa + `collection` + liczba plików (`files_count` jeśli dostępne); jeśli błąd/404 → "Niedostępne"
- Dodaj `loadWorkspaces()` do `DOMContentLoaded`
- Commit: `feat: UI — panel Workspaces z GET /workspaces`

---

## ZADANIE 1 — UI: bulk delete sesji (checkboxy + przycisk usuń zaznaczone)

- W nagłówku listy sesji dodaj: przycisk `&#9745; Zaznacz wszystkie` (toggle) i przycisk `&#128465; Usuń zaznaczone` (widoczny tylko gdy zaznaczone > 0)
- Przy każdym elemencie sesji w sidebarze dodaj `<input type="checkbox" class="sessCheckbox">` z `data-id` sesji
- Funkcja `bulkDeleteSelected()`: zbierz `data-id` zaznaczonych checkboxów → `POST /v1/sessions/bulk-delete` z `{"session_ids": [...]}` → odśwież listę sesji + `refreshSessCountBadge()`
- Przed usunięciem: `confirm('Usunąć X sesji?')`
- Commit: `feat: UI — bulk delete sesji z checkboxami i potwierdzeniem`

---

## ZADANIE 2 — UI: badge z aktualnie załadowanym modelem w nagłówku

- Znajdź górny nagłówek aplikacji (header lub area z tytułem "KlimtechRAG")
- Dodaj `<span id="modelBadge">` wyświetlający nazwę modelu
- Funkcja `loadModelBadge()`: GET `/model/status`; jeśli `model_loaded == true` → pokaż `model_name` w zielonym badgu; jeśli nie → szary "brak modelu"
- Dodaj do `DOMContentLoaded` i do `setInterval` co 30s
- Commit: `feat: UI — badge z załadowanym modelem LLM w nagłówku`

---

## ZADANIE 3 — UI: paginacja w panelu "Ostatnie pliki"

- W panelu plików (id="fileList") dodaj pod listą przyciski `< Poprzednia` i `Następna >` oraz tekst `Strona X / Y`
- Zmienna JS `var filePage = 1` i `var filePageSize = 20`
- W funkcji `loadFiles()`: dołącz `&page=${filePage}&page_size=${filePageSize}` do URL
- Z odpowiedzi odczytaj `total_pages` i aktualizuj przyciski (disabled jeśli brak poprzedniej/następnej)
- Commit: `feat: UI — paginacja w panelu plików (20 na stronę, poprzednia/następna)`

---

## ZADANIE 4 — UI: tryb skupienia (ukryj sidebar klawiszem F11 lub przyciskiem)

- Dodaj przycisk `&#8596;` (strzałki) w nagłówku aplikacji lub obok sidebara
- Kliknięcie lub `Alt+Z`: toggle klasy `hidden` na sidebarze (panel boczny z sesjami i panelami)
- Główny obszar czatu powinien rozciągnąć się na całą szerokość gdy sidebar ukryty (Tailwind: zmień `w-full` lub flex-grow)
- Stan zapamiętaj w `localStorage.setItem('sidebarHidden', ...)` i przywróć przy inicjalizacji
- Commit: `feat: UI — tryb skupienia (ukryj/pokaż sidebar Alt+Z lub przycisk)`

---

## WERYFIKACJA KOŃCOWA

```bash
cd /home/tamiel/KlimtechRAG
git log --oneline -6
echo "KOMENDA_2 Sprint 7o zakonczona"
```
