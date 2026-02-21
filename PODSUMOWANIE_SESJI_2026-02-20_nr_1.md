# Podsumowanie sesji KlimtechRAG - 2026-02-20

## 1. Wykonane zmiany

### Konfiguracja OCR (Docling)
- [x] Dodano `bitmap_area_threshold=0.0` (było 0.05) - OCR przetwarza wszystkie obrazy, nie tylko >5% strony
- [x] Dodano język polski: `lang=["english", "polish"]` (było tylko english)
- [x] Zmiany w plikach: `backend_app/main.py`, `ingest_pdfCPU.py`

### Parametry RAG
- [x] Zwiększono `top_k` z 3 do 10 w retrieverze - model widzi więcej dokumentów
- [x] Timeout ingest zwiększony z 1800s (30min) do 7200s (2h) w `watch_nextcloud.py`

### Nowe skrypty
- [x] `ingest_pdfCPU.py` - OCR na CPU (RapidOCR + onnxruntime)
- [x] `ingest_pdfGPU.py` - OCR na GPU z podziałem na strony + resume:
  - Dzieli PDF na pojedyncze strony (`data/uploads/pdf_pages/`)
  - Zapamiętuje postęp w `pdf_progress.json`
  - Można wznowić po awarii od ostatniej strony
  - Używa EasyOCR z GPU

### Zainstalowane pakiety
- [x] `onnxruntime` - backend dla RapidOCR
- [x] `easyocr` - OCR z obsługą GPU
- [x] `pymupdf` (fitz) - podział PDF na strony

### Diagnostyka
- [x] Wykryto problem: PDF z warstwą tekstową jest przetwarzany przez OCR zamiast prostego wyodrębnienia tekstu
- [x] Wykryto problem: Qdrant zawierał głównie puste/artefaktowe chunki (spacje, znaki tabel)
- [x] `pdftotext` działa natychmiast i poprawnie dla tego PDF

### Czyszczenie
- [x] Skasowano kolekcję Qdrant `klimtech_docs`
- [x] Skasowano `file_registry.db`

---

## 2. Do wykonania

### Priorytet 1 - Naprawa ingest PDF
- [ ] Stworzyć prosty skrypt używający `pdftotext` zamiast Docling dla PDF z warstwą tekstową
- [ ] Wykrywanie czy PDF ma warstwę tekstową:
  - Jeśli TAK → `pdftotext` (szybkie)
  - Jeśli NIE → Docling z OCR (dla skanów)
- [ ] Opcjonalnie: ekstrakcja obrazów z PDF osobno

### Priorytet 2 - Backend
- [ ] Zmienić `parse_with_docling()` w `backend_app/main.py` na inteligentne wykrywanie:
  ```python
  # Sprawdź czy PDF ma tekst
  text = subprocess.run(["pdftotext", pdf_path, "-"], capture_output=True)
  if len(text.stdout.strip()) > 100:
      # Użyj pdftotext - szybko
  else:
      # Użyj Docling z OCR - dla skanów
  ```

### Priorytet 3 - Watchdog
- [ ] Poprawić `watch_nextcloud.py` - błędy typów (LSP errors)
- [ ] Dodać logowanie statusu do pliku

---

## 3. Dodatkowe sugestie

### Architektura ingest
```
PDF wejściowy
    │
    ▼
┌─────────────────────────┐
│ Sprawdź warstwę tekstu  │
│ (pdftotext -l 1 ...)    │
└─────────────────────────┘
    │
    ├── Tekst > 100 znaków ──────────────┐
    │                                     ▼
    │                        ┌─────────────────────┐
    │                        │ pdftotext (szybkie) │
    │                        │ ~1-2 sekundy        │
    │                        └─────────────────────┘
    │
    └── Tekst < 100 znaków ──────────────┐
                                          ▼
                             ┌─────────────────────┐
                             │ Docling + EasyOCR   │
                             │ GPU, podział strony │
                             │ ~30-60 sek/strona   │
                             └─────────────────────┘
```

### Obsługa grafik/obrazów
- **Obrazy z tekstem** (skany) → OCR (EasyOCR)
- **Wykresy/schematy** → VLM (Vision Language Model) do opisu:
  - Opcje: LLaVA, Qwen-VL, GPT-4V
  - Może działać równolegle z LLM na tym samym GPU (mały model VLM ~2-4GB)

### Optymalizacje
1. **Embedding na CPU** - zwolnić GPU dla LLM
2. **Batch processing** - przetwarzać wiele PDF naraz
3. **Cache modeli OCR** - modele EasyOCR są już pobrane (~1GB)

### Testy do przeprowadzenia
1. Porównać jakość: `pdftotext` vs `Docling bez OCR` vs `Docling z OCR`
2. Zmierzyć czas przetwarzania dla różnych rozmiarów PDF
3. Sprawdzić czy chunki mają sensowną treść po zmianach

