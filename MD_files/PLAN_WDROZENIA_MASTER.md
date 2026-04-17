# PLAN WDROŻENIA MASTER — KlimtechRAG

**Wersja:** 1.0  
**Data:** 2026-03-30  
**Źródła:** PrivateGPT, LocalGPT, h2oGPT, RAGFlow, Quivr, Danswer, DocQuery, AnythingLLM  
**Repozytorium:** https://github.com/Satham666/KlimtechRAG

---

## CEL DOKUMENTU

Jeden plan rozwoju KlimtechRAG — skonsolidowany z trzech źródeł:
- `KATALOG_FUNKCJI_DO_WDROZENIA.md` — 34 funkcje z 7 projektów open-source
- `PLAN_PRIVATEGPT_DO_KLIMTECHRAG.md` — 8 faz z atomowymi krokami (wzorce PrivateGPT)
- Nowe funkcje z **AnythingLLM** — 6 dodatkowych (W1–W6)

Każda funkcja ma: opis, priorytet, zależności, atomowe kroki, szacowany nakład pracy.

---

## LEGENDA

| Symbol | Znaczenie |
|--------|-----------|
| 🔴 | Krytyczne — bezpośrednio poprawia jakość lub stabilność |
| 🟡 | Wartościowe — poprawia UX, ułatwia rozwój |
| 🟢 | Nice-to-have — usprawnienie, system działa bez tego |
| ⚪ | Na przyszłość — wymaga dużo pracy lub zmiany architektury |
| 🆕 | Nowa pozycja z AnythingLLM |
| ⏱️ | Szacowany czas (dni robocze jednego developera) |

---

## ANALIZA ZALEŻNOŚCI I KOLEJNOŚCI

### Dlaczego ta kolejność?

Kolejność wynika z trzech kryteriów:

1. **Zależności techniczne** — SSE streaming (D1) musi być przed UI streaming (F1). Restrukturyzacja kodu (A1) ułatwia WSZYSTKO co po niej.
2. **Stosunek korzyść/ryzyko** — Vector Cache (W3) daje ogromną oszczędność VRAM przy minimalnym ryzyku. Smart Router (B1) eliminuje crashe z przekroczonym kontekstem.
3. **Efekt kumulacyjny** — Sprint 1 buduje fundamenty (streaming + architektura), Sprint 2 poprawia jakość RAG, Sprint 3 dodaje zarządzanie i UX.

### Graf zależności (kluczowe)

```
A1 (Restrukturyzacja) ──→ Ułatwia: B1, B2, B3, B6, D1, G1
D1 (SSE Streaming backend) ──→ F1 (Streaming UI)
B7 (/v1/chunks) ──→ F2 (Podgląd źródeł)
E1 (DELETE /v1/ingest) ──→ F3 (Panel dokumentów)
W3 (Vector Cache) ──→ niezależny, wdrażaj wcześnie
W1 (Workspaces) ──→ zależy od E3 (Multi-collection)
```

---

## SPRINT 0 — QUICK WINS (1–2 dni) 🔴

Natychmiastowe usprawnienia bez ryzyka. Zero zależności.

### W3. Vector Cache — skip re-embedding 🆕 🔴
**Źródło:** AnythingLLM  
**Problem:** Przy 16 GB VRAM każdy re-embedding to 2.5 GB + kilka minut. Jeśli plik nie zmienił się (ten sam SHA256), embedding jest identyczny — ale system i tak go liczy od nowa.  
**Stan obecny:** KlimtechRAG ma SHA256 dedup plików w `file_registry.db` — ale tylko na poziomie "czy plik już był uploadowany". Brak cache samych wektorów.

**Co wdrożyć:**
- Rozszerzenie `file_registry.db` o kolumnę `content_hash` (SHA256 treści po chunking) ✅ DONE
- Przed embedding: sprawdź czy identyczny hash już istnieje w Qdrant
- Jeśli tak → skip embedding, zwróć "cached"
- Jeśli nie → normalny pipeline

**Kroki atomowe:**
1. Dodaj kolumnę `content_hash TEXT` do `file_registry.db` (migracja SQLite)
2. W `ingest.py` / `ingest_service.py`: po chunking oblicz SHA256 z połączonych chunków
3. Przed embedding sprawdź: `SELECT 1 FROM file_registry WHERE content_hash = ?`
4. Jeśli istnieje i punkty są w Qdrant → skip, log "Vector cache hit"
5. Jeśli nie → normalny embedding + zapis hash
6. Test: zaindeksuj PDF, zaindeksuj ponownie → "cached", brak GPU load

**Korzyść:** Eliminuje zbędne ładowanie e5-large (2.5 GB VRAM) dla plików, które już są zaindeksowane. Masowy re-ingest (np. po aktualizacji backendu) trwa sekundy zamiast godzin.  
**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 1 dzień**

---

### A3. Walidacja konfiguracji na starcie 🟡
**Źródło:** PrivateGPT, LocalGPT  
**Problem:** Backend startuje i dopiero pada gdy brakuje Qdrant lub katalogu modeli.

**Co wdrożyć:**
- Funkcja `validate_config()` w `lifespan()` main.py
- Sprawdza: Qdrant dostępny? Katalog modeli istnieje? `.env` istnieje? Porty wolne?
- Czytelny komunikat błędu zamiast stack trace

**Kroki atomowe:**
1. Dodaj funkcję `validate_config()` w `config.py`
2. Sprawdź: Qdrant ping, katalog modeli, .env, porty (8000, 8082 wolne)
3. Wywołaj w `lifespan()` — jeśli fail → czytelny błąd + `sys.exit(1)`
4. Test: odpal backend bez Qdrant → czytelny komunikat

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 0.5 dnia**

---

## SPRINT 1 — FUNDAMENTY (tydzień 1–2) 🔴

