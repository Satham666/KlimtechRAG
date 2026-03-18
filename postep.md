# Postep wdrozenia KlimtechRAG — Naprawa bledow i optymalizacja

**Rozpoczecie:** 2026-03-15
**Ostatnia aktualizacja:** 2026-03-18 (v7.3: New UI + Lazy Loading + GPU Dashboard + SEKCJA 16: VLM Prompts)

---

## AKTUALNY STAN — sesja naprawcza (12 punktow) + HTTPS (13)

### PLAN NAPRAW — WSZYSTKIE WYKONANE

| # | Priorytet | Opis | Status | Plik |
|---|-----------|------|--------|------|
| 1 | KRYTYCZNY | Dodano `_hash_bytes()` + import `find_duplicate_by_hash` | ✅ DONE | `backend_app/routes/ingest.py` |
| 2 | KRYTYCZNY | Usunieto zduplikowany blok dedup w `/upload` | ✅ DONE | `backend_app/routes/ingest.py` |
| 3 | POWAZNY | `stop_klimtech.py` — porty 3000->8081/5678 | ✅ DONE | `stop_klimtech.py` |
| 4 | POWAZNY | `main.py` — lifespan zamiast deprecated on_event | ✅ DONE | `backend_app/main.py` |
| 5 | SREDNI | Utworzono plik `.env` z domyslnymi wartosciami | ✅ DONE | `.env` |
| 6 | SREDNI | `model_switch.py` — relative import zamiast kruchego fallbacku | ✅ DONE | `backend_app/routes/model_switch.py` |
| 7 | SREDNI | `main.py` — ujednolicony import routerow (model_switch_router) | ✅ DONE | `backend_app/main.py` |
| 8 | NISKI | `rag.py` — fallback model name `klimtech-bielik` | ✅ DONE | `backend_app/services/rag.py` |
| 9 | NISKI | Endpoint `/v1/audio/transcriptions` (Whisper STT) | ✅ DONE | `backend_app/routes/whisper_stt.py` |
| 10 | NISKI | Nextcloud AI Assistant nie odpowiada (417) | ⏳ POZNIEJ | — |
| 11 | SREDNI | Usunieto referencje Open WebUI (nie uzywane) | ✅ DONE | `config.py`, `stop_klimtech.py` |
| 12 | SREDNI | Dopisano linki n8n + Nextcloud w komunikacie startowym | ✅ DONE | `start_klimtech_v3.py` |

**Wynik: 10/12 punktow wykonanych. Pkt 9 i 10 odlozone na pozniej (nie krytyczne).**

---

## SEKCJA 13: HTTPS — nginx reverse proxy (ZAKONCZONE)

### Finalne adresy HTTPS

| Usluga | HTTP | HTTPS (nginx) | Status |
|--------|------|---------------|--------|
| Backend + UI | :8000 | :8443 | ✅ OK (200) |
| Nextcloud | :8081 | :8444 | ✅ OK (302 redirect) |
| n8n | :5678 | :5679 | ✅ OK (200) |
| Qdrant | :6333 | :6334 | ✅ OK (200) |

### Testy HTTPS (2026-03-16)

```
curl -k https://192.168.31.70:8443/health   -> 200 OK
curl -k https://192.168.31.70:8444/         -> 302 redirect to login
curl -k https://192.168.31.70:5679/         -> 200 OK
curl -k https://192.168.31.70:6334/         -> 200 OK
```

### Naprawione problemy

1. sudo pkill timeout -> dodano sprawdzenie czy nginx juz dziala (start_nginx())
2. Nextcloud 404 -> Nextcloud redirectowal na http://IP/login (port 80) zamiast https://IP:8444/login
   - Naprawiono: dodano overwriteprotocol=https, overwritehost=192.168.31.70:8444, trusted_proxies
   - Komenda: `podman exec nextcloud php occ config:system:set overwriteprotocol --value="https"`
3. Firefox HTTP cache -> wyczyszczono cache przegladarki
4. KRYTYCZNY: sudo w signal_handler wycieka haslo -> usunieto sudo z CTRL+C handlera
   - nginx zostaje uruchomiony po CTRL+C (zatrzymaj recznie: sudo nginx -s stop)

