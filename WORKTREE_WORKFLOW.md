# WORKTREE WORKFLOW — KlimtechRAG

**Data:** 2026-03-30  
**Wymagania:** Git 2.5+, Claude Code CLI (`claude`)  
**Laptop:** tamiel@hall8000, repo: `~/KlimtechRAG`  
**Serwer:** lobo@hall9000 (192.168.31.70)

---

## KONWENCJE

```
~/KlimtechRAG/                          ← główne repo (main)
~/KlimtechRAG-worktrees/<nazwa>/        ← worktrees (feature branches)
```

- Każda runda = utwórz worktrees → Claude Code pracuje → commit → merge → test → sprzątaj
- Max 2–3 worktrees równolegle
- Po każdej rundzie: merge do main, push, test na serwerze, dopiero potem następna runda

---

## PRZYGOTOWANIE (jednorazowo)

```bash
# Utwórz katalog na worktrees
mkdir -p ~/KlimtechRAG-worktrees

# Upewnij się że main jest czysty i aktualny
cd ~/KlimtechRAG
git status
git pull
```

### Sprzątanie istniejących worktrees (jeśli były tworzone wcześniej)

```bash
# Usuń wcześniej utworzone worktrees (smart-router nie powinien istnieć przed Sprintem 1)
cd ~/KlimtechRAG
git worktree remove ~/KlimtechRAG-worktrees/smart-router
git worktree remove ~/KlimtechRAG-worktrees/validate-config
git worktree remove ~/KlimtechRAG-worktrees/vector-cache

# Usuń branche
git branch -D feature/smart-router feature/validate-config feature/vector-cache

# Weryfikacja — powinien zostać tylko main
git worktree list
```

---

# SPRINT 0 — QUICK WINS (1.5 dnia)

## Runda 0.1 — W3 (Vector Cache) + A3 (Walidacja config)

### Krok 1: Utwórz worktrees

```bash
cd ~/KlimtechRAG
git worktree add ~/KlimtechRAG-worktrees/vector-cache -b feature/vector-cache
git worktree add ~/KlimtechRAG-worktrees/validate-config -b feature/validate-config

# Sprawdź
git worktree list
```

### Krok 2: Terminal 1 — W3 Vector Cache

```bash
cd ~/KlimtechRAG-worktrees/vector-cache
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md — to Twoja konstytucja na tę sesję. Następnie przeczytaj PLAN_WDROZENIA_MASTER.md, sekcję "W3. Vector Cache". Pracujemy w trybie budowania. Potwierdź że rozumiesz zadanie i wymień pliki które będziesz modyfikować.

**Prompt 2 (krok 1/6):**
> Zaczynamy W3 Vector Cache. Krok 1/6: Dodaj kolumnę `content_hash TEXT` do `file_registry.db` — napisz migrację SQLite w `file_registry.py` która dodaje kolumnę jeśli nie istnieje. Zaproponuj diff i czekaj na moją zgodę.

**Prompt 3 (krok 2/6):**
> Krok 2/6: W `routes/ingest.py` (lub odpowiednim miejscu) — po chunking, oblicz SHA256 z połączonych chunków. Utwórz helper `compute_content_hash(chunks: list[str]) -> str`. Zaproponuj diff.

**Prompt 4 (krok 3/6):**
> Krok 3/6: Przed embedding sprawdź w file_registry: `SELECT 1 FROM file_registry WHERE content_hash = ? AND status = 'indexed'`. Jeśli istnieje — skip embedding, log "Vector cache hit: {filename}". Zaproponuj diff.

**Prompt 5 (krok 4/6):**
> Krok 4/6: Jeśli cache miss — normalny embedding pipeline, po udanym ingeście zapisz `content_hash` do file_registry. Zaproponuj diff.

**Prompt 6 (krok 5/6):**
> Krok 5/6: Dodaj logowanie — "Vector cache hit" i "Vector cache miss" z nazwą pliku i hashem. Zaproponuj diff.

**Prompt 7 (krok 6/6):**
> Krok 6/6: Sprawdź składnię i importy we wszystkich zmienionych plikach. Podsumuj co zostało zmienione i dlaczego.

### Krok 3: Terminal 2 — A3 Walidacja config

```bash
cd ~/KlimtechRAG-worktrees/validate-config
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md — to Twoja konstytucja na tę sesję. Następnie przeczytaj PLAN_WDROZENIA_MASTER.md, sekcję "A3. Walidacja konfiguracji na starcie". Pracujemy w trybie budowania. Potwierdź że rozumiesz zadanie.