Restrukturyzacja kodu + streaming — fundament pod wszystko inne.

### A1. Restrukturyzacja: Router → Service → Component 🔴
**Źródło:** PrivateGPT, Quivr  
**Problem:** `chat.py` (~277 linii, było 500) i `ingest.py` (~548 linii, było 767) — refaktoryzacja A1a/A1b częściowo wykonana, ale routing wciąż miesza się z logiką biznesową.

#### A1a. Wydzielenie warstwy Service z `routes/chat.py`

```
PRZED:
  routes/chat.py (500 linii — wszystko)

STAN OBECNY (częściowe A1a):
  routes/chat.py              (277 linii — cel ~80, wymaga dalszej pracy)
  services/chat_service.py    ✅ istnieje
  services/retrieval_service.py ✅ istnieje
  services/prompt_service.py  ✅ istnieje
  services/cache_service.py   ✅ istnieje (+ semantic cache B6)
```

**Kroki atomowe:**
1. Utwórz `backend_app/services/cache_service.py` — przenieś `_answer_cache`, `get_cached()`, `set_cached()`, `clear_cache()`
2. Utwórz `backend_app/services/retrieval_service.py` — przenieś logikę retrieval (blok `if request.use_rag` + `if request.web_search`)
3. Utwórz `backend_app/services/prompt_service.py` — przenieś `RAG_PROMPT` i budowanie `full_prompt`
4. Utwórz `backend_app/services/chat_service.py` — orkiestracja: cache → retrieval → prompt → LLM → response
5. Refaktoryzuj `routes/chat.py` — zamień ciało endpointów na wywołania `chat_service`
6. Zaktualizuj importy w `services/__init__.py`
7. Test: `curl -sk -X POST https://192.168.31.70:8443/v1/chat/completions -d '{"messages":[{"role":"user","content":"hej"}]}'`

**Trudność:** Średnia | **Ryzyko:** Niskie (czysta refaktoryzacja, bez zmiany logiki) | **⏱️ 2 dni**

#### A1b. Wydzielenie warstwy Service z `routes/ingest.py`

```
PRZED:
  routes/ingest.py (767 linii — wszystko)

STAN OBECNY (częściowe A1b):
  routes/ingest.py              (548 linii — cel ~120, wymaga dalszej pracy)
  services/parser_service.py    ✅ istnieje
  services/ingest_service.py    ✅ istnieje
  services/nextcloud_service.py ✅ istnieje
  services/dedup_service.py     ✅ istnieje
```

**Kroki atomowe:**
1. Utwórz `services/parser_service.py` — przenieś `extract_pdf_text()`, `parse_with_docling()`, `read_text_file()`, `clean_text()`
2. Utwórz `services/nextcloud_service.py` — przenieś `save_to_nextcloud()`, `rescan_nextcloud()`, `EXT_TO_DIR`
3. Utwórz `services/dedup_service.py` — przenieś `_hash_bytes()`, logikę deduplikacji
4. Utwórz `services/ingest_service.py` — orkiestracja: parse → pipeline → Qdrant
5. Refaktoryzuj `routes/ingest.py` — endpointy wywołują `ingest_service`
6. Test: upload pliku PDF przez UI, sprawdź `/files/stats`

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

### D1. SSE Streaming odpowiedzi (token-by-token) 🔴
**Źródło:** PrivateGPT, Danswer, LocalGPT  
**Problem:** `stream: bool = False` w schema istnieje, ale streaming NIE jest zaimplementowany. Użytkownik czeka 10–30s na pełną odpowiedź.  
**Zależność:** Łatwiejsze po A1a (chat_service wydzielony), ale możliwe bez tego.

**Co wdrożyć:**
```
POST /v1/chat/completions {"messages": [...], "stream": true}
→ Response: Server-Sent Events w formacie OpenAI
data: {"id":"chatcmpl-1","choices":[{"delta":{"content":"Cz"}}]}
data: [DONE]
```

**Kroki atomowe:**
1. Dodaj `StreamingResponse` import do `routes/chat.py` (lub `services/chat_service.py`)
2. Zmodyfikuj endpoint — branch na `request.stream`
3. Dla streaming: `httpx.AsyncClient` z `stream=True` do llama-server
4. Przekazuj chunki jako SSE events w formacie OpenAI
5. Test: `curl -sk -N -X POST .../v1/chat/completions -d '{"messages":[...],"stream":true}'`

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

### F1. Streaming w UI (token-by-token rendering) 🔴
**Źródło:** Danswer, LocalGPT  
**Zależność:** D1 (SSE streaming w backendzie)

**Kroki atomowe:**
1. Zmień `send()` w `index.html` — gdy `stream: true`, użyj `fetch` z `body.getReader()`
2. Renderuj tokeny incrementalnie w bańce czatu
3. Dodaj animację typing opartą na realnych tokenach
4. Test: wyślij pytanie, obserwuj token-by-token

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 1.5 dnia**

---

### B1. Smart Router — automatyczny RAG vs Direct LLM 🔴
**Źródło:** LocalGPT  
**Problem:** Użytkownik musi ręcznie włączać RAG przyciskiem globe. "hej bielik" z RAG = 78000 tokenów i crash.

**Co wdrożyć:**
- Heurystyka decyduje czy pytanie wymaga RAG:
  - Pytanie < 20 słów i nie zawiera słów kluczowych dokumentów → Direct LLM
  - Pytanie odwołuje się do dokumentów/danych/raportów → RAG
  - Użytkownik nadal może wymusić RAG przyciskiem globe

**Kroki atomowe:**
1. Utwórz `services/router_service.py` z funkcją `should_use_rag(query: str) -> bool`
2. Heurystyka: długość, słowa kluczowe (dokument, raport, specyfikacja, norma, procedura)
3. Opcjonalnie: lekki prompt do LLM ("Czy to pytanie wymaga kontekstu z dokumentów?")
4. Podepnij w `chat_service.py` — jeśli `use_rag` nie wymuszony ręcznie → auto-routing
5. Test: "hej" → Direct, "co mówi raport o temperaturze?" → RAG

