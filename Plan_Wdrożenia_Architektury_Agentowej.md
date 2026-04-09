# Plan Wdrożenia Architektury Agentowej — KlimtechRAG
**Opracowany:** 2026-04-08  
**Aktualizowany:** 2026-04-08  
**Źródło:** KlimtechRAG_sesja_planistyczna_2026-04-08.md

---

## AKTUALNY FOCUS (2026-04-08)

> **Laptop only — brak GPU1.**  
> Pracujemy nad: `wiki/` (zewnętrzna pamięć Claude Code) + Qdrant RAG na laptopie.  
> Fazy 2 i 3 (Qwen3, serwer) są zamrożone do czasu dostarczenia karty 32GB.

## Status Faz

| Faza | Nazwa | Status |
|------|-------|--------|
| 0 | Fundament (wiki + docs) | ✅ WYKONANE |
| 1 | Pamięć RAG na laptopie (Qdrant) | 🟡 W toku — kolekcje OK, endpoint do napisania |
| 2 | GPU1 + Qwen3-Coder | ⛔ ZAMROŻONE — brak karty 32GB |
| 3 | Integracja z Qwen3 (workflow nocny) | ⛔ ZAMROŻONE — wymaga Fazy 2 |
| 4 | Obsidian Dashboard | ⚪ Opcjonalne, niezależne od GPU |

---

## Architektura — Stan Aktualny (laptop only)

```
tamiel@laptop:
  - Claude Code CLI (Sonnet 4.6) — nadzorca i jedyny agent aktywny
  - wiki/ → decisions.md, lessons.md, status.md  [AKTYWNE]
  - Qdrant (Podman port 6333):
      agent_memory      dim=1024  [AKTYWNE — kolekcja istnieje]
      supervisor_memory dim=1024  [AKTYWNE — kolekcja istnieje]
```

<!-- ARCHITEKTURA DOCELOWA (po dostawie GPU1) — odkomentuj gdy gotowe:

tamiel@laptop:
  - Claude Code CLI (Sonnet 4.6) — Mistrz/Nadzorca
  - OpenCode — interfejs agentowy dla Qwen3
  - Obsidian vault → wiki/ — ludzki dashboard
  - Qdrant laptop (port 6333) → agent_memory, supervisor_memory
  - wiki/ katalog → decisions.md, lessons.md, status.md

hall9000 (serwer):
  GPU 0 (16GB AMD Instinct):
    - KlimtechRAG FastAPI :8000
    - Qdrant serwera: klimtech_docs, klimtech_colpali
    - ColPali v1.3, e5-large

  GPU 1 (32GB AMD Instinct):
    - llama-server: Qwen3-Coder-30B-A3B Q8_0
    - Port: 8083, HIP_VISIBLE_DEVICES=1

-->

---

## Faza 0 — Fundament (laptop, bez serwera)

### 0.1 Katalog wiki/ ✅ WYKONANE

```
KlimtechRAG/wiki/
  decisions.md   — decyzje architektoniczne i dlaczego
  lessons.md     — błędy, odkrycia, co nie działa i dlaczego
  status.md      — aktualny stan projektu
```

**Jak używać wiki z Claude Code:**
- Na początku każdej sesji: Claude Code czyta `wiki/status.md` → od razu wie gdzie skończyliśmy
- Na końcu sesji: aktualizuje `wiki/status.md` + dopisuje do `wiki/decisions.md` jeśli była decyzja
- Błędy i odkrycia → `wiki/lessons.md` (aby nie powtarzać tych samych błędów)

### 0.2 Aktualizacja AGENTS.md ✅ WYKONANE
- Dodano sekcję 16: Shell, Wiki i Model wykonawczy (Qwen3)
- Fish shell — bez heredoc, bez backslash `\` na końcu linii

### 0.3 Aktualizacja CLAUDE.md ✅ WYKONANE
- Dodano sekcję 18: wiki/ — zewnętrzna pamięć sesji

---

## Faza 1 — Pamięć RAG (Qdrant na laptopie)

### Stan aktualny Qdrant na laptopie

```
UWAGA: Qdrant JUŻ działa w kontenerze Podman!
Kontener: docker.io/qdrant/qdrant:latest
Nazwa:     qdrant
Porty:     6333 (REST), 6334 (gRPC)
Storage:   /home/tamiel/qdrant_storage/ (20KB — brak kolekcji)
Tryb:      uruchomiony ręcznie (NIE przez systemd)
Quadlet:   /etc/containers/systemd/qdrant.container (istnieje, inactive)
```

### 1.0 Status Qdrant — ✅ JUŻ POPRAWNIE SKONFIGUROWANY

Qdrant jest już w Podman via systemd quadlet (user service).
**Active: active (running) od 2026-04-06.**

Quadlet: `/home/tamiel/.config/containers/systemd/qdrant.container`
Storage: `/home/tamiel/qdrant_storage/`
Kolekcje: `agent_memory` ✅, `supervisor_memory` ✅

Reinstalacja nie jest potrzebna. Jeśli mimo wszystko chcesz zresetować:

```bash
# Zatrzymaj i usuń ręcznie uruchomiony kontener
podman stop qdrant
podman rm qdrant

