# 01_ROBOTNIK_SETUP — Konfiguracja systemu robotników

**Zadanie:** Skonfiguruj infrastrukturę do uruchamiania modeli-robotników
**Czas:** 0.5 dnia
**Zależności:** Brak
**VRAM:** 0 MB (sam setup, bez modeli)

---

## KONTEKST DLA ROBOTNIKA

Pracujesz w projekcie KlimtechRAG — offline'owy system RAG po polsku.
Serwer: lobo@hall9000, GPU: AMD Instinct 16GB, ROCm 7.2.
Kod edytujesz w katalogu: `/media/lobo/BACKUP/KlimtechRAG/` na laptopie,
potem push do GitHub, potem pull na serwerze.
Shell na serwerze: fish (NIE obsługuje heredoc `<< EOF`).
Backend: FastAPI na porcie 8000, llama-server na porcie 8082.
Qdrant: localhost:6333.
Python venv: `/home/lobo/klimtech_venv/`
JS w Python stringach: używaj konkatenacji (+) i var, NIE backticks/const/let.

---

## KROK 1: Pobierz model Qwen3-8B GGUF

Na serwerze hall9000:

```bash
source /home/lobo/klimtech_venv/bin/activate.fish
cd /media/lobo/BACKUP/KlimtechRAG

hf download Qwen/Qwen3-8B-GGUF qwen3-8b-q4_k_m.gguf \
  --local-dir modele_LLM/model_thinking/
```

**Test:** Sprawdź czy plik istnieje i ma rozsądny rozmiar (~5 GB):
```bash
ls -lh modele_LLM/model_thinking/qwen3-8b-q4_k_m.gguf
```
**Oczekiwany wynik:** Plik ~4.9-5.5 GB. Jeśli brak — sprawdź `hf` CLI.

---

## KROK 2: Utwórz kolekcję worklog w Qdrant

```bash
curl -X PUT http://localhost:6333/collections/klimtech_worklog \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {"size": 1024, "distance": "Cosine"},
    "optimizers_config": {"indexing_threshold": 0}
  }'
```

**Test:**
```bash
curl -s http://localhost:6333/collections/klimtech_worklog | python3 -m json.tool
```
**Oczekiwany wynik:** JSON z `"status": "green"` i `"vectors_count": 0`

---

## KROK 3: Utwórz skrypt orkiestracji worker_pipeline.py

Na laptopie, utwórz plik `backend_app/scripts/worker_pipeline.py`:

