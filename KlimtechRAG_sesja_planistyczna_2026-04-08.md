# KlimtechRAG — Sesja Planistyczna
**Data:** 2026-04-08  
**Temat:** Architektura agentowa, LLM Wiki, autoresearch, OpenCode, RAG jako pamięć agenta

---

## Pytanie 1: LLM Wiki — Zalety i Wady dla KlimtechRAG

**Maciek:**  
Wklejony dokument opisujący wzorzec LLM Wiki (persistent wiki maintainowanej przez LLM, z raw sources → wiki → schema). Pytanie: Jak mogę ten pomysł wykorzystać w projekcie KlimtechRAG? Wymień wady i zalety.

**Claude:**

### LLM Wiki w KlimtechRAG — Zalety i Wady

#### ✅ Zalety

**Skompilowana wiedza zamiast re-derivacji.** Zamiast szukać fragmentów przy każdym zapytaniu, wiki buduje syntezę raz. Dla KlimtechRAG to oznacza, że Bielik może odpowiadać szybciej i głębiej — czyta gotowe strony wiki zamiast surowych chunków z Qdrant.

**Naturalne uzupełnienie dla Qdrant.** Strony wiki to też dokumenty — mogą być indeksowane w `klimtech_docs` obok raw sources. Masz już pipeline ingestii, więc dodanie wiki layer nie wymaga nowej infrastruktury.

**Offline i zero dodatkowych zależności.** Wiki to katalog markdownów. Pasuje idealnie do twojej filozofii (prywatność, serwer domowy). Obsidian już pewnie masz lub mógłbyś dodać jako przeglądarkę.

**Flagowanie sprzeczności przy ingestii.** Przy dokumentach firmowych/technicznych (np. różne wersje instrukcji) wiki automatycznie wychwytuje konflikty — to coś, czego czyste RAG nie robi.

**log.md dopełnia istniejący SHA256 dedup.** Masz już śledzenie plików w SQLite; log.md daje chronologiczny widok historii wiedzy — komplementarne, nie redundantne.

#### ❌ Wady

**Brak agenta w obecnym stosie.** Wiki maintenance wymaga pętli agentowej: *czytaj → analizuj → zaktualizuj 10-15 stron → zaktualizuj index*. llama.cpp-server + FastAPI działa synchronicznie i nie ma wbudowanego mechanizmu multi-step reasoning. To największa luka.

**VRAM i latencja ingestii.** Ingestia jednego dokumentu z wygenerowaniem/aktualizacją wiki może zająć minuty przy Bieliku-11B. Z obecnym budżetem 16GB VRAM (LLM ~14GB) to poważny problem — nie możesz mieć jednocześnie ColPali + wiki generation.

**Trzy kopie danych.** Raw sources + Qdrant vectors + wiki pages = znacząca redundancja.

**Jakość zależy od Bielika jako pisarza.** Wiki jest tak dobra, jak LLM który ją pisze. Bielik-4.5B może generować słabej jakości strony; Bielik-11B jest lepszy, ale IQ2_XXS może mieć obniżoną jakość rozumowania przy złożonej syntezie.

**Schema (AGENTS.md dla wiki) trzeba napisać.** Ty już masz AGENTS.md dla KlimtechRAG, ale schemat *jak pisać wiki* to osobna specyfikacja.

#### 🔄 Werdykt: Z ADAPTACJĄ

Najbardziej realistyczne podejście to **hybrydowy tryb**: nie zastępujesz RAG wiki, tylko dodajesz opcjonalną warstwę wiki generowaną na żądanie:
- Ingestia ColPali/e5 pozostaje jak jest (szybka, bez LLM)
- Po ingestii użytkownik może opcjonalnie wywołać *"wygeneruj stronę wiki dla tego dokumentu"*
- Wiki pages są indeksowane w Qdrant razem z raw sources
- FastAPI dostaje nowy endpoint `/wiki/generate` i `/wiki/query`

---

## Pytanie 2: LLM Wiki + Claude Code w terminalu

**Maciek:**  
A jak może mi to pomóc w pracy z Claude code w terminalu podczas pracy nad projektem KlimtechRAG lub innym projektem?

**Claude:**

### LLM Wiki + Claude Code w terminalu

