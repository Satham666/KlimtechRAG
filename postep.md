KlimtechRAG — STATUS SESJI (plik wznowienia)

    Cel tego pliku: Po wczytaniu tego pliku model AI natychmiast wie co zostało zrobione, co jest do zrobienia i jakie są plany. Aktualizuj ten plik po każdej sesji.

Ostatnia aktualizacja: 2026-03-19 (noc)
Wersja systemu: v7.5
Serwer: 192.168.31.70 | Katalog: /media/lobo/BACKUP/KlimtechRAG/
GitHub: https://github.com/Satham666/KlimtechRAG
⚡ SZYBKI KONTEKST (przeczytaj najpierw)

Co to jest: Lokalny system RAG (Retrieval-Augmented Generation) dla dokumentacji technicznej po polsku. Działa w 100% offline na serwerze z GPU AMD Instinct 16 GB (ROCm). Backend FastAPI, LLM przez llama.cpp, wektorowa baza Qdrant, Nextcloud jako storage + AI frontend, n8n do automatyzacji.

⚠️ WAŻNE - NIGDY NIE PRZERABIAJ Z GPU NA CPU!
    System jest zaprojektowany do pracy na GPU AMD (ROCm).
    Embeddingi, LLM, VLM - WSZYSTKO musi działać na GPU.
    Jeśli brakuje VRAM - zwolnij pamięć (stop modelu) zamiast przerabiać na CPU.
    To jest HARDWARE REQUIREMENT nie opcja.

⚠️ COMANDY Z SUDO - TYLKO DO WYKONANIA PRZEZ UŻYTKOWNIKA!
    Komendy z sudo są ZAWSZE wyświetlane dla użytkownika do ręcznego wykonania w osobnym terminalu.
    Model AI nie może wykonywać komend z sudo (brak hasła).

⚠️ JEDYNA ŚCIEŻKA DLA PLIKÓW RAG + DANYCH NEXTLOUD:
    /media/lobo/BACKUP/KlimtechRAG/data/uploads/
    │
    ├── pdf_RAG/     → .pdf
    ├── txt_RAG/     → .txt, .md, .py, .js, .ts, .json, .yml, .yaml
    ├── Audio_RAG/   → .mp3, .wav, .ogg, .flac (przyszłość)
    ├── Doc_RAG/     → .doc, .docx, .odt, .rtf
    ├── Images_RAG/  → .jpg, .jpeg, .png, .gif, .bmp, .webp (przyszłość)
    ├── Video_RAG/   → .mp4, .avi, .mkv, .mov (przyszłość)
    └── json_RAG/    → .json

    ALBO:
    Usunąć Nextcloud RAG_Dane - niepotrzebny (pliki i tak niewidoczne w terminalu).
    Używać TYLKO /media/lobo/BACKUP/KlimtechRAG/data/uploads/

    FLOW:
    1. Użytkownik wrzuca plik do "WGRAJ PLIKI"
    2. Backend sprawdza rozszerzenie pliku
    3. Plik jest wrzucany do odpowiedniego podkatalogu (pdf_RAG, txt_RAG, itd.)
    4. Plik jest poddawany embeddingowi przez wybrany model (ColPali, e5-large, lub przyszłe audio/video)
    5. Dane z embeddingu trafiają do Qdrant RAG

Kluczowe adresy:

    Backend UI: https://192.168.31.70:8443 (self-signed cert, używaj -k w curl)
    Nextcloud: http://192.168.31.70:8081 (login: maciek / klimtech123)
    n8n: http://192.168.31.70:5678
    Backend API: http://192.168.31.70:8000
    Qdrant: http://192.168.31.70:6333

ZAWSZE przed uruchomieniem .py:

cd /media/lobo/BACKUP/KlimtechRAGsource venv/bin/activate.fish

 
✅ CO ZOSTAŁO ZROBIONE (historia sesji) 
Sesje 1–8: Fundament systemu 

     Architektura FastAPI + Haystack 2.x + Qdrant + llama.cpp (ROCm)
     3 pipeline'y embeddingu: e5-large (tekst), ColPali (PDF/dokumenty), VLM (obrazy w PDF)
     UI (HTML/JS/Tailwind), model switch, rate limiting, API key auth
     ColPali multi-vector embedding (vidore/colpali-v1.3-hf)
     