**Prompt 2 (krok 1/4):**
> Krok 1/4: Dodaj funkcję `validate_config()` w `config.py`. Sprawdza: czy Qdrant odpowiada (GET http://localhost:6333/collections), czy katalog `modele_LLM/` istnieje, czy `.env` istnieje. Zwraca listę błędów. Zaproponuj diff.

**Prompt 3 (krok 2/4):**
> Krok 2/4: Dodaj sprawdzenie czy porty 8000 i 8082 nie są już zajęte (socket connect test). Zaproponuj diff.

**Prompt 4 (krok 3/4):**
> Krok 3/4: Wywołaj `validate_config()` w `lifespan()` w `main.py`. Jeśli są błędy — wypisz je czytelnie (każdy w nowej linii, z emoji ❌) i zakończ `sys.exit(1)`. Jeśli OK — log "✅ Config validation passed". Zaproponuj diff.

**Prompt 5 (krok 4/4):**
> Krok 4/4: Sprawdź składnię i importy. Podsumuj zmiany.

### Krok 4: Commit w worktrees

```bash
# Terminal 1
cd ~/KlimtechRAG-worktrees/vector-cache
git add -A
git commit -m "feat: W3 vector cache - skip re-embedding for unchanged files"

# Terminal 2
cd ~/KlimtechRAG-worktrees/validate-config
git add -A
git commit -m "feat: A3 config validation on startup"
```

### Krok 5: Merge do main

```bash
cd ~/KlimtechRAG
git merge feature/vector-cache
git merge feature/validate-config
```

### Krok 6: Test na serwerze

```bash
# Na laptopie — push (ręcznie, hasło SSH)
git push

# Na serwerze (SSH)
cd /media/lobo/BACKUP/KlimtechRAG
git pull
source venv/bin/activate.fish
bash scripts/check_project.sh
# Test: uruchom backend bez Qdrant → czy wypisuje czytelny błąd?
# Test: zaindeksuj PDF dwukrotnie → czy za drugim razem "Vector cache hit"?
```

### Krok 7: Sprzątanie

```bash
cd ~/KlimtechRAG
git worktree remove ~/KlimtechRAG-worktrees/vector-cache
git worktree remove ~/KlimtechRAG-worktrees/validate-config
git branch -d feature/vector-cache feature/validate-config
git worktree list   # powinien zostać tylko main
```

---

# SPRINT 1 — FUNDAMENTY (8.5 dnia)

## Runda 1.1 — A1a (chat_service) + A1b (ingest_service) — 4 dni

### Krok 1: Utwórz worktrees

```bash
cd ~/KlimtechRAG
git pull   # zawsze aktualizuj main przed nową rundą
git worktree add ~/KlimtechRAG-worktrees/chat-service -b feature/chat-service
git worktree add ~/KlimtechRAG-worktrees/ingest-service -b feature/ingest-service
```

### Krok 2: Terminal 1 — A1a Restrukturyzacja chat.py

```bash
cd ~/KlimtechRAG-worktrees/chat-service
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md. Następnie przeczytaj PLAN_WDROZENIA_MASTER.md, sekcję "A1a. Wydzielenie warstwy Service z routes/chat.py". Przeczytaj też obecny `backend_app/routes/chat.py` — zanotuj sekcje do wydzielenia. Pracujemy w trybie budowania.

**Prompt 2 (krok 1/7):**
> Krok 1/7: Utwórz `backend_app/services/cache_service.py`. Przenieś `_answer_cache`, funkcje `get_cached()`, `set_cached()`, `clear_cache()` z `routes/chat.py`. Zachowaj singleton pattern. Zaproponuj diff.

**Prompt 3 (krok 2/7):**
> Krok 2/7: Utwórz `backend_app/services/retrieval_service.py`. Przenieś logikę retrieval — blok `if request.use_rag` i `if request.web_search` z `routes/chat.py`. Zaproponuj diff.

**Prompt 4 (krok 3/7):**
> Krok 3/7: Utwórz `backend_app/services/prompt_service.py`. Przenieś `RAG_PROMPT` i logikę budowania `full_prompt` z kontekstem. Zaproponuj diff.

**Prompt 5 (krok 4/7):**
> Krok 4/7: Utwórz `backend_app/services/chat_service.py`. Funkcja `process_chat_request()` orkiestruje: cache → retrieval → prompt → LLM → response. Używa trzech serwisów powyżej. Zaproponuj diff.

**Prompt 6 (krok 5/7):**
> Krok 5/7: Refaktoryzuj `routes/chat.py` — zamień ciało endpointów `/v1/chat/completions` i `/query` na wywołania `chat_service.process_chat_request()`. Plik powinien spaść do ~80 linii. Zaproponuj diff.

**Prompt 7 (krok 6/7):**
> Krok 6/7: Zaktualizuj `backend_app/services/__init__.py` — dodaj nowe moduły do exportów jeśli potrzebne. Sprawdź circular imports.

**Prompt 8 (krok 7/7):**
> Krok 7/7: Sprawdź składnię, importy i type hints we WSZYSTKICH zmienionych i nowych plikach. Podsumuj: ile linii miał stary `chat.py`, ile ma teraz, jakie pliki powstały.

### Krok 3: Terminal 2 — A1b Restrukturyzacja ingest.py

```bash
cd ~/KlimtechRAG-worktrees/ingest-service
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md. Następnie przeczytaj PLAN_WDROZENIA_MASTER.md, sekcję "A1b. Wydzielenie warstwy Service z routes/ingest.py". Przeczytaj obecny `backend_app/routes/ingest.py` — zanotuj sekcje do wydzielenia. Tryb budowania.

**Prompt 2 (krok 1/6):**
> Krok 1/6: Utwórz `backend_app/services/parser_service.py`. Przenieś `extract_pdf_text()`, `parse_with_docling()`, `read_text_file()`, `clean_text()` z `routes/ingest.py`. Zaproponuj diff.

**Prompt 3 (krok 2/6):**
> Krok 2/6: Utwórz `backend_app/services/nextcloud_service.py`. Przenieś `save_to_nextcloud()`, `rescan_nextcloud()`, `EXT_TO_DIR` mapowanie. Zaproponuj diff.

**Prompt 4 (krok 3/6):**
> Krok 3/6: Utwórz `backend_app/services/dedup_service.py`. Przenieś `_hash_bytes()`, logikę deduplikacji plików. Zaproponuj diff.

**Prompt 5 (krok 4/6):**
> Krok 4/6: Utwórz `backend_app/services/ingest_service.py`. Funkcja `ingest_file()` orkiestruje: dedup → parse → chunk → embed → store w Qdrant. Używa parser_service, dedup_service, nextcloud_service. Zaproponuj diff.

**Prompt 6 (krok 5/6):**
> Krok 5/6: Refaktoryzuj `routes/ingest.py` — endpointy `/upload`, `/ingest`, `/ingest_path`, `/ingest_all` wywołują `ingest_service`. Plik powinien spaść do ~120 linii. Zaproponuj diff.

**Prompt 7 (krok 6/6):**
> Krok 6/6: Sprawdź składnię, importy, circular imports. Podsumuj zmianę.

### Krok 4: Commit, merge, test, sprzątanie

```bash
# Commit
cd ~/KlimtechRAG-worktrees/chat-service
git add -A && git commit -m "refactor: A1a extract chat_service from chat.py"

cd ~/KlimtechRAG-worktrees/ingest-service
git add -A && git commit -m "refactor: A1b extract ingest_service from ingest.py"

# Merge
cd ~/KlimtechRAG
git merge feature/chat-service
git merge feature/ingest-service

# Push i test na serwerze
git push
# SSH → git pull → bash scripts/check_project.sh
# Test: curl -sk https://192.168.31.70:8443/v1/chat/completions -d '{"messages":[{"role":"user","content":"hej"}]}'
# Test: upload PDF przez UI → sprawdź /files/stats

# Sprzątanie
git worktree remove ~/KlimtechRAG-worktrees/chat-service
git worktree remove ~/KlimtechRAG-worktrees/ingest-service
git branch -d feature/chat-service feature/ingest-service
```

---

## Runda 1.2 — D1+F1 (Streaming) + B1 (Smart Router) — 3.5 dnia

### Krok 1: Utwórz worktrees

```bash
cd ~/KlimtechRAG
git pull
git worktree add ~/KlimtechRAG-worktrees/sse-streaming -b feature/sse-streaming
git worktree add ~/KlimtechRAG-worktrees/smart-router -b feature/smart-router
```

### Krok 2: Terminal 1 — D1 + F1 SSE Streaming

```bash
cd ~/KlimtechRAG-worktrees/sse-streaming
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md, sekcje "D1. SSE Streaming" i "F1. Streaming w UI". Przeczytaj `backend_app/services/chat_service.py` (nowo utworzony po refaktoryzacji A1a). Tryb budowania.

**Prompt 2 (krok 1/5):**
> Krok 1/5: W `services/chat_service.py` dodaj nową async generator function `process_chat_stream()` obok istniejącej `process_chat_request()`. Używa `httpx.AsyncClient` z `stream=True` do llama-server. Yield'uje SSE chunks w formacie OpenAI. Zaproponuj diff.

**Prompt 3 (krok 2/5):**
> Krok 2/5: W `routes/chat.py` — w endpointcie `/v1/chat/completions` dodaj branch: jeśli `request.stream == True` → zwróć `StreamingResponse(media_type="text/event-stream")` używając `chat_service.process_chat_stream()`. Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: W `static/index.html` — zmień funkcję `send()` aby dla streaming używała `fetch` z `body.getReader()`. Parsuj SSE events, renderuj tokeny incrementalnie w bańce czatu. PAMIĘTAJ: brak backticks w JS — używaj concatenation (+) i var. Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Dodaj wizualną animację typing — kursor migający podczas streamingu. Po `data: [DONE]` usuń kursor. Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię. Podsumuj zmiany. Podaj komendę curl do testowania streaming.

### Krok 3: Terminal 2 — B1 Smart Router

```bash
cd ~/KlimtechRAG-worktrees/smart-router
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md, sekcję "B1. Smart Router". Przeczytaj `backend_app/services/chat_service.py`. Tryb budowania.

**Prompt 2 (krok 1/5):**
> Krok 1/5: Utwórz `backend_app/services/router_service.py` z funkcją `should_use_rag(query: str, force_rag: bool = False) -> bool`. Jeśli `force_rag == True` → zawsze True. Inaczej: heurystyka. Zaproponuj diff.

**Prompt 3 (krok 2/5):**
> Krok 2/5: Zaimplementuj heurystykę w `should_use_rag()`:
> - Pytanie < 5 słów i nie zawiera słów kluczowych → False (Direct LLM)
> - Słowa kluczowe PL: dokument, raport, specyfikacja, norma, procedura, instrukcja, regulamin, tabela, dane, wyniki
> - Słowa kluczowe EN: document, report, specification, data, results
> - Jeśli znaleziono keyword → True (RAG)
> - Default: False (Direct LLM — bezpieczniejsze niż ładowanie RAG na "hej")
> Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: W `services/chat_service.py` — na początku `process_chat_request()` (i `process_chat_stream()` jeśli istnieje) dodaj auto-routing: jeśli użytkownik nie wymusił RAG ręcznie (use_rag nie był w request), wywołaj `router_service.should_use_rag()` i ustaw `use_rag` na wynik. Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Dodaj logging: "Smart Router: query='{query}' → use_rag={result} (reason: {keyword/short/forced})". Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię, importy. Podsumuj.

### Krok 4: Commit, merge (KOLEJNOŚĆ!), test, sprzątanie

```bash
# Commit
cd ~/KlimtechRAG-worktrees/sse-streaming
git add -A && git commit -m "feat: D1+F1 SSE streaming backend + UI token-by-token"

cd ~/KlimtechRAG-worktrees/smart-router
git add -A && git commit -m "feat: B1 smart router - auto RAG vs Direct LLM"

# Merge — STREAMING NAJPIERW (bo smart-router modyfikuje chat_service.py)
cd ~/KlimtechRAG
git merge feature/sse-streaming
git merge feature/smart-router
# Jeśli konflikt w chat_service.py → rozwiąż: oba zmiany powinny współistnieć

# Push i test
git push
# SSH → git pull → test streaming: curl -sk -N ...
# Test smart router: "hej" → brak RAG, "co mówi raport?" → RAG

# Sprzątanie
git worktree remove ~/KlimtechRAG-worktrees/sse-streaming
git worktree remove ~/KlimtechRAG-worktrees/smart-router
git branch -d feature/sse-streaming feature/smart-router
```

---

## Runda 1.3 — Weryfikacja i tag (0.5 dnia)

```bash
cd ~/KlimtechRAG

# Pełna weryfikacja
bash scripts/check_project.sh

# Test end-to-end na serwerze:
# 1. Streaming działa? (token-by-token w UI)
# 2. Smart Router: "hej" → szybka odpowiedź, "co mówi raport?" → RAG
# 3. Vector Cache: re-ingest pliku → "cached"
# 4. Walidacja: restart bez Qdrant → czytelny błąd

# Jeśli OK — tag
git tag v7.6
git push --tags
```

---

# SPRINT 2 — JAKOŚĆ RAG (9.5 dnia)

## Runda 2.1 — B2 (Hybrid Search) + C6 (Metadata) — 3 dni

### Krok 1: Utwórz worktrees

```bash
cd ~/KlimtechRAG
git pull
git worktree add ~/KlimtechRAG-worktrees/hybrid-search -b feature/hybrid-search
git worktree add ~/KlimtechRAG-worktrees/metadata-extract -b feature/metadata-extract
```

### Krok 2: Terminal 1 — B2 Hybrid Search

```bash
cd ~/KlimtechRAG-worktrees/hybrid-search
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "B2. Hybrid Search". Przeczytaj `backend_app/services/retrieval_service.py`. Tryb budowania.

**Prompt 2 (krok 1/5):**
> Krok 1/5: Zbadaj opcje BM25 dla naszego stacku. Mamy Qdrant — czy wspiera sparse vectors? Jeśli tak, to preferowane nad osobnym BM25 indexem. Jeśli nie — zaproponuj `rank_bm25`. Przeanalizuj i zaproponuj podejście.

**Prompt 3 (krok 2/5):**
> Krok 2/5: Zaimplementuj wybraną strategię BM25/sparse. Przy ingeście: oprócz dense embedding, buduj index sparse. Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: W `retrieval_service.py` — przy query: dense retrieval + sparse/BM25 retrieval → merge wyników. `final_score = 0.7 * dense + 0.3 * bm25`. Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Dodaj konfigurację w `.env`: `KLIMTECH_BM25_WEIGHT=0.3`, `KLIMTECH_HYBRID_SEARCH=true`. Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię. Podsumuj.

### Krok 3: Terminal 2 — C6 Metadata extraction

```bash
cd ~/KlimtechRAG-worktrees/metadata-extract
claude
```

**Prompt 1 (kontekst):**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "C6. Metadata extraction". Przeczytaj `backend_app/services/ingest_service.py`. Tryb budowania.

**Prompt 2 (krok 1/4):**
> Krok 1/4: Utwórz `backend_app/services/metadata_service.py`. Funkcja `extract_metadata(filepath: str) -> dict` — ekstrakcja z PDF (PyMuPDF: tytuł, autor, data, page_count) i DOCX (mammoth/python-docx). Zaproponuj diff.

**Prompt 3 (krok 2/4):**
> Krok 2/4: Dodaj detekcję języka — prosta heurystyka: jeśli ≥30% słów to polskie stop words → "pl", inaczej "en". Lub użyj `langdetect` jeśli jest w requirements. Zaproponuj diff.

**Prompt 4 (krok 3/4):**
> Krok 3/4: W `services/ingest_service.py` — po chunking, dodaj metadane do `Document.meta`: title, page_count, language, chunk_index, total_chunks, indexed_at. Zaproponuj diff.

**Prompt 5 (krok 4/4):**
> Krok 4/4: Sprawdź składnię. Podsumuj.

### Krok 4: Commit, merge, test, sprzątanie

```bash
cd ~/KlimtechRAG-worktrees/hybrid-search
git add -A && git commit -m "feat: B2 hybrid search dense + BM25"

cd ~/KlimtechRAG-worktrees/metadata-extract
git add -A && git commit -m "feat: C6 metadata extraction at ingest"

cd ~/KlimtechRAG
git merge feature/hybrid-search
git merge feature/metadata-extract

git push
# SSH → test → sprzątanie worktrees
git worktree remove ~/KlimtechRAG-worktrees/hybrid-search
git worktree remove ~/KlimtechRAG-worktrees/metadata-extract
git branch -d feature/hybrid-search feature/metadata-extract
```

---

## Runda 2.2 — B3 (Reranking) + C4 (Enrichment) — 3.5 dnia

### Krok 1: Utwórz worktrees

```bash
cd ~/KlimtechRAG
git pull
git worktree add ~/KlimtechRAG-worktrees/reranking -b feature/reranking
git worktree add ~/KlimtechRAG-worktrees/enrichment -b feature/enrichment
```

### Krok 2: Terminal 1 — B3 Reranking

```bash
cd ~/KlimtechRAG-worktrees/reranking
claude
```

**Prompt 1:**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "B3. Reranking". Przeczytaj `backend_app/services/retrieval_service.py`. Tryb budowania.

**Prompt 2 (krok 1/5):**
> Krok 1/5: Utwórz `backend_app/services/reranker_service.py`. Lazy singleton pattern (jak w embeddings.py). Model: `BAAI/bge-reranker-base`. Funkcja `rerank(query: str, documents: list, top_k: int = 5) -> list`. Zaproponuj diff.

**Prompt 3 (krok 2/5):**
> Krok 2/5: W `retrieval_service.py` — zmień retrieval: zamiast top_k=5, pobierz top_k=20 z Qdrant, potem `reranker_service.rerank()` → zwróć top 5. Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: Dodaj konfigurację: `KLIMTECH_RERANKER_ENABLED=true`, `KLIMTECH_RERANKER_MODEL=BAAI/bge-reranker-base`. W retrieval: if not enabled → stary flow (top_k=5 bezpośrednio). Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Upewnij się że reranker jest lazy loaded — nie ładuj modelu na starcie, tylko przy pierwszym użyciu. VRAM: ~400MB. Sprawdź czy nie koliduje z e5-large na CPU. Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię. Podsumuj.

### Krok 3: Terminal 2 — C4 Contextual Enrichment

```bash
cd ~/KlimtechRAG-worktrees/enrichment
claude
```

**Prompt 1:**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "C4. Contextual Enrichment". Przeczytaj `backend_app/services/ingest_service.py`. Tryb budowania.

**Prompt 2 (krok 1/5):**
> Krok 1/5: Utwórz `backend_app/services/enrichment_service.py`. Funkcja `enrich_chunk(chunk_text: str, document_title: str, chunk_index: int) -> str` — generuje 1-zdaniowy opis kontekstu. Zaproponuj diff.

**Prompt 3 (krok 2/5):**
> Krok 2/5: Zaimplementuj wywołanie LLM (przez httpx do llama-server localhost:8082). Prompt: "Opisz w 1 zdaniu po polsku kontekst tego fragmentu dokumentu '{document_title}': {chunk_text[:500]}". Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: W `ingest_service.py` — po chunking, jeśli `KLIMTECH_CONTEXTUAL_ENRICHMENT=true`: dla każdego chunku generuj kontekst → embed concatenation(kontekst + " " + chunk). Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Dodaj konfigurację: `KLIMTECH_CONTEXTUAL_ENRICHMENT=false` (domyślnie OFF). Log: "Enriching chunk {i}/{total} for {filename}". Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię. Podsumuj. Uwaga: ten feature wymaga działającego LLM przy ingeście — opisz to w docstringu.

### Krok 4: Commit, merge, test, sprzątanie

```bash
cd ~/KlimtechRAG-worktrees/reranking
git add -A && git commit -m "feat: B3 reranking with bge-reranker-base"

cd ~/KlimtechRAG-worktrees/enrichment
git add -A && git commit -m "feat: C4 contextual enrichment for chunks"

cd ~/KlimtechRAG
git merge feature/reranking
git merge feature/enrichment
git push
# SSH → test → sprzątanie
git worktree remove ~/KlimtechRAG-worktrees/reranking
git worktree remove ~/KlimtechRAG-worktrees/enrichment
git branch -d feature/reranking feature/enrichment
```

---

## Runda 2.3 — C1 (Layout Analysis) — solo, 3–5 dni

### Krok 1: Utwórz worktree

```bash
cd ~/KlimtechRAG
git pull
git worktree add ~/KlimtechRAG-worktrees/layout-analysis -b feature/layout-analysis
```

### Krok 2: Terminal 1 — C1 Layout Analysis

```bash
cd ~/KlimtechRAG-worktrees/layout-analysis
claude
```

**Prompt 1 (research):**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "C1. Layout Analysis". To najcięższe zadanie w planie. Zacznij od analizy: jakie modele layout analysis są dostępne i kompatybilne z naszym stackiem (Python 3.12, AMD GPU ROCm 7.2, 16GB VRAM)? Rozważ: docling (już mamy), LayoutLMv3, surya, RAGFlow DeepDoc. Nie implementuj jeszcze — tylko zaproponuj podejście.

**Prompt 2–N:** (zależy od wybranego podejścia — Claude Code zaproponuje kroki atomowe)

### Krok 3: Commit, merge, test, sprzątanie

```bash
cd ~/KlimtechRAG-worktrees/layout-analysis
git add -A && git commit -m "feat: C1 layout analysis for PDF structure recognition"

cd ~/KlimtechRAG
git merge feature/layout-analysis
git push
git worktree remove ~/KlimtechRAG-worktrees/layout-analysis
git branch -d feature/layout-analysis
```

---

# SPRINT 3 — API I ZARZĄDZANIE (7 dni)

## Runda 3.1 — B7 + E1/E2 + H1 — 3.5 dnia

### Krok 1: Utwórz worktrees

```bash
cd ~/KlimtechRAG
git pull
git worktree add ~/KlimtechRAG-worktrees/chunks-endpoint -b feature/chunks-endpoint
git worktree add ~/KlimtechRAG-worktrees/ingest-crud -b feature/ingest-crud
git worktree add ~/KlimtechRAG-worktrees/response-format -b feature/response-format
```

### Krok 2: Terminal 1 — B7 /v1/chunks

```bash
cd ~/KlimtechRAG-worktrees/chunks-endpoint
claude
```

**Prompt 1:**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "B7. Endpoint /v1/chunks". Tryb budowania.

**Prompt 2 (krok 1/5):**
> Krok 1/5: Dodaj do `models/schemas.py` nowe klasy: `ChunksRequest(text: str, limit: int = 10, context_filter: Optional[dict] = None)` i `ChunkItem(text: str, score: float, document: dict)` i `ChunksResponse(object: str = "list", data: list[ChunkItem])`. Zaproponuj diff.

**Prompt 3 (krok 2/5):**
> Krok 2/5: Utwórz `backend_app/routes/chunks.py` z endpointem `POST /v1/chunks`. Logika: embed pytanie (e5-large) → retrieval z Qdrant → zwróć chunki z metadanymi. BEZ LLM. Auth: `require_api_key()`. Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: Dodaj filtrowanie po `context_filter.source` — jeśli podany, dodaj filtr Qdrant: `meta.source == source`. Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Zarejestruj router w `main.py`. Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię. Podaj curl do testu.

### Krok 3: Terminal 2 — E1 DELETE + E2 list

```bash
cd ~/KlimtechRAG-worktrees/ingest-crud
claude
```

**Prompt 1:**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcje "E1. DELETE /v1/ingest/{doc_id}" i "E2. /v1/ingest/list". Tryb budowania.

**Prompt 2 (krok 1/5):**
> Krok 1/5: Dodaj endpoint `GET /v1/ingest/list` do `routes/admin.py`. Query file_registry.db → zwróć doc_id, source, status, chunks_count. Filtry query params: status, source. Auth: require_api_key. Zaproponuj diff.

**Prompt 3 (krok 2/5):**
> Krok 2/5: Dodaj endpoint `DELETE /v1/ingest/{doc_id}` do `routes/admin.py`. Usuwa chunki z Qdrant (filtr meta.source == doc_id). Auth: require_api_key. Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: Po usunięciu z Qdrant — zaktualizuj status w file_registry.db na "deleted". Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Opcjonalny param `?delete_file=true` — jeśli podany, usuń plik źródłowy z dysku. UWAGA: walidacja ścieżki (Path.resolve() + sprawdzenie base_path). Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię. Podaj curle do testów.

### Krok 4: Terminal 3 — H1 Response format

```bash
cd ~/KlimtechRAG-worktrees/response-format
claude
```

**Prompt 1:**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "H1. Standaryzacja response format". Tryb budowania.

**Prompt 2 (krok 1/3):**
> Krok 1/3: Dodaj do `models/schemas.py` nowy model `IngestResponse` — format OpenAI-like z polami: object="ingest.result", data: list z doc_id, source, status, chunks_count, collection. Zaproponuj diff.

**Prompt 3 (krok 2/3):**
> Krok 2/3: Refaktoryzuj return statements w `routes/ingest.py` — endpointy `/upload`, `/ingest`, `/ingest_path`, `/ingest_all` zwracają `IngestResponse`. Zaproponuj diff.

**Prompt 4 (krok 3/3):**
> Krok 3/3: Sprawdź składnię. Podsumuj.

### Krok 5: Commit, merge, test, sprzątanie

```bash
# Commit wszystkie trzy
cd ~/KlimtechRAG-worktrees/chunks-endpoint
git add -A && git commit -m "feat: B7 endpoint /v1/chunks for raw retrieval"

cd ~/KlimtechRAG-worktrees/ingest-crud
git add -A && git commit -m "feat: E1+E2 DELETE ingest + list with metadata"

cd ~/KlimtechRAG-worktrees/response-format
git add -A && git commit -m "feat: H1 standardize ingest response format"

# Merge — chunks-endpoint NAJPIERW (dodaje do schemas.py), potem response-format
cd ~/KlimtechRAG
git merge feature/chunks-endpoint
git merge feature/response-format
git merge feature/ingest-crud

git push
# SSH → test
git worktree remove ~/KlimtechRAG-worktrees/chunks-endpoint
git worktree remove ~/KlimtechRAG-worktrees/ingest-crud
git worktree remove ~/KlimtechRAG-worktrees/response-format
git branch -d feature/chunks-endpoint feature/ingest-crud feature/response-format
```

---

## Runda 3.2 — F2 (Źródła) + F3 (Panel dokumentów) — 3.5 dnia

### Krok 1: Utwórz worktrees

```bash
cd ~/KlimtechRAG
git pull
git worktree add ~/KlimtechRAG-worktrees/sources-ui -b feature/sources-ui
git worktree add ~/KlimtechRAG-worktrees/docs-panel -b feature/docs-panel
```

### Krok 2: Terminal 1 — F2 Podgląd źródeł

```bash
cd ~/KlimtechRAG-worktrees/sources-ui
claude
```

**Prompt 1:**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "F2. Podgląd źródeł". Przeczytaj `static/index.html`. Tryb budowania. UWAGA: JS w Python strings — brak backticks, używaj concatenation (+) i var.

**Prompt 2 (krok 1/4):**
> Krok 1/4: W `services/chat_service.py` — upewnij się że response zawiera `sources` z danymi retrieval (nazwa pliku, strona, score). Jeśli RAG off → sources = []. Zaproponuj diff.

**Prompt 3 (krok 2/4):**
> Krok 2/4: W `static/index.html` — po wyrenderowaniu odpowiedzi AI, jeśli `sources` nie jest puste, wyświetl pod odpowiedzią klikalną listę źródeł: ikona 📎, nazwa pliku, score. Zaproponuj diff.

**Prompt 4 (krok 3/4):**
> Krok 3/4: Kliknięcie źródła → fetch `/v1/chunks` z filtrem po source → pokaż modal/popup z treścią chunku. Zaproponuj diff.

**Prompt 5 (krok 4/4):**
> Krok 4/4: Sprawdź składnię. Podsumuj.

### Krok 3: Terminal 2 — F3 Panel dokumentów

```bash
cd ~/KlimtechRAG-worktrees/docs-panel
claude
```

**Prompt 1:**
> Przeczytaj CLAUDE.md. Przeczytaj PLAN_WDROZENIA_MASTER.md sekcję "F3. Panel zarządzania dokumentami". Przeczytaj `static/index.html` — sekcję sidebar. Tryb budowania. UWAGA: JS — brak backticks.

**Prompt 2 (krok 1/5):**
> Krok 1/5: W `static/index.html` — dodaj nową kartę w sidebar: "Dokumenty RAG" (ikona 📚). Kliknięcie przełącza widok. Zaproponuj diff.

**Prompt 3 (krok 2/5):**
> Krok 2/5: Zawartość karty: tabela z dokumentami z `/v1/ingest/list`. Kolumny: source, status, chunks, data. Zaproponuj diff.

**Prompt 4 (krok 3/5):**
> Krok 3/5: Przycisk "Usuń" przy każdym dokumencie → `DELETE /v1/ingest/{doc_id}` → odśwież listę. Zaproponuj diff.

**Prompt 5 (krok 4/5):**
> Krok 4/5: Przycisk "Re-indeksuj" → `POST /ingest_path` z source → odśwież listę. Zaproponuj diff.

**Prompt 6 (krok 5/5):**
> Krok 5/5: Sprawdź składnię. Podsumuj.

### Krok 4: Commit, merge (SOURCES NAJPIERW), test, sprzątanie

```bash
cd ~/KlimtechRAG-worktrees/sources-ui
git add -A && git commit -m "feat: F2 source preview in chat responses"

cd ~/KlimtechRAG-worktrees/docs-panel
git add -A && git commit -m "feat: F3 RAG document management panel"

# Merge sources-ui NAJPIERW (mniejsza zmiana w index.html)
cd ~/KlimtechRAG
git merge feature/sources-ui
git merge feature/docs-panel

git push
git worktree remove ~/KlimtechRAG-worktrees/sources-ui
git worktree remove ~/KlimtechRAG-worktrees/docs-panel
git branch -d feature/sources-ui feature/docs-panel
```

---

# SPRINT 4–6 — SCHEMAT POWTARZALNY

Dalsze sprinty używają identycznego wzorca. Komendy tworzenia worktrees:

## Sprint 4

```bash
# Runda 4.1
git worktree add ~/KlimtechRAG-worktrees/semantic-cache -b feature/semantic-cache
git worktree add ~/KlimtechRAG-worktrees/vlm-classify -b feature/vlm-classify

# Runda 4.2
git worktree add ~/KlimtechRAG-worktrees/query-decomp -b feature/query-decomp
git worktree add ~/KlimtechRAG-worktrees/table-recognition -b feature/table-recognition

# Runda 4.3
git worktree add ~/KlimtechRAG-worktrees/collections-api -b feature/collections-api
git worktree add ~/KlimtechRAG-worktrees/workspaces -b feature/workspaces
```

## Sprint 5

```bash
# Runda 5.1
git worktree add ~/KlimtechRAG-worktrees/yaml-profiles -b feature/yaml-profiles
git worktree add ~/KlimtechRAG-worktrees/tests -b feature/tests
git worktree add ~/KlimtechRAG-worktrees/health-check -b feature/health-check

# Runda 5.2
git worktree add ~/KlimtechRAG-worktrees/makefile -b feature/makefile
git worktree add ~/KlimtechRAG-worktrees/swagger-docs -b feature/swagger-docs
```

## Sprint 6 (ad hoc)

```bash
git worktree add ~/KlimtechRAG-worktrees/components -b feature/components
git worktree add ~/KlimtechRAG-worktrees/mcp-compat -b feature/mcp-compat
git worktree add ~/KlimtechRAG-worktrees/chat-widget -b feature/chat-widget
# itd.
```

---

# SZYBKA ŚCIĄGAWKA

```bash
# Utwórz worktree
git worktree add ~/KlimtechRAG-worktrees/NAZWA -b feature/NAZWA

# Lista worktrees
git worktree list

# Wejdź i uruchom Claude Code
cd ~/KlimtechRAG-worktrees/NAZWA && claude

# Commit w worktree
cd ~/KlimtechRAG-worktrees/NAZWA
git add -A && git commit -m "feat: OPIS"

# Merge do main
cd ~/KlimtechRAG
git merge feature/NAZWA

# Sprzątanie
git worktree remove ~/KlimtechRAG-worktrees/NAZWA
git branch -d feature/NAZWA

# Push (ręcznie — wymaga hasła SSH)
git push

# Na serwerze
cd /media/lobo/BACKUP/KlimtechRAG && git pull && bash scripts/check_project.sh
```

---

*Utworzono: 2026-03-30*
