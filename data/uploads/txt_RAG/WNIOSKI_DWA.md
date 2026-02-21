## Opis działania programu KlimtechRAG

KlimtechRAG to lokalny system typu **RAG (Retrieval-Augmented Generation)** zbudowany wokół FastAPI, Haystack, Qdrant i lokalnego serwera LLM (`llama.cpp`). Jego celem jest indeksowanie dokumentów (PDF, pliki tekstowe, kod źródłowy, multimedia) oraz odpowiadanie na pytania użytkownika z wykorzystaniem kontekstu z tych dokumentów oraz (opcjonalnie) wyników wyszukiwania w sieci.

### Główne komponenty

- **`backend_app/main.py`**  
  - Aplikacja **FastAPI** wystawiająca 3 kluczowe endpointy:
    - **`POST /ingest`** – przyjmuje pliki (PDF, TXT, MD, itp.), parsuje je (Docling dla PDF), dzieli na fragmenty i zapisuje wektory w Qdrant.
    - **`POST /query`** – przyjmuje pytanie użytkownika, pobiera kontekst z Qdrant, opcjonalnie korzysta z web search (DuckDuckGo), buduje prompt i wywołuje lokalnego LLM-a.
    - **`POST /code_query`** – specjalizowany endpoint do pytań programistycznych (analiza i wyjaśnianie kodu).
  - Wykorzystuje **Haystack pipelines** do przetwarzania dokumentów oraz zapytań (splitting, embedding, retriever, prompt builder, generator).

- **`watch_nextcloud.py`**  
  - Skrypt zbudowany na **watchdog**, który monitoruje katalogi Nextcloud (np. `data/nextcloud/.../RAG_Dane/...`).  
  - Po wykryciu nowych plików (PDF/TXT/MD/kod/audio/wideo/obrazy) automatycznie wywołuje endpoint **`/ingest`**, dzięki czemu użytkownik musi jedynie wrzucić plik do Nextcloud, a reszta dzieje się sama.

- **`git_sync/ingest_repo.py`**  
  - Skrypt do batchowego indeksowania repozytoriów Git (kod źródłowy).  
  - Przechodzi po drzewie katalogów, filtruje po rozszerzeniach (Python, JS, TS, JSON, YAML, Markdown) i rozmiarze pliku (limit ok. 500 KB), a następnie wysyła treść plików do **`/ingest`**.  
  - Ignoruje katalogi typu `node_modules`, `.git`, `venv`, `__pycache__` itd.

- **`start_klimtech.py` (i powiązane skrypty)**  
  - Orkiestruje uruchamianie wszystkich elementów systemu:
    - startuje serwer LLM (`llama-server`) na podstawie wybranego modelu GGUF,
    - uruchamia kontenery **Podman**: Qdrant, Nextcloud, Postgres, n8n (z odpowiednimi wolumenami w `data/`),
    - startuje backend FastAPI (`backend_app/main.py` / `uvicorn`),
    - uruchamia **`watch_nextcloud.py`**.
  - `stop_klimtech.py` odpowiada za bezpieczne zatrzymanie procesów i kontenerów.

- **`zai_wrapper.py`**  
  - Opcjonalny wrapper do zewnętrznego API Z.AI (alternatywne lub dodatkowe źródło odpowiedzi/LLM).

### Przepływ danych (end-to-end)

1. **Indeksowanie dokumentów z Nextcloud**  
   - Użytkownik wrzuca plik do odpowiedniego folderu w Nextcloud.  
   - `watch_nextcloud.py` wykrywa nowe zdarzenie (on_created) i po krótkiej logice filtrującej wywołuje `POST /ingest` z tym plikiem.  
   - `/ingest`:
     - sprawdza rozszerzenie pliku (na podstawie listy dozwolonych typów),
     - dla PDF używa **Docling** do konwersji na Markdown/tekst,
     - dzieli treść na fragmenty (chunking, np. ~200 słów),
     - tworzy embedddingi (domyślnie **multilingual-e5-large**),
     - zapisuje wektory i metadane w **Qdrant**.