**Trudność:** Niska | **Ryzyko:** Niskie | **⏱️ 1 dzień**

---

## SPRINT 2 — JAKOŚĆ RAG (tydzień 3–4) 🔴/🟡

### B2. Hybrid Search (dense + sparse/BM25) 🔴
**Źródło:** LocalGPT, RAGFlow  
**Problem:** Tylko dense vector search (e5-large). Pytanie z dokładną nazwą techniczną może nie trafić.

**Co wdrożyć:**
- BM25 index obok Qdrant vector search
- Hybrid scoring: `final_score = 0.7 * dense_score + 0.3 * bm25_score`
- Konfigurowalny weight

**Kroki atomowe:**
1. Zainstaluj `rank_bm25` lub użyj Qdrant built-in sparse vectors
2. Przy ingeście: oprócz dense embedding, buduj BM25 index (albo sparse vector w Qdrant)
3. Przy query: dwa retrieval → merge wyników → sort po `final_score`
4. Konfigurowalny weight w `.env`: `KLIMTECH_BM25_WEIGHT=0.3`
5. Test: pytanie z dokładnym terminem technicznym — sprawdź czy BM25 poprawia wyniki

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

### B3. Reranking po retrieval 🟡
**Źródło:** LocalGPT, RAGFlow  
**Problem:** Top-5 chunków z Qdrant idzie prosto do promptu. Kolejność oparta tylko na cosine similarity.

**Co wdrożyć:**
- Po retrieval top-20 → reranker (cross-encoder) → top-5 do promptu
- Model: `BAAI/bge-reranker-base` (~400 MB) — lazy loading

**Kroki atomowe:**
1. Dodaj `bge-reranker-base` do `requirements.txt`
2. Utwórz `services/reranker_service.py` — lazy singleton, cross-encoder
3. W `retrieval_service.py`: retrieval top-20 → reranker → top-5
4. Konfigurowalny: `KLIMTECH_RERANKER_ENABLED=true`
5. Test: porównaj jakość odpowiedzi z/bez rerankera

**Trudność:** Średnia | **Ryzyko:** Niskie (lazy loading, osobny model) | **⏱️ 1.5 dnia**

---

### C1. Layout Analysis — rozpoznawanie struktury PDF 🔴
**Źródło:** RAGFlow (DeepDoc), DocQuery  
**Problem:** `pdftotext -layout` + docling OCR. Tabela, diagram, nagłówek, stopka — traktowane jednakowo.

**Co wdrożyć:**
- Klasyfikacja regionów strony: tekst, tabela, obraz, nagłówek, stopka
- Tabele → osobny parser (Table Structure Recognition)
- Obrazy → VLM pipeline (vlm_prompts.py)
- Nagłówki/stopki → metadane, nie treść chunku

**Kroki atomowe:**
1. Zbadaj dostępne modele layout analysis (LayoutLMv3, RAGFlow DeepDoc, docling layout)
2. Utwórz `services/layout_service.py` — klasyfikacja regionów
3. Podepnij w `parser_service.py` — routing: tekst → chunking, tabela → table parser, obraz → VLM
4. Test: PDF z tabelami i obrazami → sprawdź jakość chunków

**Trudność:** Wysoka | **Ryzyko:** Średnie (nowy model, VRAM) | **⏱️ 3–5 dni**

---

### C6. Metadata extraction przy ingeście 🟡
**Źródło:** PrivateGPT, Danswer  
**Problem:** Chunk ma tylko `source` i `type`. Brak tytułu, autora, daty, języka.

**Co wdrożyć:**
```python
metadata = {
    "source": "raport.pdf",
    "title": "Raport kwartalny Q3",     # z metadanych PDF
    "page_count": 45,
    "language": "pl",                     # detekcja języka
    "chunk_index": 12,
    "total_chunks": 45,
    "indexed_at": "2026-03-21T14:30:00Z"
}
```

**Kroki atomowe:**
1. Utwórz `services/metadata_service.py` — ekstrakcja z PyMuPDF (PDF) / mammoth (DOCX)
2. Dodaj detekcję języka (langdetect lub heurystyka pl/en)
3. Rozszerz `Document.meta` przy tworzeniu chunków
4. Test: zaindeksuj PDF, sprawdź `/rag/debug` → metadane w payload

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 1 dzień**

---

### C4. Contextual Enrichment — wzbogacanie chunków 🟡
**Źródło:** LocalGPT (inspirowane Anthropic Contextual Retrieval)  
**Problem:** Chunk "Wartość wynosi 45%" nie mówi o czym jest — brak kontekstu dokumentu.

**Co wdrożyć:**
- Przy ingeście: LLM generuje krótki opis kontekstu chunku
- Format: `"Chunk z rozdziału 3 dokumentu X — wyniki badań temperatury"`
- Opis + chunk przechowywane razem w Qdrant

**Uwaga:** Wymaga działającego LLM przy ingeście. Rozważ użycie małego modelu (4.5B) lub batch processing.

**Kroki atomowe:**
1. Utwórz `services/enrichment_service.py` — generowanie kontekstu per chunk
2. Prompt: "Opisz w 1 zdaniu kontekst tego fragmentu dokumentu: {chunk}"
3. W `ingest_service.py`: po chunking → enrichment → embedding (embed chunk + kontekst)
4. Konfigurowalny: `KLIMTECH_CONTEXTUAL_ENRICHMENT=false` (domyślnie OFF, bo wymaga LLM)
5. Test: zaindeksuj z enrichment, porównaj jakość retrieval

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

## SPRINT 3 — API I ZARZĄDZANIE (tydzień 5–6) 🟡

