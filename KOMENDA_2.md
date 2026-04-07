# KOMENDA_2 — Sprint 7m — UI: export sesji, processing panel, kopiuj, kolekcje, skróty

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

## ZADANIE 0 — UI: przyciski eksportu sesji (MD + JSON)

- W funkcji renderującej element sesji w sidebarze (tam gdzie już jest `title` i `updated_at`): dodaj dwa małe przyciski eksportu obok nazwy sesji — widoczne przy hover (klasa CSS `opacity-0 group-hover:opacity-100`)
- Przycisk MD: `⬇ MD` — wywołuje `window.open(B+'/v1/sessions/'+id+'/export.md')`
- Przycisk JSON: `⬇ JSON` — wywołuje `window.open(B+'/v1/sessions/'+id+'/export.json')`
- Upewnij się że kontener sesji ma klasę `group` (dla hover)
- Nie rób żadnych fetch — tylko `window.open(url)` z autoryzacją przez URL query jeśli potrzeba; sprawdź jak `export.md` jest chroniony — jeśli wymaga nagłówka, zamiast window.open użyj fetch z `require_api_key` i blob download
- Commit: `feat: UI — przyciski eksportu sesji MD i JSON w sidebarze`

---

## ZADANIE 1 — UI: panel "Aktualnie przetwarzane" z auto-refresh

- Dodaj panel `<article>` PO panelu statystyk indeksowania (id="ingestStatsEl")
- Nagłówek: "&#9881; Przetwarzane teraz", przycisk odśwież wywołuje `loadProcessing()`
- Wewnątrz: `<div id="processingEl">`
- Funkcja `loadProcessing()`: GET `/v1/ingest/processing`; jeśli `total==0` wyświetl "&#10003; Brak aktywnych"; jeśli `total>0` wyświetl listę plików z `filename` i `updated_at`
- Auto-refresh: w `setInterval` co 10000ms dodaj `loadProcessing()` (ale tylko jeśli `document.getElementById('processingEl')` istnieje)
- Dodaj `loadProcessing()` do `DOMContentLoaded`
- Commit: `feat: UI — panel aktualnie przetwarzanych plików z auto-refresh 10s`

---

## ZADANIE 2 — UI: przycisk "Kopiuj" pod wiadomościami AI

- Znajdź w `index.html` miejsce gdzie renderowane są wiadomości czatu (wiadomości z rolą `assistant`)
- Pod każdą wiadomością asystenta dodaj mały przycisk `&#128203; Kopiuj` (ikona clipboard)
- Kliknięcie: `navigator.clipboard.writeText(tresc_wiadomosci)` + zmień tekst przycisku na `&#10003; Skopiowano` na 2s (setTimeout → przywróć oryginał)
- Jeśli `navigator.clipboard` niedostępne (HTTP): fallback przez `document.execCommand('copy')` z textarea
- Styl: `text-[9px] text-rag-text-muted hover:text-white px-1 cursor-pointer`
- Commit: `feat: UI — przycisk Kopiuj pod wiadomościami asystenta`

---

## ZADANIE 3 — UI: panel kolekcji Qdrant

- Dodaj panel `<article>` PO panelu "Aktualnie przetwarzane" (id="processingEl")
- Nagłówek: "&#128209; Kolekcje Qdrant", przycisk odśwież wywołuje `loadCollections()`
- Wewnątrz: `<div id="collectionsEl">`
- Funkcja `loadCollections()`: GET `/collections` (lub `/v1/collections/stats` jeśli istnieje); wyświetl każdą kolekcję jako wiersz: nazwa + liczba wektorów (`points_count`) + wymiar (`vector_size`)
- Jeśli endpoint zwróci 404 lub błąd: `el.innerHTML='<div class="text-rag-text-muted text-center py-2">Niedostępne</div>'`
- Dodaj `loadCollections()` do `DOMContentLoaded`
- Commit: `feat: UI — panel kolekcji Qdrant z GET /collections`

---

## ZADANIE 4 — UI: popup pomocy ze skrótami klawiszowymi (klawisz ?)

- Dodaj obsługę klawisza `?` (gdy focus NIE jest w input/textarea): toggle widoczności overlaya pomocy
- Overlay: `<div id="helpOverlay">` z klasami `fixed inset-0 bg-black/70 z-50 flex items-center justify-center hidden`
- Zawartość overlaya: tabela skrótów: Ctrl+K (nowa sesja), Ctrl+N (wyczyść), Esc (zamknij/wyczyść), ? (ta pomoc), Enter (wyślij)
- Zamknięcie: kliknięcie poza oknem lub Esc
- Dodaj do istniejącego `document.addEventListener('keydown',...)` obsługę klawisza `?`
- Commit: `feat: UI — popup pomocy ze skrótami klawiszowymi (klawisz ?)`

---

## WERYFIKACJA KOŃCOWA

```bash
cd /home/tamiel/KlimtechRAG
git log --oneline -6
echo "KOMENDA_2 Sprint 7m zakonczona"
```
