# 📋 Instrukcja wdrożenia — KlimtechRAG + Open WebUI
## Wariant C: OWUI → KlimtechRAG (RAG) + Qdrant + Nextcloud jako główne repozytorium
### Data: 2026-02-21

---

## Wykonaj w tej kolejności — jeden krok na raz!

---

## KROK 1: Zaktualizuj pliki projektu

Skopiuj wszystkie dostarczone pliki na miejsce:

```fish
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate.fish

# Podmień pliki (backup oryginałów najpierw!)
cp backend_app/config.py backend_app/config.py.bak
cp backend_app/routes/ingest.py backend_app/routes/ingest.py.bak
cp backend_app/routes/chat.py backend_app/routes/chat.py.bak
cp backend_app/scripts/watch_nextcloud.py backend_app/scripts/watch_nextcloud.py.bak
cp start_klimtech.py start_klimtech.py.bak
cp stop_klimtech.py stop_klimtech.py.bak
```

Wgraj nowe pliki:
- `config.py`              → `backend_app/config.py`
- `ingest.py`              → `backend_app/routes/ingest.py`
- `chat.py`                → `backend_app/routes/chat.py`
- `watch_nextcloud.py`     → `backend_app/scripts/watch_nextcloud.py`
- `start_klimtech.py`      → `./start_klimtech.py`
- `stop_klimtech.py`       → `./stop_klimtech.py`
- `env.template`           → `.env` (jeśli nie masz, skopiuj i uzupełnij)

---

## KROK 2: Zaktualizuj .env

```fish
# Otwórz .env i sprawdź czy ścieżki są poprawne
nano .env
```

Kluczowe zmienne do sprawdzenia:
```
KLIMTECH_BASE_PATH=/media/lobo/BACKUP/KlimtechRAG
KLIMTECH_NEXTCLOUD_BASE=/media/lobo/BACKUP/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane
LLAMA_MODELS_DIR=/media/lobo/BACKUP/KlimtechRAG/modele_LLM
```

---

## KROK 3: Utwórz strukturę katalogów Nextcloud

```fish
# Główne foldery RAG w Nextcloud (jeśli nie istnieją)
set NC_BASE /media/lobo/BACKUP/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane

mkdir -p $NC_BASE/pdf_RAG
mkdir -p $NC_BASE/Doc_RAG
mkdir -p $NC_BASE/txt_RAG
mkdir -p $NC_BASE/json_RAG
mkdir -p $NC_BASE/Audio_RAG
mkdir -p $NC_BASE/Video_RAG
mkdir -p $NC_BASE/Images_RAG

# Foldery backup (uploads)
set UP_BASE /media/lobo/BACKUP/KlimtechRAG/data/uploads
mkdir -p $UP_BASE/pdf_RAG $UP_BASE/Doc_RAG $UP_BASE/txt_RAG
mkdir -p $UP_BASE/json_RAG $UP_BASE/Audio_RAG $UP_BASE/Video_RAG $UP_BASE/Images_RAG

mkdir -p /media/lobo/BACKUP/KlimtechRAG/data/open-webui
mkdir -p /media/lobo/BACKUP/KlimtechRAG/logs
```

---

## KROK 4: Pobierz Open WebUI (obraz Podman)

```fish
podman pull ghcr.io/open-webui/open-webui:main
```

Sprawdź czy pobrało się poprawnie:
```fish
podman images | grep open-webui
```

---

## KROK 5: Test konfiguracji bez uruchamiania wszystkiego

```fish
source venv/bin/activate.fish

# Sprawdź czy config.py poprawnie ładuje ścieżki
python -c "
from backend_app.config import settings
print('base_path:', settings.base_path)
print('nextcloud_base:', settings.nextcloud_base)
print('qdrant_url:', settings.qdrant_url)
print('embedding_model:', settings.embedding_model)
"
```

Oczekiwany wynik:
```
base_path: /media/lobo/BACKUP/KlimtechRAG
nextcloud_base: /media/lobo/BACKUP/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane
qdrant_url: http://localhost:6333
embedding_model: intfloat/multilingual-e5-large
```

---

## KROK 6: Uruchom system

