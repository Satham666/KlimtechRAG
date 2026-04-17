# Podsumowanie czatu — decyzja o migracji UI KlimtechRAG

**Data:** 2026-04-17
**Kontekst:** ocena pomysłu integracji KlimtechRAG z Anything-LLM pod nazwą KlimtechAny_LLM

---

## 1. Punkt wyjścia

Użytkownik rozważał fork projektu Anything-LLM i włączenie do niego funkcji z KlimtechRAG, z rebrandingiem frontendu na **KlimtechAny_LLM**. Dostarczył dwie analizy od innych modeli (analiza_nr1.md, analiza_nr2.md), które popierały ten kierunek.

## 2. Weryfikacja faktów (repo Satham666/KlimtechRAG)

- Repo to **98.6% Python, 1.4% Shell** — FastAPI backend, bez frontendu
- 22 commity, brak releases, brak tagów
- W roocie repo istnieją już dwa dokumenty planujące migrację do OpenWebUI:
  - `PLAN_MIGRACJI_OpenWebUI_2026-02-21.md`
  - `PLAN_OPEN_WEBUI_QDRANT_RAG.md`

## 3. Krytyka dostarczonych analiz

- **analiza_nr1.md** — całkowicie zmyśliła stack KlimtechRAG (Streamlit/LangChain/FAISS/camelot). Zero prawdziwych faktów. Odrzucona w całości.
- **analiza_nr2.md** — bliżej prawdy (FastAPI, Qdrant, ColPali, Bielik), ale konfabulowała wersję v7.8 (nie istnieje) i błędnie sugerowała Proxmox/LXC zamiast bare-metal.

## 4. Argumenty przeciw Anything-LLM

1. **Konflikt stack'u** — Node.js (Anything-LLM) vs Python (KlimtechRAG)
2. **ColPali niekompatybilny** — multi-vector dim=128 vs single-vector w Anything-LLM
3. **Utrata optymalizacji ROCm + Bielik** — Anything-LLM łączy się tylko przez API, nie zna flag llama.cpp
4. **Master-apprentice (Sonnet + Gemma 4) nie mapuje się** na Agent Builder Anything-LLM
5. **Konflikt z istniejącym planem** — w repo są już plany migracji do OpenWebUI
6. **Nakład pracy vs zysk** — tygodnie pracy dla funkcji dostępnych taniej gdzie indziej

## 5. Rozważone warianty

- **Wariant A:** Anything-LLM jako klient do API KlimtechRAG przez MCP/OpenAI-compatible
- **Wariant B:** OpenWebUI zgodnie z istniejącym planem z repo
- **Wariant C:** własny lekki widget

## 6. Topologia sieci (podana przez użytkownika)

```
Laptop → VPN WireGuard → VPS mikrus (WireGuard) → serwer Proxmox (KlimtechRAG + AMD Instinct)
```

## 7. Decyzja końcowa: **Wariant B — OpenWebUI**

**Uzasadnienie:**
- Zgodność stack'u (OpenWebUI = FastAPI + Svelte, Python)
- UI hostowane na Proxmox, user łączy się tylko przeglądarką przez VPN
- Brak dodatkowych hop'ów API — OpenWebUI → llama-server → KlimtechRAG lokalnie na Proxmox
- Mikrus pozostaje jako pure relay WireGuard (właściwa rola dla VPS 256MB RAM)
- Zgodność z istniejącymi dokumentami planistycznymi w repo
- Solo user przez VPN — RBAC i multi-user z Anything-LLM nie mają wartości

**Odrzucone:**
- Wariant A (Anything-LLM) — podwójny backend przez VPN, cztery warstwy zamiast dwóch, ekosystem Node.js bez kompensującego zysku
- Wariant C (własny widget) — niepotrzebny nakład pracy, OpenWebUI daje 80% od ręki

## 8. Kluczowa decyzja do podjęcia przed wdrożeniem

**Kto odpowiada za RAG?**
- **Opcja 1 (preferowana):** KlimtechRAG FastAPI wystawia OpenAI-compatible endpoint z pełną logiką (Smart Router + ColPali + Answer Verification). OpenWebUI jest cienkim frontendem `/v1/chat/completions`. **Wartość KlimtechRAG zachowana.**
- **Opcja 2:** OpenWebUI używa własnego wbudowanego RAG, KlimtechRAG marginalizowany do proxy nad Bielikiem. **Do odrzucenia** — sprzeczne z celem projektu.

## 9. Status dokumentów planistycznych

Użytkownik nie udostępnił treści plików `PLAN_MIGRACJI_OpenWebUI_2026-02-21.md` i `PLAN_OPEN_WEBUI_QDRANT_RAG.md` — są w roocie repo, ale zawartość nie jest dostępna w kontekście tej rozmowy. Pliki mają ~2 miesiące, wymagają weryfikacji aktualności przed dalszymi krokami.

## 10. Co dalej

Przed rozpisaniem atomowych kroków wdrożenia należy:
1. Odczytać treść obu planów z repo (cat na laptopie lub Proxmox)
2. Zweryfikować czy założenia z lutego 2026 są nadal aktualne
3. Potwierdzić wybór Opcji 1 (KlimtechRAG jako silnik RAG, OpenWebUI jako cienki frontend)
4. Dopiero wtedy — atomowy plan wdrożenia z komendami Fish, bez heredoc

## 11. Uwaga porządkowa

W roocie repo jest dużo plików planistycznych i podsumowań (`PODSUMOWANIE_*.md`, `WDROZENIE.md`, `DRZEWO.md`, `GIT_KOMENDY.md`, `notatki.md`, `budowa_protonvpn.md`). Warto rozważyć przeniesienie do `docs/` lub `plany/` dla lepszej nawigacji. Nie blokuje decyzji o OpenWebUI.
