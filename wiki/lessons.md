# lessons.md — Lekcje, Błędy i Odkrycia KlimtechRAG
*Każdy bug który naprawiłeś, każde odkrycie — trafia tutaj. Żeby nie powtarzać.*

---

## Instalacja Ubuntu — Sprzęt X870 Eagle WiFi7

### LAN (Intel I226-V 2.5GbE) — brak/niestabilne połączenie
**Problem:** Sterownik `igc` ma bugi na kernelach < 6.2. Losowe resety lub brak sieci.  
**Fix 1 — wyłącz Energy Efficient Ethernet:**
```bash
sudo ethtool -s enp*s0 eee off
```
**Fix 2 — zaktualizuj kernel przez HWE (jeśli < 6.5):**
```bash
sudo apt install linux-generic-hwe-24.04
```
**Diagnostyka:** `lspci | grep -i ethernet; dmesg | grep igc`

### WiFi 7 (MediaTek MT7925) — karta niewidoczna
**Problem:** Sterownik `mt7925e` jest w kernelu od 6.6, ale firmware może być brakujący w Ubuntu 24.04.  
**Fix 1 — zainstaluj firmware:**
```bash
sudo apt install linux-firmware
```
**Fix 2 — sprawdź czy firmware MT7925 jest załadowany:**
```bash
dmesg | grep mt7925
ls /lib/firmware/mediatek/ | grep mt7925
```
**Diagnostyka:** `lspci | grep -i network; iwconfig`

### GRUB — menu niewidoczne przy bootowaniu
**Problem:** Ubuntu 24.04 domyślnie ukrywa GRUB (`GRUB_TIMEOUT_STYLE=hidden`, `GRUB_TIMEOUT=0`).  
**Fix — edytuj `/etc/default/grub`:**
```
GRUB_TIMEOUT_STYLE=menu
GRUB_TIMEOUT=5
```
Następnie: `sudo update-grub`  
**Uwaga:** Na systemach UEFI z `systemd-boot` zamiast GRUB — przytrzymaj `Space` lub `Esc` przy starcie.

---

## Shell i Składnia

### Fish shell — brak heredoc
**Błąd:** `cat << 'EOF' ... EOF` nie działa w fish shell na serwerze.  
**Fix:** Używaj `python3 -c "print('...')"` lub osobnego pliku .py.  
**Gdzie:** Wszystkie komendy SSH na serwer hall9000.

### Backslash na końcu linii w komendach
**Błąd:** Komendy z `\` na końcu linii kopiowane przez zsh/bash dają błędy.  
**Fix:** Zawsze jedna linia lub łącz przez `;` (nie `&&` przy fish).  
**Przykład złe:** `curl http://localhost \` → **Dobre:** `curl http://localhost -H "key: val"`

### Backtick w Python f-strings z JS
**Błąd:** `f"<script>var x = \`{value}\`</script>"` → SyntaxWarning Python + SyntaxError w przeglądarce.  
**Fix:** `"<script>var x = " + str(value) + "</script>"` — zawsze concatenation i `var`.

---

## VRAM i GPU

### Eager loading = OOM na starcie
**Błąd:** Importowanie embeddings.py na poziomie modułu ładuje e5-large od razu → 4.5 GB VRAM.  
**Fix:** Lazy singleton — `_model = None; def get(): global _model; if _model is None: _model = load()`.  
**Plik:** `backend_app/services/embeddings.py` — NIE ZMIENIAĆ.

### LLM i embedding nie mogą współistnieć
**Błąd:** Próba załadowania e5-large gdy Bielik-11B załadowany → OOM kill.  
**Fix:** Przed ingestem → `/model/stop` + `pkill -f llama-server` + sprawdź VRAM < 500 MB.

### libmtmd.so.0 — llama-server z pełną ścieżką
**Błąd:** `llama-server model.gguf` czasem nie znajdzie `libmtmd.so.0`.  
**Fix:** Uruchamiaj z pełną ścieżką do binarki: `/path/to/llama-server`.

---

## Bezpieczeństwo

### SQL string interpolation w list_files()
**Błąd:** `query += f" ORDER BY filename LIMIT {limit}"` — podatność SQL injection.  
**Fix:** `query += " ORDER BY filename LIMIT ?"; params.append(limit)`.  
**Plik:** `backend_app/file_registry.py:272`

