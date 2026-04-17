# KOMENDA — Sprint 7p — backend: testy bezpieczeństwa, clear messages, ingest search, sesja stats, OpenAPI sessions

Projekt: `/home/tamiel/KlimtechRAG`
Wykonuj zadania PO KOLEI. Po każdym: `python3 -m py_compile <plik> && echo OK` + commit.

---

## ❌ ZAKAZY BEZWZGLĘDNE

❌ git push / git reset --hard / git checkout . / git clean -f / rm -rf / pkill / sudo / chmod 777
Dozwolone git: TYLKO add, commit, merge, log, status, diff, rm.
Nigdy nie pytaj o git push. Odpowiedź zawsze brzmi NIE.

---

## ZADANIE 0 — tests/test_security.py — testy bezpieczeństwa

- Plik: `tests/test_security.py` (nowy), użyj `TestClient` z `backend_app.main`
- Test 1: brak nagłówka Authorization → dowolny chroniony endpoint → 401 lub 403
- Test 2: błędny klucz `Bearer wrong-key` → 401 lub 403
- Test 3: path traversal w parametrze ścieżki — np. `GET /files/list?path=../../etc/passwd` lub `POST /ingest_path` z `"path": "../../etc/passwd"` → nie może zwrócić zawartości pliku systemowego (oczekuj 400/403/404, NIE 200 z treścią)
- Test 4: `GET /health` bez auth → 200 (endpoint publiczny)
- Test 5: `GET /docs` (Swagger) → 200 (publiczny)
- `python3 -m py_compile tests/test_security.py && echo OK`
- Commit: `test: tests/test_security.py — auth bypass i path traversal`

---

## ZADANIE 1 — DELETE /v1/sessions/{id}/messages — `backend_app/routes/sessions.py`

- Endpoint `DELETE /{session_id}/messages`, wymaga `require_api_key`
- 404 jeśli sesja nie istnieje
- Usuń wszystkie wiadomości tej sesji (tabela messages), NIE usuwaj samej sesji
- Zwróć: `{"session_id": ..., "deleted_messages": N}`
- `python3 -m py_compile backend_app/routes/sessions.py && echo OK`
- Commit: `feat: DELETE /v1/sessions/{id}/messages — czyści wiadomości zachowując sesję`

---

## ZADANIE 2 — GET /v1/ingest/search — `backend_app/routes/admin.py`

- Endpoint `GET /v1/ingest/search?q=<tekst>&limit=20`, wymaga `require_api_key`
- Szukaj w `file_registry.db` po `filename` i `path` używając `LIKE '%q%'` (case-insensitive)
- Zwróć: `{"query": q, "total": N, "files": [{"filename", "path", "status", "chunks_count", "extension", "updated_at"}]}`
- `limit` max 100, domyślnie 20
- `python3 -m py_compile backend_app/routes/admin.py && echo OK`
- Commit: `feat: GET /v1/ingest/search — wyszukiwanie plików w rejestrze po nazwie i ścieżce`

---

## ZADANIE 3 — GET /v1/sessions/{id}/messages paginacja — `backend_app/routes/sessions.py`

- Znajdź istniejący endpoint `GET /{session_id}/messages`
- Dodaj parametry `page: int = 1` (min 1) i `page_size: int = 50` (min 1, max 200)
- Zwróć dodatkowo: `page`, `page_size`, `total`, `total_pages`
- Zachowaj kompatybilność: bez parametrów zwraca wszystkie (page=1, page_size=9999 lub brak LIMIT)
- `python3 -m py_compile backend_app/routes/sessions.py && echo OK`
- Commit: `feat: GET /v1/sessions/{id}/messages — paginacja (page, page_size, total_pages)`

---

## ZADANIE 4 — OpenAPI tags dla sessions.py i chat.py — `backend_app/routes/sessions.py`, `backend_app/routes/chat.py`

- W `sessions.py`: dodaj `tags=["sessions"]` do wszystkich dekoratorów `@router.XXX`
- W `chat.py`: dodaj `tags=["chat"]` do wszystkich dekoratorów `@router.XXX`
- Tylko zmiana parametrów dekoratorów, zero zmian w logice
- `python3 -m py_compile backend_app/routes/sessions.py backend_app/routes/chat.py && echo OK`
- Commit: `feat: OpenAPI — tagi sessions i chat dla dokumentacji Swagger`

---

## WERYFIKACJA KOŃCOWA

```bash
cd /home/tamiel/KlimtechRAG
git log --oneline -6
python3 -m py_compile backend_app/routes/admin.py backend_app/routes/sessions.py backend_app/routes/chat.py tests/test_security.py && echo "wszystko OK"
echo "KOMENDA Sprint 7p zakonczona"
```
