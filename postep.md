# Postep wdrozenia NextcloudAI

**Rozpoczecie:** 2026-03-15

---

## Krok 0: Dopisanie sekcji Whisper do NextcloudAI.md
- **Status:** DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Dodano pelna sekcje BONUS: Whisper STT do NextcloudAI.md (B.1-B.8), zaktualizowano kolejnosc implementacji (5 faz / 25 krokow), zaktualizowano tabele plikow, testow i stanu wyjsciowego.

## Krok 1.1: CORS middleware w main.py
- **Status:** DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Dodano CORSMiddleware do `backend_app/main.py` z origins dla Nextcloud (:8443), Backend UI (:8000) i localhost warianty. Import `CORSMiddleware` z `fastapi.middleware.cors`.

## Krok 1.2: Authorization: Bearer w dependencies.py
- **Status:** DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Rozszerzono `require_api_key()` w `backend_app/utils/dependencies.py` o fallback odczytujacy header `Authorization: Bearer <key>` obok istniejacego `X-API-Key`. Nextcloud integration_openai wysyla Bearer token.

## Krok 1.3: --alias w model_manager.py
- **Status:** DONE
- **Data:** 2026-03-15
- **Co zrobiono:** Dodano `--alias klimtech-bielik` do komendy llama-server w dwoch miejscach: `start_llm_server()` (linia ~167) i `start_model_with_progress()` (linia ~500). Dodano import `settings` z `config.py`. Alias bierze wartosc z `settings.llm_model_name` z fallback na "klimtech-bielik".

---
