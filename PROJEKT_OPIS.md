# KlimtechRAG — Opis Projektu

Lokalny system RAG (Retrieval-Augmented Generation) zbudowany na FastAPI + Haystack + Qdrant.
Działa na serwerze z AMD Instinct 16 GB VRAM w sieci lokalnej.

---

## Infrastruktura (stan 2026-04-09)

### Hypervisor — Proxmox VE
| Właściwość | Wartość |
|------------|---------|
| System | Proxmox VE, kernel `6.17.2-1-pve`, Debian 13 Trixie |
| Hostname | `klimtech` |
| IP | `192.168.0.2/24`, gateway `192.168.0.1` |
| Web UI | `https://192.168.0.2:8006` |
| Zdalny dostęp | VPN lub SSH tunnel (do skonfigurowania) |

### Sprzęt serwera
| Komponent | Model | Uwagi |
|-----------|-------|-------|
| Płyta główna | GIGABYTE X870 EAGLE WIFI7 | AM5, DDR5, PCIe 5.0 |
| RAM | 32 GB DDR5 | |
| Dysk | NVMe 930 GB | LVM: root 96 GB, swap 8 GB, thin pool ~793 GB |
| LAN | Realtek RTL8125 2.5GbE | |
| WiFi | Realtek RTL8922AE WiFi 7 | |
| iGPU | AMD Granite Ridge [Radeon Graphics] | Ryzen iGPU |
| GPU (docelowa) | AMD Instinct 16 GB VRAM | **jeszcze niezamontowana** |
| GPU (przyszłość) | AMD Instinct 32 GB VRAM | GPU1 dla Qwen3-Coder |

### Topologia wdrożenia (aktualny stan ✅)
```
Proxmox VE host (192.168.0.2)
└── LXC 100 — Ubuntu 24.04 (192.168.0.3) ✅ ONLINE
    ├── KlimtechRAG backend (port 8000 / nginx HTTPS 8443) ✅ autostart
    ├── Qdrant (port 6333/6334) — Podman quadlet ✅
    ├── llama-server (port 8082) — LLM (Bielik/Qwen) — ręczny start
    └── Claude Code CLI (~/.local/bin/claude) ✅
```

### Stan instalacji
```
✅ Proxmox VE zainstalowany
✅ LXC 100 Ubuntu 24.04 uruchomiony (192.168.0.3)
✅ lobo user, SSH port 2222
✅ Python venv 3.12 (/home/lobo/KlimtechRAG/venv/)
✅ Qdrant w Podman quadlet systemd (port 6333)
✅ nginx HTTPS 8443 (self-signed cert RSA 4096, ważny do 2036)
✅ KlimtechRAG backend — autostart (systemd user service)
✅ loginctl enable-linger lobo (backend startuje po restarcie LXC)
✅ Claude Code CLI v2.1.97
⬜ AMD Instinct 16 GB — fizyczna instalacja + passthrough do LXC
⬜ Zdalny dostęp do Proxmox (VPN / SSH tunnel)
```

### Porty i usługi
| Port | Usługa | Gdzie |
|------|---------|-------|
| 8006 | Proxmox Web UI (HTTPS) | host 192.168.0.2 |
| 22 | SSH Proxmox host | host |
| 2222 | SSH LXC | LXC 192.168.0.3 |
| 8000 | KlimtechRAG backend (HTTP) | LXC |
| 8443 | KlimtechRAG backend (HTTPS nginx) | LXC |
| 8082 | llama-server (LLM) | LXC — ręczny start |
| 6333 | Qdrant REST | LXC |
| 6334 | Qdrant gRPC | LXC |

---

## Architektura

```
Użytkownik → UI (index.html) → nginx :8443 → FastAPI Backend :8000
                                                  ├── Qdrant :6333 — wektory dokumentów
                                                  ├── llama-server :8082 — LLM (Bielik/Qwen)
                                                  └── SQLite — file_registry.db + sessions.db
```

### Architektura agentowa (docelowa — wymaga GPU1 32GB)
```
Claude Sonnet 4.6 (laptop, API) — Mistrz/Nadzorca
  ├── czyta/pisze → supervisor_memory (Qdrant serwera)
  ├── czyta/pisze → agent_memory (Qdrant serwera)
  └── zleca zadania → Qwen3-Coder-30B-A3B (GPU1 :8083) — Uczeń
                          ├── czyta → agent_memory
                          └── edytuje kod, testuje na GPU0
```

---

## Główne funkcje (stan v7.8)

### RAG i czat
| Funkcja | Opis | Plik |
|---------|------|------|
| Chat completions | OpenAI-compatible `/v1/chat/completions` | routes/chat.py |
| RAG retrieval | Hybrid search: dense + BM25 + reranking | services/retrieval_service.py |
| Smart Router | Auto-decyzja RAG vs Direct LLM | services/router_service.py |
| Ingest pipeline | PDF/TXT/DOCX → chunk → embed → Qdrant | services/ingest_service.py |
| SSE streaming | Token-by-token chat + postęp ingestu | services/streaming_service.py |
| Session history | Persistentna historia czatu (SQLite) | services/session_service.py |
| Answer Verification | Drugi pass LLM weryfikujący odpowiedź | services/verification_service.py |

### Multimedia i wizja
| Funkcja | Opis | Plik |
|---------|------|------|
| ColPali | Multi-vector PDF visual indexing | services/colpali_embedder.py |
| VLM | Analiza obrazów (Qwen2.5-VL) | services/vlm_service.py |