### Uruchomienie

```bash
# Start
cd /media/lobo/BACKUP/KlimtechRAG
source venv/bin/activate
python3 start_klimtech_v3.py

# Stop
python3 stop_klimtech.py
```

### Wykonane kroki

| # | Opis | Status |
|---|------|--------|
| 13a | Zainstalowano nginx | ✅ DONE |
| 13b | Wygenerowano certyfikat SSL self-signed | ✅ DONE |
| 13c-f | Utworzono konfiguracje nginx | ✅ DONE |
| 13g-1 | start_klimtech_v3.py — funkcja start_nginx() + komunikat HTTPS | ✅ DONE |
| 13g-2 | main.py CORS — dodano originy HTTPS | ✅ DONE |
| 13g-3 | stop_klimtech.py — kill_nginx() + porty HTTPS | ✅ DONE |
| 13g-4 | Testy HTTPS — nginx dziala, backend 502 (wymaga uruchomienia start_klimtech_v3.py) | ✅ DONE |

### Szczegoly

**Plik nginx:** `/etc/nginx/sites-available/klimtech`
**Certyfikat:** `/media/lobo/BACKUP/KlimtechRAG/data/ssl/klimtech.crt`

**Testy HTTPS (przed uruchomieniem backend):**
- Backend HTTPS :8443 -> 502 (brak backend :8000)
- Nextcloud HTTPS :8444 -> 302 OK
- n8n HTTPS :5679 -> 200 OK
- Qdrant HTTPS :6334 -> 200 OK

**Po uruchomieniu `start_klimtech_v3.py`:**
- Wszystkie HTTPS -> 200 OK
3. Nginx nie moze wystartowac przez bledy bind() - W TRYBIE ROZWIAZYWANIA

### Do zrobienia (po uruchomieniu nginx)

1. Uruchomic nginx: `sudo nginx`
2. Zaktualizowac CORS w `backend_app/main.py` - dodac https://192.168.31.70:8443
3. Zaktualizowac trusted_domains w Nextcloud (jesli potrzebne)
4. Przetestowac HTTPS na kazdym porcie: `curl -k https://192.168.31.70:8443/health`
5. Zaktualizowac komunikat startowy w `start_klimtech_v3.py` o HTTPS

---

## SEKCJA 14: Whisper STT (ZAKONCZONE)

### Problem z venv
- Stary venv `klimtech_venv` znajdowal sie w `/home/lobo/klimtech_venv/`
- Przeniesiony do `/media/lobo/BACKUP/KlimtechRAG/venv/` przez rsync
- Naprawiono sciezki w plikach binarnych venv (sed -i ...)

### Instalacja openai-whisper
```bash
/media/lobo/BACKUP/KlimtechRAG/venv/bin/pip install openai-whisper
```

### Nowy endpoint
- **Plik:** `backend_app/routes/whisper_stt.py` — NOWY
- **Endpoint:** `POST /v1/audio/transcriptions`
- **Rejestracja:** dodano `whisper_router` w `main.py`

### Dostepne modele whisper
- tiny, base, small, medium, large-v3, turbo
- Domyslny: `small` (~2 GB VRAM)
- Urzadzenie: CUDA GPU

### Testowanie
```bash
curl -X POST http://192.168.31.70:8000/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=whisper-1"
```

### Status
| # | Opis | Status |
|---|------|--------|
| 14a | Przeniesienie venv | ✅ DONE |
| 14b | Instalacja openai-whisper | ✅ DONE |
| 14c | Utworzenie endpointu whisper_stt.py | ✅ DONE |
| 14d | Rejestracja routera w main.py | ✅ DONE |
| 14e | Aktualizacja dokumentacji | ✅ DONE |

---

## SEKCJA 15: Nowy UI Backend (code.html) + GPU Status — W TRAKCIE

### Cel
Zamiana index.html na nowy layout (code.html) z podlaczeniem wszystkich funkcji JS.
Dodanie endpointu `/gpu/status` do monitorowania GPU w czasie rzeczywistym.

