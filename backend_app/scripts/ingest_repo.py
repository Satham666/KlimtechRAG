import os
import sys

import requests

from backend_app.config import settings


API_URL = f"http://localhost:{os.getenv('BACKEND_API_PORT', '8000')}/ingest"
MAX_FILE_SIZE = 500 * 1024  # 500 KB (dla kodu – lżejszy limit niż ogólny)

# Foldery do pominięcia (blacklist)
SKIP_FOLDERS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
    ".idea",
}


def ingest_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"BŁĄD: Folder nie istnieje: {folder_path}")
        return

    print(f"🚀 Rozpoczynam indeksowanie folderu: {folder_path}")
    processed_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(folder_path):
        # Usuń foldery z blacklisty
        dirs[:] = [d for d in dirs if d not in SKIP_FOLDERS]

        for file in files:
            if any(file.endswith(ext) for ext in settings.allowed_extensions_code):
                file_path = os.path.join(root, file)

                if os.path.getsize(file_path) > MAX_FILE_SIZE:
                    skipped_count += 1
                    continue

                relative_path = os.path.relpath(file_path, folder_path)
                print(f"📄 Wysyłanie: {relative_path}...", end=" ")

                try:
                    with open(file_path, "rb") as f:
                        files_dict = {"file": (file, f)}
                        response = requests.post(API_URL, files=files_dict, timeout=30)

                    if response.status_code == 200:
                        print("✅ OK")
                        processed_count += 1
                    else:
                        print(f"❌ BŁĄD: {response.text}")
                except Exception as e:
                    print(f"⚠️  BŁĄD POŁĄCZENIA: {e}")
            else:
                skipped_count += 1

    print(
        f"\n🎉 Zakończono! Przetworzono {processed_count} plików. Pominięto: {skipped_count}."
    )


if __name__ == "__main__":
    # Wybór ścieżki: argument z wiersza poleceń lub domyślna
    if len(sys.argv) > 1:
        target_folder = sys.argv[1]
    else:
        # Domyślnie indeksujemy pobrane repozytorium opencode
        target_folder = "/home/lobo/KlimtechRAG/git_sync/zizzania"

    ingest_folder(target_folder)
#    observer = Observer()
#    observer.start()
#
#    try:
#        while True:
#            time.sleep(1)

#    except KeyboardInterrupt:
#        observer.stop()
#        observer.join()
#        print("\nZatrzymywanie monitoringu...")
