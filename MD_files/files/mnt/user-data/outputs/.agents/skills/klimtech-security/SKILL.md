---
name: klimtech-security
description: Audyt bezpieczeństwa endpointów FastAPI i kodu KlimtechRAG — weryfikacja auth, walidacji wejścia, secret management, ścieżek plików, logowania. Użyj przed każdym nowym endpointem lub gdy CLAUDE.md sugeruje załadować AUDYT_RUN.md.
compatibility: opencode
metadata:
  project: KlimtechRAG
  phase: security-review
---

# klimtech-security — Audyt Bezpieczeństwa KlimtechRAG

## Kiedy uruchomić

- Przed mergem nowego endpointu FastAPI
- Przed nowym modułem ingestu (upload pliku, ścieżki)
- Gdy CLAUDE.md mówi „Załaduj AUDYT_RUN.md"
- Regularnie — co kilka sesji

---

## Checklist Bezpieczeństwa — Endpointy FastAPI

### [ ] 1. Autoryzacja

```python
# Każdy endpoint musi mieć require_api_key()
from backend_app.utils.dependencies import require_api_key
from fastapi import Depends

@router.post("/endpoint")
async def endpoint(_: str = Depends(require_api_key)):
    ...

# Endpointy admin (DELETE, /files/sync) → bezwzględnie chronione
```

Sprawdź: czy żaden nowy route nie został dodany bez `Depends(require_api_key)`.

---

### [ ] 2. Walidacja wejścia

```python
# Zawsze Pydantic schema dla body requestu
class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    use_rag: bool = False

# NIE używaj bezpośrednio request.body() bez walidacji
```

---

### [ ] 3. Ścieżki plików — Path Traversal

```python
# ZAWSZE waliduj ścieżkę użytkownika
from pathlib import Path

BASE_PATH = Path("/media/lobo/BACKUP/KlimtechRAG/RAG_Dane")

def safe_path(user_input: str) -> Path:
    resolved = (BASE_PATH / user_input).resolve()
    if not str(resolved).startswith(str(BASE_PATH)):
        raise ValueError("Path traversal detected")
    return resolved

# Nigdy:
# path = f"/data/{user_input}"  ← podatne na ../../../etc/passwd
```

---

### [ ] 4. Secret Management

```python
# DOBRZE:
API_KEY = os.getenv("KLIMTECH_API_KEY")

# ŹLE (absolutny zakaz):
API_KEY = "sk-1234abcd"
DB_PASSWORD = "haslo123"
```

Sprawdź: `git grep -n "sk-" --include="*.py"` — czy nie ma hardcoded tokenów.
Sprawdź: `git status` — czy `.env` nie jest w staged files.

---

### [ ] 5. Command Injection

```python
# DOBRZE — lista argumentów:
subprocess.run(["convert", input_file, output_file], check=True)

# ŹLE — shell=True z user input:
subprocess.run(f"convert {user_input}", shell=True)  # ZAKAZ
```

---

### [ ] 6. Logowanie — dane wrażliwe

```python
# ZAKAZ logowania:
logger.info(f"Document content: {chunk}")      # treść dokumentu
logger.debug(f"API key: {api_key}")            # token
logger.info(f"User query: {full_query}")       # treść zapytania (ostrożnie)

# DOZWOLONE:
logger.info(f"Indexed file: {filename}, chunks: {len(chunks)}")
logger.info(f"Request: {request_id}, endpoint: {path}")
```

---

### [ ] 7. Obsługa błędów — nie ujawniaj stack trace

```python
# Na produkcji — nigdy pełny stack trace w response HTTP
@app.exception_handler(Exception)
async def generic_handler(request, exc):
    logger.error(f"Unhandled: {exc}", exc_info=True)  # log z traceback
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}  # bez szczegółów
    )
```

---

### [ ] 8. Bezpieczne przechowywanie uploadowanych plików

```python
import re

def sanitize_filename(filename: str) -> str:
    # Usuń path separators i null bytes
    filename = filename.replace("/", "").replace("\\", "").replace("\x00", "")
    # Zostaw tylko bezpieczne znaki
    filename = re.sub(r"[^\w\-_\. ]", "", filename)
    return filename[:255]  # ogranicz długość
```

---

## Zakazy bezwzględne — przypomnienie

```
❌ eval() / exec() / pickle.loads() na danych wejściowych użytkownika
❌ shell=True w subprocess
❌ Logowanie treści dokumentów użytkownika
❌ Commit .env lub kluczy API
❌ Nowy endpoint bez require_api_key()
❌ Ścieżka z user input bez Path.resolve() + walidacji base_path
❌ Hardcoded hasła/tokeny — zawsze os.getenv()
```

---

## Komendy weryfikacyjne

```bash
# Szukaj hardcoded sekretów
git grep -n "password\s*=" --include="*.py"
git grep -n "api_key\s*=\s*['\"]" --include="*.py"
git grep -n "sk-" --include="*.py"

# Sprawdź nowe endpointy bez auth
grep -n "@router\." backend_app/routers/*.py | grep -v "require_api_key"

# Sprawdź shell=True
grep -rn "shell=True" backend_app/

# .env nie commitowany
git status | grep ".env"
```

---

## Wynik audytu — format raportu

```
## Wynik audytu bezpieczeństwa [data]

### ✅ Sprawdzone i OK
- Autoryzacja: wszystkie endpointy mają require_api_key()
- Secret management: brak hardcoded tokenów
- ...

### ⚠️ Ostrzeżenia (WARN)
- [plik:linia] — [opis problemu, sugerowana poprawka]

### ❌ Krytyczne (FAIL)
- [plik:linia] — [opis problemu, wymagana natychmiastowa poprawka]
```