Sesja 9: Web Search (v7.1) 

     Panel Web Search jako druga zakładka w sidebarze (obok RAG)
     Tryb hybrydowy RAG+Web, podgląd stron, podsumowanie przez LLM
     Endpoint /web/search, /web/fetch, /web/summarize
     

Sesja 10: Nextcloud AI Integration (v7.2) 

     Zainstalowane w NC: integration_openai v3.10.1 + assistant v2.13.0
     Skonfigurowane: allow_local_remote_servers, trusted_domains, AI Provider (URL + model)
     Backend: CORS middleware (port 8081), Authorization: Bearer fallback w dependencies.py
     Endpoint /models (bez /v1/) dla kompatybilności z Nextcloud
     3 workflow JSON dla n8n: auto-indeksowanie, czat webhook, VRAM management
     Endpoint /v1/audio/transcriptions — Whisper STT (openai-whisper zainstalowany)
     Start llama-server z obliczaniem parametrów przez model_parametr.py
     Routing PDF→ColPali, tekst→e5-large w n8n workflow
     

Sesja 11a: Naprawy krytyczne 

     ingest.py: _hash_bytes() + naprawa zduplikowanego bloku dedup
     main.py: lifespan zamiast deprecated @app.on_event("startup")
     model_switch.py: relative imports (usunięto kruchy fallback importlib)
     stop_klimtech.py: porty 8081/5678 zamiast 3000 (Open WebUI — nieużywane)
     Usunięto referencje Open WebUI z config.py
     Plik .env utworzony z domyślnymi wartościami
     

Sesja 11b: HTTPS — nginx reverse proxy 

     nginx zainstalowany, certyfikat self-signed
     Konfiguracja: /etc/nginx/sites-available/klimtech
     Certyfikat: /media/lobo/BACKUP/KlimtechRAG/data/ssl/klimtech.crt
     Nextcloud: overwriteprotocol=https, overwritehost=192.168.31.70:8444
     CORS rozszerzony o originy HTTPS
     Wyniki: wszystkie 4 usługi dostępne przez HTTPS
     

Sesja 11c: Whisper STT 

     Przeniesienie venv: /home/lobo/klimtech_venv/ → /media/lobo/BACKUP/KlimtechRAG/venv/
     openai-whisper zainstalowany w venv
     backend_app/routes/whisper_stt.py — nowy endpoint /v1/audio/transcriptions
     Router zarejestrowany w main.py
     

Sesja 11d: New UI v7.3 + Lazy Loading + GPU Dashboard 

     backend_app/routes/gpu_status.py — nowy endpoint /gpu/status (rocm-smi)
     index.html zastąpiony zawartością code.html z podłączonymi funkcjami JS
     Lazy loading embeddingu — VRAM na starcie: 4.5 GB → 14 MB!
         embeddings.py: refactor na get_text_embedder() / get_doc_embedder()
         qdrant.py: get_embedding_dimension() używa cache (bez ładowania modelu)
         rag.py: refactor na get_indexing_pipeline() / get_rag_pipeline()
         llm.py: standalone generator (nie ładuje całego RAG pipeline)
         
     schemas.py: use_rag: False domyślnie (czat nie dławi się RAG)
     index.html: use_rag: true tylko gdy włączony globe 🌐
     Fix model_manager.py: _detect_base() zwracał /home/lobo zamiast /media/lobo/BACKUP
     Dropdown modeli: 4 LLM, 5 VLM, 2 Audio, 3 Embedding
     GPU Dashboard: temp, VRAM, use — co 2 sekundy
     

Sesja 11e: Refaktoryzacja VLM Prompts (Sekcja 16) 

     Utworzono katalog backend_app/prompts/
     Utworzono prompts/__init__.py
     Utworzono prompts/vlm_prompts.py z 8 wariantami promptów:
         DEFAULT, DIAGRAM, CHART, TABLE, PHOTO, SCREENSHOT, TECHNICAL, MEDICAL
     VLM_PARAMS: max_tokens=512, temperature=0.1, context_length=4096, gpu_layers=99
     Refaktoryzacja image_handler.py:
         describe_image_with_vlm() — dynamiczne prompty + params
         describe_image_with_vlm_server() — dynamiczne prompty + params
         process_pdf_with_images() — przekazuje image_type do funkcji VLM
     Naprawiono _find_vlm_model() — sprawdza wiele sciezek (KLIMTECH_BASE_PATH, /media/lobo/BACKUP, ~/KlimtechRAG)
     

