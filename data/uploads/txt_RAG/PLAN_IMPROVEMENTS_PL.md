# Plan Poprawy Systemu KlimtechRAG

## Przegląd Aktualnej Architektury

Po przeanalizowaniu projektu KlimtechRAG, oto szczegółowy plan poprawy systemu:

### Główne Komponenty Systemu

**1. Backend API** (`/home/lobo/KlimtechRAG/backend_app/main.py`)
- Aplikacja FastAPI działająca na porcie 8000
- Endpoint do przyjmowania plików (`/ingest`) obsługujący PDF, tekst i kod
- Endpoint zapytań RAG (`/query`) z rozszerzeniem wyszukiwania internetowego
- Endpoint zapytań programistycznych (`/code_query`) dla zadań deweloperskich
- Wykorzystuje Docling do parsowania PDF i SentenceTransformers do embeddingów
- Integracja z bazą wektorową Qdrant i serwerem LLM

**2. Serwer LLM** - serwer llama.cpp na porcie 8081 z modelem LFM2-2.6B

**3. Monitor Plików** (`watch_nextcloud.py`) - obserwuje foldery Nextcloud
- Monitoruje: Doc_RAG, Audio_RAG, Video_RAG, Images_RAG, json_RAG, pdf_RAG, txt_RAG
- Automatycznie ingestuje nowe pliki do systemu RAG

**4. Synchronizacja Git** (`/home/lobo/KlimtechRAG/git_sync/ingest_repo.py`) - narzędzie do masowej indeksacji repozytoriów

**5. Orkiestracja** (`start_klimtech.py`) - główny skrypt startowy zarządzający wszystkimi usługami

### Przepływ Danych

```
Pliki Nextcloud → Watchdog → /ingest API → Docling/Parsowanie → SentenceTransformers → Qdrant
                                                                              ↓
Zapytanie użytkownika → /query API → Embedding zapytania → Qdrant Retrieval + Wyszukiwanie internetowe → LLM → Odpowiedź
```

### Główne Technologie
- FastAPI, Haystack, Qdrant, Docling, SentenceTransformers, llama.cpp
- Kontenery Podman (Qdrant, Nextcloud, PostgreSQL, n8n)
- Python 3.12.3

---

## Stan Aktualny Systemu

### Co Działa Poprawnie
- Podstawowa pipeline RAG z ingestowaniem dokumentów i zadaniami zapytań
- Monitorowanie plików z folderów Nextcloud
- Możliwość masowej indeksacji repozytoriów Git
- Wsparcie dla wielu formatów (PDF, audio, wideo, tekst, kod)
- Orkiestracja usług z kontrolą zdrowia

### Wykryte Problemy
1. **Duplikacja kodu** - klasa `CodeQueryRequest` jest zdefiniowana dwukrotnie w main.py (linie 225-226 i 278-279)
2. **Niekompletny kod** - plik wydaje się ucięty przy linii 279
3. **Ograniczona obsługa błędów** w niektórych endpointach
4. **Brak kompleksowego zestawu testów** w korzeniu projektu
5. **Potencjalny zduplikowany kod** w bloku wykonawczym main

---

## Zalecany Plan Poprawy

### Faza 1: Jakość Kodu i Stabilność

**Cel:** Poprawa jakości kodu i eliminacja błędów

#### 1.1 Naprawa Duplikacji Kodu
- Usunięcie zduplikowanej definicji klasy `CodeQueryRequest`
- Refaktoryzacja wspólnych modeli do osobnego modułu
- Unifikacja struktur danych w API

#### 1.2 Uzupełnienie Niekompletnego Kodu
- Analiza pliku main.py pod kątem brakujących fragmentów
- Dodanie brakujących importów i funkcji
- Weryfikacja spójności bloku `if __name__ == "__main__"`

#### 1.3 Poprawa Obsługi Błędów
- Opakowanie wszystkich endpointów API w properną obsługę wyjątków
- Dodanie szczegółowych komunikatów błędów
- Implementacja logowania błędów z kontekstem
- Dodanie kodów błędów HTTP dla różnych scenariuszy