### Integracje i narzędzia
| Funkcja | Opis | Plik |
|---------|------|------|
| MCP Compatibility | JSON-RPC 2.0: rag_query/list_documents/ingest_text | routes/mcp.py |
| Watcher | Asyncio background task monitorujący upload dirs | services/watcher_service.py |
| Batch Processing | Priority queue z retry i exponential backoff | services/batch_service.py |
| Embeddable Widget | Self-contained JS bubble chat | static/klimtech-widget.js |
| Workspaces | Izolowane przestrzenie dokumentów | routes/workspaces.py |
| Web Search | DuckDuckGo search (duckduckgo-search v8) | routes/web_search.py |

### Pamięć agentów (Qdrant)
| Funkcja | Opis | Plik |
|---------|------|------|
| agent_memory | POST/GET pamięć błędów i decyzji agentów | routes/agent_memory.py |
| supervisor_memory | POST/GET snapshoty sesji dla Sonnet | routes/supervisor_memory.py |

---

## Kolekcje Qdrant (serwer hall9000)

| Kolekcja | Wymiar | Model | Przeznaczenie |
|----------|--------|-------|---------------|
| `klimtech_docs` | 1024 | multilingual-e5-large | Dokumenty RAG projektu |
| `klimtech_colpali` | 128 | ColPali v1.3 | Visual PDF indexing |
| `agent_memory` | 1024 | multilingual-e5-large | Pamięć agentów (błędy, decyzje) |
| `supervisor_memory` | 1024 | multilingual-e5-large | Snapshoty sesji Sonnet |

### Laptop Qdrant (osobny, port 6333)
Laptop posiada własny Qdrant (Podman quadlet) z kolekcjami `agent_memory` i `supervisor_memory`.
Służy jako **lokalna baza wiedzy** — od czasu do czasu synchronizowana z serwerem.
Docelowo: lokalny mały model na laptopie będzie zapisywał wiedzę do laptopowego Qdrant,
a wybrane wpisy będą przesyłane do głównej bazy RAG na serwerze.

---

## Endpointy pamięci agentów

### POST /v1/agent/memory
Zapisuje wpis do `agent_memory` (błędy agenta, decyzje, wzorce sukcesu).
```json
{
  "typ": "błąd_agenta | decyzja | uwaga_sonnet | wynik_testu | wzorzec_sukcesu | snapshot",
  "content": "opis zdarzenia",
  "meta": {}
}
```

### POST /v1/supervisor/snapshot
Zapisuje snapshot stanu sesji do `supervisor_memory`.
```json
{
  "typ": "snapshot",
  "ostatni_krok": "co zostało zrobione",
  "nastepny_krok": "co zrobić następnym razem",
  "git_status": ["plik.py M"],
  "uwagi": "dodatkowe uwagi"
}
```

### GET /v1/agent/memory/search?q=...&limit=5&typ=...
### GET /v1/supervisor/memory/search?q=...&limit=5
### GET /v1/agent/memory/recent?limit=10
### GET /v1/supervisor/memory/recent?limit=10

---

## Zmienne środowiskowe (kluczowe)

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `KLIMTECH_BASE_PATH` | auto | Ścieżka bazowa projektu |
| `KLIMTECH_EMBEDDING_DEVICE` | `cpu` | `cpu` lub `cuda:0` |
| `KLIMTECH_API_KEY` | `sk-local` | Klucz API (wymagany w nagłówku) |
| `KLIMTECH_QDRANT_URL` | `http://localhost:6333` | URL Qdrant |
| `KLIMTECH_LLM_BASE_URL` | `http://localhost:8082/v1` | URL llama-server |
| `KLIMTECH_ANSWER_VERIFICATION` | `false` | B5 weryfikacja odpowiedzi |
| `KLIMTECH_WATCHER_ENABLED` | `false` | H2 watcher katalogów |
| `LOG_LEVEL` | `INFO` | Poziom logowania |

---

## Uruchomienie (LXC hall9000, użytkownik lobo)

```fish
# Manualne (debug)
cd /home/lobo/KlimtechRAG
source venv/bin/activate.fish
bash scripts/check_project.sh
python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000

# Autostart (systemd user service — działa automatycznie)
systemctl --user status klimtech-backend.service
```

### SSH do serwera
```bash
ssh lobo@192.168.0.3 -p 2222
```

---

## Embed widget (sieć lokalna)

```html
<script>
  window.KlimtechWidget = { apiUrl: "https://192.168.0.3:8443", apiKey: "sk-local", useRag: true };
</script>
<script src="https://192.168.0.3:8443/static/klimtech-widget.js"></script>
```

---

## Do zrobienia (kolejność)

| # | Zadanie | Status |
|---|---------|--------|
| 1 | supervisor_memory endpoint | 🔄 w toku |
| 2 | Kolekcja supervisor_memory w Qdrant | ⬜ |
| 3 | Zdalny dostęp do Proxmox (VPN/tunnel) | ⬜ |
| 4 | AMD Instinct 16 GB — fizyczna instalacja | ⬜ |
| 5 | GPU1 32 GB + Qwen3-Coder | ⬜ zależy od GPU1 |
| 6 | C5 Late Chunking | ⬜ |
| 7 | W6 Agent Builder | ⬜ |
| 8 | Obsidian Dashboard | ⬜ opcjonalne |