---

## 4. Aktualne problemy

| Problem | Status | Rozwiązanie |
|---------|--------|-------------|
| OCR wolny dla PDF z tekstem | 🔴 Krytyczny | Użyj pdftotext |
| Puste chunki w Qdrant | 🔴 Krytyczny | Skasowano, do naprawy ingest |
| Model nie widzi dokumentów | 🟡 Średni | Zwiększono top_k, ale źródło to puste chunki |
| watch_nextcloud błędy LSP | 🟢 Niski | Do poprawy |

---

## 5. Struktura plików po zmianach

```
~/KlimtechRAG/
├── ingest_pdfCPU.py      # OCR na CPU (RapidOCR)
├── ingest_pdfGPU.py      # OCR na GPU (EasyOCR) + podział strony + resume
├── backend_app/
│   └── main.py           # Zmieniony OCR config
├── watch_nextcloud.py    # Zwiększony timeout
└── data/
    └── uploads/
        ├── pdf_RAG/           # PDF do przetworzenia
        ├── pdf_pages/         # Podzielone strony (nowe)
        └── pdf_progress.json  # Status resume (nowe)

Przeczytaj główne pliki .py w folderze ~/KlimtechRAG oraz podfolderch. To są główne pliki z  którymi powionieneś się zapoznać:
~/KlimtechRAG/model_parametr.py
~/KlimtechRAG/stop_klimtech.py
~/KlimtechRAG/start_klimtech.py
~/KlimtechRAG/ingest_pdf.py
~/KlimtechRAG/watch_nextcloud.py
~/KlimtechRAG/backend_app/config.py
~/KlimtechRAG/backend_app/fs_tools.py
~/KlimtechRAG/backend_app/main.py
~/KlimtechRAG/backend_app/monitoring.py
~/KlimtechRAG/backend_app/file_registry.py
~/KlimtechRAG/git_sync/ingest_repo.py


(venv) lobo@hall9000 ~/KlimtechRAG> tree -P "*.txt|*.md|*.py" --prune -L 3
.
├── backend_app
│   ├── config.py
│   ├── file_registry.py
│   ├── fs_tools.py
│   ├── main.py
│   └── monitoring.py
├── data
│   └── nextcloud
│       └── robots.txt
├── git_sync
│   ├── ingest_repo.py
│   ├── opencode
│   │   ├── AGENTS.md
│   │   ├── CONTRIBUTING.md
│   │   ├── README.md
│   │   ├── README.zh-CN.md
│   │   ├── README.zh-TW.md
│   │   ├── SECURITY.md
│   │   ├── STATS.md
│   │   └── STYLE_GUIDE.md
│   └── zizzania
│       └── README.md
├── ingest_pdfCPU.py
├── ingest_pdfGPU.py
├── llama.cpp/build/bin
├── llama-batched
├── llama-batched-bench
├── llama-bench
├── llama-cli
├── llama-completion
├── llama-convert-llama2c-to-ggml
├── llama-cvector-generator
├── llama-debug
├── llama-diffusion-cli
├── llama-embedding
├── llama-eval-callback
├── llama-export-lora
├── llama-finetune
├── llama-fit-params
├── llama-gemma3-cli
├── llama-gen-docs
├── llama-gguf
├── llama-gguf-hash
├── llama-gguf-split
├── llama-idle
├── llama-imatrix
├── llama-llava-cli
├── llama-lookahead
├── llama-lookup
├── llama-lookup-create
├── llama-lookup-merge
├── llama-lookup-stats
├── llama-minicpmv-cli
├── llama-mtmd-cli
├── llama-parallel
├── llama-passkey
├── llama-perplexity
├── llama-q8dot
├── llama-quantize
├── llama-qwen2vl-cli
├── llama-retrieval
├── llama-save-load-state
├── llama-server
├── llama-simple
├── llama-simple-chat
├── llama-speculative
├── llama-speculative-simple
├── llama-tokenize
├── llama-tts
└── llama-vdot


├── model_parametr.py
├── PODSUMOWANIE_SESJI_2026-02-20.md
├── session-ses_387f.md
├── session-ses_3883.md
├── session-ses_3890.md
├── start_klimtech_backup.py
├── start_klimtech.py
├── stop_klimtech.py
├── venv
│   └── bin
│       └── vba_extract.py
├── watch_nextcloud.py
└── zai_wrapper.py

24 directories, 95 files




```

---
---

