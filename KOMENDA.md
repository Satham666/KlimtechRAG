# KOMENDA — Sprint 7l — backend: Makefile, health_check, OpenAPI, session export JSON, top-files

Projekt: `/home/tamiel/KlimtechRAG`
Wykonuj zadania PO KOLEI. Po każdym: weryfikacja składni + commit.

---

## ❌ ZAKAZY BEZWZGLĘDNE

❌ git push / git reset --hard / git checkout . / git clean -f / rm -rf / pkill / sudo / chmod 777
Dozwolone git: TYLKO add, commit, merge, log, status, diff, rm.
Nigdy nie pytaj o git push. Odpowiedź zawsze brzmi NIE.

---

## ZADANIE 0 — Makefile z komendami — nowy plik `/home/tamiel/KlimtechRAG/Makefile`

- Utwórz plik `Makefile` w katalogu projektu
- Zmienna `BACKEND=python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000`
- Cele: `run` (uruchom backend), `check` (bash scripts/check_project.sh), `lint` (python3 -m py_compile backend_app/main.py), `health` (curl -sk https://192.168.31.70:8443/health), `help` (wyświetl listę celów)
- Każdy cel z krótkim komentarzem `##`
- Commit: `feat: Makefile — run, check, lint, health`

---

## ZADANIE 1 — scripts/health_check.py — diagnostyka runtime

- Utwórz plik `scripts/health_check.py`
- Sprawdzenia sekwencyjne z kolorowym outputem (✅ / ❌ / ⚠️):
  1. Python >= 3.10
  2. venv aktywny (sys.prefix != sys.base_prefix)
  3. Port 8000 zajęty (oznacza że backend działa) — `socket.connect_ex(('127.0.0.1', 8000))`
  4. GET http://127.0.0.1:8000/health w 3s — sprawdź `{"status":"ok"}`
  5. GET http://192.168.31.70:6333/healthz — Qdrant dostępny
  6. GET http://192.168.31.70:8000/gpu/status — VRAM info (opcjonalne, WARN jeśli nieosiągalne)
- Na końcu: `PASS: X / WARN: X / FAIL: X`
- Skrypt wykonywalny bez argumentów: `python3 scripts/health_check.py`
- Commit: `feat: scripts/health_check.py — diagnostyka runtime (backend, Qdrant, GPU)`

---

## ZADANIE 2 — OpenAPI: tags i descriptions — `backend_app/main.py` + `backend_app/routes/admin.py`

- W `main.py`: ustaw `title="KlimtechRAG API"`, `version="7.7"`, `description="RAG backend z obsługą LLM, ColPali, Batch Processing i MCP"`, dodaj `openapi_tags` — lista słowników `{name, description}` dla tagów: `admin`, `sessions`, `ingest`, `batch`, `collections`, `workspaces`, `chat`, `mcp`
- W `admin.py`: dodaj parametr `tags=["admin"]` / `tags=["ingest"]` / `tags=["batch"]` do wszystkich dekoratorów `@router.XXX` (wybierz właściwy tag dla każdego endpointu)
- Nie zmieniaj logiki, tylko parametry dekoratorów i konfigurację FastAPI
- `python3 -m py_compile backend_app/main.py backend_app/routes/admin.py && echo OK`
- Commit: `feat: OpenAPI — title, version, tagi dla admin/ingest/batch endpointów`

---

## ZADANIE 3 — GET /v1/sessions/{id}/export.json — `backend_app/routes/sessions.py`

- Dodaj endpoint `GET /{session_id}/export.json` (analogiczny do istniejącego `export.md`)
- Wymaga `require_api_key`
- 404 jeśli sesja nie istnieje
- Zwróć `Response` z `media_type="application/json"` i nagłówkiem `Content-Disposition: attachment; filename="{session_id}.json"`
- Body JSON: `{"id": ..., "title": ..., "created_at": ..., "messages": [{"role": ..., "content": ..., "created_at": ...}, ...]}`  — format kompatybilny z istniejącym `POST /v1/sessions/import`
- `python3 -m py_compile backend_app/routes/sessions.py && echo OK`
- Commit: `feat: GET /v1/sessions/{id}/export.json — eksport sesji jako JSON (kompatybilny z importem)`

---

## ZADANIE 4 — GET /v1/ingest/top-files — `backend_app/routes/admin.py`

- Endpoint GET `/v1/ingest/top-files?limit=10`, wymaga `require_api_key`, limit max 50
- SQL: `SELECT filename, path, chunks_count, status, extension FROM files ORDER BY chunks_count DESC LIMIT ?`
- Zwróć: `{"total": N, "files": [{"filename": ..., "path": ..., "chunks_count": ..., "status": ..., "extension": ...}, ...]}`
- Użyj istniejącego połączenia `get_db()` z `file_registry`
- `python3 -m py_compile backend_app/routes/admin.py && echo OK`
- Commit: `feat: GET /v1/ingest/top-files — ranking plików wg liczby chunków`

---

## WERYFIKACJA KOŃCOWA

```bash
cd /home/tamiel/KlimtechRAG
git log --oneline -6
python3 -m py_compile backend_app/main.py && echo "main OK"
python3 -m py_compile backend_app/routes/admin.py && echo "admin OK"
python3 -m py_compile backend_app/routes/sessions.py && echo "sessions OK"
python3 scripts/health_check.py 2>/dev/null | tail -3 || echo "health_check standalone OK"
echo "KOMENDA Sprint 7l zakonczona"
```