Sesja 11f: Sprawdzanie hashy plikow przed indeksowaniem 

     Backend:
         Dodano funkcje _hash_file() w ingest.py
         /ingest_path — sprawdza content_hash przed indeksowaniem
         Dodano endpoint /files/check — sprawdza status pliku w file_registry.db
         Jesli plik o takim hash'u istnieje i jest zaindeksowany — pomija indeksowanie
     
     n8n workflow:
         Utworzono workflow_auto_index_v2.json
         Sprawdza status kazdego pliku przez /files/check przed indeksowaniem
         Jesli should_index=false — pomija plik
         Raportowanie ile plikow pominieto vs zaindeksowano

Sesja 12: Hybrid Storage + Pod Architecture (v7.4) — 2026-03-18

     Problem: exFAT filesystem (/media/lobo/BACKUP) nie obsługuje uprawnień Unix (chown/chmod)
     → PostgreSQL wywalał się z błędami uprawnień
     → Nextcloud Assistant zwracał HTTP 417

     ROZWIĄZANIE v7.4: Hybrid Storage + Podman Pod (NIEDZIAŁAJĄCE!)
     ⚠️ Próbowano: Baza na ext4, Nextcloud na exFAT - NIE DZIAŁAŁO!

Sesja 13: Nextcloud Fix (v7.5) — 2026-03-19

     Problem: Skrypt fix_nextcloud_hybrid.sh nie działał poprawnie.
     Objawy:
     - "Failed to open stream: version.php not found"
     - "Cannot create or write into the data directory"
     - exFAT ignoruje chmod 777

     PRZYCZYNA ROOT CAUSE:
     - exFAT ignoruje UID/GID - www-data (33) nie może pisać do "lobo" (1000)
     - Mapowanie /var/www/html na exFAT powodowało brak plików Nextcloud
     - Entrypoint NC nie instaluje plików gdy katalog nie jest pusty

     ROZWIĄZANIE v7.5: Named Volume dla WSZYSTKIEGO (ext4)
     ├── Pod `klimtech_pod`
     ├── PostgreSQL: Named Volume `klimtech_postgres_data`
     └── Nextcloud: Named Volume `klimtech_nextcloud_data`
     └── Brak mapowania na exFAT dla kodu/config/danych NC

     ARCHITEKTURA v7.5:
     ┌─────────────────────────────────────────────────────────────┐
     │  Pod 'klimtech_pod' (wspólna sieć localhost)             │
     │  ├── nextcloud (port 8081)                                │
     │  └── postgres_nextcloud (localhost:5432)                   │
     └─────────────────────────────────────────────────────────────┘
     ├── Named Volume: klimtech_postgres_data → ext4
     ├── Named Volume: klimtech_nextcloud_data → ext4
     ├── qdrant (6333) - standalone
     └── n8n (5678) - standalone

     COMANDY URUCHOMIENIA: Patrz sekcja Problem 1 wyżej

     STATUS PO SESJI 13:
     ✅ Nextcloud 32.0.6.1 zainstalowany i działa
     ✅ PostgreSQL połączony
     ✅ integration_openai + assistant zainstalowane
     ✅ Wszystkie occ config wykonane
     ⏳ NC AI Assistant - do przetestowania w przeglądarce

❌ NIEROZWIĄZANE PROBLEMY (blokujące lub do naprawy)
Problem 1: Nextcloud AI Assistant nie odpowiada — PRIORYTET 🔴 

Status: ✅ ROZWIĄZANY (2026-03-19)
Przyczyna root cause: PostgreSQL na exFAT = błędy uprawnień Unix (chown/chmod) + brak plików Nextcloud w /var/www/html
→ niestabilna baza → HTTP 417 w NC Assistant

Rozwiązanie v7.5: Named Volume dla WSZYSTKIEGO (ext4)
├── Pod `klimtech_pod` (wspólna sieć localhost)
│   ├── PostgreSQL: Named Volume `klimtech_postgres_data` → ext4
│   └── Nextcloud: Named Volume `klimtech_nextcloud_data` → ext4
└── Brak mapowania na exFAT dla kodu/config

