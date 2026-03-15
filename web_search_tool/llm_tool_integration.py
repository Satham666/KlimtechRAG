#!/usr/bin/env python3
"""
LLM Integration Example with Web Search
========================================
Przykład integracji narzędzia web_search z modelem LLM.
Pokazuje jak wdrożyć wzorzec Function Calling / Tool Use.

Ten skrypt demonstruje jak:
1. Definiować narzędzia dla LLM
2. Wykonywać funkcje na żądanie modelu
3. Zwracać wyniki do modelu

Autor: Super Z Assistant
"""

import json
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from web_search_tool import WebSearchTool, SearchResult


# =============================================================================
# DEFINICJE NARZĘDZI DLA LLM
# =============================================================================

WEB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": """
            Przeszukuje sieć internetową i zwraca relevantne wyniki.
            Używaj tego narzędzia gdy potrzebujesz aktualnych informacji z internetu,
            których nie znasz lub które mogą się zmienić.
            
            Przykłady użycia:
            - Wyszukiwanie aktualnych informacji
            - Znajdowanie projektów na GitHub
            - Sprawdzanie dokumentacji technicznych
            - Wyszukiwanie tutoriali i przykładów kodu
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Zapytanie wyszukiwania. Bądź konkretny i używaj odpowiednich słów kluczowych."
                },
                "num_results": {
                    "type": "integer",
                    "description": "Liczba wyników do zwrócenia (domyślnie 5)",
                    "default": 5
                },
                "search_type": {
                    "type": "string",
                    "enum": ["general", "github", "documentation", "code"],
                    "description": """
                        Typ wyszukiwania:
                        - 'general': ogólne wyszukiwanie w sieci
                        - 'github': wyszukiwanie projektów na GitHub
                        - 'documentation': wyszukiwanie dokumentacji technicznej
                        - 'code': wyszukiwanie przykładów kodu
                    """,
                    "default": "general"
                },
                "language": {
                    "type": "string",
                    "description": "Język programowania (opcjonalnie, dla typów 'github' i 'code')",
                    "default": None
                }
            },
            "required": ["query"]
        }
    }
}

GITHUB_SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "github_search",
        "description": """
            Wyszukuje projekty i repozytoria na GitHub.
            Zwraca informacje o popularności (gwiazdki), opis i linki.
            
            Używaj gdy użytkownik pyta o:
            - Biblioteki i frameworki
            - Przykładowe projekty
            - Open source narzędzia
            - Kod w określonym języku
        """,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Zapytanie wyszukiwania na GitHub"
                },
                "language": {
                    "type": "string",
                    "description": "Filtruj po języku programowania (np. python, javascript, rust)"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Liczba wyników (domyślnie 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}


# =============================================================================
# TOOL EXECUTOR - WYKONUJE FUNKCJE NA ŻĄDANIE LLM
# =============================================================================

class ToolExecutor:
    """
    Wykonuje narzędzia na żądanie modelu LLM.
    
    Przykład użycia z OpenAI API:
        executor = ToolExecutor()
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=executor.get_tool_definitions()
        )
        
        # Jeśli model chce wywołać narzędzie
        if response.choices[0].message.tool_calls:
            tool_results = executor.execute_tool_calls(
                response.choices[0].message.tool_calls
            )
    """
    
    def __init__(self):
        self.search_tool = WebSearchTool(default_num_results=5)
        self._tools: Dict[str, Callable] = {
            "web_search": self._web_search,
            "github_search": self._github_search,
        }
    
    def get_tool_definitions(self) -> List[Dict]:
        """Zwraca definicje narzędzi w formacie OpenAI."""
        return [WEB_SEARCH_TOOL_SCHEMA, GITHUB_SEARCH_TOOL_SCHEMA]
    
    def _web_search(self, **kwargs) -> str:
        """Wykonuje wyszukiwanie w sieci."""
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)
        search_type = kwargs.get("search_type", "general")
        language = kwargs.get("language")
        
        if search_type == "github":
            results = self.search_tool.search_github(
                query, language=language, num_results=num_results
            )
        elif search_type == "documentation":
            results = self.search_tool.search_documentation(
                language or "general", query, num_results=num_results
            )
        elif search_type == "code":
            results = self.search_tool.search_code_examples(
                language or "python", query, num_results=num_results
            )
        else:
            results = self.search_tool.search(query, num_results=num_results)
        
        return self.search_tool.format_for_llm(results)
    
    def _github_search(self, **kwargs) -> str:
        """Wyszukuje na GitHub."""
        query = kwargs.get("query", "")
        language = kwargs.get("language")
        num_results = kwargs.get("num_results", 5)
        
        results = self.search_tool.search_github(
            query, language=language, num_results=num_results
        )
        
        return self.search_tool.format_for_llm(results)
    
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """
        Wykonuje narzędzie o podanej nazwie z argumentami.
        
        Args:
            name: Nazwa narzędzia
            arguments: Argumenty wywołania
            
        Returns:
            Wynik wykonania narzędzia jako string
        """
        if name not in self._tools:
            return f"Błąd: Nieznane narzędzie '{name}'"
        
        try:
            return self._tools[name](**arguments)
        except Exception as e:
            return f"Błąd wykonania narzędzia '{name}': {str(e)}"
    
    def execute_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, str]]:
        """
        Wykonuje listę wywołań narzędzi (format OpenAI).
        
        Args:
            tool_calls: Lista obiektów tool_calls z odpowiedzi OpenAI
            
        Returns:
            Lista wyników w formacie wiadomości dla API
        """
        results = []
        
        for tool_call in tool_calls:
            name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            result = self.execute_tool(name, arguments)
            
            results.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": name,
                "content": result
            })
        
        return results