### B7. Endpoint `/v1/chunks` — Low-level retrieval bez LLM 🟡
**Źródło:** PrivateGPT, Danswer

**Co wdrożyć:**
```
POST /v1/chunks
{"text": "pytanie", "limit": 10, "context_filter": {"source": "raport.pdf"}}
→ chunki z score, source, content (BEZ LLM)
```

**Kroki atomowe:**
1. Dodaj `ChunksRequest` i `ChunksResponse` do `models/schemas.py`
2. Utwórz `routes/chunks.py` z endpointem `/v1/chunks`
3. Logika: embed pytanie → retrieval z Qdrant → zwróć chunki z metadanymi
4. Zarejestruj router w `main.py`
5. Test: `curl -sk -X POST .../v1/chunks -d '{"text":"co to RAG","limit":5}'`

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 1 dzień**

---

### E1. Endpoint `DELETE /v1/ingest/{doc_id}` 🟡
**Źródło:** PrivateGPT, Quivr

**Co wdrożyć:**
```
DELETE /v1/ingest/{doc_id}
→ Usuwa chunki z Qdrant (filter: meta.source == doc_id)
→ Aktualizuje file_registry.db
→ Opcjonalnie: ?delete_file=true
```

**Kroki atomowe:**
1. Dodaj endpoint `DELETE /v1/ingest/{doc_id}` do `routes/admin.py`
2. Usuwanie z Qdrant (filter po `meta.source`)
3. Usuwanie z `file_registry.db`
4. Parametr `?delete_file=true` — usuwa plik źródłowy
5. Test: zaindeksuj → usuń → sprawdź Qdrant

**Trudność:** Niska | **Ryzyko:** Niskie | **⏱️ 1 dzień**

---

### E2. Endpoint `/v1/ingest/list` z metadanymi 🟡
**Źródło:** PrivateGPT, Danswer

**Co wdrożyć:**
```
GET /v1/ingest/list?status=indexed&source=raport.pdf
→ doc_id, source, status, chunks_count, embedding_model, indexed_at
```

**Kroki atomowe:**
1. Dodaj endpoint `GET /v1/ingest/list` do `routes/admin.py`
2. Query `file_registry.db` → format OpenAI-style
3. Filtry: status, source, extension
4. Test

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 0.5 dnia**

---

### H1. Standaryzacja response format (OpenAI-compatible) 🟡
**Źródło:** PrivateGPT, Danswer  
**Problem:** `/upload`, `/ingest_path`, `/ingest_all` — każdy zwraca inny format.

**Co wdrożyć:**
```python
# Jednolity IngestResponse dla WSZYSTKICH endpointów ingest:
{
    "object": "ingest.result",
    "data": [{
        "doc_id": "sha256_abc123",
        "source": "raport.pdf",
        "status": "indexed",       # indexed | skipped | error | duplicate | cached
        "chunks_count": 45,
        "collection": "klimtech_docs"
    }]
}
```

**Kroki atomowe:**
1. Dodaj `IngestResponse` schema do `models/schemas.py`
2. Refaktoryzuj return statements w `/upload`, `/ingest_path`, `/ingest_all`
3. Test: upload → sprawdź nowy format

**Trudność:** Niska | **Ryzyko:** Niskie (breaking change dla klientów API — ale jedyny klient to własny UI) | **⏱️ 1 dzień**

---

### F2. Podgląd źródeł w odpowiedzi czatu 🟡
**Źródło:** PrivateGPT, Danswer, LocalGPT  
**Zależność:** B7 (/v1/chunks) dla podglądu pełnego chunku

**Kroki atomowe:**
1. Backend: upewnij się że `sources` w `ChatCompletionResponse` zawiera dane (nazwa, strona, score)
2. UI: po odpowiedzi AI → klikalna lista źródeł pod odpowiedzią
3. Kliknięcie źródła → podgląd chunku (wywołanie `/v1/chunks`)
4. Ikona 📎 z liczbą źródeł
5. Test: włącz RAG, zadaj pytanie → źródła widoczne

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 1.5 dnia**

---

### F3. Panel zarządzania dokumentami RAG 🟡
**Źródło:** PrivateGPT, LocalGPT, Quivr  
**Zależność:** E1 (DELETE endpoint), E2 (/v1/ingest/list)

**Kroki atomowe:**
1. Nowa karta w sidebar UI: "Dokumenty RAG"
2. Tabela: source, chunks, status, data, rozmiar
3. Przycisk "Usuń z RAG" → `DELETE /v1/ingest/{doc_id}`
4. Przycisk "Re-indeksuj" → `POST /ingest_path`
5. Filtrowanie po statusie
6. Test: wyświetl listę, usuń dokument, sprawdź `/files/stats`

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

## SPRINT 4 — ZAAWANSOWANE RAG (tydzień 7–8) 🟡/🟢

### B6. Semantic Cache z similarity matching 🟡
**Źródło:** LocalGPT  
**Problem:** Cache w `chat.py` jest dict z exact match. "Co to RAG?" i "Czym jest RAG?" → dwa różne klucze.

**Co wdrożyć:**
- Cache przechowuje embedding pytania + odpowiedź
- Nowe pytanie → embedding → cosine similarity z cached
- Jeśli similarity > 0.92 → cached odpowiedź
- TTL (1h) + limit rozmiaru

**Kroki atomowe:**
1. Rozszerz `cache_service.py` — dodaj embedding cache (numpy array + odpowiedź)
2. Przy nowym pytaniu: embed → cosine similarity z cached embeddings
3. Próg: `KLIMTECH_CACHE_SIMILARITY_THRESHOLD=0.92`
4. Limit: max 100 cached pytań, FIFO eviction
5. Test: "Co to RAG?" → odpowiedź, "Czym jest RAG?" → cache hit

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 1.5 dnia**