### Zmiany w plikach
| Plik | Zmiana |
|------|--------|
| `backend_app/routes/gpu_status.py` | NOWY — endpoint GET /gpu/status (rocm-smi) |
| `backend_app/main.py` | Import + rejestracja gpu_router |
| `backend_app/static/index.html` | ZASTAPIONY zawartoscia code.html + IDs + JS |
| `start_klimtech_v3.py` | Usuniecie auto-start embeddingu |

### Nowy UI — funkcje
- Wszystkie przyciski podlaczone do API backendu
- Model Selection: lista LLM/VLM, Uruchom/Zatrzymaj
- Upload: drag & drop z progress barem
- Indeksowanie RAG: wybor modelu embeddingu, przycisk indeksuj
- Czat: pelna funkcjonalnosc (sesje, historia, export/import)
- Web Search: wyszukiwanie + podglad + podsumowanie
- Panel informacyjny: GPU dashboard (temp, VRAM, use) co 2 sekundy
- Header: real-time health check serwisow (qdrant, nextcloud, postgres, n8n)
- Terminal POSTEP: logi z postepem operacji
- Menu operacji: przelaczanie LLM/VLM, status systemu, zatrzymaj model

### Status
| # | Opis | Status |
|---|------|--------|
| 15a | Endpoint /gpu/status | ✅ DONE |
| 15b | Rejestracja gpu_router w main.py | ✅ DONE |
| 15c | Zamiana index.html (code.html + IDs + JS) | ✅ DONE |
| 15d | Usuniecie auto-start embeddingu | ✅ DONE |
| 15e | Test UI | ✅ DONE (backend + GPU endpoint dziala) |
| 15f | Fix: _detect_base() zwracal /home/lobo zamiast /media/lobo/BACKUP | ✅ DONE |
| 15g | Fix: Lazy loading embeddings (VRAM 4.5GB -> 14MB na starcie) | ✅ DONE |
| 15h | Fix: llm.py import rag_pipeline -> get_rag_pipeline | ✅ DONE |
| 15i | Fix: chat.py, ingest.py — lazy imports embedder/pipeline | ✅ DONE |
| 15j | Fix: use_rag domyslnie False (byl True) - czat nie dlawi sie RAG | ✅ DONE |
| 15k | UI: use_rag:true gdy wlaczony tryb Web/RAG w UI | ✅ DONE |

### Dodatkowe naprawy (15f-15k)
- **model_manager.py**: `_detect_base()` preferowal `/home/lobo/KlimtechRAG` (stary repo bez GGUF) zamiast `/media/lobo/BACKUP/KlimtechRAG` — naprawiony priorytet
- **embeddings.py**: Calkowity refactor na lazy loading — `get_text_embedder()` / `get_doc_embedder()` zamiast module-level warm_up()
- **qdrant.py**: `get_embedding_dimension()` uzywa cache znanych wymiarow zamiast ladowac SentenceTransformer na GPU
- **rag.py**: Refactor na `get_indexing_pipeline()` / `get_rag_pipeline()` — pipeline tworzony dopiero przy uzyciu
- **llm.py**: Zwraca standalone OpenAIGenerator zamiast ladowac caly RAG pipeline
- **chat.py**, **ingest.py**, **services/__init__.py**: Wszystkie importy zaktualizowane do lazy API
- **schemas.py**: `use_rag: False` domyslnie — czat idzie prosto do llama-server
- **index.html**: Gdy wlaczony tryb Web (globe), wysyla `use_rag: true`
- **Wynik**: VRAM na starcie spadl z 4.5 GB do 14 MB!

---

## Szczegolowy log zmian — sesja naprawcza

### Pkt 1+2: ingest.py — _hash_bytes + dedup (KRYTYCZNY)
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - Dodano `import hashlib` na poczatku pliku
  - Dodano funkcje `_hash_bytes(data: bytes) -> str` (SHA-256)
  - Dodano import `find_duplicate_by_hash` i `get_connection` z `file_registry`
  - Usunieto ZDUPLIKOWANY blok dedup (linie 338-347 — identyczna kopia 328-337)
  - Usunieto ZDUPLIKOWANY blok UPDATE hash (linie 358-364 — identyczna kopia 351-357)
  - Uzyto `_get_registry_connection` zamiast lokalnego re-importu

