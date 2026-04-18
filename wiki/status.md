# status.md — Aktualny Stan Projektu KlimtechRAG
*Aktualizuj na końcu każdej sesji. To jest "punkt wejścia" dla nowej sesji Claude Code.*

---

## Stan na: 2026-04-18 (popołudnie — MVP graf wiedzy MemPalace)

### Co zrobiono w tej sesji (laptop — worktree feature/mempalace)

- **Analiza 10 MD planów** MemPalace (00-08 + PLAN_GRAF_WIEDZY.md) + identyfikacja niespójności:
  - 04_CONTEXT_LAYERS definiuje 5 wings, kod ma 14 (`backend_app/categories/definitions.py`)
  - 07_GRAPH_NER regex tylko dla construction/law — dla 14 domen wymaga opt-in per dom.
- **Scope MVP**: plan 05 (Graph Edges) + 06 (Graph API/Viz). Runtime wing extraction — bez migracji 02_METADATA
- **Worktree `feature/mempalace`** (`/home/tamiel/KlimtechRAG-worktrees/MemPalace`):
  - Commit `66dcfd7` — import 10 MD planów (3128 insertions)
  - Commit `1a2800d` — **MVP grafu wiedzy** (758 insertions, 6 plików):
    - `backend_app/services/graph_service.py` — add_edge/get_edges/get_nodes/build_wing_edges/log_co_retrieval
    - `backend_app/file_registry.py` — DDL tabeli `document_graph` (source_a, source_b, edge_type, weight)
    - `backend_app/scripts/build_graph.py` — CLI `same_wing` + `semantic` (cosine>=0.75, top-k=3)
    - `backend_app/routes/graph.py` — GET /v1/graph/data, /v1/graph/node/{source}, /graph (HTML)
    - `backend_app/main.py` — rejestracja graph_router
    - `backend_app/static/graph.html` — 3d-force-graph UI, 14 wings kolorowane, filtry edge_type + min_weight
- **Push `feature/mempalace` na GitHub** (osobny terminal, 27 obiektów, 48 KiB)
- **Archiwizacja transkryptu** przez `/export_claude`: 7 chunków w `kb_md` na GPU (2.3 GB VRAM, 2.1 chunk/s)
- **Snapshot w supervisor_memory**: id `1c05a423-738a-472d-8efe-6dfdec1e8b0c`

### Aktualny stan

**Laptop:**
- Branch `main`: bez nowych zmian w kodzie; untracked: `CUDA_LAPTOP.md`, `Plan_wdrożenia_OpenWebUI.md` (przeniesione z poprzedniej sesji)
- Branch `feature/mempalace`: 2 commity, spushowany na GitHub, gotowy do deployu
- Qdrant `kb_md`: **1290 punktów** (było 1283 + 7 z tej sesji)
- Qdrant `supervisor_memory`: +1 snapshot
- Robotnik Qwen2.5-Coder-3B Q6_K pobrany (`lmstudio-community/Qwen2.5-Coder-3B-GGUF`), jeszcze nie zintegrowany z workflow

**Serwer Proxmox** — bez zmian (`5425ca1`), brak dostępu.

### Co dalej (następna sesja)

1. **Deploy `feature/mempalace` na serwer** (gdy będzie dostęp):
   - `git fetch && git checkout feature/mempalace`
   - Restart backendu → `init_db()` stworzy tabelę `document_graph`
   - `python3 -m backend_app.scripts.build_graph --wings-only` (szybkie)
   - `python3 -m backend_app.scripts.build_graph --threshold 0.75 --top-k 3` (wolniejsze — scroll vectorów)
   - Test `http://192.168.31.70:8000/graph` w przeglądarce
2. **Decyzja merge**: PR na GitHubie (rekomendowane) vs merge lokalny do main po testach serwera
3. **Decyzja CLAUDE.md sekcja 15**: czy integrować `export_claude` z triggerem `na dzisiaj koniec` (opcja A)
4. **Dalsze fazy MemPalace**: 01 Robotnicy (Qwen2.5-Coder integracja), 02 Metadata migration, 04 Context Layers, 07 NER opt-in