### Endpoint /gpu/status bez auth
**Błąd:** `router = APIRouter(tags=["gpu"])` — brak `Depends(require_api_key)`.  
**Fix:** `router = APIRouter(tags=["gpu"], dependencies=[Depends(require_api_key)])`.  
**Plik:** `backend_app/routes/gpu_status.py`

### Log level DEBUG w produkcji
**Błąd:** `os.getenv("LOG_LEVEL", "DEBUG")` — defaultowo DEBUG = logi wrażliwych danych.  
**Fix:** `os.getenv("LOG_LEVEL", "INFO")` jako domyślny.  
**Plik:** `backend_app/config.py:setup_logging()`

---

## Import i Moduły

### get_indexing_pipeline — brakujący import w _run_indexing()
**Błąd:** `_run_indexing()` w `ingest_service.py` wywoływał `get_indexing_pipeline()` bez importu.  
**Fix:** Dodać `from ..services import get_indexing_pipeline` na początku funkcji `_run_indexing()`.  
**Plik:** `backend_app/services/ingest_service.py`



### Circular imports przy nowych plikach w backend_app/
**Zasada:** Przy tworzeniu nowego pliku w `backend_app/` zawsze sprawdź czy nie importuje z miejsca które już importuje ten plik.  
**Jak sprawdzić:** `python3 -c "from backend_app.routes.nowy_plik import router"` po dodaniu.

---

## Qdrant

### Kolekcje — wymiar musi pasować do embeddera
**Zasada:** `klimtech_docs` i `agent_memory` i `supervisor_memory` → dim=1024 (e5-large).  
`klimtech_colpali` → dim=128 (ColPali multi-vector). NIE MIESZAJ.

### Qdrant na laptopie — już w Podman
**Odkrycie (2026-04-08):** Qdrant był już zainstalowany w kontenerze Podman, storage pusty.  
Quadlet systemd istnieje ale był inactive. Kontener uruchomiony ręcznie.  
**Fix:** Włączyć quadlet: `systemctl --user enable qdrant.service && systemctl --user start qdrant.service`

### Podman w LXC — brak /dev/net/tun (slirp4netns nie działa)
**Błąd (2026-04-09):** Rootless Podman w LXC Proxmox nie ma `/dev/net/tun` → slirp4netns failuje nawet z `Network=host` w quadlecie.  
**Fix w quadlecie:** Dodać `PodmanArgs=--network=host` OBOK `Network=host` — samo `Network=host` w sekcji `[Container]` nie wystarczy.  
**Weryfikacja:** `podman run --rm --network=host docker.io/qdrant/qdrant:latest` działa bezpośrednio.  
**Alternatywa długoterminowa:** Dodać `lxc.mount.entry = /dev/net/tun` w konfiguracji LXC na Proxmox hoście.

### _detect_base() — wczytuje się przed .env pydantic-settings
**Błąd (2026-04-09):** `_detect_base()` w `config.py` jest wywoływana na poziomie modułu → przed wczytaniem `.env` przez pydantic-settings → ignoruje `KLIMTECH_BASE_PATH` z `.env`.  
**Fix tymczasowy:** Eksportować zmienną przed startem: `KLIMTECH_BASE_PATH=/home/lobo/KlimtechRAG uvicorn ...`  
**Fix właściwy:** Zamienić hardcoded ścieżki w całym projekcie na prawidłowe — co zrobiono globalnym `sed` w tej sesji.

### scp do serwera — port 2222
**Zasada:** SSH/SCP na hall9000 działa na porcie 2222, nie 22.  
**Fix:** `scp -P 2222 plik lobo@192.168.0.3:/home/lobo/KlimtechRAG/` (wielka litera -P w scp)

---

## Git i Workflow

### MEMORY.md — trzeba przeczytać przed edycją
**Błąd:** Edit tool wymaga wcześniejszego Read — `"File has not been read yet"`.  
**Fix:** Zawsze `Read(MEMORY.md)` przed `Edit(MEMORY.md)`.

### git push — tylko użytkownik w osobnym terminalu
**Zasada:** Nigdy nie pushuj przez Bash tool. Użytkownik robi `git push` ręcznie z hasłem SSH.
