# status.md — Aktualny Stan Projektu KlimtechRAG
*Aktualizuj na końcu każdej sesji. To jest "punkt wejścia" dla nowej sesji Claude Code.*

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