```fish
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate.fish
python start_klimtech.py
```

System uruchomi kolejno:
1. Wybór modelu GGUF z listy
2. LLM Server (llama.cpp) na porcie 8082
3. Kontenery: Qdrant, Nextcloud, n8n
4. Backend FastAPI na porcie 8000
5. Watchdog (obserwuje foldery Nextcloud)
6. Open WebUI na porcie 3000

---

## KROK 7: Weryfikacja backendu

```fish
# Health check
curl -s http://localhost:8000/health | python3 -m json.tool

# Test /v1/models (OWUI tego używa do wykrycia dostępnych modeli)
curl -s http://localhost:8000/v1/models | python3 -m json.tool

# Test /v1/embeddings (OWUI tego używa do RAG)
curl -s -X POST http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "test zdanie po polsku"}' | python3 -c "
import json, sys
d = json.load(sys.stdin)
emb = d['data'][0]['embedding']
print(f'OK! Wymiar wektora: {len(emb)} (powinno być 1024)')
"

# Test RAG diagnostyki
curl -s "http://localhost:8000/rag/debug?query=klimatyzacja" | python3 -m json.tool
```

---

## KROK 8: Konfiguracja Open WebUI

Otwórz przeglądarkę: `http://localhost:3000`

1. **Pierwsze logowanie** → utwórz konto admina (email + hasło)

2. **Sprawdź połączenie z LLM:**
   Admin Panel → Settings → Connections → OpenAI API
   - URL: `http://localhost:8000/v1`
   - Kliknij "Verify connection" — powinien pojawić się model

3. **Pobierz API Key OWUI** (potrzebny dla OWUI Function):
   Avatar (prawy górny róg) → Settings → Account → API Keys → Generate

4. **Wyłącz OWUI RAG** (RAG robi KlimtechRAG backend):
   Admin Panel → Settings → Documents
   - Disable Hybrid Search
   - Lub: zostaw włączony ale OWUI będzie używał własnej kolekcji `open-webui`

---

## KROK 9: Zainstaluj OWUI Function (File Router)

To jest najważniejszy krok — dzięki niemu pliki z czatu OWUI trafiają do Nextcloud + Qdrant.

1. Otwórz OWUI → **Workspace → Functions → + New Function**

2. Wklej całą zawartość pliku `owui_function_file_router.py`

3. Kliknij **Save**

4. **Skonfiguruj Valves** (kliknij ⚙️ przy funkcji):
   - `KLIMTECH_URL`: `http://localhost:8000`
   - `KLIMTECH_API_KEY`: (zostaw puste jeśli nie ustawiłeś)
   - `OWUI_URL`: `http://localhost:3000`
   - `OWUI_API_KEY`: (API Key z Kroku 8 pkt 3)
   - `ENABLED`: `true`
   - `DEBUG`: `false`

5. **Aktywuj funkcję** — przełącz przełącznik na ON

---

## KROK 10: Test end-to-end

```fish
# 1. Test upload przez backend (zapisze do Nextcloud + zaindeksuje)
curl -s -X POST http://localhost:8000/upload \
  -F "file=@/ścieżka/do/test.pdf" | python3 -m json.tool

# Sprawdź czy plik pojawił się w Nextcloud
ls /media/lobo/BACKUP/KlimtechRAG/data/nextcloud/data/admin/files/RAG_Dane/pdf_RAG/

# 2. Sprawdź Qdrant (poczekaj ~30s na indeksowanie w tle)
curl -s http://localhost:8000/rag/debug?query=test | python3 -m json.tool

# 3. Test w OWUI:
#    - Otwórz http://localhost:3000
#    - Nowy czat
#    - Dołącz plik (spinacz w polu tekstowym)
#    - Napisz: "Co jest w tym dokumencie?"
#    - Sprawdź logi: logs/backend.log
```

---

## KROK 11: Weryfikacja Nextcloud

Po uploadzie przez OWUI lub /upload, plik powinien pojawić się w Nextcloud UI:

```fish
# Sprawdź czy plik jest widoczny w Nextcloud (po rescan)
podman exec nextcloud php occ files:scan --path=/admin/files/RAG_Dane --shallow

# Sprawdź co widzi Nextcloud
podman exec nextcloud php occ files:list admin --path=RAG_Dane
```

---

## Architektura po wdrożeniu

```
Użytkownik → http://localhost:3000 (Open WebUI)
               │
               ├── Wiadomość tekstowa
               │     └── POST /v1/chat/completions → KlimtechRAG [8000]
               │           ├── Embedding zapytania
               │           ├── Retrieval z Qdrant (klimtech_docs)
               │           └── Generowanie przez llama.cpp [8082]
               │
               └── Plik załączony do czatu
                     └── OWUI Function (File Router)
                           └── GET OWUI /files/{id}/content
                                 └── POST KlimtechRAG /upload
                                       ├── Zapis → Nextcloud/RAG_Dane/{subdir}/
                                       ├── podman exec nextcloud occ files:scan
                                       └── BackgroundTask → Qdrant klimtech_docs
```

---

## Logi do monitorowania

```fish
# Backend FastAPI
tail -f /media/lobo/BACKUP/KlimtechRAG/logs/backend.log

# Watchdog (Nextcloud observer)
tail -f /media/lobo/BACKUP/KlimtechRAG/logs/watchdog.log

# LLM stdout/stderr
tail -f /media/lobo/BACKUP/KlimtechRAG/logs/llm_server_stdout.log
tail -f /media/lobo/BACKUP/KlimtechRAG/logs/llm_server_stderr.log
```

---

## Manualne indeksowanie (masowy ingest GPU)

```fish
source venv/bin/activate.fish

# Zatrzymaj LLM (zwalnia VRAM dla embeddingu GPU)
pkill llama-server

# Uruchom backend z GPU embedding
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python -m backend_app.main &

# Zaindeksuj wszystkie pending
curl -X POST "http://localhost:8000/ingest_all?limit=50"

# Sprawdź postęp
curl -s http://localhost:8000/files/stats | python3 -m json.tool

# Wróć do normalnego trybu
pkill -f backend_app.main
python start_klimtech.py
```

---

## Przyszłość: dwie karty AMD Instinct 32GB

Gdy dojdą nowe karty, w `start_klimtech.py` zmień:

```python
# Aktualne (jedna karta 16GB):
amd_env = {
    "HIP_VISIBLE_DEVICES": "0",
    ...
}
backend_env = {
    "KLIMTECH_EMBEDDING_DEVICE": "cpu",   # embedding na CPU (brak miejsca w VRAM)
    ...
}

# Docelowe (dwie karty):
amd_env = {
    "HIP_VISIBLE_DEVICES": "0",           # LLM na karcie 0 (32GB)
    ...
}
backend_env = {
    "KLIMTECH_EMBEDDING_DEVICE": "cuda:1",  # embedding na karcie 1 (32GB)
    ...
}
```

---

## Rozwiązywanie problemów

**OWUI nie widzi modelu:**
```fish
curl -s http://localhost:8000/v1/models | python3 -m json.tool
# Powinno zwrócić JSON z listą modeli. Jeśli nie — sprawdź czy backend działa.
```

**Plik wrzucony przez OWUI nie trafia do Nextcloud:**
```fish
# Sprawdź logi backendu podczas uploadu
tail -f logs/backend.log
# Sprawdź czy OWUI Function jest aktywna (przełącznik ON w Workspace → Functions)
# Sprawdź czy OWUI_API_KEY jest poprawny
```

**Qdrant nie indeksuje:**
```fish
curl -s "http://localhost:8000/rag/debug?query=test" | python3 -m json.tool
# Sprawdź qdrant_points i qdrant_indexed
# Jeśli qdrant_indexed < qdrant_points:
curl -X PATCH "http://localhost:6333/collections/klimtech_docs" \
  -H "Content-Type: application/json" \
  -d '{"hnsw_config": {"full_scan_threshold": 10}}'
```

**Nextcloud nie widzi nowych plików:**
```fish
podman exec nextcloud php occ files:scan --path=/admin/files/RAG_Dane
```

---

*Instrukcja wygenerowana: 2026-02-21 | KlimtechRAG v6.0*
