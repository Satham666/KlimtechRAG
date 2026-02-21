# Plan Wdrożenia KlimtechRAG


## 1. Konfiguracja Środowiska i Konteneryzacji

W tym etapie przygotuję system operacyjny Ubuntu 24.04.3 LTS do działania jako host dla wszystkich usług.

1.  **Aktualizacja systemu:**
    *   Wykonam pełną aktualizację pakietów systemu `apt update && apt upgrade`.
    *   Zainstaluję podstawowe narzędzia developerskie (build-essential, git, curl, wget).
2.  **Instalacja Pythona i środowiska wirtualnego:**
    *   Upewnię się, że zainstalowany jest Python 3 w wersji stabilnej (min. 3.10).
    *   Skonfiguruję `venv` (virtual environment) dla projektu RAG, aby izolować zależności.
3.  **Instalacja i konfiguracja Podman:**
    *   Zainstaluję Podman jako zamiennik Dockera (zgodnie z założeniami open source).
    *   Skonfiguruję sieć dla kontenerów, aby usługi (Nextcloud, n8n, baza danych) mogły się ze sobą komunikować bezpiecznie na localhost.
    *   Przygotuję wolumeny (volumes) na dysku SSD FireCuda dla trwałego przechowywania danych.

## 2. Uruchomienie Usług Bazowych (Kontenery)

Uruchomię usługi pomocnicze w trybie offline, korzystając z Podman.

1.  **Baza Wektorowa (Vector Store):**
    *   Wybiorę i uruchomię kontener z bazą wektorową (np. **Qdrant** lub **Weaviate**), aby przechowywać indeksy RAG. Będzie to kluczowy element backendu Haystack.
2.  **Nextcloud (Prywatna Chmura):**
    *   Uruchomię kontener **Nextcloud** oraz bazę danych PostgreSQL (lub MariaDB) w Podmanie.
    *   Skonfiguruję Nextcloud jako dostępną lokalnie usługę (np. `cloud.local`) do przechowywania plików PDF, wideo i dokumentacji.
    *   Zmapuję wolumin dysku SSD tak, aby pliki z Nextcloud były dostępne dla systemu plików Linuxa (dla skryptów RAG).
3.  **n8n (Automatyzacja):**
    *   Uruchomię instancję **n8n** w kontenerze.
    *   Skonfiguruję podstawowe credentials (np. SMTP dla e-mail, tokeny dla Signal/Telegram - w trybie lokalnym).

## 3. Konfiguracja "Mózgu Operacyjnego" (llama.cpp)

Zainstaluję i skonfiguruję model językowy, który będzie działał w pełni offline.

1.  **Kompilacja/Instalacja llama.cpp:**
    *   Sklonuję repozytorium i skompiluję `llama.cpp` z optymalizacjami pod procesor **AMD Ryzen 9 9950X** (obsługa instrukcji AVX2/AVX512).
2.  **Pobieranie Modelu:**
    *   Pobiorę kwantyzowany model LLM (np. Llama 3 Instruct lub Mistral) odpowiedni do rozmiaru pamięci RAM (32GB DDR5 jest wystarczające dla modeli 7B-14B w precyzji wysokiej).
3.  **Uruchomienie Serwera API:**
    *   Uruchomię `llama-server` na porcie np. `8080`, udostępniając punkt końcowy (endpoint) kompatybilny z OpenAI API. Dzięki temu Haystack i inne narzędzia będą mogły się z nim łączyć tak, jak z chmurowym API, ale lokalnie.

## 4. Budowa Backendu RAG (Haystack + Docling + API)

To jest serce systemu. Stworzę aplikację w Pythonie, która łączy wszystkie komponenty w jedną całość.

1.  **Instalacja bibliotek Python:**
    *   Zainstaluję `haystack-ai`, `docling`, `llama-index`, `fastapi` (do API) oraz `sentence-transformers` (lokalne embeddy).
