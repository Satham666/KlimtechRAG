#!/usr/bin/env python3
"""
Naprawia endpoint /upload w ingest.py:
- Usuwa śmieci z wklejonego patch.txt
- Przywraca poprawny return z saved_path
"""
import ast, shutil, sys, re

PATH = "/media/lobo/BACKUP/KlimtechRAG/backend_app/routes/ingest.py"

with open(PATH, "r", encoding="utf-8") as f:
    src = f.read()

# ── Pokaż co jest teraz w okolicach funkcji upload ──────────────────────────
lines = src.splitlines()
print("=== Aktualny stan ingest.py (linie 250-330) ===")
for i, l in enumerate(lines[249:329], start=250):
    print(f"{i:4}: {l}")
print("=" * 60)

# ── Sprawdź składnię PRZED naprawą ──────────────────────────────────────────
try:
    ast.parse(src)
    print("\n✅ Składnia OK przed naprawą")
    has_syntax_error = False
except SyntaxError as e:
    print(f"\n❌ Błąd składni: linia {e.lineno}: {e.text}")
    has_syntax_error = True

# ── Usuń wszystkie wersje patch.txt jeśli wklejone ──────────────────────────
# Szukamy charakterystycznych śmieci
garbage_patterns = [
    r'### PATCH.*?(?=\nasync def |\n@router|\ndef )',
    r'# STARY KOD.*?(?=\nasync def |\n@router|\ndef )',
    r'# NOWY KOD.*?(?=\nasync def |\n@router|\ndef )',
    r'""".*?PATCH.*?"""',
]
cleaned = False
for pat in garbage_patterns:
    new_src = re.sub(pat, '', src, flags=re.DOTALL)
    if new_src != src:
        src = new_src
        cleaned = True
        print("✅ Usunięto śmieci z patch.txt")

# ── Sprawdź czy upload ma return ────────────────────────────────────────────
# Znajdź funkcję upload_file_to_rag i sprawdź czy ma return {"status": "ok"
UPLOAD_FUNC = 'async def upload_file_to_rag('
if UPLOAD_FUNC not in src:
    print(f"❌ Nie znaleziono funkcji {UPLOAD_FUNC}")
    sys.exit(1)

upload_start = src.find(UPLOAD_FUNC)

# Sprawdź czy jest return z "status": "ok"
STATUS_OK = '"status": "ok"'
if STATUS_OK not in src[upload_start:upload_start+3000]:
    print("❌ Brak return {\"status\": \"ok\"} w /upload — wstawiam...")

    # Znajdź miejsce tuż przed końcem bloku try w upload
    # Szukamy "index_msg}",\n" po którym powinien być return
    # Szukamy konkretnej linii z "index_msg"
    INDEX_MSG_LINE = '            index_msg = f"Format {ext} zapisany'

    # Alternatywnie szukamy bloku który jest tuż przed:
    #   logger.info(
    #       "[Upload]
    LOGGER_INFO = '        logger.info(\n            "[Upload]'

    INSERT_AFTER = None

    # Sprawdź różne warianty zakończenia if/else bloku
    candidates = [
        '            index_msg = f"Format {ext} zapisany w Nextcloud',
        "            index_msg = f'Format {ext} zapisany",
        '        else:\n            index_msg = f"Format',
    ]

    for cand in candidates:
        idx = src.find(cand, upload_start)
        if idx != -1:
            # Znajdź koniec tej linii
            end_of_line = src.find('\n', idx)
            INSERT_AFTER = end_of_line
            print(f"   Znaleziono punkt wstawienia po: {src[idx:end_of_line+1].strip()[:60]}")
            break

    if INSERT_AFTER is None:
        # Szukamy logger.info w upload
        li_idx = src.find('        logger.info(\n            "[Upload]', upload_start)
        if li_idx != -1:
            INSERT_AFTER = li_idx - 1
            print(f"   Punkt wstawienia przed logger.info")

    if INSERT_AFTER is None:
        print("❌ Nie mogę znaleźć miejsca na return — pokaż linie 250-320 ręcznie")
        sys.exit(1)

    NEW_RETURN = '''
        return {
            "status": "ok",
            "filename": os.path.basename(target_path),
            "saved_path": target_path,
            "nextcloud_folder": f"RAG_Dane/{subdir}",
            "size_bytes": file_size,
            "indexing": ext in TEXT_INDEXABLE,
            "message": f"Plik zapisany w Nextcloud/{subdir}. {index_msg}",
        }'''

    src = src[:INSERT_AFTER+1] + NEW_RETURN + src[INSERT_AFTER+1:]
    print("✅ Wstawiono return do /upload")

else:
    print("✅ return {\"status\": \"ok\"} już istnieje")
    # Dodaj saved_path jeśli go nie ma
    if '"saved_path"' not in src[upload_start:upload_start+3000]:
        OLD = '            "filename": os.path.basename(target_path),\n            "nextcloud_folder"'
        NEW = '            "filename": os.path.basename(target_path),\n            "saved_path": target_path,\n            "nextcloud_folder"'
        if OLD in src:
            src = src.replace(OLD, NEW, 1)
            print("✅ Dodano saved_path")
        else:
            print("⚠️  Nie można dodać saved_path automatycznie")
    else:
        print("✅ saved_path już istnieje")

# ── Sprawdź składnię PO naprawie ────────────────────────────────────────────
try:
    ast.parse(src)
    print("\n✅ Składnia poprawna po naprawie")
except SyntaxError as e:
    print(f"\n❌ Nadal błąd składni po naprawie: linia {e.lineno}: {e.text}")
    lines2 = src.splitlines()
    start = max(0, e.lineno - 5)
    end   = min(len(lines2), e.lineno + 5)
    for i, l in enumerate(lines2[start:end], start=start+1):
        marker = ">>>" if i == e.lineno else "   "
        print(f"  {marker} {i}: {l}")
    print("\n❌ Plik NIE zapisany.")
    sys.exit(1)

# ── Zapisz ──────────────────────────────────────────────────────────────────
shutil.copy2(PATH, PATH + ".bak2")
with open(PATH, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\n✅ Zapisano: {PATH}")
print(f"   Backup:    {PATH}.bak2")
print("\n🎉 Gotowe! Zrestartuj backend:")
print("   CTRL+C  (zatrzymaj stary)")
print("   python3 start_backend_gpu.py")