```python
#!/usr/bin/env python3
"""
worker_pipeline.py — Orkiestracja robotników LLM dla KlimtechRAG.

Uruchamia model-robotnik (Qwen3-8B lub Bielik-4.5B) na porcie 8083,
wysyła zadanie z pliku .md, zapisuje wynik do Qdrant worklog.

Użycie:
    python3 worker_pipeline.py --task 02_METADATA_HIERARCHY.md --model qwen3
    python3 worker_pipeline.py --task 02_METADATA_HIERARCHY.md --model bielik
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("worker")

BASE_DIR = Path("/media/lobo/BACKUP/KlimtechRAG")
LLAMA_BIN = BASE_DIR / "llama.cpp" / "build" / "bin" / "llama-server"
WORKER_PORT = "8083"
QDRANT_URL = "http://localhost:6333"
WORKLOG_COLLECTION = "klimtech_worklog"

MODELS = {
    "qwen3": {
        "path": str(BASE_DIR / "modele_LLM" / "model_thinking" / "qwen3-8b-q4_k_m.gguf"),
        "name": "qwen3-8b-q4_k_m",
        "context": "8192",
    },
    "bielik": {
        "path": str(BASE_DIR / "modele_LLM" / "model_thinking" / "Bielik-4.5B-v3.0-Instruct-Q8_0.gguf"),
        "name": "bielik-4.5b-q8_0",
        "context": "8192",
    },
}

AMD_ENV = {
    "HIP_VISIBLE_DEVICES": "0",
    "GPU_MAX_ALLOC_PERCENT": "100",
    "HSA_ENABLE_SDMA": "0",
    "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
}


def stop_worker():
    """Zatrzymaj robotnika na porcie 8083."""
    subprocess.run(["pkill", "-f", "llama-server.*8083"], capture_output=True)
    time.sleep(5)
    logger.info("Worker zatrzymany")


def start_worker(model_key: str) -> bool:
    """Uruchom llama-server jako robotnika."""
    model = MODELS[model_key]
    if not os.path.exists(model["path"]):
        logger.error("Model nie istnieje: %s", model["path"])
        return False

    stop_worker()

    env = os.environ.copy()
    env.update(AMD_ENV)

    cmd = [
        str(LLAMA_BIN),
        "-m", model["path"],
        "--host", "127.0.0.1",
        "--port", WORKER_PORT,
        "-ngl", "-1",
        "-c", model["context"],
        "-fa",
        "--temp", "0.3",
        "--top-p", "0.9",
    ]

    logger.info("Uruchamiam: %s", model["name"])
    subprocess.Popen(
        cmd,
        cwd=str(LLAMA_BIN.parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Czekaj na gotowość (max 120s)
    for i in range(60):
        time.sleep(2)
        try:
            r = httpx.get(
                "http://127.0.0.1:" + WORKER_PORT + "/health",
                timeout=3,
            )
            if r.status_code == 200:
                logger.info("Worker gotowy po %d s", (i + 1) * 2)
                return True
        except Exception:
            pass
    logger.error("Worker nie odpowiada po 120s")
    return False


def send_task(task_content: str, system_prompt: str = "") -> str:
    """Wyślij zadanie do robotnika i odbierz odpowiedź."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": task_content})

    try:
        r = httpx.post(
            "http://127.0.0.1:" + WORKER_PORT + "/v1/chat/completions",
            json={
                "model": "worker",
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.3,
            },
            timeout=300,
        )
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("Błąd komunikacji z workerem: %s", e)
        return ""


def log_to_qdrant(task_id: str, model_name: str, task_type: str,
                  status: str, input_file: str, output: str):
    """Zapisz wynik pracy do kolekcji klimtech_worklog."""
    import uuid

    # Embed summary dla wyszukiwania
    try:
        embed_r = httpx.post(
            "http://localhost:8000/v1/embeddings",
            json={"input": output[:500]},
            headers={"Authorization": "Bearer sk-local"},
            timeout=30,
        )
        vector = embed_r.json()["data"][0]["embedding"]
    except Exception:
        vector = [0.0] * 1024
        logger.warning("Nie udało się embedować — wektor zerowy")

    point = {
        "id": str(uuid.uuid4()),
        "vector": vector,
        "payload": {
            "task_id": task_id,
            "worker_model": model_name,
            "task_type": task_type,
            "status": status,
            "input_file": input_file,
            "summary_pl": output[:1000],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "review_status": "pending_supervisor",
        },
    }

    try:
        httpx.put(
            QDRANT_URL + "/collections/" + WORKLOG_COLLECTION + "/points",
            json={"points": [point]},
            timeout=10,
        )
        logger.info("Zapisano do worklog: %s", task_id)
    except Exception as e:
        logger.error("Błąd zapisu do Qdrant: %s", e)


def main():
    parser = argparse.ArgumentParser(description="KlimtechRAG Worker Pipeline")
    parser.add_argument("--task", required=True, help="Plik .md z zadaniem")
    parser.add_argument("--model", default="qwen3", choices=["qwen3", "bielik"])
    parser.add_argument("--step", type=int, default=0, help="Numer kroku (0=wszystkie)")
    args = parser.parse_args()

    task_path = Path(args.task)
    if not task_path.exists():
        logger.error("Plik nie istnieje: %s", task_path)
        sys.exit(1)

    task_content = task_path.read_text(encoding="utf-8")
    task_id = task_path.stem

    # Sprawdź czy główny llama-server (8082) jest wyłączony
    try:
        r = httpx.get("http://localhost:8082/health", timeout=2)
        if r.status_code == 200:
            logger.warning("UWAGA: llama-server działa na 8082. Zatrzymaj go przed uruchomieniem robotnika!")
            logger.warning("Użyj: curl -X POST http://localhost:8000/model/stop")
            sys.exit(1)
    except Exception:
        pass  # OK — port wolny

    if not start_worker(args.model):
        sys.exit(1)

    system_prompt = (
        "Jesteś programistą Python pracującym w projekcie KlimtechRAG. "
        "Piszesz czysty kod: snake_case, type hints, docstringi. "
        "Nie używasz eval/exec/pickle. Nie hardcodujesz sekretów. "
        "Backend to FastAPI, baza wektorowa to Qdrant (localhost:6333). "
        "Kolekcje: klimtech_docs (dim=1024), klimtech_colpali (dim=128). "
        "Embeddingi: intfloat/multilingual-e5-large. "
        "Odpowiadaj TYLKO kodem i krótkimi komentarzami. Bez gadania."
    )

    logger.info("Wysyłam zadanie: %s", task_id)
    result = send_task(task_content, system_prompt)

    if result:
        output_path = Path("worker_output") / (task_id + "_output.md")
        output_path.parent.mkdir(exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        logger.info("Wynik zapisany: %s", output_path)

        log_to_qdrant(
            task_id=task_id,
            model_name=MODELS[args.model]["name"],
            task_type="code_generation",
            status="done",
            input_file=str(task_path),
            output=result,
        )
    else:
        log_to_qdrant(
            task_id=task_id,
            model_name=MODELS[args.model]["name"],
            task_type="code_generation",
            status="error",
            input_file=str(task_path),
            output="Brak odpowiedzi od modelu",
        )

    stop_worker()


if __name__ == "__main__":
    main()
```

