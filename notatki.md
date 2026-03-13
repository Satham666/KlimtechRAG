


# 1. Poprawienie ścierzek katlogów w aplikacju klimtechRAG
	- sprawdź we szystkich plikach główną ścierzkę która została zmieniona z powodu przeniesienia całego projektu z ~/KlimtechRAG/ do /media/lobo/BACKUP/KlimtechRAG/ i popraw na nową
	- llama.cpp będzie uruchamiał modele które zawsze będą pobierane do jednego katalogu /media/lobo/BACKUP/KlimtechRAG/modele_LLM
	- katalog /media/lobo/BACKUP/KlimtechRAG/modele_LLM jest podzielony na podkatalogi które zawieraja różne modele językowe stworzone do konkretych zadań:
	   - /media/lobo/BACKUP/KlimtechRAG/modele_LLM/AudioLLM - 


🗑️ Reset bazy Qdrant
Opcja 1 — Tylko usunięcie kolekcji (zalecane)
Usuwa wektory, zachowuje kontener i konfigurację:
bash# Usuń kolekcję
curl -X DELETE "http://localhost:6333/collections/klimtech_docs"

# Sprawdź czy zniknęła
curl -s http://localhost:6333/collections | python3 -m json.tool
Kolekcja zostanie odtworzona automatycznie przy następnym starcie backendu.

Opcja 2 — Usuń kolekcję + file_registry (pełny reset)
Żeby backend nie pamiętał, które pliki już zaindeksował:
bash# 1. Usuń kolekcję Qdrant
curl -X DELETE "http://localhost:6333/collections/klimtech_docs"

# 2. Usuń rejestr plików
rm /media/lobo/BACKUP/KlimtechRAG/data/file_registry.db

# 3. Zrestartuj backend
pkill -f "uvicorn backend_app"
Po restarcie start_klimtech.py kolekcja i baza SQLite zostaną odtworzone od zera.

Opcja 3 — Snapshot przed resetem (bezpieczniej)
bash# Zrób backup najpierw
curl -X POST "http://localhost:6333/collections/klimtech_docs/snapshots"

# Sprawdź gdzie zapisany
curl "http://localhost:6333/collections/klimtech_docs/snapshots"

# Potem dopiero usuń
curl -X DELETE "http://localhost:6333/collections/klimtech_docs"

Po resecie — ponowne indeksowanie
bash# Sprawdź czy kolekcja pusta
curl -s http://localhost:6333/collections/klimtech_docs | python3 -m json.tool

# Zaindeksuj wszystkie pliki od nowa (CPU)
curl -X POST "http://localhost:8000/ingest_all?limit=50"

# Lub masowo na GPU (szybciej ~70x)
pkill llama-server
./start_backend_gpu.sh
curl -X POST "http://localhost:8000/ingest_all?limit=200"