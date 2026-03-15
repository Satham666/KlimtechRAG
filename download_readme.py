import subprocess
import json
import os
import sys
import re
from datetime import datetime

# Konfiguracja
CACHE_FILE = "forks_cache.json"
OUTPUT_DIR = "readme_files"  # Katalog na pobrane README
MAX_FILES = 5  # Limit do testów (ustaw na None lub 0 dla bez limitu)


def check_github_auth():
    """Sprawdza połączenie z GitHub."""
    print("[*] Sprawdzanie połączenia z GitHub...")
    
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("[ERROR] Brak połączenia z GitHub!")
            print("Zaloguj się: gh auth login")
            return False
        
        # Test API
        test_result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True
        )
        
        if test_result.returncode != 0:
            print("[WARN] API nie odpowiada")
            return False
        
        print(f"[OK] Połączono jako: {test_result.stdout.strip()}")
        return True
        
    except FileNotFoundError:
        print("[ERROR] 'gh' nie jest zainstalowane")
        return False


def load_forks_list():
    """Wczytuje listę forków z cache lub pobiera z GitHub."""
    
    # Spróbuj wczytać z cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            # Obsługa obu formatów
            if isinstance(cache, list):
                forks = cache
            else:
                forks = cache.get("forks", [])
            
            if forks:
                print(f"[*] Wczytano {len(forks)} forków z {CACHE_FILE}")
                return forks
                
        except Exception as e:
            print(f"[WARN] Błąd odczytu cache: {e}")
    
    # Pobierz z GitHub
    print("[*] Pobieranie forków z GitHub...")
    try:
        cmd = ["gh", "repo", "list", "--fork", "--json", "url,name,parent", "--limit", "1000"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] Nie udało się pobrać forków: {result.stderr.strip()}")
            return []
        
        repos = json.loads(result.stdout)
        
        # Zbuduj listę URL-i parentów (oryginalnych repozytoriów)
        fork_urls = []
        for repo in repos:
            parent = repo.get("parent")
            if parent:
                owner = parent.get("owner", {}).get("login", "")
                name = parent.get("name", "")
                if owner and name:
                    fork_urls.append(f"https://github.com/{owner}/{name}")
        
        print(f"[*] Pobrano {len(fork_urls)} forków z GitHub")
        return fork_urls
        
    except Exception as e:
        print(f"[ERROR] Błąd: {e}")
        return []


def sanitize_filename(name):
    """Czyści nazwę pliku z niedozwolonych znaków."""
    # Usuń lub zamień niedozwolone znaki
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip()
    return name


def extract_repo_name(url):
    """Wyciąga nazwę repozytorium z URL."""
    # https://github.com/owner/repo -> repo
    parts = url.rstrip("/").split("/")
    if len(parts) >= 2:
        return parts[-1]
    return url


def download_readme(repo_url):
    """Pobiera plik README.md z repozytorium."""
    # Możliwe nazwy pliku README
    readme_variants = [
        "README.md",
        "README.markdown",
        "README.rst",
        "README.txt",
        "README",
        "readme.md"
    ]
    
    for readme_name in readme_variants:
        try:
            # Użyj gh api do pobrania zawartości pliku
            # Format URL: https://github.com/owner/repo
            parts = repo_url.rstrip("/").replace("https://github.com/", "").split("/")
            if len(parts) < 2:
                continue
            
            owner, repo = parts[0], parts[1]
            
            # Pobierz zawartość pliku przez API
            cmd = [
                "gh", "api",
                f"repos/{owner}/{repo}/contents/{readme_name}",
                "--jq", ".content"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout.strip():
                # Dekoduj base64
                import base64
                try:
                    content = base64.b64decode(result.stdout.strip()).decode('utf-8')
                    return content, readme_name
                except:
                    continue
            else:
                # Spróbuj inną nazwę pliku
                continue
                
        except Exception as e:
            continue
    
    return None, None


def download_readme_simple(repo_url):
    """Pobiera README.md prostszą metodą przez raw.githubusercontent.com."""
    try:
        parts = repo_url.rstrip("/").replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            return None, None
        
        owner, repo = parts[0], parts[1]
        
        # Lista możliwych nazw README
        readme_names = ["README.md", "readme.md", "README.markdown", "README.rst", "README"]
        
        for readme in readme_names:
            # Pobierz przez gh api repos/{owner}/{repo}/readme
            cmd = ["gh", "api", f"repos/{owner}/{repo}/readme"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    import base64
                    content = base64.b64decode(data["content"]).decode('utf-8')
                    return content, data.get("name", "README.md")
                except:
                    pass
        
        # Alternatywnie - spróbuj pobrać przez curl/wget z raw
        readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
        result = subprocess.run(
            ["curl", "-s", "-L", readme_url],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout and not result.stdout.startswith("<!DOCTYPE"):
            return result.stdout, "README.md"
        
        # Spróbuj master zamiast main
        readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
        result = subprocess.run(
            ["curl", "-s", "-L", readme_url],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout and not result.stdout.startswith("<!DOCTYPE"):
            return result.stdout, "README.md"
        
        return None, None
        
    except Exception as e:
        return None, None


def main():
    args = sys.argv[1:]
    
    # Parsuj limit z argumentów
    limit = MAX_FILES
    if "--all" in args:
        limit = None
    elif args and args[0].isdigit():
        limit = int(args[0])
    
    print("=" * 60)
    print("[*] README DOWNLOADER - pobieranie README.md z forków")
    print("=" * 60)
    
    # 1. Sprawdź połączenie
    if not check_github_auth():
        sys.exit(1)
    
    # 2. Wczytaj listę forków
    forks = load_forks_list()
    
    if not forks:
        print("[ERROR] Brak forków do przetworzenia")
        sys.exit(1)
    
    # 3. Utwórz katalog wyjściowy
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"[*] Utworzono katalog: {OUTPUT_DIR}")
    
    # 4. Limit do testów
    if limit and limit > 0:
        forks_to_process = forks[:limit]
        print(f"\n[*] Tryb testowy - pobieram {limit} z {len(forks)} forków")
        print("[*] Użyj --all aby pobrać wszystkie")
    else:
        forks_to_process = forks
        print(f"\n[*] Pobieranie z wszystkich {len(forks)} forków")
    
    print()
    
    # 5. Pobieranie README
    stats = {"success": 0, "notfound": 0, "error": 0}
    
    for i, repo_url in enumerate(forks_to_process, 1):
        repo_name = extract_repo_name(repo_url)
        safe_name = sanitize_filename(repo_name)
        output_file = os.path.join(OUTPUT_DIR, f"{safe_name}_README.md")
        
        print(f"[{i}/{len(forks_to_process)}] {repo_name}...")
        
        content, readme_name = download_readme_simple(repo_url)
        
        if content:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"    ✅ Zapisano: {output_file}")
                stats["success"] += 1
            except Exception as e:
                print(f"    ❌ Błąd zapisu: {e}")
                stats["error"] += 1
        else:
            print(f"    ⚠️  Brak README.md")
            stats["notfound"] += 1
    
    # 6. Podsumowanie
    print("\n" + "=" * 60)
    print("[*] PODSUMOWANIE:")
    print(f"    ✅ Pobrano:    {stats['success']}")
    print(f"    ⚠️  Brak README: {stats['notfound']}")
    print(f"    ❌ Błędy:     {stats['error']}")
    print(f"\n[*] Pliki w: {OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Przerwano (Ctrl+C)")
        sys.exit(0)