---

### B4. Query Decomposition — rozbijanie złożonych pytań 🟡
**Źródło:** LocalGPT  
**Problem:** Złożone pytanie idzie jako jedno zapytanie do Qdrant.

**Co wdrożyć:**
- LLM rozbija pytanie na 2–3 sub-pytania
- Każde sub-pytanie → osobny retrieval → merge wyników

**Kroki atomowe:**
1. Dodaj `services/query_decomposition_service.py`
2. Prompt: "Rozbij to pytanie na 2-3 prostsze pod-pytania: {query}"
3. Każde sub-pytanie → retrieval → deduplikacja chunków → merge
4. Konfigurowalny: `KLIMTECH_QUERY_DECOMPOSITION=false` (domyślnie OFF)
5. Test: "Porównaj temperaturę w raporcie A z B" → dwa retrieval, merge

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 1.5 dnia**

---

### C2. Automatyczna klasyfikacja typu treści dla VLM 🟡
**Źródło:** RAGFlow, DocQuery  
**Problem:** `vlm_prompts.py` ma 8 wariantów ale `image_handler.py` używa prostej heurystyki.

**Co wdrożyć:**
- Klasyfikator obrazu: heurystyka oparta na OCR text density, color variance, aspect ratio
- Wynik → odpowiedni prompt z `vlm_prompts.py`

**Kroki atomowe:**
1. W `image_handler.py`: dodaj `classify_image_type(image_bytes) -> str`
2. Heurystyka: OCR text length, unique colors, aspect ratio
3. Mapowanie: dużo tekstu → SCREENSHOT/TABLE, mało kolorów → DIAGRAM, kolorowe → PHOTO
4. Podepnij wynik do `vlm_prompts.py` → odpowiedni prompt
5. Test: tabela z PDF → prompt TABLE, zdjęcie → prompt PHOTO

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 1 dzień**

---

### C3. Table Structure Recognition (TSR) 🟡
**Źródło:** RAGFlow (DeepDoc)  
**Problem:** Tabele z PDF parsowane jako surowy tekst — tracą strukturę.

**Co wdrożyć:**
- Rozpoznawanie tabeli → konwersja do Markdown table
- Chunk z `type: table` w metadanych

**Kroki atomowe:**
1. Zbadaj: `camelot-py`, `tabula-py`, lub PyMuPDF table extraction
2. Utwórz `services/table_service.py` — PDF page → wykryte tabele → Markdown
3. W `parser_service.py`: po layout analysis → tabele do `table_service`
4. Chunk Markdown table z meta `{"type": "table", "page": N}`
5. Test: PDF z tabelą cennikową → chunk zawiera czytelną tabelę

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

### W1. Workspaces — izolowane konteksty RAG 🆕 🟡
**Źródło:** AnythingLLM  
**Problem:** Wszystkie dokumenty trafiają do jednej kolekcji `klimtech_docs`. Użytkownik nie może stworzyć tematycznej bazy (np. "medyczne", "techniczne", "HR") i przeszukiwać tylko wybranej.  
**Zależność:** E3 (Multi-collection management)

**Co wdrożyć:**
- Koncept "Workspace" = nazwana kolekcja Qdrant + UI do zarządzania
- API: `POST /workspaces`, `GET /workspaces`, `DELETE /workspaces/{name}`
- W `/v1/chat/completions`: parametr `workspace` → przeszukuj tylko tę kolekcję
- UI: dropdown z dostępnymi workspace'ami w panelu czatu
- Domyślny workspace: `klimtech_docs` (backward compatible)

**Kroki atomowe:**
1. Dodaj `WorkspaceCreate` schema do `models/schemas.py`
2. Utwórz `routes/workspaces.py` — CRUD endpointy
3. W `services/retrieval_service.py`: parametr `collection` → routing do odpowiedniej kolekcji
4. W UI: dropdown "Workspace" obok przycisków RAG/Web
5. Dodaj `workspace_id` do `file_registry.db`
6. Test: utwórz workspace "medyczne", zaindeksuj PDF → query trafia tylko tam

**Uwaga:** Każdy workspace = osobna kolekcja Qdrant z tymi samymi wymiarami (1024 dla e5-large). ColPali workspace'y to osobna logika (128 dim).

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 3 dni**

---

### E3. Multi-collection management w API 🟢
**Źródło:** Quivr  
**Uzupełnia:** W1 (Workspaces)

**Co wdrożyć:**
- `POST /collections` — utwórz kolekcję
- `GET /collections` — lista z stats
- `DELETE /collections/{name}` — usuń kolekcję

**Kroki atomowe:**
1. Utwórz `routes/collections.py`
2. Create: sprawdź wymiar, utwórz w Qdrant
3. List: stats z Qdrant (points_count, indexed_vectors)
4. Delete: walidacja (nie pozwól usunąć `klimtech_docs` bez flagi `?force=true`)
5. Test: CRUD kolekcji przez API

**Trudność:** Niska | **Ryzyko:** Niskie | **⏱️ 1 dzień**

---

## SPRINT 5 — DEVOPS I KONFIGURACJA (tydzień 9–10) 🟡/🟢

### A2. Profile konfiguracyjne YAML 🟡
**Źródło:** PrivateGPT

**Co wdrożyć:**
```
settings.yaml              — bazowa konfiguracja
settings-server.yaml       — produkcja (GPU, Bielik-11B)
settings-ingest.yaml       — tryb ingest (GPU embedding, bez LLM)
settings-dev.yaml          — laptop (CPU, mały model)
Env var: KLIMTECH_PROFILES=server
```

