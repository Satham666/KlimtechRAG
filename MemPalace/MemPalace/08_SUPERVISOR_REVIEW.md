# 08_SUPERVISOR_REVIEW — Protokół rewizji przez supervisora

**Zadanie:** Procedura przeglądu i korekty pracy robotników przez duży model
**Czas:** 1 dzień
**Zależności:** Wszystkie poprzednie kroki ukończone
**Kto wykonuje:** Supervisor (Claude lub inny zaawansowany model)

---

## KONTEKST

Robotnicy (Qwen3-8B, Bielik-4.5B) wykonali zadania 01-07.
Wyniki pracy zapisane są w kolekcji Qdrant `klimtech_worklog`.
Kod jest na laptopie w repozytorium KlimtechRAG.
Supervisor sprawdza: poprawność kodu, bezpieczeństwo, spójność, testy.

---

## PROCEDURA REWIZJI

### Faza 1: Odczyt worklog z Qdrant

```bash
# Wszystkie zadania oczekujące na rewizję
curl -s http://localhost:6333/collections/klimtech_worklog/points/scroll \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 50,
    "with_payload": true,
    "filter": {
      "must": [{"key": "review_status", "match": {"value": "pending_supervisor"}}]
    }
  }' | python3 -m json.tool

# Zadania z błędami
curl -s http://localhost:6333/collections/klimtech_worklog/points/scroll \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 50,
    "with_payload": true,
    "filter": {
      "must": [{"key": "status", "match": {"value": "error"}}]
    }
  }' | python3 -m json.tool
```

### Faza 2: Checklist bezpieczeństwa (każdy plik)

Dla KAŻDEGO pliku wygenerowanego przez robotnika sprawdź:

```
[ ] Brak eval() / exec() / pickle na danych użytkownika
[ ] Brak shell=True w subprocess
[ ] Brak hardcoded secrets (hasła, klucze API w kodzie)
[ ] Wszystkie sekrety przez os.getenv() lub config.py
[ ] Nowe endpointy FastAPI mają Depends(require_api_key)
[ ] Ścieżki plików używają Path.resolve() + walidacja base_path
[ ] Brak logowania treści dokumentów ani tokenów API
[ ] Import lazy (nie ładuje modeli przy starcie)
```

### Faza 3: Checklist czystości kodu

```
[ ] snake_case dla zmiennych i funkcji
[ ] Type hints na wszystkich argumentach i return
[ ] Docstring (po polsku) dla funkcji publicznych
[ ] JS w Python: konkatenacja (+) i var — NIE backticks/const/let
[ ] Brak zduplikowanego kodu z istniejącymi modułami
[ ] Obsługa wyjątków (try/except z logowaniem)
```

### Faza 4: Checklist integralności projektu

```
[ ] Nowe pliki dodane do odpowiednich katalogów (services/, routes/, scripts/)
[ ] Nowe routery zarejestrowane w main.py
[ ] Nowe zależności dodane do requirements.txt
[ ] Nowe zmienne .env udokumentowane w PROJEKT_OPIS.md
[ ] Brak konfliktu z istniejącymi endpointami
[ ] Brak modyfikacji istniejących API (kompatybilność wsteczna)
[ ] check_project.sh przechodzi bez FAIL
```

### Faza 5: Testy funkcjonalne

```bash
# 1. Restart backendu
cd /media/lobo/BACKUP/KlimtechRAG
source /home/lobo/klimtech_venv/bin/activate
python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000

# 2. Testy endpointów
# Health
curl -sk https://localhost:8443/health -H "Authorization: Bearer sk-local"

# Graf
curl -sk "https://localhost:8443/v1/graph/data?min_weight=0.2" \
  -H "Authorization: Bearer sk-local" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Nodes:', d['stats']['total_nodes'])
print('Edges:', d['stats']['total_edges'])
print('Types:', d['stats']['edge_types'])
"

# Kontekst warstwy
curl -sk "https://localhost:8443/v1/context/debug?query=prawo%20budowlane" \
  -H "Authorization: Bearer sk-local" | python3 -m json.tool

# Metadata w nowych punktach
curl -s http://localhost:6333/collections/klimtech_docs/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 3, "with_payload": true}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
for p in d['result']['points'][:3]:
    pl = p['payload']
    print(pl.get('source','?')[:30], '|',
          'wing=' + str(pl.get('wing','BRAK')),
          'room=' + str(pl.get('room','BRAK'))[:25],
          'hall=' + str(pl.get('hall','BRAK')),
          'valid_from=' + str(pl.get('valid_from','BRAK')))
"

# Graf wizualizacja
echo "Otwórz w przeglądarce: https://192.168.31.70:8443/graph"
```

### Faza 6: Aktualizacja statusu w worklog

Po rewizji każdego zadania:

```bash
# Oznacz jako zweryfikowane
curl -X POST "http://localhost:6333/collections/klimtech_worklog/points/payload" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {"review_status": "approved", "reviewer": "claude_supervisor"},
    "points": ["POINT_ID_HERE"]
  }'

# Lub oznacz jako wymagające poprawek
curl -X POST "http://localhost:6333/collections/klimtech_worklog/points/payload" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "review_status": "needs_fix",
      "reviewer": "claude_supervisor",
      "fix_notes": "Brak type hints w funkcji X, brak require_api_key na endpoincie Y"
    },
    "points": ["POINT_ID_HERE"]
  }'
```

### Faza 7: Aktualizacja dokumentacji

Po zatwierdzeniu wszystkich zadań, zaktualizuj:

1. **PROJEKT_OPIS.md** — dodaj nowe endpointy (/v1/graph/data, /graph, /v1/context/debug)
2. **AGENTS.md** — dodaj sekcję o grafie wiedzy i warstwach kontekstu
3. **PLAN_WDROZENIA_MASTER.md** — oznacz ukończone zadania
4. **.env.example** — dodaj nowe zmienne (KLIMTECH_PROGRESSIVE_CONTEXT)

---

## MATRYCA DECYZYJNA

| Wynik rewizji | Akcja |
|--------------|-------|
| Kod poprawny + testy PASS | → approved, git push |
| Drobne poprawki (formatowanie, docstringi) | → supervisor poprawia sam |
| Błąd logiczny / brak testu | → needs_fix, odeślij do robotnika |
| Naruszenie bezpieczeństwa | → needs_fix, priorytet KRYTYCZNY |
| Konflikt z istniejącym kodem | → supervisor decyduje o merge strategy |

---

## RAPORTOWANIE KOŃCOWE

| Zadanie | Robotnik | Status | Reviewer | Uwagi |
|---------|----------|--------|----------|-------|
| 01 Setup | — | | | |
| 02 Metadata | Qwen3-8B | | | |
| 03 Temporal | Qwen3-8B | | | |
| 04 Layers | Qwen3-8B | | | |
| 05 Graph Edges | Qwen3-8B | | | |
| 06 Graph Viz | Qwen3-8B | | | |
| 07 NER | Bielik-4.5B | | | |
| 08 Review | Supervisor | | | |
