# PROJEKTGITWEB — Analiza skryptów web_search_tool i repo_github

> Data analizy: 2026-04-06
> Lokalizacja źródeł: `/home/tamiel/programy/web_search_tool/`, `/home/tamiel/programy/repo_github/`
> Cel integracji: `/home/tamiel/KlimtechRAG/`

---

## 1. Katalog: `/home/tamiel/programy/web_search_tool/`

### 1.1 Struktura

```
web_search_tool/
├── web_search_tool.py      # Główne narzędzie wyszukiwania (432 linie)
├── llm_tool_integration.py # Integracja z LLM / Function Calling (428 linii)
└── README_web_search.md    # Dokumentacja (274 linie)
```

### 1.2 `web_search_tool.py`

**Klasa główna: `WebSearchTool`**

| Metoda | Opis | Parametry |
|--------|------|-----------|
| `search(query, num_results)` | Ogólne wyszukiwanie w sieci | query: str, num_results: int (domyślnie 10) |
| `search_github(query, language, sort_by, num_results)` | Wyszukiwanie repozytoriów na GitHub | language: str, sort_by: str ("stars"/"forks"/"updated") |
| `search_documentation(technology, topic, num_results)` | Wyszukiwanie dokumentacji technicznej | technology: str, topic: str |
| `search_code_examples(language, problem, num_results)` | Wyszukiwanie przykładów kodu | language: str, problem: str |
| `format_for_llm(results, include_snippets)` | Formatuje wyniki w formacie czytelnym dla LLM | results: List[SearchResult] |
| `to_json(results)` | Konwertuje wyniki do JSON | results: List[SearchResult] |

**Mechanizm działania:**
- Wywołuje CLI `z-ai function -n web_search -a '{"query":"...", "num":10}'` przez `subprocess.run()`
- Timeout: 30 sekund
- Parsuje odpowiedź JSON z stdout (szuka tablicy `[...]`)
- Zależność zewnętrzna: `z-ai` CLI musi być zainstalowane

**Dataclass `SearchResult`:**
```python
@dataclass
class SearchResult:
    url: str
    name: str
    snippet: str
    host_name: str
    rank: int
    date: str
    favicon: str
```

**Funkcje pomocnicze (do importu):**
- `quick_search(query, num)` — szybkie wyszukiwanie ogólne
- `quick_github_search(query, language, num)` — szybkie wyszukiwanie GitHub

**CLI (argparse):**
```bash
python web_search_tool.py "python machine learning"
python web_search_tool.py --github "network scanner" --language python
python web_search_tool.py --docs hooks --technology react
python web_search_tool.py "docker tutorial" --format json
python web_search_tool.py "fastapi tutorial" --format llm
```

### 1.3 `llm_tool_integration.py`

**Klasa: `ToolExecutor`**

| Metoda | Opis |
|--------|------|
| `get_tool_definitions()` | Zwraca schematy narzędzi w formacie OpenAI Function Calling |
| `execute_tool(name, arguments)` | Wykonuje pojedyncze narzędzie |
| `execute_tool_calls(tool_calls)` | Wykonuje listę wywołań narzędzi (format OpenAI) |

**Dostępne narzędzia (schematy OpenAI):**

1. **`web_search`** — ogólne wyszukiwanie z parametrami:
   - `query` (required) — zapytanie
   - `num_results` (domyślnie 5)
   - `search_type` — "general" | "github" | "documentation" | "code"
   - `language` (opcjonalnie)

2. **`github_search`** — wyszukiwanie na GitHub:
   - `query` (required)
   - `language` (opcjonalnie)
   - `num_results` (domyślnie 5)

**Przykłady integracji w kodzie:**
- `EXAMPLE_OPENAI_INTEGRATION` — pełny przykład z OpenAI API (GPT-4 function calling)
- `EXAMPLE_LOCAL_LLM_INTEGRATION` — przykład z Ollama/LM Studio

**Funkcja `demo()`** — testuje oba narzędzia i wyświetla wyniki.

### 1.4 Zależności

```
web_search_tool.py:
  └── subprocess (z-ai CLI)
  └── json, argparse, sys, typing, dataclasses, datetime

llm_tool_integration.py:
  └── web_search_tool (WebSearchTool, SearchResult)
  └── json, typing, dataclasses
```

### 1.5 Potencjalne punkty integracji z KlimtechRAG