**Kroki atomowe:**
1. Utwórz `settings.yaml` z bazową konfiguracją (port, LLM, embedding, Qdrant, RAG)
2. Utwórz `settings-server.yaml` z nadpisaniami
3. Zmodyfikuj `config.py` — ładowanie YAML z merge (YAML > .env)
4. Dodaj `KLIMTECH_PROFILES` env var
5. Zachowaj kompatybilność z `.env`
6. Test: `KLIMTECH_PROFILES=server python3 -m backend_app.main`

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

### G1. Struktura testów z mockami 🟡
**Źródło:** PrivateGPT

**Co wdrożyć:**
```
tests/
├── conftest.py          — fixtures (TestClient, mock Qdrant, mock LLM)
├── test_health.py       — smoke tests
├── test_chat.py         — chat z mock LLM
├── test_ingest.py       — ingest z mock Qdrant
├── test_chunks.py       — /v1/chunks
└── test_security.py     — auth, rate limiting, path traversal
```

**Kroki atomowe:**
1. Zainstaluj `pytest`, `httpx` w venv
2. Utwórz `tests/conftest.py` z `TestClient(app)` i mockami
3. Utwórz `tests/test_health.py` — smoke tests
4. Utwórz `tests/test_security.py` — auth bypass, path traversal
5. Dodaj do `scripts/check_project.sh`

**Trudność:** Średnia | **Ryzyko:** Brak | **⏱️ 2 dni**

---

### G3. System health check (diagnostyka runtime) 🟡
**Źródło:** LocalGPT  
**Problem:** `check_project.sh` sprawdza składnię ale nie runtime.

**Co wdrożyć:**
- Skrypt `scripts/health_check.py` sprawdzający: Python, venv, porty, Qdrant, llama-server, GPU
- Kolorowy output: ✅ OK / ❌ FAIL / ⚠️ WARN

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 1 dzień**

---

### G2. Makefile z komendami 🟢
**Źródło:** PrivateGPT, LocalGPT

```makefile
run:      python3 -m backend_app.main
test:     python3 -m pytest tests/ -v
check:    bash scripts/check_project.sh
lint:     python3 -m ruff check backend_app/
start:    python3 start_klimtech_v3.py
stop:     python3 stop_klimtech.py
health:   curl -sk https://192.168.31.70:8443/health
```

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 0.5 dnia**

---

### G4. Swagger/OpenAPI z pełnymi opisami 🟢
**Źródło:** PrivateGPT

**Kroki atomowe:**
1. Dodaj `description`, `summary`, `tags` do KAŻDEGO endpointu
2. Przykładowe request/response body
3. `app = FastAPI(title="KlimtechRAG API", version="7.7")` ✅ DONE
4. Test: `https://192.168.31.70:8443/docs`

**Trudność:** Niska | **Ryzyko:** Brak | **⏱️ 1 dzień**

---

## SPRINT 6 — ARCHITEKTURA ZAAWANSOWANA (tydzień 11+) 🟢/⚪

### A1c. Component Layer (wzorzec PrivateGPT) 🟢
**Źródło:** PrivateGPT  
**Zależność:** A1a + A1b ukończone

```
backend_app/components/
├── llm_component.py        — wrapper na llama-server
├── embedding_component.py  — wrapper na e5-large (lazy)
├── colpali_component.py    — wrapper na ColPali (lazy)
├── vectorstore_component.py — wrapper na Qdrant
└── whisper_component.py    — wrapper na Whisper STT
```

**Zasada:** Component = singleton z lazy loading + `unload()`. Service używa Component.

**Kroki atomowe:**
1. Utwórz `backend_app/components/__init__.py`
2. Przenieś `services/llm.py` → `components/llm_component.py`
3. Przenieś `services/embeddings.py` → `components/embedding_component.py`
4. Przenieś `services/colpali_embedder.py` → `components/colpali_component.py`
5. Przenieś `services/qdrant.py` → `components/vectorstore_component.py`
6. Zaktualizuj WSZYSTKIE importy
7. Test: pełny restart, sprawdź `/health`, `/gpu/status`

**Trudność:** Wysoka | **Ryzyko:** Średnie (masowa zmiana importów) | **⏱️ 3 dni**

---

### B5. Answer Verification 🟢 ✅ DONE
**Źródło:** LocalGPT

**Zaimplementowane:**
- `services/verification_service.py` — `verify_answer()`, flaga `KLIMTECH_ANSWER_VERIFICATION=false` (domyślnie OFF)

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 1.5 dnia**

---

### C5. Late Chunking 🟢
**Źródło:** LocalGPT (inspirowane Jina AI)  
**Problem:** Chunking → embedding. Chunk traci kontekst sąsiadów.

**Co wdrożyć:**
- Embedding CAŁEGO dokumentu (long-context model) → chunking embeddingów po fakcie
- Wymaga modelu z dużym kontekstem (Jina Embeddings v3)

**Uwaga:** Wymaga dużo VRAM. Rozważ jako opcjonalny tryb dla krótkich dokumentów.

**Trudność:** Wysoka | **Ryzyko:** Średnie (VRAM) | **⏱️ 3 dni**

---

### D2. Streaming postępu ingestu (per-chunk) 🟢 ✅ DONE
**Źródło:** RAGFlow, LocalGPT

**Zaimplementowane:**
- `services/progress_service.py` — SSE generator `stream_progress(task_id)`
- `POST /ingest/start` → zwraca `task_id`
- `GET /ingest/progress/{task_id}` → SSE stream z etapami

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 1.5 dnia**

---

### F4. Session-aware chat z persistent history 🟢 ✅ DONE
**Źródło:** LocalGPT, Danswer

**Zaimplementowane:**
- `routes/sessions.py` — pełny CRUD + wiadomości, eksport MD/JSON, import, bulk-delete, search, cleanup, export-all

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

### H2. Watcher zintegrowany z backendem 🟢 ✅ DONE
**Źródło:** PrivateGPT

**Zaimplementowane:**
- `services/watcher_service.py` — asyncio background task
- `GET /v1/watcher/status` — status (enabled, interval, watched dirs)

