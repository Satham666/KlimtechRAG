# decisions.md — Decyzje Architektoniczne KlimtechRAG
*Aktualizuj po każdej sesji gdy podjęto decyzję techniczną.*

---

## 2026-04-08

### Lazy loading embeddings (NIEODWRACALNE)
**Decyzja:** embeddings.py i rag.py używają wzorca lazy singleton — model ładowany dopiero przy pierwszym żądaniu.  
**Powód:** Bez tego backend startuje z 4.5 GB VRAM zajętego. GPU ma 16 GB, LLM potrzebuje ~14 GB.  
**Konsekwencja:** NIE COFAĆ — `_resource = None; def get_resource(): if _resource is None: _resource = _load()`

### use_rag=False domyślnie (NIEODWRACALNE)
**Decyzja:** `schemas.py` — `use_rag: bool = False`.  
**Powód:** Domyślnie czat idzie prosto do LLM bez RAG. Użytkownik włącza RAG świadomie.  
**Konsekwencja:** NIE ZMIENIAĆ — zmiana domyślnej wartości dławiłaby kontekstem każde zapytanie.

### Kolekcje Qdrant — osobne dla każdego wymiaru
**Decyzja:** `klimtech_docs` dim=1024 (e5-large), `klimtech_colpali` dim=128, `agent_memory` dim=1024, `supervisor_memory` dim=1024.  
**Powód:** Qdrant nie pozwala mieszać wymiarów w jednej kolekcji.  
**Konsekwencja:** Przy tworzeniu nowej kolekcji ZAWSZE sprawdź dim.

### Architektura agentowa — Mistrz + Uczeń
**Decyzja:** Claude Sonnet 4.6 (API) jako orkiestrator/nadzorca. Qwen3-Coder-30B-A3B (lokalnie) jako wykonawca.  
**Powód:** Planowanie → Sonnet (najlepsza jakość rozumowania, płatne API). Pisanie kodu → Qwen3 (lokalnie, za darmo, wystarczająca jakość).  
**Konsekwencja:** Sonnet JEDYNY który pisze do baz pamięci. Qwen3 tylko czyta i edytuje kod.

### Qwen3-Coder zamiast Qwen2.5-Coder-32B
**Decyzja:** Qwen3-Coder-30B-A3B-Instruct Q8_0 zamiast Qwen2.5-Coder-32B Q4_K_M.  
**Powód:** MoE — 30B parametrów total, tylko 3B aktywnych przy inferencji → 2-3x szybszy, VRAM ~18GB vs ~20GB.  
**Link:** unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF

### Qdrant na laptopie (osobny od serwera)
**Decyzja:** Laptop posiada osobny Qdrant (port 6333) z kolekcjami agent_memory i supervisor_memory.  
**Powód:** Pamięć agentów jest oddzielona od danych RAG projektu. Laptop jest zawsze dostępny do edycji.  
**Storage:** `/home/tamiel/qdrant_storage/`

### A1b — Refaktoryzacja routes/ingest.py (v7.4)
**Decyzja:** routes/ingest.py 548→196 linii. Cała logika biznesowa w services/ingest_service.py.  
**Powód:** Thin routing layer — router tylko parsuje HTTP i deleguje do service. IngestError jako boundary exception.  
**Konsekwencja:** Nowy wzorzec dla wszystkich przyszłych routes.

### F2 — Klikalne źródła w czacie
**Decyzja:** Kliknięcie nazwy źródła w odpowiedzi LLM otwiera modal z chunkami z Qdrant (POST /v1/chunks).  
**Powód:** Użytkownik może zobaczyć dokładnie co LLM "widział" przy odpowiedzi.

### Backtick w Python strings — ZAWSZE concatenation
**Decyzja:** JS osadzony w Python string: zawsze `+` concatenation i `var`, nigdy backtick ani `const`/`let`.  
**Powód:** Backtick w f-string powoduje SyntaxWarning w Python i SyntaxError w przeglądarce.

## 2026-04-17

### Migracja UI → OpenWebUI (Wariant B)
**Decyzja:** Frontend KlimtechRAG = OpenWebUI (nie Anything-LLM, nie własny widget).  
**Powód:** OpenWebUI to FastAPI + Svelte (Python stack), hostowany na Proxmox razem z backendem. Brak dodatkowych hopów API przez VPN. Zgodność z istniejącymi planami w repo.  
**Kluczowe:** KlimtechRAG FastAPI jako silnik RAG (Opcja 1) — OpenWebUI tylko cienki frontend do `/v1/chat/completions`. NIE używać wbudowanego RAG OpenWebUI.  
**Odrzucone:** Anything-LLM (Node.js, ColPali niekompatybilne, 4 warstwy zamiast 2).

### Pamięć sesji na laptopie — fastembed zamiast pełnego backendu
**Decyzja:** Laptop używa `scripts/laptop_memory.py` z fastembed (ONNX) + qdrant-client. Bez torch, bez pełnego backendu.  
**Powód:** Laptop nie jest docelową platformą projektu. llama.cpp jest dostępny, ale e5-large przez fastembed jest lżejszy i wystarczający do embeddingu snapshotów sesji.  
**Storage:** Qdrant lokalny port 6333, kolekcja `supervisor_memory` dim=1024.