| Funkcja | Gdzie wstawić | Priorytet |
|---------|---------------|-----------|
| `z-ai` jako alternatywny provider web search | `services/retrieval_service.py` | Wysoki |
| GitHub search jako tool w czacie | `utils/tools.py` + `services/github_service.py` | Wysoki |
| Schematy OpenAI function calling | `routes/mcp.py` (rozszerzenie MCP) | Średni |
| Formatowanie wyników dla LLM | `services/prompt_service.py` | Średni |

---

## 2. Katalog: `/home/tamiel/programy/repo_github/`

### 2.1 Struktura

```
repo_github/
├── scraper.py              # Scrapowanie trending repos (81 linii)
├── github_trending.py      # Scrapowanie + automatyczne forkowanie (118 linii)
├── fork_repos.py           # Zaawansowany manager forków (457 linii)
├── download_readme.py      # Pobieranie README.md z forków (302 linie)
├── repo_list.txt           # 832 URL-e repo (połączone listy z duplikatami)
├── repo_list1.txt          # 354 repo (scraper → githubawesome.com/tag/github-trending-weekly/)
├── repo_list2.txt          # 94 repo (scraper → githubawesome.com/page/2/)
├── plik_posortowane.txt    # 384 posortowane unikalne repo
├── forks_cache.json        # Cache 734 sforkowanych repo (timestamp: 2026-03-01)
├── kreuzberg/              # Podkatalog (sklonowane repo)
└── readme_files/           # Katalog na pobrane pliki README.md
```

### 2.2 `scraper.py`

**Cel:** Scrapuje stronę `githubawesome.com/tag/github-trending-weekly/` i wyciąga linki do repozytoriów GitHub.

**Mechanizm:**
1. Pobiera HTML strony głównej (requests + User-Agent header)
2. Parsuje BeautifulSoup, szuka linków `<a href>` zawierających `/github-trending-weekly-`
3. Dla każdego posta — pobiera HTML i wyciąga linki regexem:
   ```python
   pattern = r'https://github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)'
   ```
4. Filtruje duplikaty (set), sortuje, zapisuje do `repo_list1.txt`

**Zależności:** `requests`, `beautifulsoup4`, `re`, `time`

### 2.3 `github_trending.py`

**Cel:** Podobny scraper, ale ze strony `githubawesome.com/page/2/` + **automatyczne forkowanie**.

**Różnica względem scraper.py:**
- Po zebraniu repozytoriów — iteruje przez listę i wykonuje:
  ```python
  subprocess.run(["gh", "repo", "fork", repo_url, "--clone=false"])
  ```
- Delay 2s między forkami (rate limiting GitHub)
- Sprawdza "already forked" w stderr

**Zależności:** `requests`, `beautifulsoup4`, `re`, `time`, `subprocess`

### 2.4 `fork_repos.py`

**Cel:** Zaawansowany manager forków z cache, rate limiting i szczegółowym raportowaniem.

**Kluczowe funkcje:**

| Funkcja | Opis |
|---------|------|
| `check_github_auth()` | Sprawdza `gh auth status` + test API (`gh api user`) |
| `load_forks_cache()` | Wczytuje cache z `forks_cache.json` (obsługa starego i nowego formatu) |
| `save_forks_cache(forks)` | Zapisuje cache z timestampem |
| `get_github_forks(force_refresh)` | Pobiera forki z GitHub (`gh repo list --fork`) lub z cache |
| `load_repo_list()` | Wczytuje `repo_list.txt` |
| `normalize_url(url)` | Normalizuje URL do formatu `https://github.com/owner/repo` |
| `fork_repo(repo_url)` | Forkuje repo, zwraca `(status, message)` |
| `show_status()` | Pokazuje statystyki bez forkowania |

**Statusy forkowania:**
- `success` — OK
- `skip` — już sforkowane
- `blocked` — DMCA/legal (451)
- `notfound` — repo nie istnieje (404)
- `ratelimit` — rate limit (403), retry po 60s
- `unauthorized` — brak autoryzacji (401)
- `error` — inny błąd

**Mechanizm cache:**
- Format JSON z metadanymi:
  ```json
  {
    "timestamp": "2026-03-01T19:26:30.821058",
    "count": 734,
    "forks": ["https://github.com/...", ...]
  }
  ```
- Maksymalny wiek cache: 24 godziny
- Fallback na stary cache jeśli API nie odpowiada

**CLI args:**
```bash
python3 fork_repos.py           # Standardowe forkowanie
python3 fork_repos.py --refresh # Odśwież cache
python3 fork_repos.py --status  # Pokaż status
python3 fork_repos.py --check   # Sprawdź połączenie
```

### 2.5 `download_readme.py`

**Cel:** Pobiera pliki README.md z forkowanych repozytoriów.