**Kluczowa idea:** Claude Code w każdej sesji zaczyna od zera — czyta pliki, odbudowuje kontekst. Wiki rozwiązuje dokładnie ten problem.

**Co konkretnie zyskujesz:**

**Stały punkt wejścia dla Claude Code.** Plik `WIKI.md` lub katalog `wiki/` z:
- `architecture.md` — decyzje architektoniczne i dlaczego
- `decisions.md` — log: "ColPali oddzielone od e5, bo multi-vector"
- `lessons.md` — "backtick w Python strings powoduje SyntaxError", "llama-server z pełną ścieżką wywołuje błąd libmtmd.so.0"

**Skompilowane lekcje zamiast powtarzania błędów.** Każdy bug który naprawiłeś, każde odkrycie — trafia do wiki. Claude Code nie musi się uczyć od nowa.

**Cross-project transfer.** Wiki techniczna z wzorcami (ROCm gotcha, fish shell bez heredoc, Podman networking) jest przenośna.

**Pętla sesji:** Koniec sesji → Claude Code aktualizuje `decisions.md` i `lessons.md` → następna sesja zaczyna od aktualnego stanu.

**Minimalna implementacja:**
```
KlimtechRAG/
  AGENTS.md          ← już masz
  wiki/
    decisions.md     ← dlaczego tak, nie inaczej
    lessons.md       ← co nie działa i dlaczego
    status.md        ← aktualny stan projektu
```

**Jeden zdanie:** Wiki dla Claude Code to *zewnętrzna pamięć sesyjna* która sprawia, że agent zaczyna każdą sesję jako doświadczony współpracownik, nie nowy pracownik.

---

## Pytanie 3: autoresearch Karpathy + lokalny LLM

**Maciek:**  
https://github.com/karpathy/autoresearch  
A jak użyć tego projektu na moim lokalnym llm aby wykonywał "kiedy np śpię" część zadań lub tworzył nawet cały projekt?

**Claude:**

### autoresearch — ocena dla KlimtechRAG

**Ważne rozróżnienie:** w autoresearch lokalny LLM **nie jest agentem** — jest *przedmiotem badań* (to co jest trenowane). Agentem jest Claude Code / Codex.

**Co to właściwie robi:**
```
agent czyta program.md
→ edytuje train.py
→ uruchamia trening (5 min)
→ sprawdza metrykę val_bpb
→ zatrzymuje lub cofa zmianę
→ repeat (ok. 100 eksperymentów przez noc)
```
To **autoML research loop** na kodzie treningowym GPT — nie narzędzie do budowania aplikacji.

#### Zalety
- Wzorzec `program.md` jest genialny i przenośny (to twój `AGENTS.md`)
- Idea "eksperymentuj kiedy śpisz" jest realna
- Fork AMD istnieje: `andyluo7/autoresearch`

#### Wady / Ryzyka
- Bielik jako agent = zły pomysł (brak tool use, pętli agentowej)
- autoresearch ≠ autonomiczne tworzenie aplikacji
- CUDA-first; fork AMD nieoficjalny
- Ryzyko autonomous code execution na serwerze produkcyjnym

#### Werdykt: Z ADAPTACJĄ

Zaadaptuj **wzorzec** do pracy z Claude Code:
```
program.md (twój):
"Dziś w nocy: zoptymalizuj ingest_colpali.py.
Metric: czas ingestii 10 PDF-ów.
Zasady: nie dotykaj embeddings.py, nie edytuj Qdrant collections.
Po każdej próbie dopisz wynik do experiments.log."
```

---

## Pytanie 4: OpenCode Build mode + lokalny LLM

**Maciek:**  
Ale aplikacja Opencode z funkcją "Build" i podłączeniem do lokalnego modelu może działać jako "automat"? https://opencode.ai

**Claude:**

### OpenCode Build mode + lokalny LLM — Ocena

**Co "Build mode" faktycznie robi:**
- **Plan mode** (Tab raz) = agent tylko planuje, nie edytuje plików
- **Build mode** (Tab drugi raz) = agent edytuje pliki, uruchamia komendy, czyta output

OpenCode obsługuje 75+ providerów w tym lokalne modele przez `openai`-compatible endpoint — llama.cpp-server na porcie 8082 już działa jako provider.

