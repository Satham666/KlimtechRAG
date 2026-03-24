#!/usr/bin/env python3
"""
Tworzy strukturę folderów kategorii w Nextcloud (przez podman exec + occ files:mkdir).

Użycie:
    python3 scripts/create_nextcloud_folders.py [--dry-run] [--base-path PATH]

Przykład (na serwerze):
    python3 scripts/create_nextcloud_folders.py --dry-run           # tylko pokaż co zostanie utworzone
    python3 scripts/create_nextcloud_folders.py                     # utwórz foldery
    python3 scripts/create_nextcloud_folders.py --base-path /inne   # tylko ta gałąź

Struktura tworzona:
    /DOKUMENTY_RAG/
    ├── medycyna/
    │   ├── choroby/
    │   │   ├── choroby_serca/
    │   │   └── ...
    │   ├── farmakologia/
    │   └── ...
    ├── prawo/
    └── ...

UWAGA: Skrypt wymaga działającego kontenera 'nextcloud' (Podman).
"""

import argparse
import subprocess
import sys
import os

# Pozwól importować backend_app z katalogu projektu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend_app.categories.definitions import CATEGORIES

# Katalog główny w Nextcloud (na koncie admin)
NEXTCLOUD_BASE = "/DOKUMENTY_RAG"
NEXTCLOUD_USER = "admin"
NEXTCLOUD_CONTAINER = "nextcloud"


def get_all_paths(category: dict, parent_path: str = "") -> list[str]:
    """
    Rekursywnie zbiera wszystkie ścieżki folderów z kategorii.

    Returns:
        Lista ścieżek np. ["/medycyna", "/medycyna/choroby", "/medycyna/choroby/choroby_serca", ...]
    """
    paths = []
    current_path = parent_path + category["path"]
    paths.append(current_path)

    for subcat in category.get("subcategories", []):
        paths.extend(get_all_paths(subcat, parent_path=""))

    return paths


def create_nextcloud_folder(path: str, dry_run: bool = False) -> bool:
    """
    Tworzy folder w Nextcloud przez podman exec + occ files:mkdir.

    Args:
        path:    Ścieżka względna (np. "/DOKUMENTY_RAG/medycyna/choroby")
        dry_run: Tylko wypisuje, nie wykonuje

    Returns:
        True jeśli OK, False jeśli błąd.
    """
    # Pełna ścieżka dla OCC: user/files/DOKUMENTY_RAG/medycyna/...
    occ_path = f"{NEXTCLOUD_USER}/files{path}"

    cmd = [
        "podman", "exec", "-u", "www-data", NEXTCLOUD_CONTAINER,
        "php", "occ", "files:mkdir", occ_path
    ]

    if dry_run:
        print(f"  [DRY-RUN] {' '.join(cmd)}")
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"  ✅ {path}")
            return True
        else:
            # Folder już istnieje — to nie błąd
            if "already exists" in result.stderr.lower() or "already exists" in result.stdout.lower():
                print(f"  ⏭  {path} (już istnieje)")
                return True
            print(f"  ❌ {path}: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ⏰ Timeout: {path}")
        return False
    except FileNotFoundError:
        print("❌ 'podman' nie znalezione. Uruchom skrypt na serwerze.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Tworzy foldery kategorii w Nextcloud")
    parser.add_argument("--dry-run", action="store_true", help="Tylko wypisz, nie twórz")
    parser.add_argument("--base-path", default=None, help="Ogranicz do gałęzi np. /medycyna")
    parser.add_argument("--user", default=NEXTCLOUD_USER, help=f"Użytkownik Nextcloud (domyślnie: {NEXTCLOUD_USER})")
    parser.add_argument("--container", default=NEXTCLOUD_CONTAINER, help=f"Nazwa kontenera (domyślnie: {NEXTCLOUD_CONTAINER})")
    args = parser.parse_args()

    global NEXTCLOUD_USER, NEXTCLOUD_CONTAINER
    NEXTCLOUD_USER = args.user
    NEXTCLOUD_CONTAINER = args.container

    # Zbierz wszystkie ścieżki
    all_paths: list[str] = [NEXTCLOUD_BASE]  # katalog główny

    for cat_id, category in CATEGORIES.items():
        paths = get_all_paths(category, parent_path=NEXTCLOUD_BASE)
        all_paths.extend(paths)

    # Filtruj jeśli podano --base-path
    if args.base_path:
        filter_prefix = NEXTCLOUD_BASE + args.base_path
        all_paths = [p for p in all_paths if p.startswith(filter_prefix) or p == NEXTCLOUD_BASE]

    # Usuń duplikaty i posortuj (ważne — tworzyć od nadrzędnych do podrzędnych)
    all_paths = sorted(set(all_paths))

    print(f"\n📁 Tworzenie struktury folderów w Nextcloud")
    print(f"   Kontener:  {NEXTCLOUD_CONTAINER}")
    print(f"   Użytkownik: {NEXTCLOUD_USER}")
    print(f"   Katalog główny: {NEXTCLOUD_BASE}")
    print(f"   Liczba folderów: {len(all_paths)}")
    if args.dry_run:
        print("   TRYB: DRY-RUN (brak zmian)\n")
    else:
        print()

    success = 0
    errors = 0

    for path in all_paths:
        ok = create_nextcloud_folder(path, dry_run=args.dry_run)
        if ok:
            success += 1
        else:
            errors += 1

    print(f"\n{'=' * 50}")
    print(f"✅ Sukces: {success} | ❌ Błędy: {errors}")

    if not args.dry_run and errors == 0:
        print("\n🔄 Synchronizacja plików Nextcloud...")
        sync_cmd = [
            "podman", "exec", "-u", "www-data", NEXTCLOUD_CONTAINER,
            "php", "occ", "files:scan", "--all"
        ]
        try:
            subprocess.run(sync_cmd, timeout=120)
        except Exception as e:
            print(f"⚠️  Błąd synchronizacji: {e}")


def export_folder_list(output_file: str = "folder_structure.txt") -> None:
    """
    Eksportuje listę wszystkich ścieżek folderów do pliku tekstowego.
    Przydatne do podglądu struktury bez uruchamiania Nextcloud.
    """
    all_paths = [NEXTCLOUD_BASE]
    for category in CATEGORIES.values():
        all_paths.extend(get_all_paths(category, parent_path=NEXTCLOUD_BASE))
    all_paths = sorted(set(all_paths))

    with open(output_file, "w", encoding="utf-8") as f:
        for path in all_paths:
            f.write(path + "\n")

    print(f"✅ Lista folderów zapisana: {output_file} ({len(all_paths)} wpisów)")


if __name__ == "__main__":
    main()