### Pkt 3: stop_klimtech.py — porty
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - `check_ports()`: zamieniono `"3000": "Open WebUI"` na `"8081": "Nextcloud"` + `"5678": "n8n"`
  - `kill_all_remaining()`: usunieto wzorce `qdrant`, `nextcloud`, `n8n` (te procesy to kontenery Podman, nie natywne)

### Pkt 4+7: main.py — lifespan + import
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - Zamieniono `@app.on_event("startup")` na `@asynccontextmanager async def lifespan(app)`
  - Dodano shutdown log w lifespan
  - Usunieto duplikat importu `from .routes import model_switch` (linia 4)
  - Ujednolicono na `model_switch_router` z `routes/__init__.py` (jak inne routery)
  - `app = FastAPI(lifespan=lifespan)` zamiast `app = FastAPI()`

### Pkt 5: Plik .env
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - Utworzono `.env` z domyslnymi wartosciami (KLIMTECH_BASE_PATH, LLM, embedding, Qdrant, porty)
  - Dodano `.env` do `.gitignore` (bezpieczenstwo)
  - Dodano `modele_LLM/` i `.ruff_cache/` do `.gitignore`

### Pkt 6: model_switch.py — importy
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - Usunieto kruchy blok `try: from services... except: importlib.util.spec_from_file_location`
  - Zamieniono na czysty relative import: `from ..services.model_manager import ...`
  - Wszystkie potrzebne funkcje importowane raz na gorze pliku
  - Usunieto lokalne try/except importy w endpointach `/start`, `/progress-log`, `/stop`

### Pkt 8: rag.py — model name
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - `OpenAIGenerator(model=settings.llm_model_name or "klimtech-bielik")` — fallback dla pustego stringa

### Pkt 11: Usuniecie Open WebUI
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - Usunieto z `config.py`: `owui_port`, `owui_data_dir`, `owui_container` (3 zmienne)
  - Usunieto z `stop_klimtech.py`: wzorce kill dla qdrant/nextcloud/n8n natywnych (to kontenery Podman)
  - Projekt uzywa: Nextcloud (czat + pliki), Backend UI (:8000), n8n (automatyzacja)

### Pkt 12: Komunikat startowy
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - Dopisano do komunikatu startowego w `start_klimtech_v3.py`:
    - `Nextcloud: http://<IP>:8081`
    - `n8n: http://<IP>:5678`

---

## Poprzednia sesja — zrealizowane cele (2026-03-15/16)

1. ✅ Dodano sekcje Whisper STT do NextcloudAI.md
2. ✅ Zaimplementowano integracje CORS + Bearer auth
3. ✅ Utworzono 3 workflow JSON dla n8n
4. ✅ Skonfigurowano Nextcloud (apps, trusted_domains, AI provider)
5. ✅ Naprawiono start LLM z obliczaniem parametrow
6. ✅ Dodano endpoint `/models` (bez /v1/) dla Nextcloud
7. ✅ Naprawiono import settings w model_manager.py
8. ✅ Zaktualizowano start_klimtech_v3.py (weryfikacja /health)
9. ✅ Zaktualizowano stop_klimtech.py (kontenery, porty)
10. ✅ Zaktualizowano PODSUMOWANIE.md (sekcja source venv + uruchamianie .py)

---

## Zmiany w plikach — pelna lista

| Plik | Zmiany (sesja naprawcza) |
|------|--------------------------|
| `backend_app/routes/ingest.py` | Pkt 1+2: _hash_bytes, dedup fix, import find_duplicate_by_hash |
| `backend_app/main.py` | Pkt 4+7: lifespan, ujednolicony import routerow |
| `backend_app/routes/model_switch.py` | Pkt 6: relative import, czyszczenie try/except |
| `backend_app/services/rag.py` | Pkt 8: fallback model name |
| `backend_app/config.py` | Pkt 11: usunieto owui_* |
| `stop_klimtech.py` | Pkt 3+11: porty 8081/5678, usunieto kill natywnych kontenerow |
| `start_klimtech_v3.py` | Pkt 12: linki Nextcloud + n8n |
| `.env` | Pkt 5: NOWY — domyslna konfiguracja |
| `.gitignore` | Pkt 5: dodano .env, modele_LLM/, .ruff_cache/ |
| `PODSUMOWANIE.md` | Sekcja 14 rozszerzona o source venv + uruchamianie .py |
| `postep.md` | Pelny log napraw |

