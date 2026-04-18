# PLAN WDROŻENIA — MemPalace Patterns + Knowledge Graph dla KlimtechRAG

**Wersja:** 1.0
**Data:** 2026-04-12
**Repozytorium:** https://github.com/Satham666/KlimtechRAG
**Serwer:** lobo@hall9000 (192.168.31.70) | AMD Instinct 16GB | ROCm 7.2

---

## ARCHITEKTURA "ROBOTNIKÓW"

### Model Robotnik — dobór i uzasadnienie

Na karcie AMD Instinct 16GB VRAM, przy ograniczeniu ROCm (brak CUDA),
rekomendacja oparta na benchmarkach z kwietnia 2026:

#### ROBOTNIK GŁÓWNY: Qwen3-8B Q4_K_M (~5.5 GB VRAM)

**Dlaczego:**
- Najwyższy HumanEval w klasie <10B (76.0%) — kluczowe dla generowania kodu Python
- Natywne wsparcie llama.cpp z ROCm HIP (potwierdzone benchmarki)
- Tryb thinking/non-thinking (przełączalny) — reasoning gdy potrzebny
- Wielojęzyczny — rozumie polskie komentarze i docstringi
- Q4_K_M mieści się w ~5.5 GB VRAM z kontekstem 8192 tokenów
- Zostaje ~10 GB na KV cache i overhead

**Pobieranie:**
```bash
hf download Qwen/Qwen3-8B-GGUF qwen3-8b-q4_k_m.gguf \
  --local-dir /media/lobo/BACKUP/KlimtechRAG/modele_LLM/model_thinking/
```

**Uruchamianie jako robotnik (port 8083, osobny od głównego 8082):**
```bash
cd /media/lobo/BACKUP/KlimtechRAG/llama.cpp/build/bin/
HIP_VISIBLE_DEVICES=0 GPU_MAX_ALLOC_PERCENT=100 \
HSA_ENABLE_SDMA=0 HSA_OVERRIDE_GFX_VERSION=9.0.6 \
./llama-server \
  -m /media/lobo/BACKUP/KlimtechRAG/modele_LLM/model_thinking/qwen3-8b-q4_k_m.gguf \
  --host 127.0.0.1 --port 8083 \
  -ngl -1 -c 8192 -fa --jinja \
  --temp 0.3 --top-p 0.9 --repeat-penalty 1.1
```

#### ALTERNATYWA: Bielik-4.5B Q8_0 (~5 GB VRAM)

Użyj gdy zadanie wymaga generowania POLSKIEGO tekstu (docstringi, komentarze,
streszczenia dokumentów). Bielik jest gorszy od Qwen3 w kodzie, ale lepszy
w polskim. Już jest w stacku — zero dodatkowego pobierania.

#### TRYB DWÓCH ROBOTNIKÓW (sekwencyjny, NIE równoległy)

Na 16 GB VRAM nie uruchomisz dwóch llama-server naraz z modelami GPU.
Strategia: **pipeline sekwencyjny** sterowany skryptem Python:

```
[Qwen3-8B generuje kod] → pkill llama-server → sleep 5 →
[Bielik-4.5B recenzuje po polsku] → pkill llama-server → sleep 5 →
[zapisz wynik do Qdrant]
```

Skrypt orkiestracji: `worker_pipeline.py` (patrz plik 01_ROBOTNIK_SETUP.md)

---

## SYSTEM DZIENNIKA PRACY W QDRANT

Robotnicy zapisują swoją pracę do dedykowanej kolekcji Qdrant:

**Kolekcja:** `klimtech_worklog`
**Wymiar:** 1024 (ten sam e5-large co klimtech_docs)
**Payload:**
```json
{
  "task_id": "PHASE1_STEP3",
  "worker_model": "qwen3-8b-q4_k_m",
  "task_type": "code_generation | review | migration",
  "status": "done | error | needs_review",
  "input_file": "02_METADATA_HIERARCHY.md",
  "output_file": "backend_app/services/metadata_enrichment.py",
  "summary_pl": "Dodano funkcję enrich_payload() do ingest_service.py...",
  "code_diff": "--- a/backend_app/...\n+++ b/backend_app/...",
  "timestamp": "2026-04-13T14:30:00Z",
  "review_status": "pending_supervisor"
}
```

**Tworzenie kolekcji:**
```bash
curl -X PUT http://localhost:6333/collections/klimtech_worklog \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {"size": 1024, "distance": "Cosine"},
    "optimizers_config": {"indexing_threshold": 0}
  }'
```

**Jak supervisor (Claude/duży model) przegląda pracę:**
```bash
# Lista wszystkich zadań z statusem
curl -s http://localhost:6333/collections/klimtech_worklog/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 50, "with_payload": true}' | python3 -m json.tool

# Filtruj po statusie "needs_review"
curl -s http://localhost:6333/collections/klimtech_worklog/points/scroll \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 20,
    "with_payload": true,
    "filter": {
      "must": [{"key": "review_status", "match": {"value": "pending_supervisor"}}]
    }
  }' | python3 -m json.tool
```

---

## KOLEJNOŚĆ REALIZACJI

| # | Plik instrukcji | Faza | Czas | Zależności |
|---|----------------|------|------|------------|
| 01 | 01_ROBOTNIK_SETUP.md | Setup | 0.5 dnia | Brak |
| 02 | 02_METADATA_HIERARCHY.md | MemPalace | 2 dni | 01 |
| 03 | 03_TEMPORAL_METADATA.md | MemPalace | 1 dzień | 02 |
| 04 | 04_CONTEXT_LAYERS.md | MemPalace | 2 dni | 02 |
| 05 | 05_GRAPH_EDGES.md | Graf F1 | 2 dni | 02 |
| 06 | 06_GRAPH_API_VIZ.md | Graf F2 | 2 dni | 05 |
| 07 | 07_GRAPH_NER.md | Graf F3 | 2-3 dni | 06 |
| 08 | 08_SUPERVISOR_REVIEW.md | QA | 1 dzień | Wszystkie |

**Całkowity czas:** ~12-14 dni roboczych (1 developer + robotnicy)

### Zasady bezwzględne

1. **Jeden plik .md = jedno zadanie atomowe** — robotnik nie łączy zadań
2. **Każdy krok kończy się testem** — robotnik raportuje PASS/FAIL
3. **Kod ZAWSZE na laptopie** — nigdy bezpośrednio na serwerze
4. **Przed git push** — `bash scripts/check_project.sh` musi dać PASS
5. **VRAM guard** — przed uruchomieniem robotnika, sprawdź `rocm-smi`
6. **Worklog do Qdrant** — każde zakończone zadanie → punkt w klimtech_worklog

---

## GRAF ZALEŻNOŚCI

```
01_ROBOTNIK_SETUP
       ↓
02_METADATA_HIERARCHY ←── fundament dla wszystkiego
    ↓          ↓           ↓
03_TEMPORAL  04_LAYERS   05_GRAPH_EDGES
                              ↓
                         06_GRAPH_API_VIZ
                              ↓
                         07_GRAPH_NER (opcjonalny)
                              ↓
                    08_SUPERVISOR_REVIEW
```