**Trudność:** Średnia | **Ryzyko:** Średnie | **⏱️ 2 dni**

---

### W2. MCP Compatibility 🆕 🟡 ✅ DONE
**Źródło:** AnythingLLM

**Zaimplementowane:**
- `routes/mcp.py` — `GET /mcp` discovery endpoint (endpoint, protocol_version, tools_count, tools_preview)

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 3 dni**

---

### W4. Embeddable Chat Widget 🆕 🟢
**Źródło:** AnythingLLM

**Co wdrożyć:**
- `<script src="klimtech-widget.js">` — embed chat na dowolnej stronie w sieci lokalnej
- Widget komunikuje się z backendem przez API
- Konfigurowalny: workspace, styl, placeholder

**Trudność:** Średnia | **Ryzyko:** Brak | **⏱️ 2 dni**

---

### W5. Batch Processing dużych dokumentów 🆕 🟡 ✅ DONE
**Źródło:** AnythingLLM, RAGFlow

**Zaimplementowane:**
- `services/batch_service.py` — asyncio PriorityQueue, retry z exponential backoff
- Endpointy: `GET /v1/batch/stats`, `POST /v1/batch/enqueue`, `POST /v1/batch/clear`, `GET /v1/batch/history`

**Trudność:** Średnia | **Ryzyko:** Niskie | **⏱️ 2 dni**

---

### W6. No-code Agent Builder 🆕 🟢
**Źródło:** AnythingLLM  
**Uwaga:** KlimtechRAG ma już n8n do automatyzacji. Agent Builder dodałby UI do konfigurowania agentów RAG (np. "przeszukaj workspace X, potem Y, porównaj").

**Co wdrożyć:**
- UI do tworzenia prostych workflow: wybierz workspace → pytanie → tool → output
- Backend: kompozycja chain z istniejących services

**Trudność:** Wysoka | **Ryzyko:** Średnie | **⏱️ 5 dni** | Rozważ czy n8n nie pokrywa tego use case

---

## PODSUMOWANIE — HARMONOGRAM

| Sprint | Status | Funkcje |
|--------|--------|---------|
| **0** | ✅ DONE | W3 (Vector Cache), A3 (Walidacja config) |
| **1** | ✅ DONE (częściowe A1a/A1b) | A1a+A1b (Restrukturyzacja), D1+F1 (Streaming), B1 (Smart Router) |
| **2** | ✅ DONE | B2 (Hybrid Search), B3 (Reranking), C1 (Layout), C6 (Metadata), C4 (Enrichment) |
| **3** | ✅ DONE | B7 (/chunks), E1 (DELETE), E2 (list), H1 (response format), F2+F3 (UI źródła+panel) |
| **4** | ✅ DONE | B6 (Semantic Cache), B4 (Decomposition), C2+C3 (VLM+TSR), W1+E3 (Workspaces) |
| **5** | ✅ DONE (częściowe G1) | A2 (YAML), G1 (Testy), G3 (Health check), G2+G4 (Makefile+Swagger) |
| **6** | ⚠️ CZĘŚCIOWO | A1c (Components ❌), B5 ✅, C5 ?, D2 ✅, F4 ✅, H2 ✅, W2 ✅, W4 ❌, W5 ✅, W6 ❌ |

**Stan na 2026-04-07:** Sprint 0–5 ukończone. Sprint 6: większość wdrożona poza A1c (components/), W4 (widget), W6 (agent builder).  
**Pozostałe do zrobienia:** dokończenie A1a/A1b (chat.py→~80 linii, ingest.py→~120 linii), `settings-ingest.yaml` ✅, conftest.py ✅, brakujące testy ✅, `workspace_id` w file_registry, A1c, W4, W6.

---

## MACIERZ ŹRÓDEŁ

| # | Funkcja | PvtGPT | LocalGPT | h2oGPT | RAGFlow | Quivr | Danswer | DocQuery | AnyLLM | Priorytet |
|---|---------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| W3 | Vector Cache | | | | | | | | ✅ | 🔴 |
| A1 | Router→Service→Component | ✅ | | | | ✅ | | | | 🔴 |
| D1 | SSE Streaming | ✅ | ✅ | ✅ | | | ✅ | | | 🔴 |
| F1 | Streaming w UI | | ✅ | | | | ✅ | | | 🔴 |
| B1 | Smart Router | | ✅ | ✅ | | | | | | 🔴 |
| B2 | Hybrid Search | | ✅ | | ✅ | | | | | 🔴 |
| C1 | Layout Analysis | | | | ✅ | | | ✅ | | 🔴 |
| A3 | Walidacja config | ✅ | ✅ | | | | | | | 🟡 |
| B3 | Reranking | | ✅ | | ✅ | | | | | 🟡 |
| C6 | Metadata extraction | ✅ | | | | | ✅ | | | 🟡 |
| C4 | Contextual Enrichment | | ✅ | | | | | | | 🟡 |
| B7 | /v1/chunks | ✅ | | | | | ✅ | | | 🟡 |
| E1 | DELETE /v1/ingest | ✅ | | | | ✅ | | | | 🟡 |
| E2 | /v1/ingest/list | ✅ | | | | | ✅ | | | 🟡 |
| H1 | Response format | ✅ | | | | | ✅ | | | 🟡 |
| F2 | Podgląd źródeł | ✅ | ✅ | | | | ✅ | | | 🟡 |
| F3 | Panel dokumentów | ✅ | ✅ | | | ✅ | | | | 🟡 |
| B6 | Semantic Cache | | ✅ | | | | | | | 🟡 |
| B4 | Query Decomposition | | ✅ | | | | | | | 🟡 |
| C2 | Klasyfikacja VLM | | | | ✅ | | | ✅ | | 🟡 |
| C3 | Table Structure | | | | ✅ | | | | | 🟡 |
| W1 | Workspaces | | | | | ✅ | | | ✅ | 🟡 |
| A2 | Profile YAML | ✅ | | | | | | | | 🟡 |
| G1 | Testy | ✅ | | | | | | | | 🟡 |
| G3 | Health check | | ✅ | | | | | | | 🟡 |
| W2 | MCP Compatibility | | | | | | | | ✅ | 🟡 |
| W5 | Batch Processing | | | | ✅ | | | | ✅ | 🟡 |
| E3 | Multi-collection | | | | | ✅ | | | | 🟢 |
| B5 | Answer Verification | | ✅ | | | | | | | 🟢 |
| C5 | Late Chunking | | ✅ | | | | | | | 🟢 |
| D2 | Streaming ingest | | ✅ | | ✅ | | | | | 🟢 |
| F4 | Session history | | ✅ | | | | ✅ | | | 🟢 |
| G2 | Makefile | ✅ | | | | | | | | 🟢 |
| G4 | Swagger docs | ✅ | | | | | | | | 🟢 |
| H2 | Watcher w backendzie | ✅ | | | | | | | | 🟢 |
| W4 | Chat Widget | | | | | | | | ✅ | 🟢 |
| W6 | Agent Builder | | | | | | | | ✅ | 🟢 |

