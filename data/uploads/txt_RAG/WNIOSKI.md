# Analiza projektu KlimtechRAG

## Opis działania programu

### Architektura
System RAG (Retrieval-Augmented Generation) do indeksowania dokumentów i odpowiadania na pytania z użyciem LLM.

**Główne komponenty:**

| Plik | Funkcja |
|------|---------|
| `backend_app/main.py` | API FastAPI (3 endpointy) |
| `watch_nextcloud.py` | Monitorowanie folderów Nextcloud |
| `git_sync/ingest_repo.py` | Batch import repozytoriów Git |
| `start_klimtech.py` | Orkiestracja uruchamiania serwisów |
| `zai_wrapper.py` | Wrapper do zewnętrznego API Z.AI |

### Przepływ danych

```
Dokument (PDF/TXT/Kod/Audio)
        ↓
   Docling → Markdown
        ↓
   Chunking (200 słów)
        ↓
   Embeddings (multilingual-e5-large)
        ↓
   Qdrant (wektory)
        ↓
   Query → Retriever → LLM → Odpowiedź
```

### Stack technologiczny
- **FastAPI** + **Haystack** + **Qdrant**
- **llama.cpp** (lokalny LLM)
- **Docling** (PDF → Markdown)
- **DuckDuckGo** (web search)

### Endpointy API

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/ingest` | POST | Upload i indeksowanie dokumentów |
| `/query` | POST | Zapytanie RAG z web search |
| `/code_query` | POST | Zapytania programistyczne |

---

## Co warto zmienić

### Krytyczne błędy

1. **Martwy kod w `main.py:277-283`**
   - Signal handler zdefiniowany po `uvicorn.run()` - kod nigdy się nie wykona
   - Należy przenieść przed uruchomienie serwera

2. **`start_klimtech_dwa.py` - niedziałający plik**
   - Referencje do niezdefiniowanych zmiennych: `PROCESSES`, `LLAMA_BINARY`
   - Używa niezdefiniowanej funkcji `make_non_blocking`
   - Prawdopodobnie niedokończona kopia `start_klimtech.py`
   - Usunąć lub naprawić

3. **Brak walidacji rozmiaru pliku w `/ingest`**
   - Tylko `ingest_repo.py` ma limit 500KB
   - Endpoint `/ingest` przyjmuje pliki bez limitu
   - Może powodować problemy z pamięcią

### Jakość kodu

4. **Duplikacja stałych `ALLOWED_EXTENSIONS`**
   - Zdefiniowane różnie w 3 plikach:
     - `main.py`: brakuje `.js`, `.ts`, `.png`
     - `watch_nextcloud.py`: ma `.png`, brakuje `.js`, `.ts`
     - `ingest_repo.py`: ma wszystkie
   - Stworzyć jeden plik `config.py` ze wspólnymi stałymi

5. **Hardcoded konfiguracja**
   - `OPENAI_BASE_URL` hardcoded w kodzie
   - `LLM_MODEL_NAME` hardcoded
   - Przenieść do zmiennych środowiskowych `.env`

6. **Niespójne error handling**
   - `/ingest` zwraca `{"error": str(e)}` zamiast HTTPException
   - Inne endpointy używają HTTPException
   - Ujednolicić obsługę błędów

### Braki w funkcjonalności

7. **Brak testów**
   - Istnieje tylko `pytest.ini`
   - Brak plików testowych w `backend_app/` i `git_sync/`
   - Dodać testy jednostkowe i integracyjne

8. **Brak endpointu `/health`**
   - Trudne monitorowanie stanu aplikacji
   - Dodać sprawdzanie: Qdrant, LLM, status ogólny

9. **Brak strukturalnego logowania**
   - Tylko `print()` statements
   - Brak poziomów logów (DEBUG, INFO, ERROR)
   - Użyć modułu `logging` z konfigurowalnymi poziomami

### Potencjalne bugi

10. **Race condition w watcher**
    - Plik może być w trakcie zapisu gdy `on_created` się wyzwoli
    - Dodać mechanizm debounce lub sprawdzenie czy plik jest kompletny

11. **Web search failure handling**
    - Zwraca "Brak wyników z sieci." ale nie rozróżnia błędu sieci od braku wyników

---

## Funkcje do dodania

### Priorytet wysoki

| Funkcja | Opis | Korzyść |
|---------|------|---------|
| **Health check** | `/health` endpoint z statusem Qdrant, LLM | Łatwe monitorowanie |
| **Rate limiting** | Limit zapytań per IP/API key | Ochrona przed nadużyciami |
| **File size validation** | Limit w `/ingest` endpoint | Stabilność systemu |
| **Structured logging** | `logging` module z poziomami | Łatwiejsze debugowanie |

### Priorytet średni

| Funkcja | Opis | Korzyść |
|---------|------|---------|
| **Authentication** | API key lub JWT | Bezpieczeństwo |
| **Metrics endpoint** | Statystyki: liczba dokumentów, zapytań | Monitoring |
| **Batch delete** | Usuwanie dokumentów z Qdrant | Zarządzanie danymi |
| **Config consolidation** | Jeden plik `config.py` ze stałymi | Utrzymywalność |

### Priorytet niski

| Funkcja | Opis | Korzyść |
|---------|------|---------|
| **Debounce w watcher** | Opóźnienie dla plików w trakcie zapisu | Stabilność |
| **WebSocket support** | Real-time status indeksowania | UX |
| **Async document processing** | Background jobs z Celery/RQ | Skalowalność |
| **Caching** | Redis dla często zadawanych pytań | Wydajność |

---

## Podsumowanie

### Mocne strony
- Czysty podział odpowiedzialności (API, watcher, ingestion)
- Dobre wykorzystanie Haystack pipelines
- Obsługa wielu formatów dokumentów
- Web search augmentation
- Specjalizowany endpoint dla zapytań kodowych

### Obszary do poprawy
1. Naprawić martwy/niedziałający kod
2. Dodać testy
3. Zaimplementować proper logging
4. Dodać walidację input
5. Skonsolidować konfigurację
6. Dodać health check

---

*Analiza wygenerowana: 2026-02-17*
