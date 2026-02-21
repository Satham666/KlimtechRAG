📋 Skonsolidowany plan KlimtechRAG

*(z plików Plan_instalacji_RAG.md, Plan_instalacji_RAG_NR2.md i Plan_instalacji_RAG_NR_3.md)
1️⃣ Co już zostało zrobione
Obszar	Zadania zakończone
Infrastruktura / kontenery	• Instalacja i konfiguracja Podman • Uruchomienie kontenerów: Qdrant, Nextcloud (+ PostgreSQL/MariaDB), n8n
Model językowy	• Skompilowany llama.cpp • Pobrany i uruchomiony model LFM2‑2.6B‑Q5_K_M.gguf na porcie 8081 (GPU RX580)
Backend RAG	• API FastAPI nasłuchujące na porcie 8000 • End‑pointy /ingest i /query • Integracja Haystack + Docling (parsowanie PDF → Markdown) • Indeksowanie do Qdrant
Watchdog / monitorowanie	• Skrypt watch_nextcloud.py obserwuje foldery Doc_RAG, Audio_RAG, Video_RAG, Images_RAG i wywołuje /ingest przy nowych plikach
Git‑sync	• Skrypt ingest_repo.py gotowy do klonowania repozytoriów i ich indeksowania
OpenCode	• Zainstalowany na Ubuntu, gotowy do dalszej integracji
Podstawowe workflow n8n	• Odbiór e‑maili (IMAP) • Powiadomienia na Signal / Telegram (SMTP, webhook)
Dokumentacja	• Szczegółowe plany w trzech plikach markdown, opisane cele i zasoby sprzętowe
2️⃣ Co jeszcze trzeba zrobić (bez duplikatów)
🔧 Konfiguracja i integracja OpenCode

    Definicja narzędzia (Tool) w OpenCode, które wywołuje POST http://localhost:8000/query.
    Mapowanie poleceń – np. Opisz mi dokument X → wywołanie API i zwrot wyniku w edytorze.
    Testy end‑to‑end: zapytanie w OpenCode → backend → odpowiedź → wyświetlenie w terminalu/IDE.

🤖 Rozbudowa automatyzacji n8n

    Webhook /notify_success w backendzie (informuje n8n o udanym indeksowaniu).
    Workflow „Nowa dokumentacja” – nasłuchiwanie folderu Nextcloud → /ingest.
    Workflow „Powiadomienia” – po udanym indeksowaniu wysyła wiadomość na Telegram/e‑mail.

📂 Pełna automatyzacja Nextcloud → RAG

    Skrypt “Watchdog” uruchamiany jako usługa systemowa (systemd) zamiast ręcznego &.
    Obsługa trzech folderów (Doc_RAG, Audio_RAG, Video_RAG) – obecnie tylko PDF są indeksowane.

🎤 Rozwój Audio / Video RAG (przyszłe etapy)

    Dodanie Whisper (transkrypcja audio) → indeksowanie tekstu.
    Dodanie LLaVA lub podobnego modelu wideo → ekstrakcja opisów scen.

🛠️ Optymalizacja i testy

    Dostosowanie parametrów llama.cpp (liczba wątków, batch size) do Ryzen 9 9950X.
    Stress‑testy równoczesnych zapytań i dużych plików PDF.
    Monitorowanie zużycia CPU/RAM, ewentualna skalowalność (więcej dysków SSD/HDD).

📦 Usprawnienia wdrożeniowe

    Jednolity skrypt startowy (start_klimtech.sh) uruchamiający kolejno: podman, Qdrant, Nextcloud, n8n, LLM, backend, watchdog.
    SSH dostęp do OpenCode (tylko do wybranego katalogu) – konfiguracja firewalla i kluczy SSH.

3️⃣ Sugestie / dobre praktyki
Obszar	Rekomendacja
Kontenery	Użyj Podman pods do grupowania usług (Nextcloud + Postgres, n8n + Redis) – ułatwia sieci i zarządzanie.
Bezpieczeństwo	Włącz TLS (self‑signed) dla wszystkich lokalnych endpointów (/ingest, /query).
Logowanie	Centralny system logów (np. Grafana Loki + Promtail) – przydatny przy debugowaniu RAG i n8n.
Backup	Regularne snapshoty wolumenów Qdrant i Nextcloud (cron + podman cp).
Skalowalność	Rozważ oddzielny kontener z embedding model (sentence‑transformers) – przyspieszy retriever.
Testy jednostkowe	Dodaj testy w pytest dla API (/ingest, /query) i dla skryptów watchdog/ingest_repo.
Dokumentacja	Trzymaj README.md w katalogu głównym z instrukcjami uruchomienia, zależności i przykładowymi zapytaniami.
CI/CD	Skonfiguruj prosty pipeline (GitHub Actions) budujący obrazy podman i uruchamiający testy.
4️⃣ Drzewo katalogów w ~/KlimtechRAG

~/KlimtechRAG
├── AGENTS.md
├── backend_app
│   ├── main.py
│   ├── plik_testowy.py
│   └── __pycache__/
├── data
│   ├── n8n/
│   ├── nextcloud/
│   ├── nextcloud_db/
│   ├── postgres/
│   └── qdrant/
├── git_sync
│   ├── ingest_repo.py
│   └── opencode/
├── llama.cpp
│   ├── AUTHORS
│   ├── CMakeLists.txt
│   ├── README.md
│   ├── build/
│   ├── cmake/
│   ├── docs/
│   ├── examples/
│   ├── ggml/
│   ├── gguf-py/
│   ├── models/
│   ├── scripts/
│   └── src/
├── pytest.ini
├── start_klimtech.sh
├── venv/
│   ├── bin/
│   ├── include/
│   ├── lib/
│   ├── lib64/
│   └── pyvenv.cfg
└── watch_nextcloud.py

5️⃣ Zawartość pliku AGENTS.md

    Uwaga: Treść pliku AGENTS.md nie została dostarczona w przesłanych materiałach, więc nie mogę jej przytoczyć. Jeśli udostępnisz jego zawartość, chętnie ją włączę do planu.

6️⃣ Zawartość pliku klimtech_rag

    Uwaga: Nie otrzymałem pliku o nazwie klimtech_rag (ani klimtech_rag.md). Jeśli istnieje taki plik, proszę go przesłać, a ja go uwzględnię.

📌 Podsumowanie

    Co jest gotowe: większość infrastruktury, model LLM, backend RAG, watchdog, podstawowe workflow n8n oraz instalacja OpenCode.
    Co jest priorytetem: pełna integracja OpenCode jako jedynego interfejsu, automatyzacja powiadomień oraz uruchomienie usług jako spójny zestaw (skrypt startowy).
    Co warto dodać w kolejnych iteracjach: obsługa audio/video RAG, lepsze zabezpieczenia TLS, centralny system logów oraz CI/CD.

Jeżeli potrzebujesz bardziej szczegółowych instrukcji (np. przykładowy plik konfiguracyjny dla OpenCode) lub chcesz, żebym pomógł napisać konkretny skrypt, daj znać – jestem do dyspozycji! 🚀