**Kluczowe funkcje:**

| Funkcja | Opis |
|---------|------|
| `check_github_auth()` | Sprawdza połączenie z GitHub |
| `load_forks_list()` | Wczytuje listę forków z cache lub GitHub |
| `sanitize_filename(name)` | Czyści nazwę pliku z niedozwolonych znaków |
| `extract_repo_name(url)` | Wyciąga nazwę repo z URL |
| `download_readme(repo_url)` | Pobiera README przez `gh api repos/{owner}/{repo}/contents/{readme}` |
| `download_readme_simple(repo_url)` | Alternatywna metoda: `gh api repos/{owner}/{repo}/readme` + curl z raw.githubusercontent.com |

**Mechanizm pobierania README:**
1. Próbuje przez GitHub API (`gh api repos/{owner}/{repo}/readme`)
2. Dekoduje base64 z odpowiedzi
3. Fallback: curl z `raw.githubusercontent.com/{owner}/{repo}/main/README.md`
4. Fallback: próba z `master` zamiast `main`

**Warianty nazw README:** `README.md`, `README.markdown`, `README.rst`, `README.txt`, `README`, `readme.md`

**CLI args:**
```bash
python3 download_readme.py        # Test: 5 plików (MAX_FILES)
python3 download_readme.py 20     # Limit 20 plików
python3 download_readme.py --all  # Wszystkie forki
```

### 2.6 Pliki danych

**`repo_list.txt`** — 832 linie
- Połączone repozytoria z `repo_list1.txt` i `repo_list2.txt`
- Zawiera duplikaty (te same repo pojawiają się wielokrotnie)
- Format: `https://github.com/owner/repo` (po jednym na linię)

**`repo_list1.txt`** — 354 linie
- Wynik scrapera ze strony `githubawesome.com/tag/github-trending-weekly/`
- Posortowane alfabetycznie
- Unikalne

**`repo_list2.txt`** — 94 linie
- Wynik scrapera ze strony `githubawesome.com/page/2/`
- Posortowane alfabetycznie
- Unikalne

**`plik_posortowane.txt`** — 384 linie
- Posortowana, zdeduplikowana lista repozytoriów
- Prawdopodobnie wynik `sort -u` na repo_list.txt

**`forks_cache.json`** — 734 forki
- Cache sforkowanych repozytoriów
- Timestamp: `2026-03-01T19:26:30.821058`
- Format: `{"timestamp": "...", "count": 734, "forks": [...]}`
- Przykładowe repo: `deepseek-ai/DeepSeek-R1`, `open-webui/open-webui`, `ggml-org/llama.cpp`, `anthropics/claude-code`, `langchain-ai/langchain`

### 2.7 Pipeline pracy

```
scraper.py / github_trending.py
    │
    ├─→ repo_list1.txt (354 repo)
    └─→ repo_list2.txt (94 repo)
              │
              ▼
         repo_list.txt (832 z duplikatami)
              │
              ▼
    fork_repos.py (forkuje przez gh CLI)
              │
              ▼
    forks_cache.json (734 sforkowanych)
              │
              ▼
    download_readme.py (pobiera README.md)
              │
              ▼
    readme_files/ (pliki Markdown)
```

### 2.8 Zależności

```
scraper.py:
  └── requests, bs4, re, time

github_trending.py:
  └── requests, bs4, re, time, subprocess

fork_repos.py:
  └── subprocess, json, time, os, datetime

download_readme.py:
  └── subprocess, json, os, sys, re, datetime, base64
```

### 2.9 Potencjalne punkty integracji z KlimtechRAG

| Funkcja | Gdzie wstawić | Priorytet |
|---------|---------------|-----------|
| GitHub search jako tool w czacie | `utils/tools.py` + nowy serwis | Wysoki |
| Fork repo endpoint | `routes/github.py` (nowy) | Średni |
| Download README endpoint | `routes/github.py` (nowy) | Średni |
| Trending repos scraper | `services/github_service.py` | Niski |
| Cache forków | `services/github_service.py` | Średni |

---

## 3. Plan integracji z KlimtechRAG

### 3.1 Architektura docelowa