# Włącz zarządzanie przez systemd quadlet (już istnieje)
systemctl --user daemon-reload
systemctl --user enable qdrant.service
systemctl --user start qdrant.service

# Sprawdź status
systemctl --user status qdrant.service
curl http://localhost:6333/healthz
```

**Plik quadlet** (już istnieje w `/etc/containers/systemd/qdrant.container`):
```ini
[Unit]
Description=Qdrant vector database
After=network.target

[Container]
Image=docker.io/qdrant/qdrant:latest
ContainerName=qdrant
PublishPort=6333:6333
PublishPort=6334:6334
Volume=%h/qdrant_storage:/qdrant/storage:Z
AutoUpdate=registry

[Service]
Restart=always

[Install]
WantedBy=default.target
```

### 1.1 Nowa kolekcja: agent_memory

```bash
curl -X PUT http://localhost:6333/collections/agent_memory \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

**Payload punktu (schemat):**
```json
{
  "vector": [1024 floats],
  "payload": {
    "typ": "błąd_agenta | decyzja | uwaga_sonnet | plik_kontekst | wynik_testu | wzorzec_sukcesu",
    "treść": "...",
    "plik": "backend_app/routes/ingest.py",
    "linia": 142,
    "timestamp": "2026-04-08T23:14:00",
    "sesja_id": "...",
    "agent": "qwen3 | sonnet"
  }
}
```

### 1.2 Nowa kolekcja: supervisor_memory

```bash
curl -X PUT http://localhost:6333/collections/supervisor_memory \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

**Payload punktu (schemat):**
```json
{
  "vector": [1024 floats],
  "payload": {
    "typ": "snapshot | plan_niezrealizowany | decyzja_nadzorcza | kontekst_przerwania | wzorzec_błędu_ucznia",
    "treść": "...",
    "git_status": ["routes/ingest.py M"],
    "ostatni_krok": "...",
    "nastepny_krok": "...",
    "timestamp": "2026-04-08T23:14:00",
    "uwagi": "..."
  }
}
```

### 1.3 Endpoint POST /v1/agent/memory

**Plik:** `backend_app/routes/agent_memory.py` (nowy)

```python
from fastapi import APIRouter, Depends
from backend_app.utils.dependencies import require_api_key
from qdrant_client import QdrantClient
from backend_app.services.embeddings import get_text_embedder
from pydantic import BaseModel
from typing import Optional
import datetime

router = APIRouter(prefix="/v1/agent", tags=["agent"])

class MemoryItem(BaseModel):
    typ: str  # błąd_agenta | decyzja | snapshot | ...
    treść: str
    plik: Optional[str] = None
    linia: Optional[int] = None
    agent: str = "sonnet"
    uwagi: Optional[str] = None

@router.post("/memory")
async def save_memory(item: MemoryItem, _: str = Depends(require_api_key)):
    embedder = get_text_embedder()
    vector = embedder.embed_query(item.treść)
    client = QdrantClient(url="http://localhost:6333")
    point = {
        "vector": vector,
        "payload": {
            **item.dict(),
            "timestamp": datetime.datetime.now().isoformat()
        }
    }
    client.upsert(collection_name="agent_memory", points=[point])
    return {"status": "saved"}

@router.get("/memory/search")
async def search_memory(q: str, limit: int = 5, typ: Optional[str] = None,
                        _: str = Depends(require_api_key)):
    embedder = get_text_embedder()
    vector = embedder.embed_query(q)
    client = QdrantClient(url="http://localhost:6333")
    filter_ = {"must": [{"key": "typ", "match": {"value": typ}}]} if typ else None
    results = client.search(
        collection_name="agent_memory",
        query_vector=vector,
        limit=limit,
        query_filter=filter_
    )
    return [{"score": r.score, "payload": r.payload} for r in results]
```

### 1.4 Endpoint POST /v1/supervisor/snapshot

**Plik:** `backend_app/routes/agent_memory.py` (dodać do istniejącego)

```python
class SessionSnapshot(BaseModel):
    ostatni_krok: str
    nastepny_krok: str
    git_status: list[str] = []
    uwagi: Optional[str] = None

@router.post("/supervisor/snapshot")
async def save_snapshot(snap: SessionSnapshot, _: str = Depends(require_api_key)):
    client = QdrantClient(url="http://localhost:6333")
    embedder = get_text_embedder()
    tekst = f"{snap.ostatni_krok}. Następny krok: {snap.nastepny_krok}. {snap.uwagi or ''}"
    vector = embedder.embed_query(tekst)
    point = {
        "vector": vector,
        "payload": {
            "typ": "snapshot",
            **snap.dict(),
            "timestamp": datetime.datetime.now().isoformat()
        }
    }
    client.upsert(collection_name="supervisor_memory", points=[point])
    return {"status": "saved"}
