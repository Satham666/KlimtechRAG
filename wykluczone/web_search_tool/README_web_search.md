# 🔍 Web Search Tool dla LLM

Zestaw skryptów Python 3 umożliwiających integrację wyszukiwania sieciowego z modelami LLM.

## 📁 Struktura plików

```
/home/z/my-project/download/
├── web_search_tool.py      # Główne narzędzie do wyszukiwania
├── llm_tool_integration.py # Integracja z modelami LLM
└── README_web_search.md    # Ta dokumentacja
```

## 🚀 Szybki start

### 1. Użycie jako narzędzie CLI

```bash
# Podstawowe wyszukiwanie
python web_search_tool.py "python machine learning"

# Wyszukiwanie na GitHub
python web_search_tool.py --github "network scanner" --language python

# Wyszukiwanie dokumentacji
python web_search_tool.py --docs hooks --technology react

# Wynik w formacie JSON (dla LLM)
python web_search_tool.py "docker tutorial" --format json

# Wynik w formacie czytelnym dla LLM
python web_search_tool.py "fastapi tutorial" --format llm
```

### 2. Import jako moduł Python

```python
from web_search_tool import WebSearchTool, quick_search, quick_github_search

# Szybkie wyszukiwanie
results = quick_search("Python async tutorial", num=5)
for r in results:
    print(f"{r.name}: {r.url}")

# Wyszukiwanie na GitHub
results = quick_github_search("port scanner", language="python", num=5)

# Pełna kontrol
tool = WebSearchTool(default_num_results=10)
results = tool.search("docker compose tutorial")

# Formatowanie dla LLM
formatted = tool.format_for_llm(results)
print(formatted)
```

## 🤖 Integracja z LLM

### OpenAI API (Function Calling)

```python
import openai
from llm_tool_integration import ToolExecutor

client = openai.OpenAI(api_key="YOUR_API_KEY")
executor = ToolExecutor()

def chat_with_web_search(user_message: str):
    messages = [{"role": "user", "content": user_message}]
    
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        tools=executor.get_tool_definitions(),
        tool_choice="auto"
    )
    
    message = response.choices[0].message
    
    if message.tool_calls:
        messages.append(message)
        
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = executor.execute_tool(name, args)
            
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "content": result
            })
        
        final_response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages
        )
        return final_response.choices[0].message.content
    
    return message.content
```

### Przykład użycia z modelem

```python
# Przykład 1: Wyszukiwanie na GitHub
odpowiedz = chat_with_web_search(
    "Znajdź popularne biblioteki Python do web scrapingu na GitHub"
)

# Przykład 2: Aktualne informacje
odpowiedz = chat_with_web_search(
    "Jakie są najnowsze wersje Python i co nowego wprowadzają?"
)

# Przykład 3: Dokumentacja
odpowiedz = chat_with_web_search(
    "Jak używać React hooks? Znajdź dokumentację i przykłady."
)
```

## 🛠️ Dostępne funkcje

### WebSearchTool

| Metoda | Opis |
|--------|------|
| `search(query, num_results)` | Ogólne wyszukiwanie w sieci |
| `search_github(query, language, sort_by)` | Wyszukiwanie na GitHub |
| `search_documentation(technology, topic)` | Wyszukiwanie dokumentacji |
| `search_code_examples(language, problem)` | Wyszukiwanie przykładów kodu |
| `format_for_llm(results)` | Formatuje wyniki dla LLM |
| `to_json(results)` | Konwertuje wyniki do JSON |

### ToolExecutor (dla integracji LLM)

| Metoda | Opis |
|--------|------|
| `get_tool_definitions()` | Zwraca schematy narzędzi (OpenAI format) |
| `execute_tool(name, arguments)` | Wykonuje pojedyncze narzędzie |
| `execute_tool_calls(tool_calls)` | Wykonuje listę wywołań narzędzi |

## 📊 Format wyników

### SearchResult (dataclass)

```python
@dataclass
class SearchResult:
    url: str          # URL strony
    name: str         # Tytuł strony
    snippet: str      # Fragment tekstu
    host_name: str    # Nazwa domeny
    rank: int         # Pozycja w wynikach
    date: str         # Data publikacji (jeśli dostępna)
    favicon: str      # URL favicon (jeśli dostępna)
```

### Przykładowy wynik (format LLM)

```
Znaleziono 3 wyników:
============================================================

## Wynik 1
**Tytuł:** PortScout - High Performance Network Port Scanner
**URL:** https://github.com/user/portscout
**Domena:** github.com
**Opis:** PortScout is a high performance network port scanner...
----------------------------------------

## Wynik 2
...
```

## 🔧 Konfiguracja

### Wymagania systemowe

- Python 3.7+
- Dostęp do CLI `z-ai` (narzędzie web_search)

### Opcjonalne zależności

```bash
# Dla integracji z OpenAI
pip install openai

# Dla integracji z lokalnymi modelami (Ollama)
pip install requests
```

## 📝 Przykłady zastosowań

### 1. Chatbot z dostępem do aktualnych informacji

```python
def chatbot(message):
    # LLM automatycznie zdecyduje czy użyć wyszukiwania
    return chat_with_web_search(message)

chatbot("Jaka jest aktualna wersja Node.js?")
```

### 2. Asystent programistyczny

```python
def code_assistant(query, language="python"):
    tool = WebSearchTool()
    results = tool.search_code_examples(language, query)
    return tool.format_for_llm(results)

code_assistant("how to parse JSON", "python")
```

### 3. Wyszukiwarka projektów open source

```python
def find_github_projects(topic, language=None):
    tool = WebSearchTool()
    results = tool.search_github(topic, language=language)
    return [f"{r.name}: {r.url}" for r in results]

find_github_projects("machine learning", "python")
```

## ⚡ Tips & Best Practices

1. **Konkretne zapytania**: Im bardziej precyzyjne zapytanie, tym lepsze wyniki
   ```python
   # ❌ Słabe
   search("python")
   
   # ✅ Dobre
   search("python asyncio async await tutorial beginner")
   ```

2. **Filtrowanie po języku**: Dla wyszukiwania GitHub używaj parametru `language`
   ```python
   search_github("web framework", language="python")
   ```

3. **Formatowanie dla LLM**: Zawsze używaj `format_for_llm()` dla wyników przekazywanych do modelu
   ```python
   results = tool.search(query)
   llm_input = tool.format_for_llm(results, include_snippets=True)
   ```

4. **Limit wyników**: Dla szybszych odpowiedzi ogranicz liczbę wyników
   ```python
   results = tool.search(query, num_results=3)  # Szybciej
   ```

## 🐛 Rozwiązywanie problemów

### Problem: Brak wyników

```python
# Sprawdź czy z-ai jest dostępne
import subprocess
result = subprocess.run(["z-ai", "--help"], capture_output=True)
print(result.returncode)  # Powinno być 0
```

### Problem: Przekroczenie czasu

```python
# Zwiększ timeout w _execute_search() lub zmniejsz num_results
tool = WebSearchTool(default_num_results=3)  # Mniej wyników
```

## 📜 Licencja

Kod udostępniony jako public domain. Możesz swobodnie używać, modyfikować i rozprowadzać.
