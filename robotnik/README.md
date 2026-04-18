# Robotnik — lokalny LLM executor

**Architektura:** Claude myśli (planuje, reviewuje), Qwen realizuje (pisze kod).

**Faza 01 (ta implementacja):** laptop — Qwen2.5-Coder-3B-Q8_0 na Quadro P1000 via `llama-cli`.
**Faza 02 (przyszła):** Proxmox — większy model (Qwen-7B Q4 / DeepSeek-Coder-V2-Lite) via `llama-server` na AMD Instinct.

---

## Profil: laptop (domyślny)

- **GPU:** Quadro P1000 (Pascal CC 6.1, 4 GB VRAM)
- **Model:** Qwen2.5-Coder-3B-Q8_0 (~3.3 GB)
- **Wydajność:** Prompt 286 t/s, Generation 14.1 t/s, EOS natural, brak OOM
- **Kontekst:** 4096 (mieści się dzięki `-fa on -ctk q8_0 -ctv q8_0`)

### Uruchomienie CLI (jednorazowe zadanie)

```bash
# Python wrapper (streaming output do stdout)
python3 -m robotnik.runner robotnik_tasks/001_wireguard.md

# Lub z zapisem do pliku
python3 -m robotnik.runner robotnik_tasks/001_wireguard.md --out robotnik_output/001.py

# Bash wrapper (bezpośrednio Złota Komenda)
./scripts/robotnik.sh robotnik_tasks/001_wireguard.md
```

### Uruchomienie Server (daemon HTTP, OpenAI-compatible)

```bash
./scripts/robotnik_server.sh start
./scripts/robotnik_server.sh status
./scripts/robotnik_server.sh stop

# Test endpointu
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen","messages":[{"role":"user","content":"Hello"}]}'
```

---

## Profil: proxmox (przyszłość)

- **GPU:** AMD Instinct MI25 (gfx906, 16 GB VRAM, ROCm)
- **Model:** Qwen2.5-Coder-7B-Instruct-Q4_K_M (~4.5 GB) lub większy
- **Kontekst:** 8192

### Aktywacja profilu

```bash
export ROBOTNIK_PROFILE=proxmox
# Plus wymagane env vars ROCm:
export HIP_VISIBLE_DEVICES=0
export GPU_MAX_ALLOC_PERCENT=100
export HSA_ENABLE_SDMA=0
export HSA_OVERRIDE_GFX_VERSION=9.0.6

python3 -m robotnik.runner robotnik_tasks/001_task.md
```

Env vars są także dostępne jako `robotnik.config.AMD_ROCM_ENV` dict.

---

## Workflow: Claude → Qwen → Claude

1. **Claude tworzy task** w `robotnik_tasks/NNN_<slug>.md` (specyfikacja, ograniczenia, wymagania)
2. **Qwen realizuje**: `python3 -m robotnik.runner robotnik_tasks/NNN_<slug>.md --out robotnik_output/NNN.py`
3. **Claude review**: czyta output, walidacja, merge do właściwego miejsca w repo

Szablony zadań: `robotnik/prompts/templates.py` (`CODE_TASK`, `REFACTOR_TASK`, `TEST_TASK`, `DOCSTRING_TASK`).

Katalogi `robotnik_tasks/` i `robotnik_output/` są w `.gitignore` — surowe artefakty
nie są wersjonowane, tylko finalny zmergowany kod.

---

## Struktura

```
robotnik/
├── __init__.py
├── config.py           # LAPTOP_CONFIG, PROXMOX_CONFIG, AMD_ROCM_ENV
├── runner.py           # subprocess wrapper dla llama-cli
├── server.py           # daemon wrapper dla llama-server
├── README.md           # ten plik
└── prompts/
    └── templates.py    # CODE / REFACTOR / TEST / DOCSTRING

scripts/
├── robotnik.sh         # bash artefakt Złotej Komendy
└── robotnik_server.sh  # bash wrapper dla serwera
```

---

## Referencje

- `GPU_LAPTOPT_TEST.md` — dziennik testów wydajności i ustalenie Złotej Komendy v1.0
- `prompt.txt` — przykładowy produkcyjny prompt (WireGuard site-to-site)