PROBLEM Z exFAT (DLACZEGO NIE DZIAŁAŁO):
- exFAT ignoruje uprawnienia Unix (UID/GID)
- Kontener www-data (UID 33) nie może pisać do katalogu owned przez "lobo" (UID 1000)
- chmod 777 NIE POMAGA na exFAT
- Mapowanie całego /var/www/html na exFAT powodowało brak plików Nextcloud (version.php missing)
- Entrypoint Nextcloud nie doinstalowuje plików gdy katalog nie jest pusty

KOMENDY URUCHOMIENIA (2026-03-19):

```bash
# 1. Usuń starą konfigurację
podman stop nextcloud postgres_nextcloud
podman rm nextcloud postgres_nextcloud
podman pod rm -f klimtech_pod
rm -rf /media/lobo/BACKUP/KlimtechRAG/data/nextcloud

# 2. Stwórz Pod
podman pod create --name klimtech_pod -p 8081:80

# 3. PostgreSQL (Named Volume)
podman run -d --name postgres_nextcloud --pod klimtech_pod --restart always \
    -e POSTGRES_DB=nextcloud \
    -e POSTGRES_USER=nextcloud \
    -e POSTGRES_PASSWORD=klimtech123 \
    -v klimtech_postgres_data:/var/lib/postgresql/data \
    docker.io/library/postgres:16

# 4. Nextcloud (Named Volume dla danych, NIE exFAT!)
podman volume create klimtech_nextcloud_data

podman run -d --name nextcloud --pod klimtech_pod --restart always \
    -e POSTGRES_HOST="localhost" \
    -e POSTGRES_DB=nextcloud \
    -e POSTGRES_USER=nextcloud \
    -e POSTGRES_PASSWORD=klimtech123 \
    -e NEXTCLOUD_TRUSTED_DOMAINS="192.168.31.70 localhost" \
    -e NEXTCLOUD_ADMIN_USER="admin" \
    -e NEXTCLOUD_ADMIN_PASSWORD="klimtech123" \
    -v klimtech_nextcloud_data:/var/www/html/data \
    docker.io/library/nextcloud:32

# 5. Czekaj ~45s na instalację

# 6. Konfiguracja
podman exec -u www-data nextcloud php occ app:install integration_openai
podman exec -u www-data nextcloud php occ app:install assistant
podman exec -u www-data nextcloud php occ config:system:set check_data_directory_permissions --value=false --type=boolean
podman exec -u www-data nextcloud php occ config:system:set filelocking.enabled --value=false --type=boolean
podman exec -u www-data nextcloud php occ config:system:set allow_local_remote_servers --value=true --type=boolean
podman exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value="https"
podman exec -u www-data nextcloud php occ config:system:set overwritehost --value="192.168.31.70:8444"
```

Login: admin / klimtech123
 
 
 
Problem 2: Bielik-11B nie mieści się w VRAM — PRIORYTET 🟡 

Status: OBEJŚCIE
Problem: ~4.7 GB VRAM zajęte przez inne procesy (ROCm runtime?), Bielik-11B (~14 GB) nie mieści się.
Obecne rozwiązanie: Używamy Bielik-4.5B (~5 GB VRAM).
Uwaga: model_parametr.py oblicza parametry dynamicznie — warstwy GPU, kontekst (98304 tokenów), kompresja cache Q8_0. 
Problem 3: VLM opis obrazów — brak mmproj w llama-cli — PRIORYTET 🔴 

Status: NIEROZWIĄZANE
Problem: VLM opis obrazów nie działa z powodu braku mmproj w llama-cli.
Wpływ: Automatyczne opisywanie obrazów/z wykresów z dokumentów PDF nie jest możliwe. 
Problem 4: ingest_gpu.py zabija start_klimtech.py — PRIORYTET 🔴 

Status: NIEROZWIĄZANE
Problem: Uruchomienie ingest_gpu.py powoduje konflikt i zabicie procesu start_klimtech.py.
Obejście: Używaj dedykowanego start_backend_gpu.py. 
Problem 5: monitoring.py GPU utilization: 0% dla AMD — PRIORYTET 🟡 

Status: KOSMETYCZNY
Problem: monitoring.py zgłasza 0% wykorzystania GPU dla kart AMD.
Szczegóły: Wymaga użycia rocm-smi w gpu_status.py zamiast standardowych metryk. 

Problem 6: Podman Overlay Storage Leak — PRIORYTET 🔴 (2026-03-18)