2. **Indeksowanie kodu z repozytorium**  
   - Administrator/deweloper uruchamia `git_sync/ingest_repo.py` wskazując katalog repo.  
   - Skrypt czyści ścieżki z katalogów technicznych, filtruje pliki po rozszerzeniach oraz rozmiarze, a następnie wysyła ich zawartość do **`/ingest`**.  
   - Dzięki temu pytania do endpointu **`/code_query`** lub zwykłego **`/query`** mogą korzystać z wiedzy zarówno z dokumentów, jak i z kodu.

3. **Obsługa zapytań użytkownika**  
   - Klient (np. curl, UI, integracja z innym systemem) wysyła `POST /query` z tekstem pytania.  
   - Pipeline:
     - embedduje pytanie przy użyciu tego samego modelu co dokumenty,
     - odpytuje **Qdrant** (retriever) o najbardziej podobne fragmenty (kontekst),
     - opcjonalnie zbiera dodatkowy kontekst z wyszukiwarki DuckDuckGo (web search),
     - buduje prompt (instrukcje + kontekst + pytanie) i wysyła go do lokalnego **llama.cpp** (serwer LLM),
     - zwraca odpowiedź sformatowaną w JSON.  
   - `POST /code_query` działa podobnie, ale stosuje bardziej techniczny prompt i może np. zwracać bardziej szczegółowe wyjaśnienia kodu.

4. **Infrastruktura i serwer LLM**  
   - Qdrant, Nextcloud, Postgres, n8n działają w kontenerach Podman spiętych w sieci `klimtech-net`, z danymi w `data/`.  
   - `llama.cpp` jest budowane lokalnie (z obsługą HIP/ROCm lub Vulkan), a serwer **`llama-server`** nasłuchuje na lokalnym porcie (8080/8081/8082, zależnie od konfiguracji).  
   - Backend FastAPI odwołuje się do LLM po URL skonfigurowanym w kodzie/`.env` (OpenAI‑kompatybilny endpoint).

---

## Co bym zmienił (refaktoryzacja i poprawki)

Poniższe punkty rozszerzają wnioski z `WNIOSKI.md` i grupują je w konkretne obszary prac.

### 1. Porządek w punktach wejścia i procesach

- **Naprawić/usunąć martwy kod**  
  - Przenieść rejestrację signal handlerów z końca `main.py` (po `uvicorn.run(...)`) na górę modułu lub całkowicie do osobnego skryptu startowego. Obecnie kod w dolnych liniach `main.py` nigdy się nie wykona.
  - Zweryfikować, czy w ogóle potrzebujemy uruchamiania serwera z `if __name__ == "__main__":` – w środowisku produkcyjnym sensowniejsze jest uruchamianie przez `uvicorn`/`gunicorn` z zewnątrz.

- **Ujednolicić skrypty start/stop**  
  - `start_klimtech_dwa.py` albo doprowadzić do pełnej sprawności (wzorując się na `start_klimtech.py`), albo usunąć, jeśli to tylko niedokończony eksperyment.
  - Wprowadzić jedną „oficjalną” ścieżkę uruchamiania:
    - np. `python start_klimtech.py` w trybie dev,
    - plik unit `.service` dla systemd w trybie prod (bezpośrednio uruchamiający `uvicorn backend_app.main:app` i oddzielny unit dla `watch_nextcloud.py`).

### 2. Konfiguracja i stałe w jednym miejscu