# =============================================================================
# PRZYKŁAD INTEGRACJI Z OPENAI API
# =============================================================================

EXAMPLE_OPENAI_INTEGRATION = '''
import openai
from tool_integration import ToolExecutor

# Inicjalizacja
client = openai.OpenAI(api_key="YOUR_API_KEY")
executor = ToolExecutor()

def chat_with_web_search(user_message: str, conversation_history: list = None):
    """
    Funkcja czatu z dostępem do wyszukiwania w sieci.
    
    Args:
        user_message: Wiadomość użytkownika
        conversation_history: Historia konwersacji (opcjonalnie)
    
    Returns:
        Odpowiedź asystenta
    """
    messages = conversation_history or []
    messages.append({"role": "user", "content": user_message})
    
    # Pierwsze zapytanie do modelu
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        tools=executor.get_tool_definitions(),
        tool_choice="auto"
    )
    
    assistant_message = response.choices[0].message
    
    # Sprawdź czy model chce użyć narzędzi
    if assistant_message.tool_calls:
        # Dodaj wiadomość asystenta z tool_calls do historii
        messages.append(assistant_message)
        
        # Wykonaj narzędzia
        tool_results = executor.execute_tool_calls(assistant_message.tool_calls)
        
        # Dodaj wyniki narzędzi do historii
        for result in tool_results:
            messages.append({
                "tool_call_id": result["tool_call_id"],
                "role": "tool",
                "content": result["content"]
            })
        
        # Wyślij zapytanie ponownie z wynikami narzędzi
        final_response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages
        )
        
        return final_response.choices[0].message.content
    
    return assistant_message.content


# Przykład użycia
if __name__ == "__main__":
    # Przykład 1: Ogólne wyszukiwanie
    odpowiedz = chat_with_web_search(
        "Jakie są najnowsze wersje Python i jakie mają nowe funkcje?"
    )
    print(odpowiedz)
    
    # Przykład 2: Wyszukiwanie na GitHub
    odpowiedz = chat_with_web_search(
        "Znajdź popularne biblioteki Python do web scrapingu"
    )
    print(odpowiedz)
'''


# =============================================================================
# PRZYKŁAD INTEGRACJI Z LOKALNYM MODELEM (Ollama, LM Studio, etc.)
# =============================================================================

EXAMPLE_LOCAL_LLM_INTEGRATION = '''
import requests
import json
from tool_integration import ToolExecutor

class LocalLLMWithWebSearch:
    """
    Integracja z lokalnym modelem LLM (Ollama, LM Studio, etc.)
    obsługującym function calling.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.executor = ToolExecutor()
    
    def chat(self, user_message: str, model: str = "llama3.1") -> str:
        """Czat z lokalnym modelem z dostępem do wyszukiwania."""
        
        # Dla Ollama z obsługą narzędzi
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": user_message}
            ],
            "tools": self.executor.get_tool_definitions()
        }
        
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload
        )
        
        result = response.json()
        message = result.get("message", {})
        
        # Jeśli model wywołał narzędzia
        if "tool_calls" in message:
            tool_results = []
            for tool_call in message["tool_calls"]:
                name = tool_call["function"]["name"]
                args = tool_call["function"]["arguments"]
                
                result = self.executor.execute_tool(name, args)
                tool_results.append(result)
            
            # Kontynuuj konwersację z wynikami
            payload["messages"].append(message)
            for tr in tool_results:
                payload["messages"].append({
                    "role": "tool",
                    "content": tr
                })
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            return response.json()["message"]["content"]
        
        return message.get("content", "")

# Użycie
# llm = LocalLLMWithWebSearch()
# odpowiedz = llm.chat("Znajdź najlepsze biblioteki Python do ML")
'''


# =============================================================================
# DEMO / TEST
# =============================================================================

def demo():
    """Demonstracja działania narzędzia."""
    print("=" * 60)
    print("🤖 DEMO: Web Search Tool dla LLM")
    print("=" * 60)
    
    executor = ToolExecutor()
    
    print("\n📋 Dostępne narzędzia:")
    for tool in executor.get_tool_definitions():
        print(f"  - {tool['function']['name']}: {tool['function']['description'][:50]}...")
    
    print("\n" + "=" * 60)
    print("🔍 TEST 1: Wyszukiwanie na GitHub")
    print("=" * 60)
    
    result = executor.execute_tool("github_search", {
        "query": "network port scanner",
        "language": "python",
        "num_results": 3
    })
    print(result)
    
    print("\n" + "=" * 60)
    print("🔍 TEST 2: Ogólne wyszukiwanie")
    print("=" * 60)
    
    result = executor.execute_tool("web_search", {
        "query": "Python asyncio tutorial",
        "num_results": 3
    })
    print(result)
    
    print("\n" + "=" * 60)
    print("✅ Demo zakończone!")
    print("=" * 60)
    
    print("\n💡 Aby zintegrować z modelem LLM, zobacz przykłady w kodzie:")
    print("   - EXAMPLE_OPENAI_INTEGRATION")
    print("   - EXAMPLE_LOCAL_LLM_INTEGRATION")


if __name__ == "__main__":
    demo()