#### Zalety
- Natychmiastowa kompatybilność z Bielikiem (llama.cpp `/v1/chat/completions`)
- AGENTS.md już masz — OpenCode go czyta
- Multi-session: kilka agentów równolegle
- Tryb nocny realny przez `tmux`
- Skills w `.agents/skills/` są w formacie który OpenCode rozumie

#### Wady / Ryzyka
- Bielik jako agent coding = ograniczona skuteczność
- VRAM konflikt — llama-server z Bielikiem-11B + długie konteksty
- Brak hamulca awaryjnego przy destruktywnych operacjach
- fish shell — OpenCode może generować bash-style heredoki

#### Werdykt: Z ADAPTACJĄ

Realny plan:
1. Model: Bielik-4.5B zamiast 11B dla trybu agentowego
2. Zakres: Jeden moduł na sesję
3. Zabezpieczenie: `git` — każda zmiana revertowalna
4. AGENTS.md: dodaj "Shell: fish — nie używaj heredoc"
5. Monitoring: `tmux` + log do pliku

> Jeśli chcesz wyższe bezpieczeństwo — Claude API (Haiku) jako agent jest 10x skuteczniejszy niż Bielik.

---

## Pytanie 5: Claude Haiku na Hugging Face

**Maciek:**  
Haiku a jaka wielkość i kwantyzacja byłaby optymalna. Wyszukaj na hugging face.

**Claude:**

### Claude Haiku NIE jest na Hugging Face

Claude Haiku (i cała rodzina Claude) to modele **zamknięte, własnościowe** od Anthropic. Nie można ich pobrać, nie ma GGUF, nie można uruchomić lokalnie. To wyłącznie API.

Wyniki znalezione to modele *trenowane na outputach* Claude Haiku (distillation) — znikome downloady (16–233).

**Claude API Haiku:** $0.80 / 1M tokenów input — noc pracy = kilkadziesiąt centów.

**Alternatywy GGUF na 16GB ROCm:**

| Model | Rozmiar Q4 | Uwagi |
|-------|-----------|-------|
| Qwen2.5-Coder-7B | ~4.5GB | Najlepsza jakość coding w tej klasie |
| DeepSeek-Coder-V2-Lite | ~9GB | Silniejszy reasoning |
| Bielik-4.5B | ~3GB | Masz go — po polsku |

---

## Pytanie 6: Poszukaj modeli kodujących (nie Bielik)

**Maciek:**  
Poszukaj innych modeli niż Bielik które będą dobre w roli kodującego agenta.

**Claude:**

### Modele kodujące GGUF — ranking dla KlimtechRAG

#### 🥇 Qwen2.5-Coder-7B-Instruct — rekomendacja główna

**314K pobrań** — zdecydowany lider wśród coding GGUF.

| Kwantyzacja | VRAM | Jakość |
|-------------|------|--------|
| Q4_K_M | ~4.5GB | ✅ dobra |
| Q8_0 | ~8GB | ✅✅ lepsza |