- **Konsolidacja konfiguracji**  
  - Obecnie stałe takie jak `ALLOWED_EXTENSIONS` są zduplikowane i różnią się w `main.py`, `watch_nextcloud.py` i `ingest_repo.py`.  
  - Propozycja:
    - dodać moduł `backend_app/config.py` (lub `config/` z kilkoma plikami),
    - umieścić tam:
      - `ALLOWED_EXTENSIONS_DOCS`, `ALLOWED_EXTENSIONS_CODE` itp.,
      - limity rozmiarów plików,
      - nazwy kolekcji Qdrant, ścieżki katalogów, nazwy modeli embeddingowych,
      - domyślne wartości portów/URL (Qdrant, LLM, itp.).
  - Wszystkie wartości, które mogą się różnić między dev/test/prod, powinny być pobierane z **`.env`** za pomocą `pydantic-settings` lub `python-dotenv`.

- **Usunięcie „magic strings” z kodu**  
  - `OPENAI_BASE_URL`, `LLM_MODEL_NAME`, rozmiary chunków, liczbę top_k z retrievera itd. trzymać w jednym, jasno opisanym miejscu zamiast w wielu rozproszonych miejscach w kodzie.

### 3. Walidacja i bezpieczeństwo

- **Limit rozmiaru pliku w `/ingest`**  
  - Dodać walidację rozmiaru (np. `MAX_FILE_SIZE_BYTES`) i zwracać czytelny błąd HTTP 413 (Payload Too Large), jeśli limit jest przekroczony.  
  - Dzięki temu unikniemy sytuacji, w której duży PDF zapcha RAM lub zawiesi pipeline.

- **Spójna obsługa błędów**  
  - Ujednolicić użycie `HTTPException` we wszystkich endpointach – tam, gdzie teraz zwracane jest „gołe” `{"error": "..."}`, powinna być odpowiednia klasa błędu (`HTTPException(status_code=400/500, detail=...)`).  
  - Rozważyć dodanie globalnego handlera błędów FastAPI (`app.exception_handler`) z ustrukturyzowaną odpowiedzią.

- **Podstawowe uwierzytelnianie i rate limiting**  
  - Dodać prosty mechanizm API key / JWT (np. w nagłówku `Authorization`) oraz limit zapytań per IP/api key:
    - w dev – prosty dekorator z licznikiem w pamięci,
    - w prod – integracja z Redis / n8n / API Gateway (w przyszłości).

### 4. Obserwowalność: health check, logi, metryki

- **Endpoint `/health`**  
  - Prosty endpoint zwracający:
    - status Qdrant (np. testowa prosta operacja, jak `get_collections` lub `count` na głównej kolekcji),
    - status połączenia z LLM (krótkie zapytanie testowe „ping” lub samo sprawdzenie dostępności endpointu),
    - wersję aplikacji / środowiska.  
  - Może zwracać `{"status": "ok", "qdrant": "ok", "llm": "ok"}` oraz kod HTTP 200 lub 503 w razie problemu.

- **Strukturalne logowanie**  
  - Zastąpić większość `print()` przez moduł `logging`:
    - konfiguracja w jednym miejscu (`logging.config.dictConfig`),
    - logi w formacie JSON (opcjonalnie) z polami: timestamp, level, endpoint, request_id, itp.  
  - `watch_nextcloud.py` powinien logować kluczowe zdarzenia (start, błąd w `on_created`, czas indeksowania, itp.) na poziomach INFO/WARNING/ERROR.

- **Podstawowe metryki**  
  - Dodać prosty endpoint `/metrics` lub zwrócić część metryk z `/health`:
    - liczba dokumentów w kolekcji,
    - liczba zapytań (od startu lub z ostatniego okna czasowego),
    - średni czas przetwarzania `/query` (nawet liczony „ręcznie” w kodzie).

### 5. Stabilność watchera

- **Debounce / sprawdzanie kompletności pliku**  
  - W `watch_nextcloud.py` dodać:
    - krótki sleep + porównanie rozmiaru pliku w odstępie czasu,
    - lub logikę „ponów próbę, jeśli plik jest w trakcie zapisu”.  
  - Zmniejszy to ryzyko indeksowania niekompletnego pliku (co może kończyć się błędem Doclinga czy pustymi chunkami).