#### 1.4 Walidacja Danych Wejściowych
- Walidacja rozmiarów i typów plików przed przetwarzaniem
- Sprawdzanie poprawności parametrów zapytań
- Ograniczenie rozmiaru przesyłanych plików
- Weryfikacja rozszerzeń plików

---

### Faza 2: Testy i Zapewnienie Jakości

**Cel:** Stworzenie kompleksowego zestawu testów

#### 2.1 Testy Jednostkowe
- **Testy logiki ingestowania plików:**
  - Walidacja rozszerzeń plików
  - Sprawdzanie rozmiarów plików
  - Testy parsowania różnych formatów
  - Obsługa błędnych plików

- **Testy przetwarzania zapytań:**
  - Poprawne formatowanie zapytań
  - Walidacja odpowiedzi LLM
  - Integracja z wyszukiwaniem internetowym

- **Testy walidacji typów plików:**
  - Rozpoznawanie formatów
  - Obsługa nieobsługiwanych typów
  - Walidacja zawartości

- **Testy scenariuszy błędów:**
  - Nieistniejące pliki
  - Błędy połączenia z Qdrant
  - Problemy z serwerem LLM
  - Timeout'y i przekroczenia czasu

#### 2.2 Testy Integracyjne
- **Testy endpointów API:**
  - `/ingest` - przesyłanie i przetwarzanie plików
  - `/query` - obsługa zapytań RAG
  - `/code_query` - zapytania programistyczne
  - Testy autentykacji i autoryzacji (jeśli zaimplementowane)

- **Testy łączności z bazą danych:**
  - Połączenie z Qdrant
  - Operacje CRUD na dokumentach
  - Wyszukiwanie wektorowe

- **Testy kondycji usług:**
  - Health check endpointów
  - Dostępność serwera LLM
  - Status połączeń

#### 2.3 Automatyzacja Jakości Kodu
- Konfiguracja CI/CD z automatycznym uruchamianiem testów
- Integracja lintingu w procesie commitowania
- Sprawdzanie pokrycia kodu testami
- Automatyczne formatowanie zgodnie ze standardami

---

### Faza 3: Optymalizacja Wydajności

**Cel:** Zwiększenie wydajności systemu

#### 3.1 Przetwarzanie Asynchroniczne
- Refaktoryzacja ingestowania plików na async
- Równoległe przetwarzanie wielu plików
- Kolejkowanie zadań długotrwałych
- Optymalizacja wykorzystania wątków

#### 3.2 Przetwarzanie Wsadowe
- Implementacja batch processing dla dużych plików
- Grupowanie zapytań do Qdrant
- Buforowanie embeddingów
- Optymalizacja zapytań do LLM

#### 3.3 System Cache'owania
- Cache częstych zapytań
- Przechowywanie wyników embeddingów
- Cache konfiguracji i metadanych
- Strategia invalidacji cache

#### 3.4 Optymalizacja Generowania Embeddingów
- Batch processing dla wielu dokumentów
- Wykorzystanie GPU (jeśli dostępne)
- Kompresja modeli embeddingowych
- Leniwa inicjalizacja modeli

---

### Faza 4: Rozszerzenia Funkcjonalne

**Cel:** Dodanie nowych funkcji do systemu

#### 4.1 Bezpieczeństwo API
- Implementacja autentykacji użytkowników
- System autoryzacji i ról
- Rate limiting dla endpointów
- Ochrona przed atakami DoS
- Szyfrowanie komunikacji

#### 4.2 Monitoring i Metryki
- Endpointy statusu systemu
- Metryki wydajności (latency, throughput)
- Dashboard administracyjny
- Alertowanie o problemach
- Integracja z systemami monitoringowymi

#### 4.3 Zaawansowane Funkcje RAG
- Wiele kolekcji dokumentów (różne źródła)
- Filtrowanie według metadanych
- Reranking wyników
- Kontekstowe podpowiedzi
- Historia konwersacji

