#!/bin/bash
# KlimtechRAG - Project Health Check
# Uruchom po git pull na serwerze lub przed git push na laptopie.
# Wynik zapisuje do logs/check_YYYY-MM-DD_HH-MM.log

# ── Konfiguracja ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend_app"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/check_$(date +%Y-%m-%d_%H-%M).log"
BACKEND_URL="http://192.168.31.70:8000"
BACKEND_URL_HTTPS="https://192.168.31.70:8443"

mkdir -p "$LOG_DIR"

# ── Helpers ─────────────────────────────────────────────────────────────────
PASS=0; WARN=0; FAIL=0

log()  { echo "$1" | tee -a "$LOG_FILE"; }
pass() { log "  [PASS] $1"; ((PASS++)); }
warn() { log "  [WARN] $1"; ((WARN++)); }
fail() { log "  [FAIL] $1"; ((FAIL++)); }
section() { log ""; log "══════════════════════════════════════"; log "  $1"; log "══════════════════════════════════════"; }

# ── Start ────────────────────────────────────────────────────────────────────
log "KlimtechRAG Health Check — $(date '+%Y-%m-%d %H:%M:%S')"
log "Projekt: $PROJECT_DIR"

# ════════════════════════════════════════
section "1. GIT STATUS"
# ════════════════════════════════════════

cd "$PROJECT_DIR" || { fail "Nie można wejść do $PROJECT_DIR"; exit 1; }

GIT_STATUS=$(git status --porcelain 2>/dev/null)
if [ -z "$GIT_STATUS" ]; then
    pass "Brak niezatwierdzonych zmian"
else
    warn "Niezatwierdzone zmiany:"
    git status --short 2>/dev/null | tee -a "$LOG_FILE"
fi

# Sprawdź czy .env nie jest staged
if git diff --cached --name-only 2>/dev/null | grep -q "\.env"; then
    fail ".env jest w staged files — NIE commituj!"
else
    pass ".env nie jest staged"
fi

# Ostatni commit
LAST_COMMIT=$(git log -1 --oneline 2>/dev/null)
log "  Ostatni commit: $LAST_COMMIT"

# ════════════════════════════════════════
section "2. SKŁADNIA PYTHON"
# ════════════════════════════════════════

PY_FILES=$(find "$BACKEND_DIR" -name "*.py" -not -path "*/__pycache__/*" 2>/dev/null)
PY_TOTAL=$(echo "$PY_FILES" | wc -l)
PY_ERRORS=0

while IFS= read -r f; do
    ERROR=$(python3 -m py_compile "$f" 2>&1)
    if [ -n "$ERROR" ]; then
        fail "Błąd składni: $f"
        log "         $ERROR"
        ((PY_ERRORS++))
    fi
done <<< "$PY_FILES"

if [ "$PY_ERRORS" -eq 0 ]; then
    pass "Składnia OK — $PY_TOTAL plików .py"
fi

# ════════════════════════════════════════
section "3. BEZPIECZEŃSTWO — SZYBKI SKAN"
# ════════════════════════════════════════

# shell=True
HITS=$(grep -rn "shell=True" "$BACKEND_DIR" --include="*.py" 2>/dev/null)
if [ -n "$HITS" ]; then
    fail "shell=True znalezione:"
    echo "$HITS" | tee -a "$LOG_FILE"
else
    pass "Brak shell=True"
fi

# eval/exec/pickle na danych użytkownika
HITS=$(grep -rn "eval(\|exec(\|pickle\.loads(" "$BACKEND_DIR" --include="*.py" 2>/dev/null)
if [ -n "$HITS" ]; then
    warn "eval/exec/pickle — sprawdź ręcznie czy to dane użytkownika:"
    echo "$HITS" | tee -a "$LOG_FILE"
else
    pass "Brak eval/exec/pickle"
fi

# Hardcoded secrets
HITS=$(grep -rn 'API_KEY\s*=\s*"sk-\|password\s*=\s*"[^{]' "$BACKEND_DIR" --include="*.py" 2>/dev/null | grep -v "os\.getenv\|\.env\|#")
if [ -n "$HITS" ]; then
    fail "Potencjalne hardcoded secrets:"
    echo "$HITS" | tee -a "$LOG_FILE"
