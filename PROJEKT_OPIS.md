# KlimtechRAG — Opis Projektu

Lokalny system RAG (Retrieval-Augmented Generation) zbudowany na FastAPI + Haystack + Qdrant.
Działa na serwerze z AMD Instinct 16 GB VRAM w sieci lokalnej.

## Infrastruktura Docelowa (stan 2026-04-08)

### Hypervisor — Proxmox VE
| Właściwość | Wartość |
|------------|---------|
| System | Proxmox VE, kernel `6.17.2-1-pve`, Debian 13 Trixie |
| Hostname | `klimtech` |
| IP | `192.168.0.2/24`, gateway `192.168.0.1` |
| Web UI | `https://192.168.0.2:8006` |

### Sprzęt serwera
| Komponent | Model | Uwagi |
|-----------|-------|-------|
| Płyta główna | GIGABYTE X870 EAGLE WIFI7 | AM5, DDR5, PCIe 5.0 |
| RAM | 32 GB DDR5 | |
| Dysk | NVMe 930 GB | LVM: root 96 GB, swap 8 GB, thin pool ~793 GB |
| LAN | **Realtek RTL8125** 2.5GbE | (nie Intel I226-V jak planowano) |
| WiFi | **Realtek RTL8922AE** WiFi 7 | (nie MediaTek MT7925) |
| iGPU | AMD Granite Ridge [Radeon Graphics] | Ryzen iGPU, `/dev/dri/renderD128`, `/dev/kfd` |
| GPU (docelowa) | AMD Instinct 16 GB VRAM | **jeszcze niezamontowana** — do instalacji |
| GPU (przyszłość) | AMD Instinct 32 GB VRAM | GPU1 dla Qwen3-Coder |

### Topologia wdrożenia
```
Proxmox VE host (192.168.0.2)
└── LXC 100 — Ubuntu 24.04 (192.168.0.3) [DO STWORZENIA]
    ├── KlimtechRAG backend (port 8000/8443)
    ├── Qdrant (port 6333/6334) — Podman quadlet
    ├── llama-server (port 8082) — LLM
    └── Claude Code CLI
```

### Stan instalacji (checklist)
```
✅ Proxmox VE zainstalowany
✅ Storage local-lvm (~793 GB dostępne)
✅ /dev/kfd i /dev/dri widoczne na hoście
✅ Repo KlimtechRAG w /root/KlimtechRAG (host)
⬜ Faza 2: GRUB, repo update, apt dist-upgrade
⬜ Faza 3: LXC Ubuntu 24.04 + GPU passthrough
⬜ Faza 4: lobo user, ROCm, SSH, firewall
⬜ Faza 5: KlimtechRAG + Qdrant w LXC
⬜ Faza 6: Claude Code CLI w LXC
⬜ AMD Instinct 16 GB — fizyczna instalacja + passthrough
```

### Porty i usługi (docelowo)
| Port | Usługa | Gdzie |
|------|---------|-------|
| 8006 | Proxmox Web UI (HTTPS) | host 192.168.0.2 |
| 22 | SSH Proxmox host | host |
| 2222 | SSH LXC | LXC 192.168.0.3 |
| 8000 | KlimtechRAG backend | LXC |
| 8443 | KlimtechRAG HTTPS | LXC |
| 8082 | llama-server (LLM) | LXC |
| 6333 | Qdrant REST | LXC |
| 6334 | Qdrant gRPC | LXC |

## Architektura

```
Użytkownik → UI (index.html) → FastAPI Backend (port 8000/8443)
                                    ├── Qdrant (port 6333) — wektory dokumentów
                                    ├── llama-server (port 8082) — LLM (Bielik/Qwen)
                                    └── SQLite — file_registry.db + sessions.db
```

## Główne funkcje (stan v7.7)

| Funkcja | Opis | Plik |
|---------|------|------|
| Chat completions | OpenAI-compatible `/v1/chat/completions` | routes/chat.py |
| RAG retrieval | Hybrid search: dense + BM25 + reranking | services/retrieval_service.py |
| Smart Router | Auto-decyzja RAG vs Direct LLM | services/router_service.py |
| Ingest pipeline | PDF/TXT/DOCX → chunk → embed → Qdrant | services/ingest_service.py |
| SSE streaming | Token-by-token chat + postęp ingestu | services/streaming_service.py |
| Session history | Persistentna historia czatu (SQLite) | services/session_service.py |
| MCP Compatibility | JSON-RPC 2.0: rag_query/list_documents/ingest_text | routes/mcp.py |
| Answer Verification | Drugi pass LLM weryfikujący odpowiedź | services/verification_service.py |
| Watcher | Asyncio background task monitorujący upload dirs | services/watcher_service.py |
| Batch Processing | Priority queue z retry i exponential backoff | services/batch_service.py |
| Embeddable Widget | Self-contained JS bubble chat | static/klimtech-widget.js |
| ColPali | Multi-vector PDF visual indexing | services/colpali_embedder.py |
| VLM | Analiza obrazów (Qwen2.5-VL) | services/vlm_service.py |
| Workspaces | Izolowane przestrzenie dokumentów | routes/workspaces.py |

## Zmienne środowiskowe (kluczowe)

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `KLIMTECH_BASE_PATH` | auto | Ścieżka bazowa projektu |
| `KLIMTECH_EMBEDDING_DEVICE` | `cpu` | `cpu` lub `cuda:0` |
| `KLIMTECH_ANSWER_VERIFICATION` | `false` | B5 weryfikacja odpowiedzi |
| `KLIMTECH_WATCHER_ENABLED` | `false` | H2 watcher katalogów |
| `KLIMTECH_CONTEXTUAL_ENRICHMENT` | `false` | C4 enrichment chunków |
| `KLIMTECH_BM25_WEIGHT` | `0.3` | Waga BM25 w hybrid search |

## Kolekcje Qdrant

| Kolekcja | Wymiar | Model |
|----------|--------|-------|
| `klimtech_docs` | 1024 | multilingual-e5-large |
| `klimtech_colpali` | 128 | ColPali v1.3 |

## Uruchomienie (docelowo w LXC, użytkownik lobo)

```fish
cd /home/lobo/KlimtechRAG
source venv/bin/activate.fish
bash scripts/check_project.sh
python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000
```

## Embed widget (sieć lokalna)

```html
<script>
  window.KlimtechWidget = { apiUrl: "http://192.168.0.3:8000", apiKey: "sk-local", useRag: true };
</script>
<script src="http://192.168.0.3:8000/static/klimtech-widget.js"></script>
```