### Pliki krytyczne — tej sesji
```
backend_app/services/graph_service.py  — nowy serwis grafu (feature/mempalace)
backend_app/routes/graph.py            — 3 endpointy API + HTML (feature/mempalace)
backend_app/static/graph.html          — 3d-force-graph UI (feature/mempalace)
backend_app/scripts/build_graph.py     — CLI builder (feature/mempalace)
backend_app/file_registry.py           — +DDL document_graph (feature/mempalace)
backend_app/main.py                    — +graph_router (feature/mempalace)
```

### Numer wersji następnego release
Ostatni tag: `v7.9`
Następny: **`v7.10`** (MVP graf wiedzy MemPalace + feature/mempalace)

---

## Stan na: 2026-04-18 (przedpołudnie — GPU na Pascalu przez PyTorch)

### Co zrobiono w tej sesji (laptop — lokalna baza wiedzy GPU)

- **Reboot po `nvidia-driver-580`** → GPU Pascal P1000 działa: nvidia-smi, /dev/nvidia*, lsmod OK
- **Diagnoza**: fastembed CUDAExecutionProvider dalej padał na `CUDNN_STATUS_EXECUTION_FAILED_CUDART 5003`. Root cause: Pascal CC 6.1 + cuDNN 9.21 → brak kerneli `cudnnReduceTensor` dla starej architektury
- **Rozwiązanie — przejście na PyTorch** w `ttkb_tut/venv/`:
  - torch 2.5.1+cu121 (z wbudowanym cuDNN 9.1 — działa na Pascalu)
  - sentence-transformers 5.4.1, qdrant-client 1.17.1
  - Bench: **2.1 chunk/s** na e5-large, VRAM peak 2.3 GB/4 GB
- **`scripts/index_md.py`** (commit `11ffbdb`) — portable indexer .md/.txt → Qdrant
  - chunking 400/50, SHA-256 idempotencja (UUID deterministyczny), `--file` flag, auto-device
  - Kolekcja `kb_md` (dim=1024 Cosine) — **1283 punkty** (72 .md + 23 .txt, 189 auto-dedup 13%)
  - Test semantic search: scores 0.86-0.87 — działa
- **Porządki** (commit `b159413`):
  - Duplikaty sesji z root → `MD_files/` (KOMENDA*, session-ses_*, PLAN_WDROZENIA_MASTER*, CHECK_LISTA, proxmox_install, KlimtechRAG_sesja_planistyczna_2026-04-08)
  - `.gitignore`: dodano `ttkb_tut/`
  - `PROJEKT_OPIS.md`: sekcja o lokalnych venvs laptopa + plan index_md.py
- **`/export_claude` skill** rozszerzony (globalny `~/.claude/commands/`):
  - Nowy Krok 2: indeksowanie pliku eksportu GPU → kb_md

### Aktualny stan

**Laptop (tamiel@hall8000):**
- Qdrant: `kb_md` 1283 pkt, `agent_memory` + `supervisor_memory` (używane przez skills)
- PyTorch venv: `ttkb_tut/venv/` — 2.1 chunk/s na Pascalu
- fastembed venv: `/home/tamiel/programy/klimtech-embed-venv/` — nadal tam, używany tylko przez laptop_memory.py (fastembed pada na Pascalu, dlatego CPU)
- Commity niepushowane: `b159413`, `11ffbdb`

**Serwer Proxmox** — bez zmian od poprzedniej sesji (`5425ca1`).

### Co dalej (następna sesja)

1. **git push** commitów `b159413`, `11ffbdb` (użytkownik w osobnym terminalu)
2. Commit `CUDA_LAPTOP.md`, `MemPalace/`, `Plan_wdrożenia_OpenWebUI.md` (wciąż untracked)
3. `index_md.py` na serwerze Proxmox — indeksowanie `klimtech_docs` lub `agent_memory` przez ROCm (AMD Instinct)
4. Eksperymenty wydajności: batch=16/32, fp16 na Pascalu
5. BLOKER 8x ignorowany: czy zaindeksować `~/Dokumenty`?