## 6. 
1. Jeśli trzeba będzie cokolwiek zainstalowac za pomocą apt lub pip w moim środowisku venv podaj komendy do instalacji
2. Nie pokazuj kilku lub kilkunastu komend które musze wykonac bo zdarza się że po już po pierwszej komendzie są błędy i trzeba najpierw rozwiązać jeden problem a później dopiero można zająć sie kolejnymi.
3. w backend_app przeanalizuj pliki .py plik main.py jest za długi a ten czat wogóle nie działa tak jak powinien. Niby pokazuje że ładuje pliki np .txt do bazy a później jak pytam modelu to nie ma dostępu do bazy qdrant. w pliku config.py linie kodu 18-24 po co one są skoro jak używam innego modelu to po co tam jest konkretny model już zdefiniowany. Wracam do początku planu gdzie foldery w nexcloud RAG_Dane... Tam będą wrzucał przez przeglądarkę różne pliki a Doclin lub jeśli plik .pdf to widzę że szybciej pdftotext wyodrębnia tekst. Jeśli chodzi o obrazy to zaraz pobiorę odpowiedni model który bedzie obrabiał obrazy, filmy a inny będzie do głosu na tekst i odwrotnie. Uruchamianie ich będzie odbywać się w tle za pomocą llama.cpp-cli.Będziemy pracować testowo na małych modelach bo na razie mam jedną kartę AMD instinct 16GB tak aby można uruchomić jeden model dla llama.cpp-server a drugi w tle obrabia pliki. Stwórz na podstawie tego co teraz napisałem plan aj go przeczytam i ewentualnie naniosę poprawki 

---

## 7 PLAN WYGENEROWANY LECZ MOŻE ULEDZ ZMIANOM

📋 PLAN RESTRUKTURYZACJI KLIMTECHRAG 
🔴 ZIDENTYFIKOWANE PROBLEMY 
1. main.py (943 linie - MONOLIT) 
Problem
 
  
Linie
 
  
Opis
 
 
Wszystko w jednym pliku 1-943 Routing, pipeline, UI, tools - wszystko wymieszane 
HTML w kodzie 736-935 ~200 linii HTML jako string 
Nowy embedder za każdym razem 563-574 W /v1/chat/completions tworzy nowy embedder zamiast używać pipeline 
Duplikaty modeli Pydantic 172-237 ChatMessage, ChatCompletionRequest etc. 
Web search bez konfiguracji 421-431 DuckDuckGo hardcodowany 
   
2. config.py (Linie 22-24) 
python
 
  
 
llm_model_name: str = "speakleash_Bielik-11B-v3.0-Instruct-Q8_0"
 
 
 

Problem: Sztywna definicja modelu - klient powinien wybierać model przez API! 
3. file_registry.py (Linie 11-31) 
python
 
  
 
DB_PATH = "/home/lobo/KlimtechRAG/data/file_registry.db"
NEXTCLOUD_BASE = "/home/lobo/KlimtechRAG/data/nextcloud/..."
WATCH_DIRS = [f"{UPLOAD_BASE}/Audio_RAG", ...]
 
 
 

Problem: Sztywne ścieżki zamiast z config.py 
4. monitoring.py (Linie 72-108) 

Problem: Zduplikowany kod w get_amd_gpu_stats() - linie 72-108 to kopia 19-67 
5. Problem RAG/Qdrant - DLACZEGO NIE DZIAŁA 

W /v1/chat/completions (linie 563-574): 
python
 
  
 
embedder = SentenceTransformersTextEmbedder(...)  # NOWA instancja!
embedder.warm_up()  # Za każdym razem!
 
 
 

To tworzy nowy embedder przy KAŻDYM żądaniu - wolne i może powodować błędy. 
✅ PROPOZOWANA STRUKTURA 
text
 
  
 
~/KlimtechRAG/backend_app/
├── __init__.py
├── main.py                    # TYLKO routing i app setup (~100 linii)
├── config.py                  # Konfiguracja (bez sztywnego modelu)
│
├── routes/
│   ├── __init__.py
│   ├── chat.py                # /v1/chat/completions, /query
│   ├── ingest.py              # /ingest, /upload
│   ├── filesystem.py          # /fs/list, /fs/glob, /fs/read, /fs/grep
│   ├── admin.py               # /health, /metrics, /documents
│   └── ui.py                  # /, /chat (HTML)
│
├── services/
│   ├── __init__.py
│   ├── qdrant.py              # QdrantDocumentStore singleton
│   ├── embeddings.py          # Embedder singleton (CPU/GPU)
│   ├── llm.py                 # OpenAIGenerator wrapper
│   ├── rag.py                 # RAG pipeline
│   └── web_search.py          # DuckDuckGo search
│
├── ingest/
│   ├── __init__.py
│   ├── base.py                # Klasa bazowa
│   ├── pdf_handler.py         # PDF: pdftotext vs OCR
│   ├── txt_handler.py         # TXT, MD, PY, JSON etc.
│   ├── image_handler.py       # Obrazy → llama.cpp-cli VLM
│   ├── audio_handler.py       # Audio → Whisper
│   └── video_handler.py       # Video → frames + VLM
│
├── models/
│   ├── __init__.py
│   ├── requests.py            # Pydantic request models
│   └── responses.py           # Pydantic response models
│
├── utils/
│   ├── __init__.py
│   ├── rate_limit.py          # Rate limiting
│   └── logging.py             # Request ID filter etc.
│
├── fs_tools.py                # Bez zmian (OK)
├── monitoring.py              # Usunąć duplikat kodu
└── file_registry.py           # Przenieść ścieżki do config
 
 
 