---

## Porty systemowe (OFICJALNE)

| Usluga | Port | Uwagi |
|--------|------|-------|
| Nextcloud | **8081** | Czat AI + pliki |
| Backend FastAPI | 8000 | Glowny backend + UI |
| llama-server | 8082 | LLM/VLM (llama.cpp, AMD Instinct) |
| n8n | 5678 | Automatyzacja workflow |
| Qdrant | 6333 | Baza wektorowa |

---

## SEKCJA 16: Refaktoryzacja VLM Prompts — Z AKCEPTACJI

**Status:** DO WYKONANIA  
**Data akceptacji:** 2026-03-18  
**Dotyczy:** `backend_app/ingest/image_handler.py`

### Plan (z akceptacja.md)

| # | Co | Gdzie | Efekt |
|---|-----|-------|-------|
| 1 | Prompty → plik konfiguracyjny | Nowy `backend_app/prompts/vlm_prompts.py` | Zmiana promptu bez zmiany kodu |
| 2 | Rozbudowa DEFAULT prompt | `vlm_prompts.py` → `DEFAULT` | Lepsze opisy, format, ekstrakcja tekstu |
| 3 | 8 promptów per typ obrazu | `vlm_prompts.py` → 8 wariantów | Auto-dobór promptu do typu obrazu |
| 4 | Dynamiczne parametry llama-cli | `image_handler.py` + `config.py` | Spójność z resztą systemu |

### Szczegóły

**Punkt 1: Wyciągnięcie promptów z kodu do pliku konfiguracyjnego**
- Nowy: `backend_app/prompts/__init__.py`
- Nowy: `backend_app/prompts/vlm_prompts.py`
- Zmiana: `backend_app/ingest/image_handler.py` — import promptów z nowego modułu

**Punkt 2: Rozbudowa promptu domyślnego**
- Obecny prompt obsługuje tylko 3 typy (medyczne, diagramy, wykresy)
- Brak instrukcji o formacie wyjścia, brak wyciągania tekstu/numerów, brak kontekstu dokumentu
- NOWY prompt `DEFAULT` — uniwersalny, szczegółowy, z instrukcjami formatu wyjścia

**Punkt 3: Zestaw promptów per typ obrazu**
- 8 wariantów w `vlm_prompts.py`:

```
vlm_prompts.py:
├── DEFAULT          — uniwersalny, szczegółowy, z formatem wyjścia
├── DIAGRAM          — dla schematów, flowchartów, algorytmów
├── CHART            — dla wykresów (dane, osie, trendy, wartości)
├── TABLE            — dla tabel (zachowaj strukturę, kolumny, wiersze)
├── PHOTO            — dla zdjęć (co widać, kontekst, detale)
├── SCREENSHOT       — dla screenów UI (elementy interfejsu, tekst)
├── TECHNICAL        — dla schematów technicznych (wymiary, części)
└── MEDICAL          — dla obrazów medycznych (anatomia, procedury)
```

Każdy prompt zawiera:
- Jasną instrukcję CO opisać
- Format wyjścia (structured, max ~200 słów)
- Instrukcję wyciągania tekstu/numerów z obrazu
- Język odpowiedzi (polski)

Dobór promptu automatyczny na podstawie `image_type` z `ExtractedImage`.

**Punkt 4: Dynamiczne parametry llama-cli**

Problem: W `image_handler.py` linie 128-145 mają hardcoded parametry:
```python
cmd = [
    LLAMA_CLI_BIN,
    "-m", VLM_MODEL,
    "--image", image_path,
    "-p", prompt,
    "-n", "512",        # ← hardcoded
    "--temp", "0.1",    # ← hardcoded
    "-ngl", "99",       # ← hardcoded
    "-c", "4096",       # ← hardcoded
    "--no-display",
]
```