### Pliki krytyczne — tej sesji
```
scripts/index_md.py                 — nowy indexer GPU (commit 11ffbdb)
.gitignore, PROJEKT_OPIS.md         — sprzątanie (commit b159413)
~/.claude/commands/export_claude.md — rozszerzony o indeksowanie GPU (global, nie w repo)
```

### Numer wersji następnego release
Ostatni tag: `v7.9` (po `3b40576`)
Następny: `v7.10` lub `v7.11` (sesja GPU na Pascalu + scripts/index_md.py)

---

## Stan na: 2026-04-17

### Co zrobiono w tej sesji (laptop — synchronizacja + narzędzia)

- **Decyzja:** migracja UI → OpenWebUI (Wariant B) — zapisana w `migracja_openwebui.md`
- **Synchronizacja laptopa z GitHub:** git pull (laptop był 5 commitów za serwerem Proxmox)
- **GitHub auth na laptopie:** SSH key "laptop" wgrany na GitHub (read/write), remote przełączony SSH→HTTPS→SSH
- **`scripts/laptop_memory.py`** — lekki klient pamięci sesji (fastembed ONNX + qdrant-client, bez torch)
- **`/home/tamiel/programy/klimtech-embed-venv/`** — dedykowany venv dla fastembed + qdrant-client
- **`~/.claude/commands/export_claude.md`** — skill eksportu sesji z embeddingiem do Qdrant
- **`~/.claude/commands/import_claude.md`** — skill wczytania ostatniego snapshotu z Qdrant
- **Push:** commit `3b40576` — wszystkie nowe pliki laptopa na GitHub

### Aktualny stan

**Laptop (tamiel@hall8000) — ŚRODOWISKO DEWELOPERSKIE:**
- Repo: `/home/tamiel/KlimtechRAG/` ✅ (zsynchronizowane z GitHub)
- Qdrant lokalny: port 6333 ✅ (kolekcje: supervisor_memory, agent_memory — puste)
- Claude Code: zainstalowany ✅
- Skills: `/export_claude`, `/import_claude` ✅
- venv fastembed: `/home/tamiel/programy/klimtech-embed-venv/` ✅
- Backend KlimtechRAG: NIE uruchomiony (nie potrzebny na laptopie) ⬜
- llama.cpp: `/home/tamiel/programy/llama.cpp` ✅ (Quadro P1000 GPU)

**Serwer Proxmox (lobo@hall9000) — PLATFORMA PRODUKCYJNA:**
- Ostatni commit na serwerze: `5425ca1` (supervisor_memory endpoint)
- Backend: weryfikować przy następnej sesji na serwerze
- AMD Instinct 16 GB: aktywna

### Co dalej (następna sesja)

#### Priorytet 1 — planowanie wdrożenia OpenWebUI
- [ ] Przeczytać `wiki/decisions.md` — decyzja o OpenWebUI
- [ ] Potwierdzić Opcję 1: KlimtechRAG FastAPI jako silnik RAG, OpenWebUI jako cienki frontend
- [ ] Rozpisać atomowy plan wdrożenia (Fish shell, bez heredoc)

#### Priorytet 2 — weryfikacja serwera po ostatnich commitach
- [ ] Sprawdzić czy `supervisor_memory` i `agent_memory` endpointy działają na serwerze
- [ ] `git pull` na serwerze po nowym commicie `3b40576`

### Pliki krytyczne — ostatnio modyfikowane
```
scripts/laptop_memory.py            — nowy (fastembed + Qdrant, laptop only)
migracja_openwebui.md               — decyzja o migracji UI
~/.claude/commands/export_claude.md — skill eksportu sesji
~/.claude/commands/import_claude.md — skill importu sesji
```

### Numer wersji następnego release
Ostatni tag: `v7.9`
Następny: `v7.10` (sesja synchronizacji laptopa + narzędzia pamięci)

---

## Szablon dla Następnej Sesji

```
Przeczytałem wiki/status.md.
Kontynuujemy od: planowanie wdrożenia OpenWebUI
Laptop zsynchronizowany z GitHub (commit 3b40576)
Qdrant lokalny: aktywny (puste kolekcje)
Następny krok: atomowy plan migracji UI → OpenWebUI
```
