# status.md — Aktualny Stan Projektu KlimtechRAG
*Aktualizuj na końcu każdej sesji. To jest "punkt wejścia" dla nowej sesji Claude Code.*

---

## Stan na: 2026-04-09

### Co właśnie skończyliśmy (sesja Faza 5 — uruchomienie w LXC hall9000)

- **Krok 1:** remote zmieniony SSH → HTTPS (`git fetch` działa bez kluczy)
- **Krok 2:** Python venv + `pip install -r requirements.txt` (requirements.txt stworzony od zera)
- **Krok 3:** SSL cert self-signed RSA 4096, SAN 192.168.0.3, ważny do 2036
- **Krok 4:** nginx zainstalowany + konfiguracja HTTPS 8443 → proxy do :8000
- **Krok 5:** Qdrant v1.17.1 w Podman quadlet systemd (Network=host + PodmanArgs — LXC nie ma /dev/net/tun)
- **Krok 6:** `.env` skonfigurowany, katalogi data/ i logs/ stworzone
- **Fix globalny:** zamieniono wszystkie ścieżki `/media/lobo/BACKUP/KlimtechRAG` → `/home/lobo/KlimtechRAG` w całym projekcie (config.py, model_manager.py, start scripts, n8n workflows, server_setup/, scripts/)
- **Backend działa:** `curl http://localhost:8000/health` → `{"status":"ok","qdrant":true}`
- **nginx działa:** `curl -sk https://localhost:8443/health` → OK

### Aktualny stan

**LXC hall9000 (192.168.0.3) — PLATFORMA AKTYWNA:**
- SSH: `ssh lobo@192.168.0.3 -p 2222` ✅
- Repo: `/home/lobo/KlimtechRAG/` ✅
- Claude Code: `~/.local/bin/claude` v2.1.97 ✅
- venv Python 3.12: `/home/lobo/KlimtechRAG/venv/` ✅
- Qdrant (Podman quadlet): port 6333 ✅
- `.env`: skonfigurowany ✅
- nginx HTTPS 8443: ✅
- Backend KlimtechRAG: **OFFLINE** (tylko test, nie autostart) ⬜
- AMD Instinct 16 GB: **NIE zamontowana fizycznie** ⬜

### Co zostało do zrobienia (kolejność)

#### Priorytet 1 — autostart backendu
- [ ] Systemd unit dla uvicorn (user service) — żeby backend startował przy restarcie LXC
- [ ] Test pełnego stacku po restarcie LXC

#### Priorytet 2 — pakiety opcjonalne (tylko WARN, nie blokują)
- [ ] `pip install duckduckgo-search trafilatura` — używane przez niektóre trasy
- [ ] `model_switch.py:135` — zmienić `regex=` na `pattern=` (FastAPI deprecation)

#### Priorytet 3 — agent_memory endpoint
- [ ] `backend_app/routes/agent_memory.py` — POST /v1/agent/memory, GET search
- [ ] Rejestracja w `backend_app/main.py`

#### Odłożone
- AMD Instinct 16 GB — fizyczna instalacja + passthrough do LXC
- C5 Late Chunking, W6 Agent Builder, Obsidian Dashboard

### Pliki krytyczne — ostatnio modyfikowane
```
backend_app/config.py               — ścieżka /home/lobo/KlimtechRAG
backend_app/services/model_manager.py — j.w.
requirements.txt                    — nowy (stworzony w tej sesji)
ssl/cert.pem, ssl/key.pem          — nowe (self-signed)
ssl/klimtech_nginx.conf             — kopia konfigu nginx
wiki/                               — zaktualizowane
```

### Numer wersji następnego release
Ostatni tag: `v7.7`
Następny: `v7.8` (Faza 5 ukończona)

---

## Szablon dla Następnej Sesji

```
Przeczytałem wiki/status.md.
Kontynuujemy od: autostart backendu (systemd unit dla uvicorn)
Serwer online: tak (hall9000 192.168.0.3)
Qdrant: aktywny (quadlet systemd)
Backend: wymaga ręcznego startu
```