Niespójne z `start_klimtech_v3.py`, gdzie parametry są obliczane dynamicznie przez `model_parametr.calculate_params()`.

Rozwiązanie:
1. Wywołać `model_parametr.calculate_params(VLM_MODEL)` przy starcie VLM
2. Parametry specyficzne dla VLM (`-n`, `--temp`) przenieść do konfiguracji:
   - `config.py` → nowe pola: `vlm_max_tokens`, `vlm_temperature`, `vlm_context`
   - Lub `vlm_prompts.py` → sekcja `VLM_PARAMS`
3. Zachować sensowne domyślne wartości jako fallback

### Status

| # | Opis | Status |
|---|------|--------|
| 16a | Utworzyć katalog `backend_app/prompts/` | ⏳ DO ZROBIENIA |
| 16b | Utworzyć `prompts/__init__.py` | ⏳ DO ZROBIENIA |
| 16c | Utworzyć `prompts/vlm_prompts.py` z 8 wariantami | ⏳ DO ZROBIENIA |
| 16d | Refaktoryzować `image_handler.py` — import promptów | ⏳ DO ZROBIENIA |
| 16e | Refaktoryzować `image_handler.py` — dynamiczne params | ⏳ DO ZROBIENIA |

### Pliki do zmiany

- `backend_app/ingest/image_handler.py` — refactor (import promptów, dynamiczne params)
- Nowy: `backend_app/prompts/__init__.py`
- Nowy: `backend_app/prompts/vlm_prompts.py`
- `backend_app/config.py` — dodanie VLM params (opcjonalne)

### Pliki BEZ zmian

- `start_klimtech_v3.py`
- `model_manager.py`
- `routes/chat.py`
- `routes/ingest.py`
- `static/index.html` (już zamieniony na code.html)

---

## Pozostale do zrobienia (POZNIEJ)

| # | Opis | Priorytet |
|---|------|-----------|
| 9 | Endpoint `/v1/audio/transcriptions` (Whisper STT) | NISKI — Faza 4 |
| 10 | Diagnostyka Nextcloud AI Assistant (417) | NISKI — wymaga testow na serwerze |

---

## Znane problemy

### 1. Nextcloud AI Assistant nie odpowiada
- **Status:** ❌ NIEROZWIAZANY
- **Objawy:** Ciagle zapytania POST /check_generation z kodem 417
- **Diagnoza:** Backend dziala i odpowiada na curl. API key ustawiony. URL poprawny.
- **Mozliwe przyczyny:** sesja przegladarki, CORS, provider nie ustawiony

### 2. VRAM — Bielik-11B
- **Status:** ⚠️ OBEJSCIE
- **Problem:** ~4.7GB VRAM zajete, Bielik-11B (~14GB) nie miesci sie
- **Rozwiazanie:** Uzywamy Bielik-4.5B (~5GB VRAM)

---

## Dane dostepowe

### HTTP (oryginalne porty)
- **URL Backend:** http://192.168.31.70:8000
- **URL Nextcloud:** http://192.168.31.70:8081
- **URL n8n:** http://192.168.31.70:5678
- **URL Qdrant:** http://192.168.31.70:6333
- **Login:** admin
- **Haslo:** admin123

### HTTPS (nginx reverse proxy - do uruchomienia)
- **URL Backend:** https://192.168.31.70:8443
- **URL Nextcloud:** https://192.168.31.70:8444
- **URL n8n:** https://192.168.31.70:5679
- **URL Qdrant:** https://192.168.31.70:6334

**Uwaga:** Certyfikat self-signed, wymaga akceptacji w przegladarce lub `curl -k`.

---

## Wazne zasady

- **Przed uruchomieniem JAKIEGOKOLWIEK pliku .py:**
  ```bash
  cd /media/lobo/BACKUP/KlimtechRAG
  source venv/bin/activate
  ```
- **llama.cpp** — skompilowany pod AMD Instinct 16GB, NIE instalowac z pip
- **Brakujace biblioteki** — instalowac na biezaco: `pip install <nazwa>`