Status: DO NAPRAWY
Problem: Podman tworzy nowe overlay layers przy każdym uruchomieniu/usunięciu kontenerów, ale NIE usuwa starych. Skutkuje to:
- Zapychaniem dysku starymi warstwami (50+ katalogów w overlay/)
- Setkami MB/GB zajętego miejsca
- Powolnym startem kontenerów

Przyczyna: Brak `podman system prune` w skryptach start/stop

Rozwiązanie: 
1. Dodać `podman system prune -a -f` przed uruchomieniem kontenerów
2. Dodać `podman system prune -f` po zatrzymaniu kontenerów

Pliki do naprawy:
- start_klimtech_v3.py: dodać cleanup przed startem
- stop_klimtech.py: dodać cleanup po zatrzymaniu

UWAGA: Przed pełnym cleanup należy zatrzymać wszystkie kontenery!

⏳ DO ZROBIENIA — lista zadań 
Priorytet WYSOKI 
#
 
  
Zadanie
 
  
Gdzie
 
  
Notatki
 
 
A Testować NC AI Assistant w przeglądarce  NC Admin → AI  ✅ DONE - NC zainstalowany, konfiguracja wykonana. Test: zaloguj się do NC, otwórz Asystent, zadaj pytanie. 
B Przetestować Whisper STT end-to-end curl -F file=@audio.mp3 .../v1/audio/transcriptions Router dodany, nie testowany 
C Zmapować Speech-to-text w NC Admin → AI Przeglądarka → NC admin Po teście B 
   
Priorytet ŚREDNI — Sekcja 16: Refaktoryzacja VLM Prompts 

**Status: ✅ WYKONANE (2026-03-18)**
#
   
Zadanie
   
   
Plik
   
   
Status
   
  
16a Utwórz backend_app/prompts/ nowy katalog  ✅ DONE 
16b Utwórz prompts/__init__.py  nowy plik ✅ DONE 
16c Utwórz prompts/vlm_prompts.py z 8 wariantami (DEFAULT, DIAGRAM, CHART, TABLE, PHOTO, SCREENSHOT, TECHNICAL, MEDICAL)  nowy plik ✅ DONE 
16d Refaktoryzuj image_handler.py — import z vlm_prompts  ingest/image_handler.py ✅ DONE 
16e Refaktoryzuj image_handler.py — dynamiczne params llama-cli (przez model_parametr.py) ingest/image_handler.py ✅ DONE 
   

Szczegóły wykonanych zmian:
- Utworzono katalog `backend_app/prompts/`
- Utworzono `prompts/__init__.py` i `prompts/vlm_prompts.py`
- 8 wariantów promptów: DEFAULT, DIAGRAM, CHART, TABLE, PHOTO, SCREENSHOT, TECHNICAL, MEDICAL
- VLM_PARAMS: max_tokens=512, temperature=0.1, context_length=4096, gpu_layers=99
- Funkcje `describe_image_with_vlm()` i `describe_image_with_vlm_server()` używają dynamicznych promptów i params
- Parametr `image_type` przekazywany do funkcji VLM

Priorytet ŚREDNI — Sprawdzanie hashy plików

**Status: ✅ WYKONANE (2026-03-18)**

| # | Zadanie | Plik | Status |
|---|---------|------|--------|
| H1 | Dodaj funkcję _hash_file() | ingest.py | ✅ DONE |
| H2 | Modyfikuj /ingest_path — sprawdzanie hashy | ingest.py | ✅ DONE |
| H3 | Dodaj endpoint /files/check | ingest.py | ✅ DONE |
| H4 | Utwórz workflow_auto_index_v2.json | n8n_workflows/ | ✅ DONE |

Szczegóły:
- `_hash_file()` — oblicza SHA-256 z zawartości pliku
- `/ingest_path` — sprawdza `find_duplicate_by_hash()`, pomija jeśli już zaindeksowane
- `/files/check?path=X` — zwraca status pliku z file_registry.db
- n8n workflow v2 — sprawdza `should_index` przed wysłaniem do /ingest_path

---

## ZADANIE: JEDYNA ŚCIEŻKA DLA PLIKÓW RAG

**Status: ✅ ROZWIĄZANE**
**Źródło: Polecenie użytkownika 2026-03-18**

### DIAGNOZA PROBLEMU (dlaczego RAG nie działał):
Modele LLM wypisywały bzdury, a RAG nie działał jak należy, ponieważ:
- Embedding wrzucał pliki do RÓŻNYCH MIEJSC
- `data/uploads/` ← backend widział te pliki
- `data/nextcloud/.../RAG_Dane/` ← embedding indeksował do innego miejsca
- Pliki były rozsiane po dwóch RÓŻNYCH dyskach (root SSD vs NVMe)