📝 ZADANIA DO WYKONANIA 
Faza 1: Porządkowanie konfiguracji 
#
 
  
Zadanie
 
  
Plik
 
  
Opis
 
 
1.1 Usunąć sztywny model LLM  config.py:24  llm_model_name: str = "" (puste) 
1.2 Dodać ścieżki do config config.py db_path, upload_base, nextcloud_base 
1.3 Dodać konfigurację VLM/Whisper  config.py vlm_model_path, whisper_model_path 
1.4 Usunąć duplikat kodu  monitoring.py:72-108  Usunąć powtórzony blok 
   
Faza 2: Refaktoryzacja main.py 
#
 
  
Zadanie
 
  
Opis
 
 
2.1 Stworzyć services/qdrant.py Singleton QdrantDocumentStore 
2.2 Stworzyć services/embeddings.py Singleton embedder (CPU/GPU) 
2.3 Stworzyć services/rag.py  RAG pipeline z proper retrieval 
2.4 Naprawić /v1/chat/completions Używać singletonów zamiast tworzyć nowe instancje 
2.5 Wydzielić HTML do routes/ui.py  Lub do pliku templates/chat.html 
2.6 Wydzielić modele do models/ Pydantic models 
   
Faza 3: Inteligentny ingest 
#
 
  
Zadanie
 
  
Opis
 
 
3.1 Stworzyć ingest/pdf_handler.py  Wykrywanie warstwy tekstowej + pdftotext 
3.2 Stworzyć ingest/txt_handler.py  Proste pliki tekstowe 
3.3 Stworzyć ingest/image_handler.py  VLM przez llama.cpp-cli (placeholder) 
3.4 Stworzyć ingest/audio_handler.py  Whisper (placeholder) 
3.5 Stworzyć ingest/video_handler.py  Frames + VLM (placeholder) 
   
Faza 4: Naprawa połączenia RAG 
#
 
  
Zadanie
 
  
Opis
 
 
4.1 Debug Qdrant  Sprawdzić czy dokumenty są w bazie 
4.2 Poprawić retrieval  Używać gotowego retrievera z pipeline 
4.3 Dodać logowanie Ile dokumentów znaleziono w Qdrant 
4.4 Test end-to-end Czy model dostaje kontekst? 
   
🎯 PRIORYTET ZADAŃ 
text
 
  
 
┌─────────────────────────────────────────────────────────────┐
│  PILNE (zrobić najpierw):                                    │
│  1. Naprawić RAG - model nie widzi dokumentów!              │
│  2. Usunąć sztywny model z config.py                         │
│  3. Usunąć duplikat kodu w monitoring.py                     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  WAŻNE (refaktoryzacja):                                     │
│  4. Podzielić main.py na moduły                              │
│  5. Stworzyć singleton embeddera                             │
│  6. Przenieść ścieżki do config.py                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  ROZSZERZENIA (ingest):                                      │
│  7. Inteligentny PDF handler (pdftotext vs OCR)             │
│  8. Placeholdery dla VLM/Whisper                             │
└─────────────────────────────────────────────────────────────┘
 
 
 
❓ PYTANIA DO CIEBIE 

    Czy struktura katalogów jest OK? Czy chcesz inne nazwy folderów?  

    Priorytet: Czy najpierw naprawić RAG (dlaczego model nie widzi dokumentów), czy najpierw refaktoryzacja?  

    Modele VLM/Whisper: Czy masz już pobrane modele GGUF do obróbki? Jakie konkretnie?  

    Sztywne ścieżki: Czy /home/lobo/KlimtechRAG/ to stała lokalizacja, czy przenieść do zmiennej środowiskowej?  

Przeczytaj plan i napisz co chcesz zmienić. Potem zaczynamy implementację. 


*Wygenerowane: 2026-02-20*
Zapisano w PODSUMOWANIE_SESJI_2026-02-20.md.
Główne wnioski:
- PDF ma warstwę tekstową → pdftotext działa natychmiast
- Docling OCR jest zbędny i problematyczny dla tego typu PDF
- Baza Qdrant skasowana - gotowa na nowy, poprawny ingest
Następny krok: Stworzyć inteligentny ingest (pdftotext dla PDF z tekstem, OCR tylko dla skanów)?