else
    pass "Brak hardcoded secrets"
fi

# Endpointy bez require_api_key
ROUTES_DIR="$BACKEND_DIR/routes"
if [ -d "$ROUTES_DIR" ]; then
    UNPROTECTED=$(grep -rn "@router\.\(get\|post\|delete\|put\|patch\)" "$ROUTES_DIR" --include="*.py" -l 2>/dev/null | while read -r rfile; do
        # Znajdź dekoratory routera bez require_api_key w tej samej funkcji
        python3 - "$rfile" <<'PYEOF' 2>/dev/null
import ast, sys

with open(sys.argv[1]) as f:
    src = f.read()

try:
    tree = ast.parse(src)
except SyntaxError:
    sys.exit(0)

for node in ast.walk(tree):
    if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
        has_route = any(
            isinstance(d, ast.Call) and
            isinstance(d.func, ast.Attribute) and
            d.func.attr in ("get", "post", "delete", "put", "patch")
            for d in node.decorator_list
        )
        if not has_route:
            continue
        args = node.args
        has_auth = any(
            isinstance(a.annotation, ast.Call) and
            isinstance(a.annotation.func, ast.Name) and
            a.annotation.func.id == "Depends"
            for a in args.args + args.kwonlyargs
            if a.annotation
        )
        if not has_auth:
            print(f"{sys.argv[1]}:{node.lineno} — {node.name}()")
PYEOF
    done)

    if [ -n "$UNPROTECTED" ]; then
        warn "Endpointy bez Depends(require_api_key) — sprawdź czy celowo:"
        echo "$UNPROTECTED" | tee -a "$LOG_FILE"
    else
        pass "Wszystkie endpointy mają Depends (lub brak routerów do sprawdzenia)"
    fi
fi

# Hardcoded ścieżki /home/tamiel/
HITS=$(grep -rn "/home/tamiel/" "$BACKEND_DIR" --include="*.py" 2>/dev/null | grep -v "config\.py\|_detect_base")
if [ -n "$HITS" ]; then
    warn "Hardcoded ścieżki /home/tamiel/ (poza config.py):"
    echo "$HITS" | tee -a "$LOG_FILE"
else
    pass "Brak hardcoded ścieżek /home/tamiel/"
fi

# ════════════════════════════════════════
section "4. MARTWY KOD I PLIKI"
# ════════════════════════════════════════

BAK_FILES=$(find "$BACKEND_DIR" -name "*.bak" -o -name "*.old" -o -name "*.backup" 2>/dev/null)
if [ -n "$BAK_FILES" ]; then
    warn "Pliki .bak/.old/.backup:"
    echo "$BAK_FILES" | tee -a "$LOG_FILE"
else
    pass "Brak plików .bak/.old/.backup"
fi

PYCACHE=$(find "$PROJECT_DIR" -name "__pycache__" -type d -not -path "*/venv/*" 2>/dev/null | wc -l)
if [ "$PYCACHE" -gt 0 ]; then
    warn "__pycache__ katalogów: $PYCACHE (rozważ dodanie do .gitignore)"
else
    pass "Brak __pycache__ poza venv"
fi

# ════════════════════════════════════════
section "5. BACKEND — HEALTH CHECK"
# ════════════════════════════════════════

# HTTP
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$BACKEND_URL/health" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    pass "Backend HTTP $BACKEND_URL/health → 200"
elif [ "$HTTP_CODE" = "000" ]; then
    warn "Backend HTTP niedostępny (timeout/brak połączenia) — może nie być uruchomiony"
else
    fail "Backend HTTP $BACKEND_URL/health → $HTTP_CODE"
fi

# HTTPS
HTTPS_CODE=$(curl -sk -o /dev/null -w "%{http_code}" --max-time 5 "$BACKEND_URL_HTTPS/health" 2>/dev/null)
if [ "$HTTPS_CODE" = "200" ]; then
    pass "Backend HTTPS $BACKEND_URL_HTTPS/health → 200"
elif [ "$HTTPS_CODE" = "000" ]; then
    warn "Backend HTTPS niedostępny"
else
    fail "Backend HTTPS → $HTTPS_CODE"
fi

# ════════════════════════════════════════
section "6. GPU / VRAM STATUS"
# ════════════════════════════════════════

