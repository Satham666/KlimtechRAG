# KOMENDA — Sprint 7n — backend: testy, export-all, cleanup-old, paginacja ingest/list, doc info

Projekt: `/home/tamiel/KlimtechRAG`
Wykonuj zadania PO KOLEI. Po każdym: `python3 -m py_compile <plik> && echo OK` + commit.

---

## ❌ ZAKAZY BEZWZGLĘDNE

❌ git push / git reset --hard / git checkout . / git clean -f / rm -rf / pkill / sudo / chmod 777
Dozwolone git: TYLKO add, commit, merge, log, status, diff, rm.
Nigdy nie pytaj o git push. Odpowiedź zawsze brzmi NIE.

---

## ZADANIE 0 — tests/test_admin.py — testy endpointów admin

- Plik: `tests/test_admin.py` (nowy)
- Użyj istniejącego `client` fixture z `tests/test_api.py` (importuj lub powiel)
- Przetestuj (z mockiem `require_api_key` → zwraca `"test-key"`):
  - `GET /health` → 200, `{"status": "ok"}`
  - `GET /v1/ingest/stats` → 200, JSON zawiera klucze `total_files`, `indexed`, `pending`, `errors`
  - `GET /v1/system/info` → 200, JSON zawiera `python_version`, `base_path`
  - `GET /v1/batch/stats` → 200, JSON zawiera `queue_size`
  - `GET /v1/ingest/top-files` → 200, JSON zawiera `files` (lista)
- Mock bazy danych: użyj `unittest.mock.patch` na `sqlite3.connect` lub `get_db` jeśli potrzeba
- `python3 -m py_compile tests/test_admin.py && echo OK`
- Commit: `test: tests/test_admin.py — smoke testy endpointów admin i ingest`

---

## ZADANIE 1 — tests/test_sessions.py — testy sesji

- Plik: `tests/test_sessions.py` (nowy)
- Użyj `TestClient` z `backend_app.main`
- Testy CRUD (in-memory, nie mockuj bazy — TestClient używa tej samej SQLite w pamięci jeśli możliwe):
  - `POST /v1/sessions` → 201, zwraca `id` i `title`
  - `GET /v1/sessions` → 200, lista zawiera nowo utworzoną sesję
  - `GET /v1/sessions/{id}` → 200
  - `PATCH /v1/sessions/{id}` z `{"title": "nowy"}` → 200
  - `DELETE /v1/sessions/{id}` → 204
  - `GET /v1/sessions/{id}` po delete → 404
- `python3 -m py_compile tests/test_sessions.py && echo OK`
- Commit: `test: tests/test_sessions.py — testy CRUD sesji`

---

## ZADANIE 2 — GET /v1/sessions/export-all — `backend_app/routes/sessions.py`

- Endpoint `GET /export-all`, wymaga `require_api_key`
- Zwróć `Response` z `media_type="application/json"`, `Content-Disposition: attachment; filename="sessions_backup.json"`
- Body: lista wszystkich sesji z wiadomościami: `[{"id":..., "title":..., "created_at":..., "messages":[...]}, ...]`
- Pobierz wszystkie sesje przez istniejące funkcje repozytoriów (nie pisz surowego SQL)
- Limit: max 500 sesji
- `python3 -m py_compile backend_app/routes/sessions.py && echo OK`
- Commit: `feat: GET /v1/sessions/export-all — eksport wszystkich sesji jako JSON backup`

---

## ZADANIE 3 — POST /v1/sessions/cleanup-old — `backend_app/routes/sessions.py`

- Endpoint `POST /cleanup-old?days=30`, wymaga `require_api_key`, `days` min 1 max 365
- Usuń sesje gdzie `updated_at < now - days` I `messages_count == 0` (puste sesje)
- Alternatywnie jeśli trudno zliczyć wiadomości: usuń sesje bez żadnych wiadomości w tabeli messages
- Zwróć: `{"deleted": N, "days_threshold": days}`
- `python3 -m py_compile backend_app/routes/sessions.py && echo OK`
- Commit: `feat: POST /v1/sessions/cleanup-old — usuwa puste sesje starsze niż N dni`

---

## ZADANIE 4 — GET /v1/ingest/list paginacja — `backend_app/routes/admin.py`

- Znajdź istniejący endpoint `GET /v1/ingest/list`
- Dodaj parametry: `page: int = 1` (min 1), `page_size: int = 50` (min 1, max 200)
- Zwróć dodatkowo w response: `page`, `page_size`, `total_pages` (math.ceil(total/page_size))
- Zachowaj istniejące filtry (`status`, `source`, `extension`)
- `python3 -m py_compile backend_app/routes/admin.py && echo OK`
- Commit: `feat: GET /v1/ingest/list — paginacja (page, page_size, total_pages)`

---

## WERYFIKACJA KOŃCOWA

```bash
cd /home/tamiel/KlimtechRAG
git log --oneline -6
python3 -m py_compile backend_app/routes/admin.py backend_app/routes/sessions.py tests/test_admin.py tests/test_sessions.py && echo "wszystko OK"
echo "KOMENDA Sprint 7n zakonczona"
```
