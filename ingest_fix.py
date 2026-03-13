#!/usr/bin/env python3
"""
Skrypt naprawczy — usuwa błędnie wklejony patch z ingest.py
i dodaje saved_path do odpowiedzi /upload.

Uruchom: python3 ingest_fix.py
"""
import re, sys, os

INGEST_PATH = "/media/lobo/BACKUP/KlimtechRAG/backend_app/routes/ingest.py"

with open(INGEST_PATH, "r", encoding="utf-8") as f:
    src = f.read()

# ── 1. Usuń błędnie wklejony blok patch (jeśli istnieje) ──────────────────
bad_block = '''### PATCH dla backend_app/routes/ingest.py
### Znajdź blok return w endpoint /upload i zastąp:

# STARY KOD (okolice linii "return {" w async def upload_file_to_rag):
        return {
            "status": "ok",
            "filename": os.path.basename(target_path),
            "nextcloud_folder": f"RAG_Dane/{subdir}",
            "size_bytes": file_size,
            "indexing": ext in TEXT_INDEXABLE,
            "message": f"Plik zapisany w Nextcloud/{subdir}. {index_msg}",
        }

# NOWY KOD (dodano saved_path — używane przez UI do VLM ingest):
        return {
            "status": "ok",
            "filename": os.path.basename(target_path),
            "saved_path": target_path,                    # ← NOWE — potrzebne dla VLM
            "nextcloud_folder": f"RAG_Dane/{subdir}",
            "size_bytes": file_size,
            "indexing": ext in TEXT_INDEXABLE,
            "message": f"Plik zapisany w Nextcloud/{subdir}. {index_msg}",
        }'''

# Sprawdź czy jest błędny blok
if "### PATCH dla" in src or '"""        return {' in src:
    print("⚠️  Znaleziono błędnie wklejony patch — usuwam...")

    # Usuń wszystko między liniami patch
    # Szukamy sekcji która jest docstringiem lub gołym tekstem
    # Najpierw spróbujmy prostego podejścia - znajdź i wytnij
    idx = src.find("### PATCH dla")
    if idx == -1:
        idx = src.find('"""        return {')
    if idx != -1:
        # Znajdź koniec tego bloku (koniec triple-quote lub koniec komentarza)
        end_idx = src.find('\nasync def ', idx)
        if end_idx == -1:
            end_idx = src.find('\n@router', idx)
        if end_idx == -1:
            end_idx = src.find('\ndef ', idx)
        if end_idx != -1:
            src = src[:idx] + src[end_idx:]
            print("  ✅ Usunięto błędny blok")
        else:
            print("  ❌ Nie mogę automatycznie usunąć — sprawdź plik ręcznie")
            sys.exit(1)
    else:
        print("  Nie znaleziono bloków do usunięcia")
else:
    print("✅ Nie znaleziono błędnego patch — plik jest czysty (lub już naprawiony)")

# ── 2. Dodaj saved_path jeśli jeszcze nie ma ──────────────────────────────
OLD_RETURN = '''        return {
            "status": "ok",
            "filename": os.path.basename(target_path),
            "nextcloud_folder": f"RAG_Dane/{subdir}",
            "size_bytes": file_size,
            "indexing": ext in TEXT_INDEXABLE,
            "message": f"Plik zapisany w Nextcloud/{subdir}. {index_msg}",
        }'''

NEW_RETURN = '''        return {
            "status": "ok",
            "filename": os.path.basename(target_path),
            "saved_path": target_path,
            "nextcloud_folder": f"RAG_Dane/{subdir}",
            "size_bytes": file_size,
            "indexing": ext in TEXT_INDEXABLE,
            "message": f"Plik zapisany w Nextcloud/{subdir}. {index_msg}",
        }'''

if '"saved_path"' in src:
    print("✅ saved_path już istnieje w pliku — pomijam")
elif OLD_RETURN in src:
    src = src.replace(OLD_RETURN, NEW_RETURN, 1)
    print("✅ Dodano saved_path do odpowiedzi /upload")
else:
    print("⚠️  Nie znaleziono bloku return do zmiany — sprawdź ingest.py ręcznie")
    print("   Szukany wzorzec:")
    print(OLD_RETURN)

# ── 3. Sprawdź składnię ───────────────────────────────────────────────────
import ast
try:
    ast.parse(src)
    print("✅ Składnia Python poprawna")
except SyntaxError as e:
    print(f"❌ Nadal błąd składni: {e}")
    print(f"   Linia {e.lineno}: {e.text}")
    # Pokaż kontekst
    lines = src.splitlines()
    start = max(0, e.lineno - 5)
    end   = min(len(lines), e.lineno + 5)
    print("\n   Kontekst:")
    for i, line in enumerate(lines[start:end], start=start+1):
        marker = ">>> " if i == e.lineno else "    "
        print(f"   {marker}{i}: {line}")
    # Nie zapisuj uszkodzonego pliku
    print("\n❌ Plik NIE został zapisany. Napraw ręcznie.")
    sys.exit(1)

# ── 4. Zapis ──────────────────────────────────────────────────────────────
backup = INGEST_PATH + ".fix_backup"
with open(backup, "w", encoding="utf-8") as f:
    # Zapisz poprzednią wersję
    pass

import shutil
shutil.copy2(INGEST_PATH, backup)
print(f"✅ Backup: {backup}")

with open(INGEST_PATH, "w", encoding="utf-8") as f:
    f.write(src)
print(f"✅ Zapisano: {INGEST_PATH}")
print("\n🎉 ingest.py naprawiony!")
print("\nTeraz uruchom:")
print("  podman start qdrant")
print("  python3 start_backend_gpu.py")
