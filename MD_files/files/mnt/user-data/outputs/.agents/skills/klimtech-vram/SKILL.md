---
name: klimtech-vram
description: Zarządzanie VRAM i GPU dla KlimtechRAG — AMD Instinct 16GB/ROCm. Protokół bezpiecznego ingestu ColPali, reguły współdzielenia GPU, procedury po OOM kill. Użyj przed każdą operacją ingestu lub zmiany modelu.
compatibility: opencode
metadata:
  project: KlimtechRAG
  phase: gpu-management
---

# klimtech-vram — Zarządzanie VRAM i GPU

## Zasady bezwzględne (Zero Exceptions)

| Reguła | Opis |
|---|---|
| **Reguła 1** | Tylko **JEDEN** model na GPU naraz — zawsze |
| **Reguła 2** | Przed ColPali/VLM → `pkill -f llama-server`, czekaj 10s, sprawdź `/gpu/status` |
| **Reguła 3** | NIE ładuj embedding (e5-large) gdy LLM jest załadowany → OOM kill |
| **Reguła 4** | Po OOM kill backend może mieć zombie state → wymagany pełny restart |
| **Reguła 5** | Po każdej operacji ingest ColPali → sprawdź czy VRAM zwalniany |
| **Reguła 6** | NIGDY nie cofać lazy loading — to kluczowa optymalizacja v7.3 |

---

## Architektura VRAM (stan v7.3)

| Stan / Model | VRAM | Uruchomienie |
|---|---|---|
| Backend sam (v7.3) | **14 MB** | Automatyczny |
| Bielik-11B Q8_0 | **~14 GB** | Ręcznie przez UI dropdown |
| Bielik-4.5B Q8_0 | **~4.8 GB** | Ręcznie przez UI dropdown |
| e5-large (embedding) | **~2.5 GB** | Lazy — przy "Indeksuj RAG" |
| ColPali v1.3 | **~6–8 GB** | On-demand |
| Qwen2.5-VL-7B Q4 | **~4.7 GB** | On-demand VLM |
| Whisper small | **~2 GB** | Lazy STT |

**Łączna dostępna VRAM: 16 GB** → kombinacje niemożliwe jednocześnie:
- ❌ Bielik-11B + e5-large (14 + 2.5 = 16.5 GB)
- ❌ ColPali + e5-large (8 + 2.5 = 10.5 GB — marginalnie może przejść, ale ryzykowne)
- ✅ Bielik-4.5B + e5-large (4.8 + 2.5 = 7.3 GB — bezpieczne)

---

## Protokół bezpiecznego ingestu ColPali/VLM

Wykonaj kroki **w tej kolejności**:

```bash
# Krok 1: Zatrzymaj model przez UI lub curl
curl -X POST http://192.168.31.70:8000/model/stop

# Krok 2: Wymuś kill llama-server
pkill -f llama-server

# Krok 3: Poczekaj
sleep 10

# Krok 4: Sprawdź VRAM — musi być < 500 MB
curl -s http://192.168.31.70:8000/gpu/status

# Krok 5: Uruchom ingest ColPali
# (przez UI lub endpoint)

# Krok 6: Po zakończeniu ingestu — wróć model
curl -X POST http://192.168.31.70:8000/model/start
```

---

## AMD GPU Environment — wymagane zmienne

Przy każdym uruchomieniu llama-server muszą być ustawione:

```python
amd_env = {
    "HIP_VISIBLE_DEVICES": "0",
    "GPU_MAX_ALLOC_PERCENT": "100",
    "HSA_ENABLE_SDMA": "0",
    "HSA_OVERRIDE_GFX_VERSION": "9.0.6",
}
```

Bez `HSA_OVERRIDE_GFX_VERSION=9.0.6` → llama-server nie znajdzie GPU.

---

## Lazy Loading — wzorzec obowiązkowy

> **NIGDY nie zmieniać na eager loading.** Backend startuje z 14 MB VRAM właśnie dzięki temu.

```python
# ZAWSZE ten wzorzec dla modeli i pipeline'ów:
_resource = None

def get_resource():
    global _resource
    if _resource is None:
        _resource = _load_resource()  # ładuj dopiero tutaj
    return _resource
```

Pliki objęte tym wzorcem (NIE modyfikować bez jawnej zgody):
- `backend_app/services/embeddings.py`
- `backend_app/services/rag.py`

---

## Kolekcje Qdrant — wymiary (nie mieszaj!)

| Kolekcja | Wymiar | Model |
|---|---|---|
| `klimtech_docs` | **1024** | intfloat/multilingual-e5-large |
| `klimtech_colpali` | **128** | vidore/colpali-v1.3-hf (MAX_SIM) |

---

## Diagnostyka VRAM

```bash
# Monitorowanie GPU (AMD ROCm) — uwaga: monitoring.py raportuje GPU: 0%
# To jest kosmetyczny błąd ROCm, nie świadczy o problemie.
# Sprawdź VRAM i temperaturę:
curl -s http://192.168.31.70:8000/gpu/status

# Bezpośrednio przez rocm-smi (na serwerze):
rocm-smi
```

---

## Reakcja na OOM Kill

```bash
# 1. Kill wszystkiego co zajmuje GPU
pkill -f llama-server
pkill -f uvicorn

# 2. Poczekaj min. 30 sekund
sleep 30

# 3. Sprawdź czy VRAM zwolniony
curl -s http://192.168.31.70:8000/gpu/status
# lub: rocm-smi

# 4. Dopiero teraz pełny restart backendu
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000
```

Po OOM — zawsze sprawdź logi: czy Qdrant nadal odpowiada (`podman ps`).