2.  **Integracja Docling (Parser Dokumentów):**
    *   Stworzę własny komponent Haystack (lub wrapper), który wykorzystuje bibliotekę `docling` do konwersji plików PDF (szczególnie tych z tabelami) na czysty Markdown/tekst przed indeksowaniem.
3.  **Pipeline Indeksowania (Ingestion):**
    *   Stworzę pipeline Haystack: Plik (z dysku/Nextcloud) -> Docling (parsing) -> Embedder (lokalny) -> Zapis do Bazy Wektorowej.
4.  **Pipeline Zapytań (RAG):**
    *   Stworzę pipeline RAG: Zapytanie -> Retriever (Baza Wektorowa) -> PromptBuilder -> Generator (llama.cpp API).
5.  **Warstwa API (FastAPI):**
    *   Stworzę prosty serwer FastAPI (np. na porcie `8000`) udostępniający dwa endpointy dla OpenCode:
        *   `POST /ingest` – do wysyłania plików do bazy wiedzy.
        *   `POST /query` – do zadawania pytań.

## 5. Integracja z Zewnętrznymi Źródłami (GitHub/GitLab)

Zautomatyzuję pozyskiwanie wiedzy z repozytoriów kodu.

1.  **Skrypty Synchronizacji:**
    *   Napiszę skrypty w Pythonie/Bash, które używają `git clone` do pobierania repozytoriów i forków z GitHub/GitLab do katalogu lokalnego.
    *   Skonfiguruję `git pull` cyklicznie (via n8n lub Cron), aby aktualizować lokalne repozytoria.
2.  **Indeksowanie Kodu:**
    *   Rozszerzę pipeline indeksowania, aby czytał pliki kodu (`.py`, `.js`, `.md`) z pobranych repozytoriów.
    *   Wykorzystam `LlamaIndex` do parsowania struktury kodu (jeśli wymagana jest głębsza analiza AST) lub Haystack do prostszego wyszukiwania fragmentów kodu.
3.  **Web Search:**
    *   Zaimplementuję prosty komponent w Haystack używający biblioteki typu `duckduckgo-search` do pobierania treści stron WWW i dodawania ich do kontekstu RAG "w locie".

## 6. Automatyzacja i Workflow (n8n)

Połączyę usługi w logiczne procesy.

1.  **Workflow "Nowa Dokumentacja":**
    *   W n8n stworzę nasłuchiwanie katalogu Nextcloud (lub Webhook).
    *   Gdy pojawi się nowy plik PDF -> n8n wywołuje lokalne API (`/ingest`) -> Haystack przetwarza plik przez Docling.
2.  **Workflow "Powiadomienia":**
    *   Skonfiguruję n8n do odbierania e-maili (IMAP).
    *   Gdy przyjdzie mail z określonym tematem -> n8n wyśle powiadomienie na Signal/Telegram.

## 7. Konfiguracja OpenCode jako Agent (IDE)

Na koniec zintegruję środowisko programistyczne z zbudowanym backendem.

1.  **Instalacja OpenCode:**
    *   Zainstaluję OpenCode.ai na systemie Ubuntu.
2.  **Definicja Narzędzia (Tool Definition):**
    *   W pliku konfiguracyjnym OpenCode dodam definicję nowego narzędzia (Tool).
    *   Skonfiguruję je tak, aby przy pytaniach dotyczących projektu ("Jak skonfigurować X?"), OpenCode wysyłał zapytanie JSON na `http://localhost:8000/query`.
3.  **Testowanie Loopa:**
    *   Przetestuję scenariusz: Użytkownik pyta w terminalu OpenCode o fragment dokumentacji PDF -> OpenCode wywołuje API -> Haystack (z Docling) znajduje odpowiedź -> Odpowiedź wraca do terminala.

## 8. Optymalizacja i Testy Sprzętowe

1.  **Optymalizacja pod Ryzen 9 9950X:**
    *   Dostroję parametry `llama.cpp` (liczba wątków, wielkość batcha) oraz `PyTorch` (jeśli użyty), aby w pełni wykorzystać 16 rdzeni i szybkość RAM DDR5.