**Test:** Na serwerze (po git pull):
```bash
python3 backend_app/scripts/worker_pipeline.py --help
```
**Oczekiwany wynik:** Wyświetla help z opcjami --task, --model, --step.

---

## KROK 4: Dodaj httpx do requirements (jeśli brak)

```bash
grep -q "httpx" requirements.txt || echo "httpx>=0.27.0" >> requirements.txt
pip install httpx --break-system-packages
```

---

## KROK 5: Test integracyjny

1. Zatrzymaj główny llama-server: `curl -X POST http://localhost:8000/model/stop -H "Authorization: Bearer sk-local"`
2. Poczekaj 10s
3. Uruchom test:
```bash
python3 backend_app/scripts/worker_pipeline.py \
  --task docs/test_task.md --model qwen3
```

Plik testowy `docs/test_task.md`:
```markdown
# TEST: Wygeneruj prostą funkcję Python

Napisz funkcję Python:
- Nazwa: `health_check`
- Przyjmuje: `url: str`
- Zwraca: `dict` z kluczami "status" (bool) i "latency_ms" (float)
- Używa httpx z timeout 5s
- Type hints, docstring po polsku
- Obsługa wyjątków (zwraca status=False przy błędzie)
```

**Oczekiwany wynik:**
- Worker uruchomiony na porcie 8083
- Odpowiedź z kodem funkcji health_check
- Punkt w kolekcji klimtech_worklog
- Worker zatrzymany

---

## RAPORTOWANIE

Po zakończeniu kroków 1-5, zapisz status:

| Krok | Status | Uwagi |
|------|--------|-------|
| 1. Pobieranie Qwen3-8B | PASS/FAIL | rozmiar pliku |
| 2. Kolekcja worklog | PASS/FAIL | status kolekcji |
| 3. worker_pipeline.py | PASS/FAIL | --help działa |
| 4. httpx | PASS/FAIL | import działa |
| 5. Test integracyjny | PASS/FAIL | punkt w Qdrant |