#### 4.4 Interfejs Użytkownika
- Panel webowy do zarządzania dokumentami
- Interfejs testowania zapytań
- Wizualizacja metryk systemu
- Konfiguracja przez GUI

---

### Faza 5: Dokumentacja i Utrzymanie

**Cel:** Zapewnienie łatwości utrzymania systemu

#### 5.1 Dokumentacja API
- Kompletna dokumentacja OpenAPI/Swagger
- Przykłady użycia każdego endpointu
- Opisy kodów błędów
- Wersjonowanie API

#### 5.2 Przewodniki Wdrożeniowe
- Instrukcje dla różnych środowisk
- Konfiguracja zmiennych środowiskowych
- Procedury backup i restore
- Skalowanie horyzontalne

#### 5.3 Rozwiązywanie Problemów
- Najczęstsze błędy i ich rozwiązania
- Procedury diagnostyczne
- Logowanie i analiza logów
- Kontakt ze wsparciem technicznym

#### 5.4 Konfiguracja Logowania
- Agregacja logów
- Formatowanie i poziomy logowania
- Rotacja logów
- Integracja z systemami logowania

---

## Harmonogram Realizacji

| Faza | Priorytet | Czas Realizacji | Główne Cele |
|------|-----------|------------------|-------------|
| Faza 1 | Krytyczny | 1-2 tygodnie | Stabilność i poprawki krytyczne |
| Faza 2 | Wysoki | 2-3 tygodnie | Zapewnienie jakości |
| Faza 3 | Średni | 3-4 tygodnie | Wydajność |
| Faza 4 | Opcjonalny | 4-6 tygodni | Nowe funkcje |
| Faza 5 | Ciągły | Bieżące | Dokumentacja |

---

## Wymagania Przed Rozpoczęciem

### Wymagania Wstępne
1. Dostęp do środowiska deweloperskiego
2. Uprawnienia do modyfikacji plików projektu
3. Dostęp do serwera testowego
4. Kopia zapasowa aktualnej konfiguracji

### Zależności do Zainstalowania
- pytest i fixtures
- biblioteki do mockowania
- narzędzia do analizy pokrycia kodu
- serwer CI/CD (opcjonalnie)

---

## Kroki Następne

### Przed Przystąpieniem do Implementacji

1. **Potwierdzenie Priorytetów:**
   - Która faza jest najważniejsza dla Ciebie?
   - Czy wszystkie fazy są potrzebne?
   - Czy są dodatkowe wymagania?

2. **Weryfikacja Środowiska:**
   - Czy mam pełny dostęp do kodu?
   - Czy mogę uruchamiać testy?
   - Czy jest dostępne środowisko testowe?

3. **Oczekiwania Czasowe:**
   - Kiedy planujesz mieć gotowy system?
   - Czy są jakieś deadline'y?
   - Czy można pracować równolegle nad wieloma fazami?

---

## Pytania do Wyjaśnienia

1. **Czy chcesz, abym kontynuował z tą listą zadań?** Jeśli tak, od której fazy?

2. **Czy są jakieś konkretne problemy,** które chciałbyś, abym naprawił w pierwszej kolejności?

3. **Czy potrzebujesz dodatkowych funkcji,** które nie zostały uwzględnione w tym planie?

4. **Czy masz preferencje** co do narzędzi testowych lub formatu dokumentacji?

5. **Czy chciałbyś otrzymywać raporty postępu** po zakończeniu każdej fazy?

---

## Informacje o Projekcie

- **Lokalizacja:** `/home/lobo/KlimtechRAG`
- **Python:** 3.12.3
- **Główne pliki:** `backend_app/main.py`, `watch_nextcloud.py`, `git_sync/ingest_repo.py`
- **Testy:** Konfiguracja w `pytest.ini` (ignore: data, llama.cpp, venv)
- **Linting:** `ruff check .` i `ruff format .`

---

*Data utworzenia: 2026-02-08*
*Wersja: 1.0*