2.  **Stress Test:**
    *   Przeprowadzę testy ładowania dużych plików PDF (Docling) oraz jednoczesnych zapytań RAG, aby upewnić się, że system działa stabilnie offline.

    

    1. Pełna automatyzacja Nextcloud -> RAG:
    Obecnie ręcznie wywołujesz curl, żeby dodać plik z Nextcloud. Możemy napisać skrypt "Watchdog" (Pies warty), który będzie monitorował folder RAG_Dane i od razu wysyłał nowe pliki do backendu. Dzięki temu: wrzucasz PDF do chmury -> minuta później system o nim wie. 

        a) Nexcloud zostawimy bez automatyzacji. Wszystkie zmiany w Nexcloud będę robił ręcznie przez stronę www lub aplikację. Jedynie można dodać 3 foldery do których będę przerzucał pliki video, muzyczne(np.ebook. muzyka, inne nagrania plików .mp3 .mp4 itp) oraz trzeci folder na pliki tekstowe (np. .pdf, .txt. .word itp). Stworzymy trzy foldery o nazwach:
        - Video_RAG
        - Audio_RAG
        - Doc_RAG
        b) Tylko do tych folderów będzie miał dostęp model i automatyzacja n8n. O dodatkowych podfolderach w tych folderach bedę myślał później w tracie jak będę wymyślał nowe funkcję i zastanawiał sie na całym drzewem katalogów mojej przyszłej biblioteki.
        Mam już zakupione dwa dyski : SSD 2TB duży i bardzo szybki dysk oraz drugi HDD 5TB na przechowywanie danych

    2. Integracja z OpenCode (zgodnie z oryginałem):
    Zamiast n8n, możemy skonfigurować Twój terminal OpenCode, żeby używał endpointu http://localhost:8000/query jako domyślnego narzędzia (Tool). Wtedy w terminalu wpisujesz: Opisz mi dokument z Nextcloud, a OpenCode (IDE) dzwoni do Twojego RAG i zwraca wynik w edytorze kodu. 

        a) Tak. Myślę ż OpenCode będzie najlepszym rozwiązaniem jako głóne narzędie do kontroli całego systemu(RAG, obsługa modeli, ingeręcja w pliki na komputerze, pisanie kodu itd). OpenCode ma możliwość przełączania pomiędzy agentami. Może da się nawet tak zmodyfikować kod abym mógł przełączać sobie pomiędzy odpowiednimi modelami do konkretnych zadań np: osobno operacje na tekscie, wideo lub audio a inny do kodowania itp.

    3. Kolejne repozytoria GitHuba:
    Twoj skrypt ingest_repo.py jest gotowy. Możesz teraz wrzucać do niego każde repozytorium (np. dokumentację sprzętu, instrukcje obsługi), które chcesz mieć w głowie. 

        a) Jeśli chodzi o repozytorium GithUb to jak już zainstaluję dysk 5TB to wtedy ściągnę moje "295 repositories" aby mieć do nich szybki dostęp w bazie GitHub_database_RAG
        Ale tym zajmiemy się dopiero później

# Drzewo katalogów i programów :

~/KlimtechRAG >> plik.txt 

AGENTS.md
backend_app
data
git_sync
llama.cpp
pytest.ini
start_klimtech.sh
venv
watch_nextcloud.py
watch_nextcloud.py.bac

~/KlimtechRAG/backend_app
 main.py
plik_testowy.py
__pycache__

~/KlimtechRAG/git_sync

ingest_repo.py
opencode


Robię nowy plan na podstawie tego co było już zrobione :

WYPISZ MI cały plan KlimtechRAG
1. Co było zrobione.
2. Co trzeba zrobić.
3. Twoje sugestie.
4. Twoja odpowiedź ma być jak najbardziej szczegółowa.
5. wypisz mi drzewo katalogów w ~/KlimtechRAG.
6. dołącz do nowego planu zawartość pliku AGENTS.md.
7. dołącz do nowego planu zawartość pliku zawartość pliku klimtech_rag.