---

## Funkcje, które warto dodać

Poniżej rozwinięcie i uporządkowanie proponowanych nowych funkcji (częściowo pokrywa się z listą z `WNIOSKI.md`).

### Priorytet wysoki

- **Endpoint `/health`**  
  - Jak wyżej – prosty status całego stosu (API, Qdrant, LLM).  
  - Ułatwia integrację z monitorowaniem (np. Icinga, Prometheus, n8n).

- **Walidacja rozmiaru i typu pliku w `/ingest`**  
  - Limit rozmiaru (np. 10–50 MB, konfigurowalny) oraz jasny komunikat błędu przy przekroczeniu.  
  - Blokowanie nieobsługiwanych typów już na poziomie FastAPI (zanim Docling dostanie plik).

- **Strukturalne logowanie i korelacja zapytań**  
  - Dodanie `request_id` (np. UUID w nagłówku lub generowany w middleware) i logowanie go w całym pipeline, żeby łatwo śledzić jedno żądanie od `/query` do llama.cpp i z powrotem.

- **Podstawowy rate limiting**  
  - Chociażby prosty mechanizm w pamięci, który ogranicza liczbę zapytań z jednego IP w krótkim oknie czasowym – wystarczające na początek.

### Priorytet średni

- **Uwierzytelnianie (API key / JWT)**  
  - Dodanie zależności od prostego komponentu bezpieczeństwa FastAPI (`Depends`) pozwoli w przyszłości łatwo przełączyć się na zewnętrzny provider (np. Keycloak, Auth0).

- **Endpoint administracyjny do zarządzania kolekcją**  
  - `DELETE /documents` z parametrami:
    - po ID dokumentu,
    - po tagach (np. `source=nextcloud`, `source=git_repo`),
    - lub po nazwie repo/ścieżce.  
  - Umożliwi to „sprzątanie” bazy bez ręcznego grzebania w Qdrant.

- **Lepsze raportowanie web search**  
  - Oddzielenie:
    - „brak wyników” (0 trafień) od
    - „błąd sieci / błąd API”.  
  - Użytkownik powinien wiedzieć, czy brak web contextu wynika z braku treści, czy z błędu.

### Priorytet niski

- **WebSocket / SSE dla statusu indeksowania**  
  - Możliwość podglądu w czasie rzeczywistym, jakie pliki są właśnie przetwarzane, ile chunków zostało wygenerowanych, czy pojawiły się błędy.

- **Asynchroniczne przetwarzanie dokumentów**  
  - Wprowadzenie kolejki zadań (np. RQ/Celery, a w przyszłości może n8n/worker) do ciężkich operacji:
    - duże PDF-y,
    - masowe ingest repozytorium.  
  - `/ingest` mógłby wtedy szybko zwracać `202 Accepted` z `task_id`, a status zadania byłby sprawdzany osobnym endpointem.

- **Caching odpowiedzi**  
  - Prosty cache (np. w Redisie) dla najczęściej zadawanych pytań lub identycznych promptów:
    - mniejsza liczba wywołań do LLM,
    - szybsza odpowiedź przy powtarzających się pytaniach.

---

## Podsumowanie

KlimtechRAG już teraz ma **dobrą, modularną architekturę**: wyraźny podział na API, watcher Nextcloud, batch ingest repozytoriów i wyodrębniony serwer LLM. Największe zyski przyniosą teraz **porządki techniczne** (usunięcie martwego kodu, konsolidacja konfiguracji, spójna obsługa błędów i logowanie) oraz dodanie kilku **kluczowych endpointów pomocniczych** (`/health`, ew. `/metrics`, administacyjne operacje na dokumentach). Dopiero na tym stabilnym fundamencie warto rozwijać funkcje „premium” jak WebSockety, async processing czy cache, bo całość będzie wtedy łatwiejsza w utrzymaniu i skalowaniu.

