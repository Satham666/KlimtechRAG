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

```

---

*Wygenerowane: 2026-02-20*
Zapisano w PODSUMOWANIE_SESJI_2026-02-20.md.
Główne wnioski:
- PDF ma warstwę tekstową → pdftotext działa natychmiast
- Docling OCR jest zbędny i problematyczny dla tego typu PDF
- Baza Qdrant skasowana - gotowa na nowy, poprawny ingest
Następny krok: Stworzyć inteligentny ingest (pdftotext dla PDF z tekstem, OCR tylko dla skanów)?