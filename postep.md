# Postęp wdrożenia NextcloudAI

**Rozpoczęcie:** 2026-03-15
**Ostatnia aktualizacja:** 2026-03-16

---

## Podsumowanie sesji

### Zrealizowane cele:
1. ✅ Dodano sekcję Whisper STT do NextcloudAI.md
2. ✅ Zaimplementowano integrację CORS + Bearer auth
3. ✅ Utworzono 3 workflow JSON dla n8n
4. ✅ Skonfigurowano Nextcloud (apps, trusted_domains, AI provider)
5. ✅ Naprawiono start LLM z obliczaniem parametrów

### Znane problemy:
- ❌ Nextcloud AI Assistant - brak odpowiedzi (taskId w pętli 417)
- ⚠️ Bielik-11B nie mieści się w VRAM - używamy Bielik-4.5B

---

## Szczegółowy log zmian

### Krok 0: Sekcja Whisper (BONUS)
- **Status:** ✅ DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Dodano pełną sekcję BONUS: Whisper STT do NextcloudAI.md (B.1-B.8), zaktualizowano kolejność implementacji (5 faz / 25 kroków)

### Krok 1.1: CORS middleware
- **Status:** ✅ DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Dodano CORSMiddleware do `backend_app/main.py` z origins dla Nextcloud (:8081), Backend UI (:8000)
- **Uwaga:** Port zmieniony z 8443 na 8081

### Krok 1.2: Authorization Bearer
- **Status:** ✅ DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Rozszerzono `require_api_key()` w `backend_app/utils/dependencies.py` o fallback dla header `Authorization: Bearer`

### Krok 1.3: --alias llama-server
- **Status:** ✅ DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Dodano `--alias klimtech-bielik` do komendy llama-server

### Krok 1.4: Testy backendu
- **Status:** ✅ DONE
- **Data:** 2026-03-15/16
- **Wyniki testów:**
  - /health → ✅ {"status":"ok"}
  - /v1/models → ✅ {"id":"klimtech-bielik"}
  - Bearer auth → ✅ Działa
  - CORS preflight → ✅ Nagłówki obecne
  - Chat completion → ✅ Odpowiedź od modelu
- **Problem:** Bielik-11B nie mieści się w VRAM (4.7GB zajęte). Uruchomiono Bielik-4.5B

### Krok 2.1: Konfiguracja Nextcloud - apps
- **Status:** ✅ DONE
- **Data:** 2026-03-15
- **Co zrobiono:**
  - Zainstalowano integration_openai 3.10.1
  - Zainstalowano assistant 2.13.0
  - Ustawiono allow_local_remote_servers = true
  - Dodano trusted_domains: localhost, 127.0.0.1, 192.168.31.70
  - Zmieniono hasło admin na admin123

### Krok 2.2: Endpoint /models (bez /v1)
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:** Dodano endpoint `/models` w `backend_app/routes/chat.py` dla kompatybilności z Nextcloud integration_openai
- **Problem:** Nextcloud woła `/models` ale backend miał tylko `/v1/models`

### Krok 2.3: Naprawa importu w model_manager.py
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:** 
  - Dodano try/except dla importu `settings` w model_manager.py
  - Dodano fallback jeśli settings jest None

### Krok 2.4: Obliczanie parametrów LLM
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:** 
  - Zmieniono start_llm_server() żeby używał calculate_params() z model_parametr.py
  - Parametry obliczane dynamicznie na podstawie dostępnego VRAM
  - Używa model_parametr.py do optymalizacji parametrów (kontekst, kompresja cache)

### Krok 2.5: Aktualizacja plików start/stop
- **Status:** ✅ DONE
- **Data:** 2026-03-16
- **Co zrobiono:**
  - start_klimtech_v3.py - dodano weryfikację /health po starcie
  - stop_klimtech.py - zaktualizowano listę kontenerów i porty (8081 dla Nextcloud)

---

## Zmiany w plikach

| Plik | Zmiany |
|------|--------|
| `NextcloudAI.md` | Dodano sekcję Whisper, zaktualizowano porty (8443→8081), stan implementacji |
| `postep.md` | Pełny log zmian sesji |
| `PODSUMOWANIE.md` | Wymaga aktualizacji |
| `backend_app/main.py` | Dodano CORS middleware z portem 8081 |
| `backend_app/utils/dependencies.py` | Dodano obsługę Bearer token |
| `backend_app/routes/chat.py` | Dodano endpoint /models |
| `backend_app/services/model_manager.py` | Dodano obliczanie parametrów, naprawiono import settings |
| `start_klimtech_v3.py` | Dodano weryfikację /health |
| `stop_klimtech.py` | Zaktualizowano kontenery i porty |
| `n8n_workflows/workflow_auto_index.json` | Utworzono |
| `n8n_workflows/workflow_chat_webhook.json` | Utworzono |
| `n8n_workflows/workflow_vram_manager.json` | Utworzono |

---

## Porty systemowe (OFICJALNE)

| Usługa | Port | Uwagi |
|--------|------|-------|
| Nextcloud | **8081** | Zmieniono z 8443! |
| Backend FastAPI | 8000 | - |
| llama-server | 8082 | - |
| n8n | 5678 | - |
| Qdrant | 6333 | - |

---

## Znane problemy

### 1. Nextcloud AI Assistant nie odpowiada
- **Status:** ❌ NIEROZWIĄZANY
- **Objawy:** Po wysłaniu pytania - ciągłe zapytania POST /check_generation z kodem 417
- **Diagnoza:** Backend działa i odpowiada na curl. API key ustawiony. URL poprawny.
- **Możliwe przyczyny:**
  - Sesja przeglądarki trzyma starą konfigurację
  - Problem z CORS po stronie przeglądarki
  - Provider "Rozmowa" nie jest ustawiony na integration_openai

### 2. VRAM - Bielik-11B
- **Status:** ⚠️ OBEJŚCIE
- **Problem:** ~4.7GB VRAM zajęte, Bielik-11B (~14GB) nie mieści się
- **Rozwiązanie:** Używamy Bielik-4.5B (~5GB VRAM)
- **Parametry obliczane przez model_parametr.py:**
  - Kontekst: 98304 tokenów
  - Kompresja cache: Q8_0
  - Warstwy GPU: wszystkie (-ngl -1)

---

## Następne kroki (do implementacji)

1. ❓ Rozwiązać problem Nextcloud Assistant (brak odpowiedzi)
2. 🔧 Dodać obsługę Bielik-11B (potrzeba więcej VRAM lub mniejszy model)
3. 📝 Zaktualizować PODSUMOWANIE.md
4. 🧪 Testy integracji Nextcloud + RAG

---

## Dane dostępowe

- **URL Nextcloud:** http://192.168.31.70:8081
- **URL Backend:** http://192.168.31.70:8000
- **Login:** admin
- **Hasło:** admin123
- **Model:** klimtech-bielik (Bielik-4.5B)

---