**Link:** [bartowski/Qwen2.5-Coder-7B-Instruct-GGUF](https://hf.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF)

Apache 2.0, świetne tool use i function calling, najczęściej używany coding model w ekosystemie llama.cpp.

#### 🥈 Qwen2.5-Coder-14B-Instruct

**60K pobrań.** Q4_K_M ~9GB VRAM — agent-only, bez ColPali.

**Link:** [Qwen/Qwen2.5-Coder-14B-Instruct-GGUF](https://hf.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF)

#### 🥉 DeepSeek-Coder-V2-Lite-Instruct

**60K pobrań** (bartowski imatrix). Q4_K_M ~9-10GB. Architektura MoE 16B.

⚠️ **Uwaga ROCm:** MoE + niestandardowy attention — może być niestabilny na AMD.

**Link:** [bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF](https://hf.co/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF)

**Rekomendacja finalna:**
```
hf download bartowski/Qwen2.5-Coder-7B-Instruct-GGUF \
             Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf
```

---

## Pytanie 7: Dual AMD Instinct (16GB + 32GB)

**Maciek:**  
A jeśli będę miał dodatkową kartę AMD instinct 32GB to tą pierwszą ze 16G mogę mieć do wł/wył testów skryptów lub całego projektu a w tym czasie duży agent na 32GB będzie kontrolowany przez Claude Sonnet 4.6 też otwarty w opencode lub terminalowej aplikacji Claude dla Linux.

**Claude:**

### Dual AMD Instinct: Architektura multi-agent

**Ogólna ocena: ✅ TAK — to sensowny i realny setup**

#### Podział kart

```
GPU 0 (16GB) — HIP_VISIBLE_DEVICES=0
  └─ KlimtechRAG: Qdrant, ColPali, e5-large, Bielik-4.5B
  └─ rola: środowisko testowe, izolowane

GPU 1 (32GB) — HIP_VISIBLE_DEVICES=1
  └─ Qwen2.5-Coder-32B-Instruct (~20GB przy Q4_K_M)
  └─ rola: lokalny agent wykonawczy
  └─ sterowany przez: Claude Sonnet 4.6 via OpenCode
```

#### Model na 32GB

**Qwen2.5-Coder-32B-Instruct Q4_K_M** — 31K pobrań, Apache 2.0

| Kwantyzacja | VRAM |
|-------------|------|
| Q4_K_M | ~20GB |
| Q5_K_M | ~24GB |

**Bartowski imatrix wersja preferowana.**

#### Rola Claude Sonnet 4.6

Claude Code CLI (`claude` w terminalu) jako orkiestrator:
- **Poziom 1 — planowanie:** Sonnet czyta AGENTS.md, decyduje *co* ma być zrobione
- **Poziom 2 — delegacja:** Qwen2.5-Coder-32B dostaje atomowe zadania przez llama-server API

**Efektywny podział:** Planowanie → Sonnet (API, tanie). Brutalna robota: pisanie kodu → Qwen32B (lokalnie, za darmo).

#### Kluczowe ryzyka
- ROCm multi-GPU: dwie karty muszą być widoczne przez `rocm-smi`
- Dwa osobne procesy llama-server na różnych portach
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`

---

## Pytanie 8: RAG jako pamięć agenta

**Maciek:**  
Jeszcze dodać do modelu Qwen3 dodatkową bazę rag do której wrzuca wszystkie informacje z plików, zadania błędy jakie popełni które wykrył Sonnet od Claude. Każdą uwagę itd. Czy jest to możliwe?

**Claude:**

### Odkrycie: Qwen3-Coder-30B-A3B — upgrade modelu

**Qwen3-Coder-30B-A3B-Instruct** — MoE: 30B parametrów total, tylko **3B aktywnych przy inferencji**.

| Wersja | VRAM (Q4_K_M) | Szybkość | Pobierania |
|--------|--------------|----------|-----------|
| Qwen2.5-Coder-32B Q4_K_M | ~20GB | wolniejszy | 31K |
| **Qwen3-Coder-30B-A3B Q4_K_M** | **~18GB** | **2-3x szybszy** | **136K+216K** |

**Link:** [unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF](https://hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF)

### RAG jako pamięć agenta — Tak, możliwe

**Nowa kolekcja Qdrant: `agent_memory`** (dim=1024, ten sam e5-large)

Co trafia automatycznie:
```
typ: błąd_agenta     → "próbowałem shell=True, Sonnet odrzucił"
typ: decyzja         → "ColPali musi być na osobnej kolekcji dim=128"
typ: uwaga_sonnet    → "brakuje Depends(require_api_key) na /wiki/generate"
typ: plik_kontekst   → chunk z edytowanego pliku
typ: wynik_testu     → "test_colpali_embedder.py FAILED: VRAM OOM"
typ: wzorzec_sukcesu → "fix: lazy loading rozwiązuje OOM"
```

**Jak działa w sesji:**
```
Qwen3 dostaje zadanie od Sonnet
  → odpytuje agent_memory (podobne zadania, błędy, uwagi)
  → dostaje kontekst z poprzednich sesji
  → zaczyna pisać kod z wiedzą o historii

Po sesji Sonnet robi "post-mortem":
  → klasyfikuje co poszło dobrze/źle
  → zapisuje do agent_memory przez FastAPI endpoint
```

**Implementacja — nakład pracy:**
1. Nowa kolekcja `agent_memory` w Qdrant — 5 minut
2. Endpoint `POST /agent/memory` z `Depends(require_api_key)` — 1h
3. Instrukcja w AGENTS.md dla Claude Code — 30 minut

---

## Pytanie 9: Bazy RAG dla "Mistrza" i "Ucznia"

**Maciek:**  
A czy można zastosować kolejny dodatkowy Qdrant dla Clauda w terminalu aby to nadzorca też coraz lepiej "nadzorował" projekt bo widziałem że czasem jak przerwałem pracę i mimo to jak na nowo zapoznał się z plikami to popełnił błąd który wynikał z przerwania kontekstu. Chodzi mi o takie lokalne bazy Qdrant RAG dla "mistrza" i "ucznia".

**Claude:**

### Dwie bazy RAG: "Mistrz" i "Uczeń" — Tak, możliwe

#### Architektura dwóch kolekcji

```
Qdrant:
  klimtech_docs      (dim=1024) — dokumenty projektu, już masz
  agent_memory       (dim=1024) — pamięć Qwen3-Coder (Uczeń)
  supervisor_memory  (dim=1024) — pamięć Sonnet (Mistrz) ← nowe
```

#### Co trafia do `supervisor_memory`

```
typ: sesja_przerwana
  → "zatrzymano przy refaktoryzacji ingest_colpali.py linia 142,
     powód: VRAM OOM, następny krok: zmniejszyć batch_size"

typ: plan_niezrealizowany
  → "miało być: dodanie endpoint /wiki/generate,
     zrobiono: tylko szkielet funkcji bez testów"

typ: decyzja_nadzorcza
  → "Qwen3 trzykrotnie próbował użyć shell=True — blokuję"

typ: kontekst_przerwania
  → "użytkownik przerwał o 23:14, git status: 3 pliki niezcommitowane"

typ: wzorzec_błędu_ucznia
  → "Qwen3 konsekwentnie pomija walidację Path.resolve()"
```

#### Rozwiązanie problemu przerwania kontekstu

Snapshot stanu przy wyjściu:
```json
{
  "typ": "snapshot",
  "timestamp": "2026-04-08T23:14",
  "git_status": ["routes/ingest.py M", "embeddings.py M"],
  "ostatni_krok": "batch_size zmniejszony do 4, test nie uruchomiony",
  "nastepny_krok": "uruchom test_colpali, commit jeśli przejdzie",
  "uwagi": "nie commitować dopóki test nie przejdzie"
}
```

#### Kto zapisuje do której bazy

```
supervisor_memory:
  ZAPISUJE: Sonnet — na końcu każdej sesji
  CZYTA:    Sonnet — na początku każdej sesji

agent_memory:
  ZAPISUJE: Sonnet — po weryfikacji pracy Qwen3
  CZYTA:    Qwen3 — przed każdym zadaniem
```

#### Pełna mapa pamięci

```
┌─────────────────────────────────────────────┐
│              Claude Sonnet 4.6              │
│              (Mistrz/Nadzorca)              │
│  czyta ──→ supervisor_memory                │
│  czyta ──→ agent_memory                     │
│  pisze ──→ supervisor_memory (snapshoty)    │
│  pisze ──→ agent_memory (oceny Qwen3)       │
└───────────────────┬─────────────────────────┘
                    │ zleca zadania
                    ↓
┌─────────────────────────────────────────────┐
│           Qwen3-Coder-30B-A3B               │
│              (Uczeń/Wykonawca)              │
│  czyta ──→ agent_memory                     │
│  czyta ──→ klimtech_docs                    │
│  NIE PISZE do żadnej bazy                   │
└─────────────────────────────────────────────┘
```

---

## Pytanie 10: Rola Obsidian w tej architekturze

**Maciek:**  
A jaką rolę pełniłaby w tych wszystkich twoich rozważaniach aplikacja Obsidian?

**Claude:**

### Obsidian — rola "Ludzkiego Interfejsu"

Obsidian to **twoje okno na cały system**. Jest warstwą czytelności dla człowieka nad tym co robią agenci.

#### Konkretne role

**1. Podgląd wiki agenta w czasie rzeczywistym**  
Agenci piszą markdown do `wiki/` — ty otwierasz Obsidian na tym katalogu. Graph view pokazuje które moduły są najczęściej dotykane, które strony są "hubami", które są sierotami.

**2. Przeglądanie pamięci przez Dataview**  
Wtyczka Dataview + query:
```
TABLE typ, timestamp FROM "agent_memory"
WHERE typ = "błąd_agenta"
SORT timestamp DESC
```
Widzisz historię błędów Qwen3 jako tabelę. Bez terminala.

**3. Ty jako trzeci agent — piszesz notatki do supervisor_memory**  
```markdown
## Przerwanie sesji 2026-04-08 23:14
Stan: ingest_colpali.py niezakończony
Następna sesja: najpierw test, potem commit
Uwaga dla Sonnet: nie pozwól Qwen3 commitować przed testem
```
Plik zapisuje się → watcher wykrywa zmianę → indeksuje do `supervisor_memory` przez FastAPI.

**4. Clipper źródeł dla KlimtechRAG**  
Obsidian Web Clipper konwertuje artykuły, dokumentację ROCm, release notes → do markdown → automatycznie indeksowane do `klimtech_docs`.

**5. Widok "co agenci zrobiły w nocy"**  
`wiki/log.md` w Obsidian — chronologiczny log wszystkich sesji nocnych.

#### Czym Obsidian NIE jest

Nie jest bazą danych (Qdrant), nie jest IDE (OpenCode/terminal), nie zastępuje git (GitHub). Jest **dashboardem dla ciebie** — jedynego człowieka w tym systemie.

#### Mapa z Obsidianem

```
TY (człowiek)
  │
  ├─ czytasz ──→ Obsidian vault
  │               ├─ wiki/ (co piszą agenci)
  │               ├─ log.md (historia sesji)
  │               ├─ błędy/ (Dataview z agent_memory)
  │               └─ twoje notatki → do supervisor_memory
  │
  └─ zlecasz ──→ Claude Sonnet 4.6 (Mistrz)
                    └─ zleca ──→ Qwen3-Coder (Uczeń)
                                    └─ testuje na GPU 0 (KlimtechRAG)
```

Obsidian siedzi **obok** całego systemu jako ludzki interfejs — nie w środku jako zależność.

---

## Podsumowanie Architektury Finalnej

```
hall9000 (serwer):
  GPU 0 (16GB AMD Instinct):
    - KlimtechRAG (FastAPI :8000)
    - Qdrant: klimtech_docs, klimtech_colpali,
              agent_memory, supervisor_memory
    - ColPali v1.3, e5-large (embeddings)
    - Środowisko testowe (wł/wył)

  GPU 1 (32GB AMD Instinct):
    - llama-server: Qwen3-Coder-30B-A3B-Instruct Q8_0
    - Port: 8083, HIP_VISIBLE_DEVICES=1

tamiel@hall8000 (laptop, development):
  - Claude Code CLI (Sonnet 4.6) — Mistrz/Nadzorca
  - OpenCode — interfejs agentowy
  - Obsidian vault — ludzki dashboard

Przepływ nocny:
  Sonnet czyta supervisor_memory (kontekst poprzedniej sesji)
    → zleca zadanie Qwen3
    → Qwen3 czyta agent_memory (historia błędów)
    → Qwen3 edytuje kod, testuje na GPU 0
    → Sonnet weryfikuje wynik
    → Sonnet zapisuje ocenę do agent_memory
    → Sonnet zapisuje snapshot do supervisor_memory
    → git commit (jeśli testy przeszły)

Rano:
  Ty otwierasz Obsidian → widzisz co się stało
```

**Kluczowe modele:**
- Qwen3-Coder-30B-A3B Q8_0 (~30GB) → [unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF](https://hf.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF)
- Qwen2.5-Coder-7B Q4_K_M (~4.5GB) backup → [bartowski/Qwen2.5-Coder-7B-Instruct-GGUF](https://hf.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF)

**Zasady bezpieczeństwa (niezmienne):**
- Sonnet jest jedynym który zapisuje do baz pamięci
- Qwen3 tylko czyta i edytuje kod
- Każda zmiana przez git — revertowalna
- `Depends(require_api_key)` na wszystkich nowych endpointach
- fish shell: bez heredoc, bez `&&`