```
KlimtechRAG/
├── backend_app/
│   ├── services/
│   │   ├── web_search_providers.py   # NOWY: Abstrakcja providerów web search
│   │   ├── github_service.py         # NOWY: GitHub API, fork, README, trending
│   │   └── retrieval_service.py      # MODYFIKACJA: Używa web_search_providers
│   ├── routes/
│   │   ├── github.py                 # NOWY: Endpointy GitHub
│   │   └── web_search.py             # MODYFIKACJA: Nowe endpointy
│   ├── utils/
│   │   └── tools.py                  # MODYFIKACJA: Nowe tool: github_search
│   ├── models/
│   │   └── schemas.py                # MODYFIKACJA: Nowe schematy
│   └── config.py                     # MODYFIKACJA: Nowe ustawienia
│   └── static/
│       └── index.html                # OPCJONALNIE: UI dla GitHub search
```

### 3.2 Faza 1: z-ai jako alternatywny web search provider

**Krok 1/4 — `config.py`**
```python
# Dodane pola:
web_search_provider: str = "ddg"        # "ddg" | "z-ai"
z_ai_cli_path: str = "z-ai"
z_ai_search_timeout: int = 30
```

**Krok 2/4 — `services/web_search_providers.py`**
```python
class BaseSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, num: int) -> List[Document]: ...

class DuckDuckGoProvider(BaseSearchProvider):
    # Obecna logika z retrieval_service.py (DDGS)

class ZAiProvider(BaseSearchProvider):
    # subprocess.run(["z-ai", "function", "-n", "web_search", ...])
    # Parsowanie JSON → Haystack Document

def get_search_provider() -> BaseSearchProvider:
    # Factory na podstawie config.web_search_provider
    # Fallback na DDG jeśli z-ai nieznaleziony
```

**Krok 3/4 — `services/retrieval_service.py`**
```python
# Zamiast bezpośredniego DDGS():
from .web_search_providers import get_search_provider

def retrieve_web(query: str, num_results: int = 5):
    provider = get_search_provider()
    docs = provider.search(query, num_results)
    return docs
```

**Krok 4/4 — Frontend (opcjonalnie)**
- Dropdown przy guziku Web: "DuckDuckGo" / "z-ai"
- Lub automatyczny wybór na podstawie configu

### 3.3 Faza 2: GitHub search jako tool w czacie

**Krok 1/4 — `services/github_service.py`**
```python
class GitHubService:
    def search_github(self, query: str, language: str = None, num: int = 5) -> str:
        # subprocess z gh CLI lub requests do GitHub API
        # Formatowanie wyników dla LLM

    def search_code_examples(self, language: str, problem: str, num: int = 5) -> str:
        # Wyszukiwanie przykładów kodu

    def search_documentation(self, technology: str, topic: str, num: int = 5) -> str:
        # Wyszukiwanie dokumentacji

    def is_available(self) -> bool:
        # Sprawdzenie czy gh CLI jest zainstalowane
```

**Krok 2/4 — `utils/tools.py`**
```python
# Dodane do tool_instructions():
"""
- github_search: Szukaj repozytoriów na GitHub.
  Format: {"tool":"github_search","args":{"query":"...","language":"python"}}
"""

# Dodane do execute_tool():
if tool_name == "github_search":
    return github_service.search_github(**args)
```

**Krok 3/4 — `routes/web_search.py`**
```python
@router.post("/github")
async def github_search(body: GitHubSearchRequest, _: str = Depends(require_api_key)):
    result = github_service.search_github(body.query, body.language, body.num_results)
    return {"results": result}
```

**Krok 4/4 — `models/schemas.py`**
```python
class GitHubSearchRequest(BaseModel):
    query: str
    language: Optional[str] = None
    num_results: int = 5
```

### 3.4 Faza 3: Repo fork + README download

**Krok 1/5 — `config.py`**
```python
github_cache_file: str = "forks_cache.json"
github_readme_output_dir: str = "readme_files"
github_fork_delay: float = 10.0
github_cache_max_age_hours: int = 24
```

**Krok 2/5 — Rozbudowa `services/github_service.py`**
```python
    def list_forks(self) -> List[str]:
        # Wczytaj forks_cache.json lub pobierz z GitHub

    def fork_repo(self, repo_url: str) -> dict:
        # gh repo fork {url} --clone=false
        # Obsługa statusów: success, skip, blocked, notfound, ratelimit

    def download_readme(self, repo_url: str) -> Optional[str]:
        # gh api repos/{owner}/{repo}/readme → base64 decode
        # Fallback: raw.githubusercontent.com

    def get_status(self) -> dict:
        # gh auth status + cache info

    def scrape_trending(self) -> List[str]:
        # Scrapowanie githubawesome.com
```