GPU_RESP=$(curl -s --max-time 5 "$BACKEND_URL/gpu/status" 2>/dev/null)
if [ -n "$GPU_RESP" ]; then
    pass "GPU status endpoint odpowiada"
    log "  $GPU_RESP"
else
    warn "GPU status niedostępny (backend offline?)"
fi

MODEL_RESP=$(curl -s --max-time 5 "$BACKEND_URL/model/status" 2>/dev/null)
if [ -n "$MODEL_RESP" ]; then
    log "  Model status: $MODEL_RESP"
fi

# ════════════════════════════════════════
section "7b. SPRINT 6 — NOWE PLIKI"
# ════════════════════════════════════════

S6_FILES=(
  "backend_app/services/session_service.py"
  "backend_app/services/verification_service.py"
  "backend_app/services/watcher_service.py"
  "backend_app/services/batch_service.py"
  "backend_app/services/progress_service.py"
  "backend_app/routes/sessions.py"
  "backend_app/routes/mcp.py"
  "backend_app/static/klimtech-widget.js"
)

for f in "${S6_FILES[@]}"; do
  if [ -f "$PROJECT_DIR/$f" ]; then
    pass "Sprint 6 plik istnieje: $f"
  else
    fail "Sprint 6 plik BRAKUJE: $f"
  fi
done

# backtick check w widget.js
if [ -f "$PROJECT_DIR/backend_app/static/klimtech-widget.js" ]; then
  if grep -q '`' "$PROJECT_DIR/backend_app/static/klimtech-widget.js" 2>/dev/null; then
    warn "klimtech-widget.js zawiera backticki (mogą być OK w czystym JS)"
  else
    pass "klimtech-widget.js: brak backtików"
  fi
fi


# ════════════════════════════════════════
section "7c. SPRINT 7 — NOWE PLIKI I SKRYPTY"
# ════════════════════════════════════════

S7_FILES=(
  "scripts/backup.sh"
  "scripts/restore.sh"
  "PROJEKT_OPIS.md"
)

for f in "${S7_FILES[@]}"; do
  if [ -f "$PROJECT_DIR/$f" ]; then
    pass "Sprint 7 plik istnieje: $f"
  else
    warn "Sprint 7 plik BRAKUJE: $f"
  fi
done

# Sprawdź czy backup.sh jest wykonywalny
if [ -x "$PROJECT_DIR/scripts/backup.sh" ]; then
    pass "backup.sh jest wykonywalny"
else
    warn "backup.sh nie jest wykonywalny (chmod +x scripts/backup.sh)"
fi

# Sprawdź składnię skryptów
for script in backup.sh restore.sh; do
  if [ -f "$PROJECT_DIR/scripts/$script" ]; then
    if bash -n "$PROJECT_DIR/scripts/$script" 2>/dev/null; then
      pass "$script — składnia bash OK"
    else
      fail "$script — błąd składni bash"
    fi
  fi
done


# ════════════════════════════════════════
section "7. PORTY (lokalne)"
# ════════════════════════════════════════

for PORT in 8000 8082 6333 8081 5678; do
    if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
        pass "Port $PORT otwarty"
    else
        warn "Port $PORT nie nasłuchuje"
    fi
done

# ════════════════════════════════════════
section "PODSUMOWANIE"
# ════════════════════════════════════════

TOTAL=$((PASS + WARN + FAIL))
log ""
log "  PASS: $PASS / $TOTAL"
log "  WARN: $WARN / $TOTAL"
log "  FAIL: $FAIL / $TOTAL"
log ""

if [ "$FAIL" -gt 0 ]; then
    log "  ✖ WYNIK: BŁĘDY — nie deployuj przed naprawą FAIL"
    EXIT_CODE=2
elif [ "$WARN" -gt 0 ]; then
    log "  △ WYNIK: OSTRZEŻENIA — sprawdź WARN przed deployem"
    EXIT_CODE=1
else
    log "  ✔ WYNIK: OK — projekt gotowy do deploymentu"
    EXIT_CODE=0
fi

log ""
log "Log zapisany: $LOG_FILE"
echo ""
echo "Log: $LOG_FILE"

exit $EXIT_CODE