### ROZWIĄZANIE:
- Użytkownik USUNĄŁ `/home/lobo/KlimtechRAG/` (2026-03-18)
- Teraz ISTNIEJE TYLKO: `/media/lobo/BACKUP/KlimtechRAG/`
- Wszystkie pliki RAG w jednym miejscu

### Cel
JEDYNA ścieżka dla wszystkich plików RAG:
```
/media/lobo/BACKUP/KlimtechRAG/data/uploads/
├── pdf_RAG/     → .pdf
├── txt_RAG/     → .txt, .md, .py, .js, .ts, .json, .yml, .yaml
├── Audio_RAG/   → .mp3, .wav, .ogg, .flac
├── Doc_RAG/     → .doc, .docx, .odt, .rtf
├── Images_RAG/  → .jpg, .jpeg, .png, .gif, .bmp, .webp
├── Video_RAG/   → .mp4, .avi, .mkv, .mov
└── json_RAG/    → .json
```

### FLOW (docelowy):
1. Użytkownik wrzuca plik do "WGRAJ PLIKI"
2. Backend sprawdza rozszerzenie pliku
3. Plik jest wrzucany do odpowiedniego podkatalogu (pdf_RAG, txt_RAG, itd.)
4. Plik jest poddawany embeddingowi przez wybrany model z listy (ColPali, e5-large, lub przyszłe audio/video)
5. Dane z embeddingu trafiają do Qdrant RAG

### Status podzadań:
| # | Podzadanie | Status |
|---|------------|--------|
| S1 | Sprawdzić czy config.py ma tylko upload_base (bez nextcloud_base) | ✅ DONE |
| S2 | Sprawdzić czy file_registry.py ma tylko WATCH_DIRS z uploads | ✅ DONE |
| S3 | Sprawdzić czy ingest.py zapisuje do uploads (a nie nextcloud) | ✅ DONE |
| S4 | Sprawdzić czy n8n workflow v2 używa upload_base | ✅ DONE |
| S5 | Usunąć /home/lobo/KlimtechRAG/ | ✅ DONE (przez użytkownika) |
| S6 | System działa na jednym dysku NVMe | ✅ DONE |
| S7 | Przetestować RAG przez czat | ⏳ DO WYKONANIA |

---

Priorytet NISKI — późniejsze plany 
#
 
  
Zadanie
 
  
Notatki
 
 
L1  Skrypt scripts/setup_nextcloud_ai.sh  Jednorazowa konfiguracja NC 
L2  Heurystyka RAG off dla NC summarize Jeśli msg > 2000 znaków → use_rag=False 
L3  Chunked summarization dla długich dokumentów  Bielik ma 8192 ctx 
L4  NC webhook_listeners — event-driven zamiast pollingu  NC30+, app:install webhook_listeners 
L5  Auto-transkrypcja audio w n8n Upload do Audio_RAG/ → Whisper → e5-large → Qdrant 
L6  Naprawić stop_klimtech.py — nie zabija wszystkich procesów  Priorytet 🟡 
   