```

---

<!-- ============================================================
FAZA 2 — ZAMROŻONA (brak GPU1 32GB)
Odkomentuj gdy karta dostępna.
===============================================================

## Faza 2 — GPU1 + Qwen3-Coder

### Model docelowy
Qwen3-Coder-30B-A3B-Instruct Q8_0
Źródło: unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF
VRAM: ~30GB (GPU1 32GB AMD Instinct)
MoE — 30B params total, 3B aktywnych = 2-3x szybszy od Qwen2.5-Coder-32B

### Pobieranie modelu
huggingface-cli download unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF --include "Qwen3-Coder-30B-A3B-Instruct-Q8_0.gguf" --local-dir /media/lobo/BACKUP/KlimtechRAG/modele_LLM/qwen3-coder/

### Start llama-server GPU1
HIP_VISIBLE_DEVICES=1 GPU_MAX_ALLOC_PERCENT=100 HSA_ENABLE_SDMA=0 HSA_OVERRIDE_GFX_VERSION=9.0.6 llama-server --model .../Qwen3-Coder-30B-A3B-Instruct-Q8_0.gguf --port 8083 --ctx-size 32768 --n-gpu-layers 99 --host 0.0.0.0

### Aktualizacja start_klimtech_v3.py
Dodać: {"name":"qwen3-coder","cmd":[...,"--port","8083"],"env":{"HIP_VISIBLE_DEVICES":"1"},"optional":True}

## Faza 3 — Integracja z Qwen3 (workflow nocny)

### 3.1 session_snapshot.sh — zapisuje snapshot do supervisor_memory przez FastAPI
### 3.2 OpenCode — npm install -g @opencode-ai/opencode + config port 8083
### 3.3 Trigger "na dzisiaj koniec" — dodaj krok: bash scripts/session_snapshot.sh

-->

---

## Faza 4 — Obsidian Dashboard (opcjonalne)

### Setup

```
Obsidian → Open Vault → wskaż /home/tamiel/KlimtechRAG/wiki/
```

### Wtyczki do instalacji

- **Dataview** — query nad agent_memory (gdy pliki markdown)
- **Git** — auto-commit zmian wiki
- **Calendar** — widok log.md po datach

### File watcher (opcjonalnie)

```bash
# Gdy plik wiki/ zmieni się → zaindeksuj do supervisor_memory
inotifywait -m /home/tamiel/KlimtechRAG/wiki/ -e modify |
  while read path event file; do
    curl -X POST http://localhost:8000/v1/agent/memory \
      -d "{\"typ\": \"notatka_obsidian\", \"treść\": \"$(cat ${path}${file})\"}"
  done
```

---

## Elementy do zainstalowania (checklist)

### Laptop — już zainstalowane
- [x] Podman 4.9.3
- [x] Qdrant w kontenerze Podman (port 6333)
- [x] Python venv z FastAPI, qdrant-client

### Laptop — do instalacji
- [ ] OpenCode (`npm install -g @opencode-ai/opencode`)
- [ ] Obsidian (AppImage z obsidian.md)
- [ ] inotify-tools (`apt install inotify-tools`) — opcjonalnie do file watchera

### Serwer — do instalacji (gdy GPU1 dostępne)
- [ ] Qwen3-Coder-30B-A3B-Instruct-GGUF Q8_0 (~30GB)
- [ ] llama-server na porcie 8083, HIP_VISIBLE_DEVICES=1

### Kod — do napisania
- [ ] `backend_app/routes/agent_memory.py` — endpointy POST /v1/agent/memory, /v1/supervisor/snapshot, GET /v1/agent/memory/search
- [ ] Rejestracja routera w `backend_app/main.py`
- [ ] `scripts/session_snapshot.sh`

---

## Decyzje Architektoniczne

| Decyzja | Powód |
|---------|-------|
| Qdrant na laptopie dla agent/supervisor memory | Oddzielenie pamięci agentów od danych RAG serwera; laptop zawsze dostępny |
| Qwen3-Coder-30B-A3B zamiast Qwen2.5-Coder-32B | MoE: 3B aktywnych parametrów → 2-3x szybszy, mniejszy VRAM (18GB vs 20GB) |
| Sonnet jako jedyny writer do baz pamięci | Qwen3 nie może modyfikować swojej własnej historii — bezpieczeństwo i wiarygodność |
| wiki/ w katalogu projektu (nie osobny vault) | Git tracking zmian wiki; Obsidian może punkt do podkatalogu |
| dim=1024 dla agent/supervisor_memory | Ten sam embedder co klimtech_docs (e5-large) → spójność API |

---

## Historia Zmian

| Data | Co zmieniono |
|------|-------------|
| 2026-04-08 | Opracowanie planu, Faza 0 wdrożona (wiki/, AGENTS.md, CLAUDE.md) |
| 2026-04-08 | Faza 1 częściowo: kolekcje agent_memory + supervisor_memory (dim=1024) utworzone w Qdrant |
