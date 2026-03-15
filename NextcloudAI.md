# NextcloudAI — Plan wdrożenia (Sekcje 11, 12, 13)

**Data:** 2026-03-15
**Wersja docelowa:** v7.2
**Powiązanie:** PODSUMOWANIE.md sekcje 11, 12, 13

---

## Stan wyjściowy — co już istnieje

| Komponent | Status | Szczegóły |
|-----------|--------|-----------|
| Kontener Nextcloud (Podman) | ISTNIEJE | start/stop w skryptach, dane w `data/nextcloud/` |
| Kontener PostgreSQL | ISTNIEJE | `postgres_nextcloud`, baza Nextcloud |
| Kontener n8n | ISTNIEJE | dane w `data/n8n/`, port 5678 |
| Backend `/v1/chat/completions` | ISTNIEJE | OpenAI-compatible, RAG domyślnie włączony |
| Backend `/v1/models` | ISTNIEJE | Zwraca `klimtech-bielik`, format OpenAI |
| Backend `/v1/embeddings` | ISTNIEJE | e5-large (1024 dim), format OpenAI |
| Watchdog (watch_nextcloud.py) | ISTNIEJE | v3.0, monitoruje RAG_Dane/*, auto-ingest |
| ColPali embedder | ISTNIEJE | `klimtech_colpali`, multi-vector, on-demand |
| Model switch endpoints | ISTNIEJE | `/model/start`, `/model/stop`, `/model/switch` |
| **CORS middleware** | **BRAK** | Krytyczne dla Nextcloud (przeglądarka) |
| **integration_openai app** | **BRAK** | Nie zainstalowana w Nextcloud |
| **assistant app** | **BRAK** | Nie zainstalowana w Nextcloud |
| **config.php: allow_local** | **BRAK** | Blokuje połączenia do prywatnych IP |
| **n8n workflow JSON** | **BRAK** | Tylko opis w PODSUMOWANIE.md |
| **VRAM management API** | **BRAK** | Brak dedykowanego mechanizmu dla n8n |
| **Mini LLM serwis** | **BRAK** | Brak drugiego llama-server |
| **Whisper STT** | **BRAK** | Brak Speech-to-Text (endpoint + model) |

---

## Architektura embedding/indeksowania — pipeline dokumentów

Trzy pipeline'y do przetwarzania różnych typów dokumentów:

| Pipeline | Model | VRAM | Kolekcja Qdrant | Typ dokumentów | Plik źródłowy |
|----------|-------|------|-----------------|----------------|---------------|
| **A: Tekst** | `intfloat/multilingual-e5-large` (1024 dim) | ~2.5 GB GPU / CPU | `klimtech_docs` | .txt, .md, .py, .json, .docx, PDF z warstwą tekstową | `services/embeddings.py` |
| **B: ColPali (dokumenty)** | `vidore/colpali-v1.3-hf` (128 dim, multi-vector) | ~6-8 GB | `klimtech_colpali` | PDF skany, dokumenty mieszane (tekst+grafika+zdjęcia+tabele) | `services/colpali_embedder.py` |
| **C: VLM wzbogacanie** | Qwen2.5-VL-7B / LFM2.5-VL-1.6B | ~4.7 / ~3.2 GB | (wzbogaca tekst → Pipeline A) | PDF z osadzonymi obrazami | `ingest/image_handler.py` |

**ColPali** to pipeline dedykowany do pracy z dokumentami — rozumie layout strony, tabele, wykresy i diagramy na poziomie wizualnym. Każda strona PDF jest traktowana jako obraz i embedowana jako multi-vector (ColBERT-style). Idealny do skanów PDF, które stanowią ~95% plików.

**Routing:** Obecnie ręczny (nagłówek `X-Embedding-Model` lub dropdown w UI). W n8n workflow dodamy automatyczny routing: pliki .txt/.md → Pipeline A, pliki .pdf → Pipeline B (ColPali).

---

## Architektura VRAM (16 GB GPU)

Kluczowe ograniczenie: na GPU zmieści się tylko **jeden duży model** naraz.

| Model | VRAM | Rola |
|-------|------|------|
| Bielik-11B Q8_0 | ~14 GB | Główny LLM (RAG, czat) |
| Bielik-4.5B Q8_0 | ~4.8 GB | Mini LLM (proste zadania Nextcloud) |
| e5-large (embedding tekstu) | ~2.5 GB GPU / CPU | Embedding tekstu (domyślnie CPU) |
| ColPali v1.3 (embedding dokumentów) | ~6-8 GB | Embedding wizualny PDF — dokumenty mieszane |
| Qwen2.5-VL-7B Q4 | ~4.7 GB | VLM opisy obrazów ze skanów PDF |
| LFM2.5-VL-1.6B | ~3.2 GB | Lekki VLM do obrazów |

**Strategia:** Przełączanie VRAM przez n8n — jeden model na GPU naraz. n8n workflow decyduje który model załadować w zależności od zadania (RAG chat vs indeksowanie tekstu vs ColPali dokumenty vs VLM).

**Ścieżki modeli (do użycia w n8n i skryptach):**

| Model | Ścieżka |
|-------|---------|
| Bielik-11B | `modele_LLM/model_thinking/speakleash_Bielik-11B-v3.0-Instruct-GGUF_Bielik-11B-v3.0-Instruct.Q8_0.gguf` |
| Bielik-4.5B | `modele_LLM/model_thinking/speakleash_Bielik-4.5B-v3.0-Instruct-GGUF_Bielik-4.5B-v3.0-Instruct.Q8_0.gguf` |
| Qwen2.5-VL-7B | `modele_LLM/model_video/unsloth_Qwen2.5-VL-7B-Instruct-GGUF_Qwen2.5-VL-7B-Instruct-UD-Q4_K_XL.gguf` |
| LFM2.5-VL-1.6B | `modele_LLM/model_video/LiquidAI_LFM2.5-VL-1.6B-GGUF_LFM2.5-VL-1.6B-BF16.gguf` |

---

## SEKCJA 11: Integracja Nextcloud AI Assistant

### 11.1 Instalacja aplikacji Nextcloud

**Cel:** Zainstalować `integration_openai` i `assistant` w kontenerze Nextcloud.

**Kroki:**

1. **Zainstaluj integration_openai:**
   ```bash
   podman exec -u www-data nextcloud php occ app:install integration_openai
   ```

2. **Zainstaluj assistant:**
   ```bash
   podman exec -u www-data nextcloud php occ app:install assistant
   ```

3. **Zweryfikuj instalację:**
   ```bash
   podman exec -u www-data nextcloud php occ app:list --enabled | grep -E "integration_openai|assistant"
   ```

### 11.2 Konfiguracja config.php — KRYTYCZNE

**Cel:** Umożliwić Nextcloud łączenie się z lokalnym backendem (prywatne IP).

**Plik:** `data/nextcloud/config/config.php`
(wewnątrz kontenera: `/var/www/html/config/config.php`)

**Dodać do tablicy `$CONFIG`:**
```php
'allow_local_remote_servers' => true,
```

**Metoda — przez podman exec:**
```bash
podman exec -u www-data nextcloud php occ config:system:set \
  allow_local_remote_servers --value=true --type=boolean
```

**Weryfikacja:**
```bash
podman exec -u www-data nextcloud php occ config:system:get allow_local_remote_servers
# Oczekiwany wynik: true
```

**Bez tego ustawienia Nextcloud zwróci błąd połączenia — to najczęstsza przyczyna niepowodzenia integracji.**

### 11.3 Konfiguracja AI Provider (Admin -> Artificial Intelligence)

**Cel:** Podłączyć Nextcloud do backendu KlimtechRAG jako OpenAI-compatible provider.

**Konfiguracja w panelu admina Nextcloud (`http://192.168.31.70:8443/settings/admin/ai`):**

| Pole | Wartość | UWAGA |
|------|---------|-------|
| Service URL | `http://192.168.31.70:8000` | **BEZ `/v1/` na końcu!** Nextcloud sam dodaje `/v1/` |
| API Key | `sk-local` lub pusty | Backend ma auth wyłączony (`api_key=None`) |
| Service Name | `KlimtechRAG Bielik-11b` | Opcjonalne, dla czytelności |
| Model | `klimtech-bielik` | Z dropdown (pobierane z `/v1/models`) |

**Pułapki:**
- Podwójne `/v1/v1/` — jeśli wpiszesz URL z `/v1/` na końcu
- Pusty dropdown modeli — sprawdź czy backend działa: `curl http://192.168.31.70:8000/v1/models`
- "Connection refused" — brak `allow_local_remote_servers` w config.php

### 11.4 Mapowanie zadań (Task Providers)

**Cel:** Przypisać KlimtechRAG jako provider dla typów zadań AI w Nextcloud.

W panelu **Admin -> Artificial Intelligence**, dla każdego z poniższych typów zadań wybrać "OpenAI and LocalAI integration":

| Typ zadania | Provider | Uwagi |
|-------------|----------|-------|
| Free prompt | OpenAI and LocalAI integration | Główny czat AI |
| Summarize | OpenAI and LocalAI integration | Podsumowania dokumentów |
| Generate headline | OpenAI and LocalAI integration | Nagłówki |
| Reformulate | OpenAI and LocalAI integration | Przeformułowanie tekstu |
| Context Write | OpenAI and LocalAI integration | Pisanie z kontekstem |
| Extract topics | OpenAI and LocalAI integration | Ekstrakcja tematów |

**Obsługiwane po wdrożeniu Whisper (Faza 4):**
- Speech-to-text -> OpenAI and LocalAI integration (po dodaniu `/v1/audio/transcriptions`)

**NIE obsługiwane (zostawić domyślne lub wyłączyć):**
- Image generation (wymaga Stable Diffusion / DALL-E)

### 11.5 Dodanie CORS do backendu — WYMAGANE

**Cel:** Backend musi akceptować żądania cross-origin z Nextcloud.

**Plik:** `backend_app/main.py`

**Zmiana:** Dodać `CORSMiddleware` z FastAPI:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.31.70:8443",   # Nextcloud
        "http://192.168.31.70:8000",   # Backend UI
        "http://localhost:8443",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Uwaga:** Nextcloud `integration_openai` wykonuje requesty server-side (PHP), więc CORS nie jest wymagany dla samych API calls. Jednak jest potrzebny jeśli Nextcloud Assistant UI wykonuje bezpośrednie żądania z przeglądarki. Dodajemy prewencyjnie.

### 11.6 Test integracji

```bash
# 1. Sprawdź czy backend zwraca modele
curl http://192.168.31.70:8000/v1/models

# 2. Test chat completion (symulacja Nextcloud)
curl -X POST http://192.168.31.70:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{
    "model": "klimtech-bielik",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Co to jest RAG?"}
    ]
  }'

# 3. Test z poziomu Nextcloud Assistant
# Otwórz http://192.168.31.70:8443 -> ikona AI Assistant -> wpisz pytanie
```

### 11.7 Skrypt automatyzujący (opcjonalny)

**Cel:** Skrypt `scripts/setup_nextcloud_ai.sh` do jednorazowej konfiguracji.

Zawartość:
- Instalacja apps (integration_openai, assistant)
- Ustawienie `allow_local_remote_servers`
- Weryfikacja połączenia z backendem
- Raport statusu

---

## SEKCJA 12: Workflow n8n — automatyzacja

### 12.1 Konfiguracja credentials w n8n

**Cel:** Skonfigurować połączenia n8n z Nextcloud (WebDAV) i backendem KlimtechRAG.

**Nextcloud WebDAV credentials:**

| Pole | Wartość |
|------|---------|
| Type | HTTP Request (lub WebDAV) |
| URL | `http://192.168.31.70:8443/remote.php/webdav` |
| Authentication | Basic Auth |
| Username | `admin` |
| Password | **Hasło aplikacji** (wygenerowane w Nextcloud: Settings -> Security -> App passwords) |

**KlimtechRAG API credentials:**

| Pole | Wartość |
|------|---------|
| Type | HTTP Request |
| Base URL | `http://192.168.31.70:8000` |
| Authentication | Header Auth (`X-API-Key: sk-local`) lub brak (auth wyłączony) |

### 12.2 Workflow 1: Auto-indeksowanie nowych plików

**Cel:** Co 5 minut sprawdzać czy w Nextcloud RAG_Dane/ pojawiły się nowe pliki. Jeśli tak — zatrzymać LLM (zwolnić VRAM), zaindeksować (tekst przez e5-large, PDF przez ColPali), uruchomić LLM ponownie.

**Plik JSON do importu:** `n8n_workflows/workflow_auto_index.json`

**Schemat:**

```
Schedule (5 min)
    |
    v
Nextcloud List /RAG_Dane/ (WebDAV PROPFIND)
    |
    v
Code: Compare z poprzednim skanem (Static Data)
    |
    v
IF: nowe pliki > 0
    |
    | TAK
    v
HTTP POST /model/stop  (zwolnij VRAM)
    |
    v
Wait 10s (VRAM release)
    |
    v
Loop: dla każdego nowego pliku
    |
    +--> IF rozszerzenie == .pdf
    |       |
    |       v
    |    ColPali ingest (HTTP POST /ingest_path + X-Embedding-Model: vidore/colpali)
    |
    +--> ELSE (.txt, .md, .docx, .py, .json, ...)
            |
            v
         Standard ingest (HTTP POST /ingest_path)  -- e5-large na CPU
    |
    v
HTTP POST /model/start  (Bielik-11B)
    |
    v
Wait 20s + HTTP GET /health (weryfikacja)
```

**Automatyczny routing dokumentów:**
- `.pdf` -> ColPali (Pipeline B) — bo ~95% PDF to skany/dokumenty mieszane
- `.txt`, `.md`, `.py`, `.json`, `.docx` -> e5-large (Pipeline A)
- Pliki audio/video/obrazy -> rejestracja w file_registry, bez indeksowania

**Węzły n8n:**

| # | Węzeł | Typ | Konfiguracja |
|---|-------|-----|-------------|
| 1 | Trigger | Schedule Trigger | Co 5 minut |
| 2 | List files | HTTP Request | GET WebDAV PROPFIND na `/RAG_Dane/` |
| 3 | Compare | Code | Porównaj z poprzednim skanem (Static Data) |
| 4 | IF new | IF | `newFiles.length > 0` |
| 5 | Stop LLM | HTTP Request | POST `/model/stop` |
| 6 | Wait VRAM | Wait | 10 sekund |
| 7 | Loop files | Loop Over Items | Iteracja po nowych plikach |
| 8 | Route | IF | `.pdf` -> ColPali, inne -> standard |
| 9 | Ingest PDF | HTTP Request | POST `/ingest_path` + header `X-Embedding-Model: vidore/colpali-v1.3-hf` |
| 10 | Ingest text | HTTP Request | POST `/ingest_path` (domyślny e5-large) |
| 11 | Start LLM | HTTP Request | POST `/model/start` z modelem Bielik-11B |
| 12 | Health check | HTTP Request | GET `/health` (po 20s wait) |

### 12.3 Workflow 2: Czat webhook

**Cel:** Wystawić webhook HTTP w n8n, który przekazuje pytania do KlimtechRAG i zwraca odpowiedzi. Przydatne do integracji z Mattermost, Slack, lub innymi systemami.

**Plik JSON do importu:** `n8n_workflows/workflow_chat_webhook.json`

**Schemat:**

```
Webhook POST /chat  -->  HTTP POST /v1/chat/completions  -->  Respond to Webhook
```

**Węzły:**

| # | Węzeł | Typ | Konfiguracja |
|---|-------|-----|-------------|
| 1 | Webhook | Webhook | POST `http://192.168.31.70:5678/webhook/chat` |
| 2 | Chat API | HTTP Request | POST `/v1/chat/completions`, body z wiadomością |
| 3 | Response | Respond to Webhook | Zwraca odpowiedź LLM |

### 12.4 Workflow 3: VRAM management — przełączanie modeli

**Cel:** Inteligentne przełączanie modeli w zależności od typu zadania. Centralne sterowanie VRAM.

**Plik JSON do importu:** `n8n_workflows/workflow_vram_manager.json`

**Scenariusze przełączania:**

| Zadanie | Wymagany model | VRAM | Akcja n8n |
|---------|---------------|------|-----------|
| Czat RAG (domyślny) | Bielik-11B | ~14 GB | `/model/start` z Bielik-11B |
| Proste zadania NC | Bielik-4.5B | ~4.8 GB | `/model/stop` -> `/model/start` z Bielik-4.5B |
| Indeksowanie tekstu | e5-large (CPU) | 0 GPU | e5-large działa na CPU — nie wymaga GPU |
| Indeksowanie PDF (dokumenty) | ColPali | ~6-8 GB | `/model/stop` -> ingest ColPali -> `/model/start` LLM |
| VLM opis obrazów z PDF | Qwen2.5-VL-7B | ~4.7 GB | `/model/stop` -> start VLM -> ingest -> restart LLM |

**Schemat workflow:**

```
Webhook /vram-task  (z polem task_type)
    |
    v
Code: Determine task type
    |
    v
Switch on task_type
    |
    +-- "rag_chat"      --> Start Bielik-11B
    +-- "rag_chat_mini" --> Start Bielik-4.5B (proste zadania)
    +-- "index_text"    --> Stop LLM -> Ingest (e5-large CPU) -> Start LLM
    +-- "index_pdf"     --> Stop LLM -> Ingest ColPali (GPU) -> Start LLM
    +-- "vlm_ingest"    --> Stop LLM -> Start VLM -> Ingest -> Stop VLM -> Start LLM
```

### 12.5 Nextcloud Webhooks (opcja na przyszłość)

Aplikacja `webhook_listeners` (NC30+) pozwala na event-driven triggering zamiast pollingu:

```bash
podman exec -u www-data nextcloud php occ app:install webhook_listeners
```

Konfiguracja eventu `NodeCreatedEvent` -> trigger n8n webhook `/vram-task` z typem `index_text` lub `index_pdf`.

---

## SEKCJA 13: Dostosowanie endpointów pod Nextcloud

### 13.1 Co Nextcloud wysyła

Nextcloud `integration_openai` generuje standardowe OpenAI API requests:

**Chat (Free prompt / Assistant):**
```json
{
  "model": "klimtech-bielik",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Treść pytania"}
  ],
  "max_tokens": 4096
}
```

**Summarize / Reformulate (background tasks):**
```json
{
  "model": "klimtech-bielik",
  "messages": [
    {"role": "system", "content": "Summarize the following text..."},
    {"role": "user", "content": "[PEŁNA TREŚĆ DOKUMENTU]"}
  ]
}
```

**Kluczowe cechy requestów z Nextcloud:**
- System message zawsze pierwszy
- Brak pól `use_rag`, `web_search`, `top_k` (Nextcloud ich nie zna — Pydantic defaults się włączą)
- Header `Authorization: Bearer {key}` (nie `X-API-Key`!)
- Background tasks: bez `stream`
- Chat: ostatnie 10 tur historii

### 13.2 Format `/v1/models` — GOTOWY

Obecna implementacja (`backend_app/routes/chat.py:76-93`) jest kompatybilna:

```json
{
  "object": "list",
  "data": [{
    "id": "klimtech-bielik",
    "object": "model",
    "created": 1700000000,
    "owned_by": "klimtechrag"
  }]
}
```

**Opcjonalna zmiana:** Dodać `--alias "klimtech-bielik"` do komendy llama-server w `model_manager.py:158` aby jego własny `/v1/models` też zwracał czystą nazwę.

### 13.3 Format `/v1/chat/completions` — GOTOWY z uwagami

Obecna implementacja (`backend_app/routes/chat.py:231-382`) jest kompatybilna.

**Routing RAG vs Direct:**

| Źródło | `use_rag` | `web_search` | Zachowanie |
|--------|-----------|-------------|------------|
| Nextcloud (domyślnie) | `true` (default) | `false` (default) | RAG retrieval -> Qdrant -> LLM |
| KlimtechRAG UI | Ustawiane przez UI | Ustawiane przez UI | Pełna kontrola |

Każde zapytanie z Nextcloud przechodzi przez RAG automatycznie — to pożądane.

### 13.4 Zmiany wymagane w kodzie

#### 13.4.1 Dodać CORS middleware

**Plik:** `backend_app/main.py`
**Zmiana:** Dodać `CORSMiddleware` (szczegóły w sekcji 11.5)

#### 13.4.2 Dodać `--alias` do llama-server

**Plik:** `backend_app/services/model_manager.py`
**Lokalizacja:** Linia ~158 (tablica `llama_cmd`) oraz funkcja `start_model_with_progress`

**Zmiana:** Dodać `"--alias", "klimtech-bielik"` do tablicy argumentów.

#### 13.4.3 Obsługa `Authorization: Bearer` header

**Plik:** `backend_app/utils/dependencies.py`
**Problem:** Obecna implementacja sprawdza `X-API-Key`, Nextcloud wysyła `Authorization: Bearer {key}`.

**Zmiana:** Dodać fallback czytający `Authorization` header:
```python
def require_api_key(request: Request):
    if not settings.api_key:
        return  # auth wyłączony
    key = request.headers.get("X-API-Key")
    if not key:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:]
    if key != settings.api_key:
        raise HTTPException(401, "Invalid API key")
```

#### 13.4.4 Obsługa długich kontekstów (summarize)

**Problem:** Nextcloud przy "Summarize" wysyła cały dokument. Bielik-11B ma kontekst 8192 tokenów.

**Rozwiązania:**
- Zwiększyć `-c` llama-server (np. 16384 jeśli VRAM pozwala)
- Dodać truncation/chunked summarization w `/v1/chat/completions`

#### 13.4.5 Heurystyka RAG off dla summarize (opcjonalne)

**Problem:** Nextcloud Summarize wysyła dokument w treści wiadomości — RAG retrieval jest zbędny.

**Rozwiązanie (przyszłe):**
- Jeśli system message zawiera "summarize"/"streszczenie" -> `use_rag = false`
- Jeśli user message > 2000 znaków -> prawdopodobnie dokument, `use_rag = false`

---

## SEKCJA BONUS: Whisper — Speech-to-Text (wisienka na torcie)

### B.1 Czym jest Whisper

[OpenAI Whisper](https://github.com/openai/whisper) to uniwersalny model rozpoznawania mowy. Obsługuje transkrypcję wielojęzyczną (w tym polski), tłumaczenie mowy na angielski i identyfikację języka. Licencja MIT — w pełni lokalne użycie.

**Dostępne rozmiary modeli:**

| Rozmiar | Parametry | VRAM | Szybkość wzgl. | Uwagi |
|---------|-----------|------|----------------|-------|
| tiny | 39M | ~1 GB | ~10x | Szybki, niska jakość |
| base | 74M | ~1 GB | ~7x | Dobry kompromis dla prostych zadań |
| small | 244M | ~2 GB | ~4x | Dobra jakość polskiego |
| medium | 769M | ~5 GB | ~2x | Bardzo dobra jakość polskiego |
| large-v3 | 1550M | ~10 GB | 1x | Najlepsza jakość, wolny |
| turbo | 809M | ~6 GB | ~8x | Zoptymalizowany large-v3, szybki |

**Rekomendacja dla KlimtechRAG:** Model `small` lub `medium` — dobra jakość polskiego przy rozsądnym VRAM.
- `small` (~2 GB) — zmieści się obok Bielik-11B (14+2=16 GB, ciasno ale możliwe)
- `medium` (~5 GB) — wymaga przełączenia VRAM (jak inne modele)
- `turbo` (~6 GB) — najlepsza relacja jakość/szybkość, ale nie tłumaczy (tylko transkrypcja)

### B.2 Cel integracji

1. **Nextcloud Speech-to-Text** — Nextcloud Assistant obsługuje zadanie "Speech-to-text". Aktualnie oznaczone jako "NIE obsługiwane". Po integracji Whisper stanie się dostępne.
2. **Transkrypcja plików audio** — pliki z `Audio_RAG/` mogą być automatycznie transkrybowane i indeksowane w Qdrant jako tekst.
3. **Wzbogacenie RAG** — transkrypcje nagrań (spotkania, rozmowy, notatki głosowe) stają się częścią bazy wiedzy.

### B.3 Instalacja Whisper

```bash
# Aktywacja venv projektu
source /media/lobo/BACKUP/KlimtechRAG/venv/bin/activate

# Instalacja Whisper
pip install -U openai-whisper

# Wymagane: ffmpeg (prawdopodobnie już zainstalowany)
sudo apt install ffmpeg
```

**Weryfikacja:**
```bash
python3 -c "import whisper; print(whisper.available_models())"
# Oczekiwany wynik: ['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'turbo']
```

### B.4 Nowy endpoint: `/v1/audio/transcriptions`

**Cel:** Endpoint OpenAI-compatible do transkrypcji audio. Nextcloud `integration_openai` używa tego endpointu dla Speech-to-text task.

**Plik:** `backend_app/routes/whisper_stt.py` (NOWY)

**Schemat API (OpenAI-compatible):**

```
POST /v1/audio/transcriptions
Content-Type: multipart/form-data

Pola:
  file: <plik audio> (mp3, wav, flac, m4a, ogg, webm)
  model: "whisper-1" (ignorowane — używamy lokalny)
  language: "pl" (opcjonalne — auto-detect jeśli brak)
  response_format: "json" | "text" | "verbose_json" (domyślnie "json")

Odpowiedź:
{
  "text": "Transkrybowany tekst..."
}
```

**Schemat kodu:**

```python
import whisper
from fastapi import APIRouter, UploadFile, File, Form
import tempfile, os

router = APIRouter(tags=["whisper"])

# Model ładowany leniwie (lazy loading) — nie zajmuje VRAM do pierwszego użycia
_whisper_model = None

def get_whisper_model(size="small"):
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(size, device="cuda:0")
    return _whisper_model

@router.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form("whisper-1"),
    language: str = Form(None),
    response_format: str = Form("json"),
):
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(file.filename)[1], delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        whisper_model = get_whisper_model()
        result = whisper_model.transcribe(
            tmp_path,
            language=language,
            fp16=True,  # szybsze na GPU
        )
        text = result["text"].strip()
    finally:
        os.unlink(tmp_path)

    if response_format == "text":
        return text
    return {"text": text}
```

### B.5 Integracja z Nextcloud

**Mapowanie zadania w Nextcloud Admin -> Artificial Intelligence:**

| Typ zadania | Provider | Uwagi |
|-------------|----------|-------|
| Speech-to-text | OpenAI and LocalAI integration | NOWE — po dodaniu `/v1/audio/transcriptions` |

Nextcloud wysyła plik audio do `/v1/audio/transcriptions` i otrzymuje transkrypcję. Działa bezpośrednio z Nextcloud Talk (transkrypcja wiadomości głosowych) i z plikami audio w Nextcloud Files.

### B.6 Integracja z pipeline RAG (auto-transkrypcja)

**Cel:** Pliki audio wrzucone do `Audio_RAG/` automatycznie transkrybowane i indeksowane.

**Rozszerzenie watchdog (`watch_nextcloud.py`):**
- Dodać rozszerzenia audio: `.mp3`, `.wav`, `.flac`, `.m4a`, `.ogg`, `.webm`
- Nowy flow: audio -> Whisper transkrypcja -> zapis .txt -> e5-large embedding -> Qdrant

**Rozszerzenie n8n workflow (auto-indeksowanie):**
```
IF rozszerzenie in (.mp3, .wav, .flac, .m4a, .ogg)
    |
    v
HTTP POST /v1/audio/transcriptions (plik audio)
    |
    v
HTTP POST /ingest_path (transkrybowany tekst -> e5-large -> Qdrant)
```

### B.7 Zarządzanie VRAM z Whisper

| Model Whisper | VRAM | Koegzystencja z Bielik-11B (~14 GB) |
|---------------|------|--------------------------------------|
| tiny | ~1 GB | TAK (14+1=15 GB) |
| base | ~1 GB | TAK (14+1=15 GB) |
| small | ~2 GB | CIASNO (14+2=16 GB) — na granicy |
| medium | ~5 GB | NIE — wymaga przełączenia VRAM |
| turbo | ~6 GB | NIE — wymaga przełączenia VRAM |

**Strategia:**
- `small` lub `base` — lazy loading, współdzielenie GPU z Bielik-11B
- `medium`/`turbo` — wymagają `/model/stop` przed transkrypcją (jak ColPali)

**Dodać do n8n VRAM management workflow:**

| Zadanie | Model | VRAM | Akcja |
|---------|-------|------|-------|
| Transkrypcja (mały) | Whisper small | ~2 GB | Lazy load obok LLM |
| Transkrypcja (duży) | Whisper medium | ~5 GB | Stop LLM -> Whisper -> Start LLM |

### B.8 Powiązanie z istniejącym modelem audio

W `modele_LLM/model_audio/` istnieje już `LFM2.5-Audio-1.5B` (~2.2 GB) — model audio od LiquidAI działający przez llama.cpp. Whisper jest alternatywą z dojrzalszym ekosystemem i lepszym wsparciem polskiego. Obie opcje mogą współistnieć:
- **Whisper** — dedykowany STT, OpenAI-compatible API, integracja z Nextcloud
- **LFM2.5-Audio** — ogólny model audio (llama.cpp), może obsługiwać inne zadania audio w przyszłości

---

## Kolejność implementacji

### Faza 1: Backend (zmiany w kodzie)
1. [ ] Dodać CORS middleware do `main.py`
2. [ ] Dodać obsługę `Authorization: Bearer` w `dependencies.py`
3. [ ] Dodać `--alias` do llama-server w `model_manager.py`
4. [ ] Przetestować endpointy curlem

### Faza 2: Nextcloud (konfiguracja kontenera)
5. [ ] Ustawić `allow_local_remote_servers` w config.php
6. [ ] Zainstalować `integration_openai` i `assistant`
7. [ ] Skonfigurować AI Provider w admin panelu
8. [ ] Zmapować typy zadań
9. [ ] Przetestować czat w Nextcloud Assistant

### Faza 3: n8n Workflows
10. [ ] Skonfigurować credentials (Nextcloud WebDAV + KlimtechRAG API)
11. [ ] Utworzyć i zaimportować workflow: Auto-indeksowanie (z routingiem PDF->ColPali, tekst->e5)
12. [ ] Utworzyć i zaimportować workflow: Czat webhook
13. [ ] Utworzyć i zaimportować workflow: VRAM management
14. [ ] Przetestować pełny cykl: upload pliku -> auto-index -> czat

### Faza 4: Whisper Speech-to-Text
15. [ ] Zainstalować openai-whisper + ffmpeg w venv
16. [ ] Utworzyć endpoint `/v1/audio/transcriptions` (whisper_stt.py)
17. [ ] Zarejestrować router w main.py
18. [ ] Przetestować transkrypcję curlem
19. [ ] Zmapować Speech-to-text w Nextcloud Assistant
20. [ ] Rozszerzyć watchdog/n8n o auto-transkrypcję audio

### Faza 5: Opcjonalne ulepszenia
21. [ ] Skrypt `scripts/setup_nextcloud_ai.sh`
22. [ ] Heurystyka RAG off dla summarize
23. [ ] Chunked summarization dla długich dokumentów
24. [ ] Nextcloud webhook_listeners (event-driven zamiast polling)
25. [ ] Auto-start watchdog w `start_klimtech_v3.py`

---

## Pliki do utworzenia/zmodyfikowania

| Plik | Akcja | Sekcja |
|------|-------|--------|
| `backend_app/main.py` | EDYCJA — dodać CORS | 11, 13 |
| `backend_app/utils/dependencies.py` | EDYCJA — Bearer auth | 13 |
| `backend_app/services/model_manager.py` | EDYCJA — --alias flag | 13 |
| `scripts/setup_nextcloud_ai.sh` | NOWY — skrypt setup | 11 |
| `n8n_workflows/workflow_auto_index.json` | NOWY — workflow JSON | 12 |
| `n8n_workflows/workflow_chat_webhook.json` | NOWY — workflow JSON | 12 |
| `n8n_workflows/workflow_vram_manager.json` | NOWY — workflow JSON | 12 |
| `backend_app/routes/whisper_stt.py` | NOWY — endpoint STT | Bonus |

---

## Testy weryfikacyjne

| # | Test | Polecenie | Oczekiwany wynik |
|---|------|-----------|-----------------|
| 1 | Backend health | `curl http://192.168.31.70:8000/health` | `{"status": "ok"}` |
| 2 | Lista modeli | `curl http://192.168.31.70:8000/v1/models` | JSON z `klimtech-bielik` |
| 3 | Chat completion | `curl -X POST .../v1/chat/completions -d '...'` | Odpowiedź LLM |
| 4 | CORS preflight | `curl -X OPTIONS ... -H "Origin: http://...:8443"` | Headers CORS |
| 5 | Bearer auth | `curl -H "Authorization: Bearer sk-local" .../v1/models` | 200 OK |
| 6 | Nextcloud AI | Przeglądarka -> NC Assistant | Odpowiedź od Bielik |
| 7 | n8n auto-index | Upload pliku do NC -> czekaj 5 min | Plik w Qdrant |
| 8 | n8n VRAM switch | Trigger workflow | Model zmieniony |
| 9 | ColPali PDF | Upload PDF skanu -> n8n -> ColPali ingest | Punkt w `klimtech_colpali` |
| 10 | Whisper STT | `curl -F file=@audio.mp3 .../v1/audio/transcriptions` | JSON z transkrypcją |
| 11 | NC Speech-to-text | Nextcloud Talk -> transkrybuj | Tekst z audio |

---

*Plan utworzony: 2026-03-15 — gotowy do implementacji faza po fazie*
*Zaktualizowany: 2026-03-15 — dodano sekcję Whisper STT (wisienka na torcie)*