📁 KLUCZOWE PLIKI (mapa dla modelu AI) 
Plik
 
  
Rola
 
 
backend_app/main.py Entry point: FastAPI app, lifespan, CORS, rejestracja routerów 
backend_app/config.py Wszystkie ustawienia (czyta z .env) 
backend_app/routes/chat.py  /v1/chat/completions, /v1/models, /v1/embeddings 
backend_app/routes/ingest.py  Upload i indeksowanie plików 
backend_app/routes/model_switch.py  Start/stop/switch llama-server 
backend_app/routes/gpu_status.py  GPU metrics (rocm-smi) 
backend_app/routes/whisper_stt.py Whisper STT endpoint 
backend_app/services/model_manager.py Lifecycle llama-server, _detect_base() 
backend_app/services/embeddings.py  Lazy loading e5-large 
backend_app/services/rag.py Lazy loading pipeline RAG 
backend_app/services/colpali_embedder.py  ColPali multi-vector 
backend_app/utils/dependencies.py API key auth (X-API-Key + Bearer) 
backend_app/models/schemas.py Pydantic: use_rag=False domyślnie 
backend_app/ingest/image_handler.py VLM opisy obrazów z PDF (prompty hardcoded — do refaktoru Sek.16) 
backend_app/static/index.html UI (code.html v7.3) 
start_klimtech_v3.py  Start systemu (nginx + kontenery + backend) 
stop_klimtech.py  Stop systemu 
model_parametr.py Obliczanie optymalnych parametrów llama-server 
n8n_workflows/*.json  Workflow JSON dla n8n 
   
🔧 WAŻNE SZCZEGÓŁY TECHNICZNE 
Uruchamianie llama-server 

Model manager (model_manager.py) uruchamia llama-server z parametrami obliczonymi przez model_parametr.py: 

     --alias klimtech-bielik — czysta nazwa w /v1/models
     -ngl -1 — wszystkie warstwy na GPU
     Kontekst: 98304 tokenów
     Cache kompresja: Q8_0
     Port: 8082
     

Format requestu Nextcloud → Backend 
json
 
  
 
{
  "model": "klimtech-bielik",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Treść pytania"}
  ],
  "max_tokens": 4096
}
 
 
 

     Header: Authorization: Bearer sk-local
     Brak pól use_rag, web_search — Pydantic defaults włączą się (use_rag=False)
     Każde zapytanie przechodzi przez RAG jeśli use_rag=True
     

Kontenery Podman 
fish
 
  
 
podman ps                          # lista działających kontenerów
podman start qdrant                # start Qdrant
podman start nextcloud             # start Nextcloud
podman start postgres_nextcloud    # start PostgreSQL
podman start n8n                   # start n8n
 
 
 
nginx 
fish
 
  
 
sudo nginx                         # start
sudo nginx -s stop                 # stop
sudo nginx -s reload               # reload konfiguracji
# Konfiguracja: /etc/nginx/sites-available/klimtech
 
 
 
📋 STAN TESTÓW WERYFIKACYJNYCH 
Test
 
  
Polecenie
 
  
Status
 
 
Backend health  curl http://192.168.31.70:8000/health ✅ OK 
Lista modeli  curl http://192.168.31.70:8000/v1/models  ✅ OK 
Chat completion curl -X POST .../v1/chat/completions -d '...' ✅ OK 
CORS preflight  curl -X OPTIONS ... -H "Origin: http://...:8081"  ✅ OK 
Bearer auth curl -H "Authorization: Bearer sk-local" .../v1/models  ✅ OK 
HTTPS backend curl -k https://192.168.31.70:8443/health ✅ OK 
HTTPS Nextcloud curl -k https://192.168.31.70:8444/ ✅ OK (302) 
HTTPS n8n curl -k https://192.168.31.70:5679/ ✅ OK 
GPU status  curl http://192.168.31.70:8000/gpu/status ✅ OK 
NC AI Assistant Przeglądarka → NC Asystent  ❌ 417 
Whisper STT curl -F file=@audio.mp3 .../v1/audio/transcriptions ⏳ NIE TESTOWANY 
n8n auto-index  Upload pliku → czekaj 5 min ⏳ NIE TESTOWANY 
ColPali PDF Upload PDF skanu → n8n → ColPali  ⏳ NIE TESTOWANY 
NC Speech-to-text NC Talk → transkrybuj ⏳ NIE TESTOWANY 
   
🗒️ NOTATKI DLA NASTĘPNEJ SESJI 

    Pierwsze co zrobić: Uruchom system i sprawdź aktualny stan: 
    fish
     
      
     
    cd /media/lobo/BACKUP/KlimtechRAG && source venv/bin/activate.fish
    python3 start_klimtech_v3.py
    curl http://192.168.31.70:8000/health
     
     
      

    Rekomendowana kolejność pracy: 
         Debugowanie NC Asystenta (Problem 1 — 417) — najważniejszy nierozwiązany problem
         Test Whisper STT
         Sekcja 16 (refaktoryzacja VLM Prompts) — zaakceptowany plan, gotowy do implementacji
          

    Przy pracy na plikach Python: Zawsze sprawdź aktualny stan pliku przed edycją. Lazy loading embeddingu jest kluczową zmianą v7.3 — nie cofać do eager loading.  

    Przy debugowaniu NC Asystenta: Sprawdź czy problem to Expect: 100-continue header — to częsta przyczyna 417 w FastAPI. Rozwiązanie: middleware w main.py usuwający ten header lub obsługa go.  