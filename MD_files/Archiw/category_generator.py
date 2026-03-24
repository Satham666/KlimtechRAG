"""
Generator kategorii dokumentów RAG.

Ten moduł służy do generowania i zarządzania kategoriami dokumentów
w systemie RAG. Obsługuje wiele języków (PL, EN, DE) i pozwala na
modułowe zarządzanie kategoriami.

Użycie z terminala:
    python3 -m backend_app.utils.category_generator medicine pl
    python3 -m backend_app.utils.category_generator --all pl
    python3 -m backend_app.utils.category_generator --list

Użycie z kodu:
    from backend_app.utils.category_generator import generate_category, load_category
    
    medicine = generate_category("medicine", "pl")
    medicine = load_category("medicine")
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import definicji kategorii
from backend_app.config.category_definitions import (
    CATEGORY_TEMPLATES,
    get_category_template,
    list_available_categories,
    get_all_keywords
)


# ============================================================================
# KONFIGURACJA ŚCIEŻEK
# ============================================================================

def _get_categories_dir() -> Path:
    """Zwraca ścieżkę do katalogu z plikami kategorii."""
    # Ścieżka względna do tego pliku
    current_dir = Path(__file__).parent
    return current_dir.parent / "config" / "categories"


def _ensure_categories_dir() -> None:
    """Upewnia się, że katalog kategorii istnieje."""
    categories_dir = _get_categories_dir()
    categories_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# GENEROWANIE KATEGORII
# ============================================================================

def generate_category(category_name: str, language: str = "pl") -> Dict[str, Any]:
    """
    Generuje pełną strukturę kategorii dla podanej dziedziny.
    
    Args:
        category_name: Identyfikator kategorii (np. "medicine", "law")
        language: Kod języka ("pl", "en", "de")
    
    Returns:
        Dict z pełną strukturą kategorii w formacie JSON
        
    Raises:
        KeyError: Jeśli kategoria nie istnieje
        ValueError: Jeśli język nie jest wspierany
        
    Example:
        >>> medicine = generate_category("medicine", "pl")
        >>> print(medicine["name"])
        'Medycyna'
    """
    if category_name not in CATEGORY_TEMPLATES:
        available = list_available_categories()
        raise KeyError(
            f"Kategoria '{category_name}' nie istnieje. "
            f"Dostępne kategorie: {available}"
        )
    
    if language not in ["pl", "en", "de"]:
        raise ValueError(
            f"Język '{language}' nie jest wspierany. "
            f"Dostępne języki: pl, en, de"
        )
    
    # Pobierz template z category_definitions
    template = get_category_template(category_name, language)
    
    # Dodaj metadane
    result = {
        "version": "1.0",
        "category_id": category_name,
        "language": language,
        "generated_at": _get_timestamp(),
        "data": template
    }
    
    return result


def generate_all_categories(language: str = "pl") -> Dict[str, Dict[str, Any]]:
    """
    Generuje wszystkie dostępne kategorie.
    
    Args:
        language: Kod języka ("pl", "en", "de")
    
    Returns:
        Dict {category_id: category_data}
    """
    result = {}
    for category_id in list_available_categories():
        try:
            result[category_id] = generate_category(category_id, language)
        except Exception as e:
            print(f"Błąd generowania kategorii '{category_id}': {e}")
    
    return result


# ============================================================================
# ZAPIS I ODCZYT PLIKÓW
# ============================================================================

def save_category_to_file(
    category_name: str, 
    language: str = "pl",
    output_dir: Optional[Path] = None
) -> Path:
    """
    Generuje i zapisuje kategorię do pliku JSON.
    
    Args:
        category_name: Identyfikator kategorii
        language: Kod języka
        output_dir: Opcjonalny katalog wyjściowy (domyślnie config/categories/)
    
    Returns:
        Path do utworzonego pliku
        
    Example:
        >>> path = save_category_to_file("medicine", "pl")
        >>> print(path)
        'backend_app/config/categories/medicine.json'
    """
    _ensure_categories_dir()
    
    # Generuj kategorię
    category_data = generate_category(category_name, language)
    
    # Określ ścieżkę pliku
    if output_dir is None:
        output_dir = _get_categories_dir()
    
    # Nazwa pliku: {category_id}.json (bez języka w nazwie - plik jest wielojęzyczny)
    filename = f"{category_name}.json"
    filepath = output_dir / filename
    
    # Zapisz do pliku z formatowaniem
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(category_data, f, ensure_ascii=False, indent=2)
    
    return filepath


def save_all_categories(language: str = "pl") -> List[Path]:
    """
    Generuje i zapisuje wszystkie kategorie do plików JSON.
    
    Args:
        language: Kod języka
    
    Returns:
        Lista ścieżek do utworzonych plików
    """
    paths = []
    for category_id in list_available_categories():
        try:
            path = save_category_to_file(category_id, language)
            paths.append(path)
            print(f"✓ Zapisano: {path}")
        except Exception as e:
            print(f"✗ Błąd zapisu '{category_id}': {e}")
    
    return paths


def load_category(category_name: str) -> Dict[str, Any]:
    """
    Wczytuje kategorię z pliku JSON.
    
    Args:
        category_name: Identyfikator kategorii
    
    Returns:
        Dict z danymi kategorii
        
    Raises:
        FileNotFoundError: Jeśli plik kategorii nie istnieje
        
    Example:
        >>> medicine = load_category("medicine")
        >>> print(medicine["data"]["name"])
        'Medycyna'
    """
    categories_dir = _get_categories_dir()
    filepath = categories_dir / f"{category_name}.json"
    
    if not filepath.exists():
        raise FileNotFoundError(
            f"Plik kategorii '{category_name}' nie istnieje. "
            f"Ścieżka: {filepath}. "
            f"Uruchom: python3 -m backend_app.utils.category_generator {category_name} pl"
        )
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def category_exists(category_name: str) -> bool:
    """
    Sprawdza czy plik kategorii istnieje.
    
    Args:
        category_name: Identyfikator kategorii
    
    Returns:
        True jeśli plik istnieje, False w przeciwnym razie
    """
    categories_dir = _get_categories_dir()
    filepath = categories_dir / f"{category_name}.json"
    return filepath.exists()


def list_generated_categories() -> List[str]:
    """
    Zwraca listę wygenerowanych kategorii (pliki JSON).
    
    Returns:
        Lista identyfikatorów kategorii z wygenerowanymi plikami
    """
    categories_dir = _get_categories_dir()
    if not categories_dir.exists():
        return []
    
    return [
        f.stem for f in categories_dir.glob("*.json")
        if f.stem != "__init__"
    ]


# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def _get_timestamp() -> str:
    """Zwraca aktualny timestamp w formacie ISO."""
    from datetime import datetime
    return datetime.now().isoformat()


def print_category_tree(category_name: str, language: str = "pl") -> None:
    """
    Wypisuje drzewo kategorii w czytelnym formacie.
    
    Args:
        category_name: Identyfikator kategorii
        language: Kod języka
    """
    try:
        data = load_category(category_name)
    except FileNotFoundError:
        data = generate_category(category_name, language)
    
    print(f"\n📁 {data['data']['name']} ({data['data']['id']})")
    print(f"   Ścieżka: {data['data']['path']}")
    print(f"   Słowa kluczowe: {', '.join(data['data']['keywords'][:5])}...")
    
    def print_tree(subcats: List[Dict], indent: int = 3) -> None:
        for sub in subcats:
            print(" " * indent + f"├── 📁 {sub['name']} ({sub['id']})")
            if "subcategories" in sub and sub["subcategories"]:
                print_tree(sub["subcategories"], indent + 4)
    
    if "subcategories" in data["data"]:
        print_tree(data["data"]["subcategories"])


# ============================================================================
# CLI INTERFACE
# ============================================================================

def main():
    """Główna funkcja CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generator kategorii dokumentów RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  python3 -m backend_app.utils.category_generator medicine pl
  python3 -m backend_app.utils.category_generator medicine en
  python3 -m backend_app.utils.category_generator --all pl
  python3 -m backend_app.utils.category_generator --list
  python3 -m backend_app.utils.category_generator --tree medicine
        """
    )
    
    parser.add_argument(
        "category",
        nargs="?",
        help="Nazwa kategorii do wygenerowania (np. medicine, law)"
    )
    
    parser.add_argument(
        "language",
        nargs="?",
        default="pl",
        help="Kod języka (pl, en, de). Domyślnie: pl"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Generuj wszystkie dostępne kategorie"
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Wyświetl listę dostępnych kategorii"
    )
    
    parser.add_argument(
        "--tree", "-t",
        metavar="CATEGORY",
        help="Wyświetl drzewo kategorii"
    )
    
    parser.add_argument(
        "--generated", "-g",
        action="store_true",
        help="Wyświetl listę wygenerowanych kategorii (pliki JSON)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Katalog wyjściowy dla plików JSON"
    )
    
    args = parser.parse_args()
    
    # Wyświetl listę dostępnych kategorii
    if args.list:
        print("\n📋 Dostępne kategorie w definicjach:")
        for cat_id in list_available_categories():
            template = CATEGORY_TEMPLATES.get(cat_id, {})
            name = template.get("names", {}).get("pl", cat_id)
            print(f"   • {cat_id}: {name}")
        return
    
    # Wyświetl listę wygenerowanych kategorii
    if args.generated:
        generated = list_generated_categories()
        print("\n📋 Wygenerowane kategorie (pliki JSON):")
        if generated:
            for cat_id in generated:
                print(f"   • {cat_id}")
        else:
            print("   Brak wygenerowanych kategorii.")
            print("   Uruchom: python3 -m backend_app.utils.category_generator --all pl")
        return
    
    # Wyświetl drzewo kategorii
    if args.tree:
        try:
            print_category_tree(args.tree, args.language)
        except KeyError:
            print(f"✗ Kategoria '{args.tree}' nie istnieje.")
            print(f"   Dostępne: {list_available_categories()}")
        return
    
    # Generuj wszystkie kategorie
    if args.all:
        print(f"\n🔧 Generowanie wszystkich kategorii (język: {args.language})...")
        paths = save_all_categories(args.language)
        print(f"\n✅ Wygenerowano {len(paths)} kategorii.")
        return
    
    # Generuj konkretną kategorię
    if args.category:
        try:
            path = save_category_to_file(args.category, args.language, args.output)
            print(f"\n✅ Wygenerowano kategorię: {args.category}")
            print(f"   Plik: {path}")
            print_category_tree(args.category, args.language)
        except KeyError as e:
            print(f"✗ {e}")
        except Exception as e:
            print(f"✗ Błąd: {e}")
        return
    
    # Brak argumentów - wyświetl pomoc
    parser.print_help()


if __name__ == "__main__":
    main()