---

## DOCELOWA STRUKTURA KATALOGÓW

```
backend_app/
├── main.py                      # Entry point (+ lifespan z validate_config)
├── config.py                    # + ładowanie YAML profiles
│
├── components/                  # NOWE (Sprint 6) — implementacje singleton + lazy
│   ├── llm_component.py
│   ├── embedding_component.py
│   ├── colpali_component.py
│   ├── vectorstore_component.py
│   └── whisper_component.py
│
├── services/                    # ROZSZERZONE (Sprint 1–4) — logika biznesowa
│   ├── chat_service.py          # Sprint 1 — orkiestracja czatu
│   ├── retrieval_service.py     # Sprint 1 — RAG retrieval
│   ├── prompt_service.py        # Sprint 1 — budowanie promptów
│   ├── cache_service.py         # Sprint 1 — cache z TTL + semantic (Sprint 4)
│   ├── router_service.py        # Sprint 1 — Smart Router (RAG vs Direct)
│   ├── ingest_service.py        # Sprint 1 — orkiestracja ingestu
│   ├── parser_service.py        # Sprint 1 — ekstrakcja tekstu
│   ├── nextcloud_service.py     # Sprint 1 — integracja Nextcloud
│   ├── dedup_service.py         # Sprint 1 — deduplikacja
│   ├── reranker_service.py      # Sprint 2 — reranking
│   ├── layout_service.py        # Sprint 2 — layout analysis
│   ├── metadata_service.py      # Sprint 2 — ekstrakcja metadanych
│   ├── enrichment_service.py    # Sprint 2 — contextual enrichment
│   ├── table_service.py         # Sprint 4 — TSR
│   ├── query_decomposition_service.py  # Sprint 4
│   ├── model_manager.py         # (bez zmian)
│   ├── rag.py                   # (używa services bezpośrednio — components/ jeszcze nie istnieje)
│   ├── batch_service.py         # ✅ Sprint 6 — W5 Batch Processing
│   ├── progress_service.py      # ✅ Sprint 6 — D2 SSE ingest progress
│   ├── verification_service.py  # ✅ Sprint 6 — B5 Answer Verification
│   ├── watcher_service.py       # ✅ Sprint 6 — H2 Watcher
│   └── ...                      # istniejące
│
├── routes/                      # UPROSZCZONE (Sprint 1) + NOWE (Sprint 3–6)
│   ├── chat.py                  # 277 linii (cel ~80 — A1a niekompletne)
│   ├── ingest.py                # 548 linii (cel ~120 — A1b niekompletne)
│   ├── chunks.py                # ✅ Sprint 3 — /v1/chunks
│   ├── workspaces.py            # ✅ Sprint 4 — /workspaces
│   ├── collections.py           # ✅ Sprint 4 — /collections
│   ├── sessions.py              # ✅ Sprint 6 — F4 pełne CRUD sesji
│   ├── mcp.py                   # ✅ Sprint 6 — W2 MCP
│   ├── admin.py                 # ✅ rozbudowane — stats, config, batch, watcher
│   └── ...                      # istniejące
│
├── models/schemas.py            # ✅ ChunksRequest, IngestResponse, WorkspaceCreate
├── static/index.html            # ✅ streaming, panele, eksport, kolekcje, workspace
│
├── settings.yaml                # ✅ Sprint 5
├── settings-server.yaml         # ✅ Sprint 5
├── settings-dev.yaml            # ✅ Sprint 5
├── settings-ingest.yaml         # ✅ dodane 2026-04-07
├── Makefile                     # ✅ Sprint 5
└── tests/                       # ✅ Sprint 5 + rozbudowane
```

---

## CZEGO NIE KOPIUJEMY

| Element | Powód |
|---------|-------|
| LlamaIndex | KlimtechRAG używa Haystack — zmiana frameworka to miesiące |
| Poetry | pip/venv wystarczy — Poetry dodaje złożoność |
| Gradio UI | Custom UI jest lepsze (GPU dashboard, model switch) |
| Ollama integration | llama.cpp bezpośrednio — mniej overhead |
| Multi-user auth (JWT) | Sieć lokalna, single-user — API key wystarczy |
| SDKs (Python/TS) | Overkill dla lokalnego systemu |
| AnythingLLM Docker orchestration | KlimtechRAG używa Podman + ręczny start |

---

*Skonsolidowano: 2026-03-30*
*Źródła: PrivateGPT (57k★), LocalGPT, h2oGPT, RAGFlow, Quivr, Danswer, DocQuery, AnythingLLM*
