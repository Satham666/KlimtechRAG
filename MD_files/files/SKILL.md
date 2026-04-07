---
name: klimtech-preflight
description: Obowiązkowy pre-flight checklist na start każdej sesji KlimtechRAG — weryfikacja git status, health backendu, załadowanego modelu i zajętości VRAM. Użyj ZAWSZE przed pierwszą zmianą w sesji.
compatibility: opencode
metadata:
  project: KlimtechRAG
  phase: session-start
---

# klimtech-preflight — Start Sesji KlimtechRAG

## Cel

Przed jakąkolwiek zmianą kodu upewnij się, że środowisko jest w określonym, bezpiecznym stanie.
**Nigdy nie zaczynaj edytować kodu, gdy serwer jest w nieokreślonym stanie.**

---

## Checklist — wykonaj w tej kolejności

### [ ] 1. Status repozytorium (laptop)

```bash
git status
```

- Czy są niezatwierdzone zmiany?
- Jeśli TAK → zapytaj użytkownika czy wykonać commit przed dalszą pracą (umożliwia rollback).
- Sprawdź też: `git log --oneline -5` — jaki jest ostatni commit?

---

### [ ] 2. Health backendu

```bash
curl -s http://192.168.31.70:8000/health
```

Oczekiwana odpowiedź: `{"status": "ok"}` lub podobna.
Jeśli backend nie odpowiada → patrz **Protokół błędów** poniżej.

---

### [ ] 3. Status załadowanego modelu

```bash
curl -s http://192.168.31.70:8000/model/status
```

Ustal: który model jest aktualnie załadowany (Bielik-11B, Bielik-4.5B, brak)?
Zapisz ten stan — będzie potrzebny przy planowaniu ingestu ColPali.

---

### [ ] 4. Zajętość VRAM

```bash
curl -s http://192.168.31.70:8000/gpu/status
```

Tabela referencyjna (AMD Instinct 16 GB):

| Stan | VRAM |
|---|---|
| Backend sam (v7.3) | ~14 MB |
| Bielik-11B Q8_0 | ~14 GB |
| Bielik-4.5B Q8_0 | ~4.8 GB |
| e5-large (embedding) | ~2.5 GB |
| ColPali v1.3 | ~6–8 GB |
| Qwen2.5-VL-7B Q4 | ~4.7 GB |
| Whisper small | ~2 GB |

Reguła: **tylko JEDEN model na GPU naraz**.

---

### [ ] 5. Aktualność pliku do edycji

- Czy masz aktualną wersję pliku po ostatnim `git pull`?
- Dla plików z **Mapy Plików Krytycznych** (patrz niżej) → zawsze zrób commit przed edycją.

---

## Mapa Plików Krytycznych

> Przed zmianą któregokolwiek z tych plików: zrób commit, napisz minidiff (przed/po), zapytaj o zgodę.

| Plik | Ryzyko |
|---|---|
| `backend_app/models/schemas.py` | `use_rag=False` domyślnie — nie zmieniać |
| `backend_app/services/embeddings.py` | Lazy loading singleton — nie cofać do eager |
| `backend_app/services/rag.py` | Pipeline lazy — j.w. |
| `backend_app/services/llm.py` | Standalone OpenAIGenerator |
| `backend_app/config.py` | `_detect_base()` — priorytet serwera |
| `start_klimtech_v3.py` | Kolejność startu kontenerów |
| `.env` | Nigdy nie commitować do Git |

---

## Protokół błędów — backend nie odpowiada

**Poziom 3 — Backend nie odpowiada:**
```bash
pkill -f uvicorn
ss -tlnp | grep 8000   # sprawdź czy port wolny
# Uruchom ręcznie:
KLIMTECH_EMBEDDING_DEVICE=cuda:0 python3 -m uvicorn backend_app.main:app --host 0.0.0.0 --port 8000
```
NIE używaj `start_klimtech_v3.py` do restartu samego backendu.

**Poziom 4 — OOM / GPU crash:**
```bash
pkill -f llama-server
pkill -f uvicorn
# Poczekaj 30s, sprawdź VRAM, dopiero potem pełny restart
```

**Poziom 5 — Qdrant niedostępny:**
```bash
podman start qdrant
sleep 15
curl http://192.168.31.70:8000/rag/debug
# NIE reinicjalizuj kolekcji bez backupu punktów
```

---

## Po zakończeniu checklisty

Raportuj użytkownikowi:
```
✅ Pre-flight zakończony:
- git status: [czysty / X niezatwierdzonych zmian]
- Backend: [odpowiada / nie odpowiada]
- Model: [nazwa / brak]
- VRAM: [X MB / X GB]
- Tryb pracy: [Planowanie / Budowanie]
```

Następnie zapytaj: **"W którym trybie pracujemy? (Planowanie / Budowanie)"**
