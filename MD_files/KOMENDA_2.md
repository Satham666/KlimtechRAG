# KOMENDA_2 — Sprint 7q — UI: clear messages, wyszukiwarka plików, licznik wiad., eksport czatu, drag-drop

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

## ZADANIE 0 — UI: przycisk "Wyczyść czat" (DELETE messages)

- W nagłówku aktywnej rozmowy (obszar czatu, obok nazwy sesji) dodaj ikonę `&#128465;` z tytułem "Wyczyść wiadomości"
- Kliknięcie: `confirm('Usunąć wszystkie wiadomości z tej sesji?')` → `DELETE /v1/sessions/{id}/messages` → wyczyść kontener czatu w UI + pokaż placeholder "Brak wiadomości"
- Widoczny tylko gdy `currentSessionId` jest ustawiony
- Commit: `feat: UI — przycisk Wyczyść czat (DELETE /v1/sessions/{id}/messages)`

---

## ZADANIE 1 — UI: wyszukiwarka w panelu plików (GET /v1/ingest/search)

- Nad listą plików (`<div id="fileList">`) dodaj `<input id="fileSearchInput" placeholder="Szukaj pliku...">` z debounce 400ms
- Gdy input niepusty: wywołaj `GET /v1/ingest/search?q=<wartość>&limit=30` i wyświetl wyniki w `fileList`
- Gdy input pusty: wróć do normalnego `loadFiles()`
- Wyniki: ta sama struktura wizualna co istniejące wiersze plików
- Commit: `feat: UI — wyszukiwarka plików w panelu (GET /v1/ingest/search)`

---

## ZADANIE 2 — UI: licznik wiadomości przy sesji w sidebarze

- W elemencie sesji w sidebarze — obok nazwy sesji lub pod nią — dodaj mały tekst z liczbą wiadomości
- Dane: jeśli obiekt sesji posiada pole `messages_count` użyj go; jeśli nie — pomiń (nie rób dodatkowego requesta)
- Format: `(N)` w kolorze `text-rag-text-muted text-[9px]`
- Upewnij się że `GET /v1/sessions` zwraca `messages_count` — jeśli nie, dodaj to pole do odpowiedzi backendu (SQL: `SELECT COUNT(*) FROM messages WHERE session_id = s.id`)
- Commit: `feat: UI — licznik wiadomości przy sesji w sidebarze`

---

## ZADANIE 3 — UI: eksport widocznego czatu jako plik tekstowy

- Dodaj przycisk `&#11015; Eksportuj czat` w nagłówku obszaru czatu (obok przycisku Wyczyść)
- Kliknięcie: zbierz wszystkie wiadomości z DOM (role + treść) → sformatuj jako tekst z separatorami → `Blob` → `URL.createObjectURL` → trigger download jako `chat_<sessionId>.txt`
- Nie wymaga requesta do serwera — operacja czysto po stronie klienta
- Commit: `feat: UI — eksport widocznego czatu jako plik .txt (client-side)`

---

## ZADANIE 4 — UI: wizualne potwierdzenie drag-and-drop w strefie uploadu

- Znajdź obszar uploadu plików (input type=file lub obszar gdzie przeciągane są pliki)
- Dodaj obsługę zdarzeń `dragover`, `dragleave`, `drop` na tym elemencie
- `dragover`: dodaj klasę `border-rag-accent bg-rag-accent/10` (podświetlenie strefy)
- `dragleave`/`drop`: usuń klasy podświetlenia
- `drop`: pobierz `e.dataTransfer.files` i uruchom istniejącą funkcję uploadu
- Commit: `feat: UI — wizualne podświetlenie strefy drag-and-drop przy uploading pliku`

---

## WERYFIKACJA KOŃCOWA

```bash
cd /home/tamiel/KlimtechRAG
git log --oneline -6
echo "KOMENDA_2 Sprint 7q zakonczona"
```