**Krok 3/5 — `routes/github.py`**
```python
router = APIRouter(prefix="/github", tags=["GitHub"])

@router.post("/fork")
async def fork_repo(body: ForkRepoRequest, _: str = Depends(require_api_key)):
    return github_service.fork_repo(body.url)

@router.get("/forks")
async def list_forks(_: str = Depends(require_api_key)):
    return github_service.list_forks()

@router.post("/readme")
async def download_readme(body: ReadmeRequest, _: str = Depends(require_api_key)):
    return github_service.download_readme(body.url)

@router.get("/status")
async def github_status():
    return github_service.get_status()

@router.post("/trending")
async def scrape_trending(_: str = Depends(require_api_key)):
    return github_service.scrape_trending()

@router.post("/search")
async def github_search(body: GitHubSearchRequest, _: str = Depends(require_api_key)):
    return github_service.search_github(body.query, body.language, body.num_results)
```

**Krok 4/5 — `main.py`**
```python
from .routes import github_router
app.include_router(github_router)
```

**Krok 5/5 — `models/schemas.py`**
```python
class ForkRepoRequest(BaseModel):
    url: str

class ReadmeRequest(BaseModel):
    url: str

class ForkStatusResponse(BaseModel):
    auth_ok: bool
    forks_count: int
    cache_age_hours: float
    gh_installed: bool
```

### 3.5 Mapa zależności między plikami

```
web_search_tool.py
    │
    ├──→ llm_tool_integration.py (importuje WebSearchTool)
    │
    └──→ KlimtechRAG/services/web_search_providers.py (ZAiProvider)
              │
              └──→ KlimtechRAG/services/retrieval_service.py (get_search_provider)
                    │
                    └──→ KlimtechRAG/services/chat_service.py (retrieve_web)

repo_github/scraper.py
    │
    └──→ KlimtechRAG/services/github_service.py (scrape_trending)

repo_github/fork_repos.py
    │
    └──→ KlimtechRAG/services/github_service.py (fork_repo, list_forks, cache)

repo_github/download_readme.py
    │
    └──→ KlimtechRAG/services/github_service.py (download_readme)

repo_github/github_trending.py
    │
    └──→ KlimtechRAG/services/github_service.py (scrape_trending + fork)
```

### 3.6 Ryzyka i mitigacje

| Ryzyko | Prawdopodobieństwo | Mitigacja |
|--------|-------------------|-----------|
| `z-ai` CLI nie zainstalowane na serwerze | Wysokie | Fallback na DDG, `shutil.which("z-ai")` przy starcie |
| `gh` CLI nie zainstalowane | Średnie | `/github/status` zwraca `gh_installed: false`, endpointy zwracają 503 |
| Brak autoryzacji GitHub | Średnie | Sprawdzanie `gh auth status` przed operacjami |
| Rate limiting GitHub API | Wysokie | Delay 10s między forkami, retry po 60s przy 429 |
| Timeout web search (30s) | Średnie | Async endpoint, timeout konfigurowalny |
| VRAM — brak wpływu | — | Wszystkie operacje przez subprocess/CPU |
| Cache stale (>24h) | Niskie | Auto-refresh przy przeterminowanym cache |
| Path traversal w nazwach plików README | Niskie | `sanitize_filename()` + `Path.resolve()` |

### 3.7 Wymagane zależności systemowe

| Narzędzie | Wymagane dla | Instalacja |
|-----------|-------------|------------|
| `z-ai` CLI | Web search przez z-ai | `npm install -g z-ai` (lub odpowiednik) |
| `gh` CLI | GitHub operations | `sudo apt install gh` |
| `requests` | Scraping, GitHub API | `pip install requests` |
| `beautifulsoup4` | Scraping HTML | `pip install beautifulsoup4` |
| `ddgs` (DuckDuckGo) | Obecny web search | Już zainstalowane |

---

## 4. Podsumowanie

### Co już działa w KlimtechRAG
- Web search przez DuckDuckGo w czacie (guzik Web)
- Standalone endpointy `/web/search`, `/web/fetch`, `/web/summarize`
- Tool calling w czacie (ls, glob, grep, read)
- MCP endpoint z 3 narzędziami

### Co dodają skrypty zewnętrzne
- Alternatywny provider web search (`z-ai`)
- Wyszukiwanie GitHub z filtrowaniem po języku
- Forkowanie repozytoriów przez CLI
- Pobieranie README.md z repozytoriów
- Scrapowanie trending repos z githubawesome.com
- Cache forków z metadanymi

### Docelowy zakres integracji
- 3 nowe pliki w backend_app/
- 3 modyfikacje istniejących plików
- ~15 nowych endpointów API
- 1 nowy tool w czacie (github_search)
- 0 wpływu na VRAM/GPU
