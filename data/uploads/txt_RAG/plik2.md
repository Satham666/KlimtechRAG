# Plan_instalacji_RAG.md

## 1. Nazwa projektu
**KlimtechRAG**

---

## 2. Projekt
Zintegrowanie środowiska i narzędzi: `llama.cpp`, `Haystack`, `Docling`, `LlamaIndex`, `offline-friendly` baza RAG, `n8n`, `OpenCode` (https://opencode.ai/), `Nextcloud`, `GitHub`, `GitLab`, `Podman` (open source container tools), `Web-search`.

---

## 3. Platforma / Technologia

### System i język:
- **System operacyjny:** Ubuntu 24.04.3 LTS
- **Język programowania:** Python 3

### Sprzęt (Hardware):
- **Dysk:** Seagate SSD FireCuda 540 1TB PCIe M.2
- **Procesor:** AMD Ryzen 9 9950X Tray Socket AM5 | 64MB | 5.7GHz
- **Płyta główna:** Gigabyte X870 GAMING X WIFI7 (ATX)
- **Pamięć RAM:** GOODRAM UDIMM 2x16GB DDR5 7200MHz CL34 IRDM

### Kluczowe technologie:
- Haystack, Docling, LlamaIndex, n8n, OpenCode (https://opencode.ai/)

---

## 4. Cel projektu / Koncepcja

- **Mózg operacyjny:** Lokalny model językowy `llama.cpp` sterujący wszystkimi procesami na localhost.
- **RAG jako Serwis (RAG-as-a-Service) dla IDE:** Backend działający jako rozszerzenie systemu OpenCode.
- **Automatyzacja (n8n):** Automatyzacja procesów, w tym powiadomień Signal, Telegram i obsługi e-mail.
- **Integracja z Nextcloud:** Prywatna chmura z możliwością dodawania plików do bazy RAG.
- **Integracja z GitHub/GitLab:**
  - Pobieranie repozytoriów do bazy RAG.
  - Synchronizacja lokalnej bazy z chmurą.
  - Przeszukiwanie kodu w GitHub i GitLab dla OpenCode.
- **Dostęp do sieci:** Web-search w celu pozyskiwania aktualnych informacji.

---

## 5. Najważniejsze założenia i zasady

### Interakcja Użytkownika:
- Użytkownik wpisuje w terminalu OpenCode:
  - *"Wytłumacz mi jak skonfigurować X w naszym projekcie"*
  - *"Znajdź błąd w pliku PDF z dokumentacją"*

### Agent (OpenCode):
- Rozpoznaje intencję i decyduje o pobraniu kontekstu z dokumentów lub źródeł zewnętrznych.

### Narzędzie (Tool):
- OpenCode wywołuje lokalny endpoint HTTP (Haystack API).

### Przetwarzanie (Backend):
- **Haystack** używa **Docling** do parsowania dokumentów.
- **LlamaIndex / Haystack** przeszukują bazę wiedzy i generują odpowiedź.

### Wynik:
- Gotowa odpowiedź lub kontekst wraca do terminala OpenCode.

### Zasada działania:
- Wszystko działa na localhost (offline-first).
- Możliwość przeszukiwania WWW i zewnętrznych chmur.

### Zarządzanie kodem:
- Lokalna baza GitHub (klonowanie repozytoriów).
- Synchronizacja z chmurą GitHub.

---

## 6. Typowe zadania i workflow

- **Tworzenie kodu:** Generowanie i modyfikacja kodu w OpenCode z kontekstem RAG.
- **Tłumaczenia:** Techniczne tłumaczenia z zachowaniem kontekstu.
- **Zarządzanie wiedzą:** Tworzenie i utrzymywanie baz RAG.
- **Przechowywanie plików:** Nextcloud jako prywatny serwer plików.
- **Agregacja danych:** Web-search i budowa własnej bazy wiedzy.
- **Automatyzacja (n8n):**
  - Odbieranie e-maili.
  - Powiadomienia e-mail, Signal, Telegram.

---

## 7. Ważne linki do stron i dokumentacji

### Modele i Backend:
- **Llama.cpp:** https://github.com/ggml-org/llama.cpp
- **Haystack:** https://github.com/deepset-ai/haystack
- **Docling:** https://github.com/docling-project/docling
- **LlamaIndex:** https://github.com/run-llama/LlamaIndexTS

### Automatyzacja i IDE:
- **n8n:** https://github.com/n8n-io/n8n , https://docs.n8n.io/
- **OpenCode:** https://opencode.ai/ , https://github.com/anomalyco/opencode

### Chmura i Kontenery:
- **Nextcloud:** https://nextcloud.com/ , https://docs.nextcloud.com/
- **Podman:** https://podman.io/ , https://github.com/containers/podman

### Repozytoria:
- **GitHub:** https://github.com/ , https://docs.github.com/
- **GitLab:** https://about.gitlab.com/ , https://docs.gitlab.com/

---

## 8. Analiza architektury i rozbicie projektu na komponenty
- Zidentyfikuję wszystkie elementy systemu:
  - llama.cpp, Haystack, Docling, LlamaIndex, n8n, OpenCode, Nextcloud, GitHub/GitLab, Web-search
- Określę:
  - które komponenty działają w Podman
  - które działają natywnie w Pythonie
- Zaprojektuję przepływ danych:
  - OpenCode → Haystack API → RAG → llama.cpp → OpenCode

---

## 9. Przygotowanie środowiska systemowego (Ubuntu 24.04.3)
- Aktualizacja systemu
- Instalacja: git, curl, wget, build-essential, python3, python3-venv, pip
- Konfiguracja środowiska Python (venv)
- Instalacja Podman (rootless)
- Sprawdzenie zasobów sprzętowych

---

## 10. Instalacja i konfiguracja llama.cpp
- Klon repozytorium
- Kompilacja z optymalizacją pod CPU
- Pobranie modelu GGUF
- Uruchomienie lokalnego serwera HTTP
- Test endpointów API

---

## 11. Instalacja Haystack jako backendu RAG
- Instalacja w venv
- Konfiguracja DocumentStore (FAISS / SQLite / DuckDB)
- Integracja z llama.cpp
- Utworzenie API (FastAPI):
  - `/query`
  - `/ingest`

---

## 12. Integracja Docling
- Instalacja Docling
- Parsowanie PDF, tabel, dokumentacji
- Test importu dokumentów

---

## 13. Integracja LlamaIndex
- Instalacja
- Indeks hybrydowy (kod + tekst)
- Integracja z Haystack
- Test jakości wyszukiwania

---

## 14. Budowa lokalnej bazy RAG (offline-first)
- Struktura katalogów danych
- Metadane dokumentów
- Import plików i katalogów
- Brak zależności od chmury

---

## 15. Integracja OpenCode (RAG-as-a-Service)
- Analiza API OpenCode
- Adapter: OpenCode → Haystack
- Test zapytań kontekstowych

---

## 16. Integracja GitHub i GitLab
- Klonowanie repozytoriów
- Skanowanie kodu
- Indeksowanie plików źródłowych
- Wyszukiwanie w lokalnej bazie

---

## 17. Integracja Nextcloud
- WebDAV
- Import plików do RAG
- Zachowanie niezależności chmury

---

## 18. Web-search
- Pobieranie treści WWW
- Filtrowanie i zapisywanie do RAG
- Praca offline z ręcznymi aktualizacjami

---

## 19. Automatyzacja z n8n
- Instalacja n8n
- Workflow:
  - e-mail → RAG
  - Nextcloud → RAG
  - Git → RAG
  - Powiadomienia Signal / Telegram

---

## 20. Konteneryzacja (Podman)
- Kontenery: Haystack, n8n, Nextcloud
- Sieć lokalna
- Wolumeny danych
- Test komunikacji

---

## 21. Testy integracyjne
- Test OpenCode
- Test importów
- Test automatyzacji
- Optymalizacja chunkingu i kontekstu

---

## 22. Dokumentacja i rozwój
- Dokumentacja instalacji i architektury
- Przykładowe workflow n8n
- Plan dalszej rozbudowy

---

## 23. Efekt końcowy
- Lokalny, offline-first system RAG
- RAG-as-a-Service dla OpenCode
- Pełna kontrola nad danymi, dokumentami i kodem