#!/usr/bin/env python3
"""
Web Search Tool for LLM Integration
====================================
Skrypt umożliwiający modelowi LLM przeszukiwanie sieci internetowej.
Może być używany jako samodzielne narzędzie CLI lub importowany jako moduł.

Autor: Super Z Assistant
"""

import json
import subprocess
import argparse
import sys
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SearchResult:
    """Reprezentuje pojedynczy wynik wyszukiwania."""
    url: str
    name: str
    snippet: str
    host_name: str
    rank: int
    date: str
    favicon: str

    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje wynik do słownika."""
        return {
            "url": self.url,
            "name": self.name,
            "snippet": self.snippet,
            "host_name": self.host_name,
            "rank": self.rank,
            "date": self.date,
            "favicon": self.favicon
        }

    def __str__(self) -> str:
        """Zwraca czytelną reprezentację tekstową wyniku."""
        output = f"\n[{self.rank + 1}] {self.name}\n"
        output += f"    URL: {self.url}\n"
        output += f"    Host: {self.host_name}\n"
        output += f"    Opis: {self.snippet}\n"
        if self.date:
            output += f"    Data: {self.date}\n"
        return output


class WebSearchTool:
    """
    Narzędzie do przeszukiwania sieci internetowej dla modeli LLM.
    
    Wykorzystuje z-ai-web-dev-sdk do wykonywania zapytań web_search.
    
    Przykłady użycia:
        # Podstawowe wyszukiwanie
        tool = WebSearchTool()
        results = tool.search("python machine learning tutorial")
        
        # Wyszukiwanie na GitHub
        results = tool.search_github("network port scanner", language="python")
        
        # Formatowanie dla LLM
        formatted = tool.format_for_llm(results)
    """

    def __init__(self, default_num_results: int = 10):
        """
        Inicjalizuje narzędzie do wyszukiwania.
        
        Args:
            default_num_results: Domyślna liczba wyników do zwrócenia
        """
        self.default_num_results = default_num_results

    def _execute_search(self, query: str, num_results: int) -> List[SearchResult]:
        """
        Wykonuje wyszukiwanie przez z-ai CLI.
        
        Args:
            query: Zapytanie wyszukiwania
            num_results: Liczba wyników do zwrócenia
            
        Returns:
            Lista wyników wyszukiwania
        """
        args_json = json.dumps({
            "query": query,
            "num": num_results
        }, ensure_ascii=False)
        
        cmd = [
            "z-ai", "function",
            "-n", "web_search",
            "-a", args_json
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"Błąd wyszukiwania: {result.stderr}", file=sys.stderr)
                return []
            
            # Parsowanie wyjścia - szukamy JSON w output
            output = result.stdout
            lines = output.strip().split('\n')
            
            # Znajdź początek i koniec tablicy JSON
            json_start = -1
            json_end = -1
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith('[') and json_start == -1:
                    json_start = i
                if stripped.startswith(']') and json_start != -1:
                    json_end = i
                    break
            
            if json_start == -1 or json_end == -1:
                print("Nie znaleziono danych JSON w odpowiedzi", file=sys.stderr)
                return []
            
            # Wyciągnij tylko linie z JSON
            json_lines = lines[json_start:json_end + 1]
            json_output = '\n'.join(json_lines)
            data = json.loads(json_output)
            
            results = []
            for item in data:
                results.append(SearchResult(
                    url=item.get("url", ""),
                    name=item.get("name", ""),
                    snippet=item.get("snippet", ""),
                    host_name=item.get("host_name", ""),
                    rank=item.get("rank", 0),
                    date=item.get("date", ""),
                    favicon=item.get("favicon", "")
                ))
            
            return results
            
        except subprocess.TimeoutExpired:
            print("Przekroczono limit czasu wyszukiwania", file=sys.stderr)
            return []
        except json.JSONDecodeError as e:
            print(f"Błąd parsowania JSON: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Nieoczekiwany błąd: {e}", file=sys.stderr)
            return []

    def search(self, query: str, num_results: Optional[int] = None) -> List[SearchResult]:
        """
        Przeszukuje sieć internetową.
        
        Args:
            query: Zapytanie wyszukiwania
            num_results: Liczba wyników (opcjonalnie, używa domyślnej)
            
        Returns:
            Lista wyników wyszukiwania
        """
        num = num_results or self.default_num_results
        return self._execute_search(query, num)

    def search_github(
        self, 
        query: str, 
        language: Optional[str] = None,
        sort_by: str = "stars",
        num_results: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Wyszukuje projekty na GitHub.
        
        Args:
            query: Zapytanie wyszukiwania
            language: Język programowania do filtrowania (np. "python", "javascript")
            sort_by: Sortowanie ("stars", "forks", "updated")
            num_results: Liczba wyników
            
        Returns:
            Lista wyników wyszukiwania
        """
        # Konstrukcja zapytania specyficznego dla GitHub
        full_query = f"github {query}"
        if language:
            full_query += f" {language}"
        if sort_by:
            full_query += f" {sort_by}"
        
        num = num_results or self.default_num_results
        return self._execute_search(full_query, num)

    def search_documentation(
        self, 
        technology: str, 
        topic: str,
        num_results: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Wyszukuje dokumentację techniczną.
        
        Args:
            technology: Nazwa technologii (np. "react", "python", "docker")
            topic: Temat do wyszukania
            num_results: Liczba wyników
            
        Returns:
            Lista wyników wyszukiwania
        """
        query = f"{technology} documentation {topic}"
        num = num_results or self.default_num_results
        return self._execute_search(query, num)

    def search_code_examples(
        self,
        language: str,
        problem: str,
        num_results: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Wyszukuje przykłady kodu.
        
        Args:
            language: Język programowania
            problem: Opis problemu
            num_results: Liczba wyników
            
        Returns:
            Lista wyników wyszukiwania
        """
        query = f"{language} code example {problem}"
        num = num_results or self.default_num_results
        return self._execute_search(query, num)

    @staticmethod
    def format_for_llm(results: List[SearchResult], include_snippets: bool = True) -> str:
        """
        Formatuje wyniki w formacie czytelnym dla LLM.
        
        Args:
            results: Lista wyników wyszukiwania
            include_snippets: Czy uwzględnić fragmenty tekstowe
            
        Returns:
            Sformatowany tekst z wynikami
        """
        if not results:
            return "Brak wyników wyszukiwania."
        
        output = f"Znaleziono {len(results)} wyników:\n"
        output += "=" * 60 + "\n"
        
        for result in results:
            output += f"\n## Wynik {result.rank + 1}\n"
            output += f"**Tytuł:** {result.name}\n"
            output += f"**URL:** {result.url}\n"
            output += f"**Domena:** {result.host_name}\n"
            if include_snippets and result.snippet:
                output += f"**Opis:** {result.snippet}\n"
            if result.date:
                output += f"**Data:** {result.date}\n"
            output += "-" * 40 + "\n"
        
        return output

    @staticmethod
    def to_json(results: List[SearchResult]) -> str:
        """
        Konwertuje wyniki do formatu JSON.
        
        Args:
            results: Lista wyników wyszukiwania
            
        Returns:
            String JSON z wynikami
        """
        return json.dumps(
            [r.to_dict() for r in results],
            indent=2,
            ensure_ascii=False
        )


def main():
    """Główna funkcja CLI."""
    parser = argparse.ArgumentParser(
        description="Narzędzie do przeszukiwania sieci dla modeli LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  # Podstawowe wyszukiwanie
  python web_search_tool.py "python machine learning"
  
  # Wyszukiwanie na GitHub
  python web_search_tool.py --github "network scanner" --language python
  
  # Wyszukiwanie dokumentacji
  python web_search_tool.py --docs react hooks
  
  # Format JSON dla LLM
  python web_search_tool.py "docker tutorial" --format json
        """
    )
    
    parser.add_argument(
        "query",
        help="Zapytanie wyszukiwania"
    )
    
    parser.add_argument(
        "-n", "--num",
        type=int,
        default=10,
        help="Liczba wyników (domyślnie: 10)"
    )
    
    parser.add_argument(
        "--github",
        action="store_true",
        help="Wyszukuj na GitHub"
    )
    
    parser.add_argument(
        "--language",
        help="Język programowania (dla wyszukiwania GitHub)"
    )
    
    parser.add_argument(
        "--docs",
        action="store_true",
        help="Wyszukuj dokumentację techniczną"
    )
    
    parser.add_argument(
        "--technology",
        help="Nazwa technologii (dla wyszukiwania dokumentacji)"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json", "llm"],
        default="text",
        help="Format wyjścia: text (czytelny), json, llm (dla LLM)"
    )
    
    parser.add_argument(
        "--no-snippets",
        action="store_true",
        help="Pomiń fragmenty tekstowe w formacie LLM"
    )
    
    args = parser.parse_args()
    
    tool = WebSearchTool(default_num_results=args.num)
    
    # Wykonanie odpowiedniego typu wyszukiwania
    if args.github:
        results = tool.search_github(
            args.query,
            language=args.language,
            num_results=args.num
        )
    elif args.docs:
        tech = args.technology or "general"
        results = tool.search_documentation(
            tech,
            args.query,
            num_results=args.num
        )
    else:
        results = tool.search(args.query, num_results=args.num)
    
    # Formatowanie wyjścia
    if args.format == "json":
        print(tool.to_json(results))
    elif args.format == "llm":
        print(tool.format_for_llm(results, include_snippets=not args.no_snippets))
    else:
        print(f"\n🔍 Wyniki wyszukiwania dla: '{args.query}'")
        print("=" * 60)
        for result in results:
            print(result)


# Funkcje pomocnicze do importu jako moduł
def quick_search(query: str, num: int = 10) -> List[SearchResult]:
    """
    Szybka funkcja wyszukiwania (dla importu).
    
    Args:
        query: Zapytanie wyszukiwania
        num: Liczba wyników
        
    Returns:
        Lista wyników wyszukiwania
    """
    tool = WebSearchTool()
    return tool.search(query, num)


def quick_github_search(query: str, language: str = None, num: int = 10) -> List[SearchResult]:
    """
    Szybkie wyszukiwanie na GitHub (dla importu).
    
    Args:
        query: Zapytanie wyszukiwania
        language: Język programowania
        num: Liczba wyników
        
    Returns:
        Lista wyników wyszukiwania
    """
    tool = WebSearchTool()
    return tool.search_github(query, language=language, num_results=num)


if __name__ == "__main__":
    main()
