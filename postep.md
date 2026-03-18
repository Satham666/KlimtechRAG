KlimtechRAG — STATUS SESJI (plik wznowienia)

    Cel tego pliku: Po wczytaniu tego pliku model AI natychmiast wie co zostało zrobione, co jest do zrobienia i jakie są plany. Aktualizuj ten plik po każdej sesji.

Ostatnia aktualizacja: 2026-03-18
Wersja systemu: v7.3
Serwer: 192.168.31.70 | Katalog: /media/lobo/BACKUP/KlimtechRAG/
GitHub: https://github.com/Satham666/KlimtechRAG
⚡ SZYBKI KONTEKST (przeczytaj najpierw)

Co to jest: Lokalny system RAG (Retrieval-Augmented Generation) dla dokumentacji technicznej po polsku. Działa w 100% offline na serwerze z GPU AMD Instinct 16 GB (ROCm). Backend FastAPI, LLM przez llama.cpp, wektorowa baza Qdrant, Nextcloud jako storage + AI frontend, n8n do automatyzacji.

Kluczowe adresy:

    Backend UI: https://192.168.31.70:8443 (self-signed cert, używaj -k w curl)
    Nextcloud: http://192.168.31.70:8081 (login: admin / klimtech123)
    n8n: http://192.168.31.70:5678
    Backend API: http://192.168.31.70:8000

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
     

❌ NIEROZWIĄZANE PROBLEMY (blokujące lub do naprawy) 
Problem 1: Nextcloud AI Assistant nie odpowiada — PRIORYTET 🔴 

Status: NIEROZWIĄZANY
Objawy: Po wysłaniu pytania w Asystencie NC — ciągłe zapytania POST /check_generation z kodem HTTP 417 (Expectation Failed). Pętla bez końca.
Diagnoza do tej pory: 

     Backend działa — curl do /v1/chat/completions zwraca poprawną odpowiedź
     API key sk-local ustawiony w NC admin
     URL http://192.168.31.70:8000 dostępny z wnętrza kontenera
     Endpoint /models (bez /v1/) działa
     CORS dodany dla portu 8081
     

Możliwe przyczyny (NIE zbadane): 

    Sesja/cache przeglądarki trzyma starą konfigurację 
    Provider w NC admin dla konkretnego zadania nie jest ustawiony na "OpenAI and LocalAI integration" 
    Problem specyficzny dla /check_generation — NC używa background task queue, backend może nie zwracać odpowiedzi w oczekiwanym formacie 
    Header Expect: 100-continue wysyłany przez NC — FastAPI domyślnie go nie obsługuje → 417 

Do wypróbowania w następnej sesji: 
fish
 
  
 
# Sprawdź logi NC podczas próby użycia Asystenta
podman logs nextcloud 2>&1 | tail -100

# Sprawdź czy NC wysyła Expect: 100-continue
# Dodaj logowanie headerów do backendu tymczasowo

# Wyczyść cache przeglądarki / spróbuj incognito
# Sprawdź w NC Admin → AI czy wszystkie taski mają provider
 
 
 
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
⏳ DO ZROBIENIA — lista zadań 
Priorytet WYSOKI 
#
 
  
Zadanie
 
  
Gdzie
 
  
Notatki
 
 
A Debugować 417 z NC Asystentem NC admin, nginx logi, backend logi  Patrz Problem 1 wyżej 
B Przetestować Whisper STT end-to-end curl -F file=@audio.mp3 .../v1/audio/transcriptions Router dodany, nie testowany 
C Zmapować Speech-to-text w NC Admin → AI Przeglądarka → NC admin Po teście B 
   
Priorytet ŚREDNI — Sekcja 16: Refaktoryzacja VLM Prompts 

Zaakceptowany plan (z akceptacja.md), NIE zaczęty: 
#
 
  
Zadanie
 
  
Plik
 
  
Status
 
 
16a Utwórz backend_app/prompts/ nowy katalog  ⏳ 
16b Utwórz prompts/__init__.py  nowy plik ⏳ 
16c Utwórz prompts/vlm_prompts.py z 8 wariantami (DEFAULT, DIAGRAM, CHART, TABLE, PHOTO, SCREENSHOT, TECHNICAL, MEDICAL)  nowy plik ⏳ 
16d Refaktoryzuj image_handler.py — import z vlm_prompts  ingest/image_handler.py ⏳ 
16e Refaktoryzuj image_handler.py — dynamiczne params llama-cli (przez model_parametr.py) ingest/image_handler.py ⏳ 
   

Szczegóły 16e: Aktualnie hardcoded: -n 512, --temp 0.1, -ngl 99, -c 4096. Przenieść do config.py jako vlm_max_tokens, vlm_temperature, vlm_context. 
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