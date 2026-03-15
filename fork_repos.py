import subprocess
import json
import time
import sys
import os
from datetime import datetime

# Konfiguracja
INPUT_FILE = "repo_list.txt"
CACHE_FILE = "forks_cache.json"
FORK_DELAY = 10  # sekundy między forkami
RATE_LIMIT_WAIT = 60  # sekundy przy rate limit
CACHE_MAX_AGE = 24  # godziny - maksymalny wiek cache'u


def check_github_auth():
    """Sprawdza połączenie i autoryzację z GitHub."""
    print("[*] Sprawdzanie połączenia z GitHub...")
    
    try:
        # Sprawdź status autoryzacji
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True
        )
        
        # Jeśli błąd - brak autoryzacji
        if result.returncode != 0:
            print("\n" + "=" * 60)
            print("[ERROR] BRAK POŁĄCZENIA Z GITHUB!")
            print("=" * 60)
            print(f"\n{result.stderr.strip()}")
            print("\n[Rozwiązanie] Zaloguj się:")
            print("    gh auth login")
            print("\nLub z przeglądarką:")
            print("    gh auth login -w")
            print("=" * 60)
            return False
        
        # Wyciągnij nazwę użytkownika z outputu
        output = result.stdout + result.stderr
        username = ""
        for line in output.split('\n'):
            if "Logged in as" in line:
                username = line.split("as")[-1].strip()
                break
        
        # Dodatkowe sprawdzenie - test API
        test_result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True,
            text=True
        )
        
        if test_result.returncode != 0:
            print("\n[WARN] Autoryzacja jest, ale API nie odpowiada")
            print(f"       {test_result.stderr.strip()}")
            print("\nMożliwe przyczyny:")
            print("  - Rate limiting (za dużo zapytań)")
            print("  - Problemy z siecią")
            print("  - Token wygasł")
            print("\nOdczekaj kilka minut lub zaloguj się ponownie:")
            print("    gh auth refresh")
            return False
        
        api_username = test_result.stdout.strip()
        
        print(f"[OK] Połączono jako: {api_username}")
        return True
        
    except FileNotFoundError:
        print("\n" + "=" * 60)
        print("[ERROR] 'gh' nie jest zainstalowane!")
        print("=" * 60)
        print("\nInstalacja:")
        print("    Ubuntu/Debian: sudo apt install gh")
        print("    Fedora: sudo dnf install gh")
        print("    Arch: sudo pacman -S github-cli")
        print("=" * 60)
        return False
    except Exception as e:
        print(f"[ERROR] Błąd sprawdzania połączenia: {e}")
        return False


def load_forks_cache():
    """Wczytuje cache forków z pliku JSON."""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        # Obsługa starego formatu (sama lista) i nowego (obiekt z metadanymi)
        if isinstance(cache, list):
            # Stary format - sama lista URL-i
            forked_repos = set(cache)
            print(f"[*] Wczytano {len(forked_repos)} forków z cache (stary format)")
            # Migracja do nowego formatu przy następnym zapisie
            return forked_repos
        
        # Nowy format - obiekt z timestamp i forks
        cached_time = datetime.fromisoformat(cache.get("timestamp", "2000-01-01"))
        age_hours = (datetime.now() - cached_time).total_seconds() / 3600
        
        if age_hours > CACHE_MAX_AGE:
            print(f"[*] Cache jest stary ({age_hours:.1f}h), pobieram świeże dane...")
            return None
        
        forked_repos = set(cache.get("forks", []))
        print(f"[*] Wczytano {len(forked_repos)} forków z cache ({age_hours:.1f}h temu)")
        return forked_repos
        
    except json.JSONDecodeError as e:
        print(f"[WARN] Błąd parsowania cache: {e}")
        return None
    except Exception as e:
        print(f"[WARN] Błąd odczytu cache: {e}")
        return None


def save_forks_cache(forked_repos):
    """Zapisuje cache forków do pliku JSON."""
    try:
        cache = {
            "timestamp": datetime.now().isoformat(),
            "count": len(forked_repos),
            "forks": list(forked_repos)
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"[*] Zapisano {len(forked_repos)} forków do cache: {CACHE_FILE}")
    except Exception as e:
        print(f"[WARN] Błąd zapisu cache: {e}")


def get_github_forks(force_refresh=False):
    """Pobiera listę forków z GitHub (lub z cache)."""
    
    if not force_refresh:
        cached = load_forks_cache()
        if cached is not None:
            return cached
    
    print("[*] Pobieranie forków z GitHub...")
    
    try:
        cmd = ["gh", "repo", "list", "--fork", "--json", "url,name,parent", "--limit", "2000"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[ERROR] Nie udało się pobrać forków: {result.stderr.strip()}")
            cached = load_forks_cache()
            if cached is not None:
                print("[*] Używam starego cache jako fallback")
                return cached
            return set()
        
        forks = json.loads(result.stdout)
        
        forked_repos = set()
        for fork in forks:
            parent = fork.get("parent")
            if parent:
                owner_login = parent.get("owner", {}).get("login", "")
                repo_name = parent.get("name", "")
                if owner_login and repo_name:
                    parent_url = f"https://github.com/{owner_login}/{repo_name}"
                    forked_repos.add(parent_url)
        
        print(f"[*] Pobrano {len(forked_repos)} forków z GitHub")
        save_forks_cache(forked_repos)
        
        return forked_repos
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] Błąd parsowania JSON: {e}")
        return set()
    except Exception as e:
        print(f"[ERROR] Błąd pobierania forków: {e}")
        return set()


def load_repo_list():
    """Wczytuje listę repozytoriów z pliku."""
    try:
        with open(INPUT_FILE, 'r') as f:
            repos = set(line.strip() for line in f if line.strip())
        print(f"[*] Wczytano {len(repos)} repozytoriów z {INPUT_FILE}")
        return repos
    except FileNotFoundError:
        print(f"[ERROR] Plik {INPUT_FILE} nie istnieje")
        return set()
    except Exception as e:
        print(f"[ERROR] Błąd odczytu pliku: {e}")
        return set()


def normalize_url(url):
    """Normalizuje URL do formatu: https://github.com/owner/repo."""
    url = url.strip().rstrip("/")
    if url.startswith("https://github.com/"):
        return url
    if "/" in url and not url.startswith("http"):
        return f"https://github.com/{url}"
    return url


def fork_repo(repo_url):
    """Forkuje repozytorium. Zwraca: (status, wiadomość)"""
    try:
        cmd = ["gh", "repo", "fork", repo_url, "--clone=false"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return ("success", "")
        
        stderr = result.stderr.strip()
        stderr_lower = stderr.lower()
        
        if "already forked" in stderr_lower or "already exists" in stderr_lower:
            return ("skip", "")
        if "451" in stderr:
            return ("blocked", "DMCA/legal")
        if "404" in stderr:
            return ("notfound", "nie istnieje")
        if "403" in stderr or "too quickly" in stderr_lower:
            return ("ratelimit", stderr)
        if "401" in stderr or "authentication" in stderr_lower:
            return ("unauthorized", "brak autoryzacji")
        
        return ("error", stderr[:80])
        
    except Exception as e:
        return ("error", str(e))


def print_help():
    """Wyświetla pomoc."""
    print("""
Użycie: python3 fork_repos.py [opcje]

Opcje:
  --refresh    Odśwież cache forków z GitHub
  --status     Pokaż status bez forkowania
  --check      Sprawdź tylko połączenie z GitHub
  --help       Ta pomoc

Pliki:
  repo_list.txt      - lista repozytoriów do sforkowania
  forks_cache.json   - cache forków (automatyczny)
""")


def show_status():
    """Pokazuje status bez forkowania."""
    print("=" * 60)
    print("[*] STATUS FORKÓW")
    print("=" * 60)
    
    if not check_github_auth():
        return
    
    existing_forks = get_github_forks()
    repos_to_process = load_repo_list()
    
    if not repos_to_process:
        return
    
    repos_needing_fork = []
    already_forked = []
    
    for repo_url in repos_to_process:
        normalized = normalize_url(repo_url)
        if normalized in existing_forks:
            already_forked.append(repo_url)
        else:
            repos_needing_fork.append(repo_url)
    
    print("\n" + "-" * 60)
    print(f"[*] Statystyki:")
    print(f"    Repo w pliku:      {len(repos_to_process)}")
    print(f"    Już sforkowane:    {len(already_forked)}")
    print(f"    Do zrobienia:      {len(repos_needing_fork)}")
    print("-" * 60)
    
    if already_forked:
        print(f"\n[*] Już sforkowane ({len(already_forked)}):")
        for r in already_forked[:10]:
            print(f"    ✅ {r}")
        if len(already_forked) > 10:
            print(f"    ... i {len(already_forked) - 10} więcej")
    
    if repos_needing_fork:
        print(f"\n[*] Do sforkowania ({len(repos_needing_fork)}):")
        for r in repos_needing_fork[:10]:
            print(f"    ⏳ {r}")
        if len(repos_needing_fork) > 10:
            print(f"    ... i {len(repos_needing_fork) - 10} więcej")


def main():
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print_help()
        return
    
    if "--check" in args:
        check_github_auth()
        return
    
    if "--status" in args:
        show_status()
        return
    
    force_refresh = "--refresh" in args
    
    print("=" * 60)
    print("[*] FORK REPOS - z cache i sprawdzaniem połączenia")
    print("=" * 60)
    
    # 1. Sprawdź połączenie z GitHub
    if not check_github_auth():
        sys.exit(1)
    
    print()
    
    # 2. Pobierz forki (z cache lub GitHub)
    existing_forks = get_github_forks(force_refresh=force_refresh)
    
    # 3. Wczytaj listę repozytoriów
    repos_to_process = load_repo_list()
    
    if not repos_to_process:
        print("[ERROR] Brak repozytoriów do przetworzenia")
        return
    
    # 4. Porównaj
    repos_needing_fork = []
    already_forked = []
    
    for repo_url in repos_to_process:
        normalized = normalize_url(repo_url)
        if normalized in existing_forks:
            already_forked.append(repo_url)
        else:
            repos_needing_fork.append(repo_url)
    
    # 5. Podsumowanie
    print("\n" + "-" * 60)
    print(f"[*] W pliku: {len(repos_to_process)} | Forkowane: {len(already_forked)} | Do zrobienia: {len(repos_needing_fork)}")
    print("-" * 60)
    
    if not repos_needing_fork:
        print("\n[OK] Wszystkie repozytoria są już sforkowane!")
        return
    
    # 6. Szacowany czas
    est_min = (len(repos_needing_fork) * FORK_DELAY) // 60
    print(f"\n[*] Czas szacowany: ~{est_min} min | Opóźnienie: {FORK_DELAY}s\n")
    
    # 7. Forkowanie
    stats = {"success": 0, "skip": 0, "blocked": 0, "notfound": 0, "ratelimit": 0, "error": 0, "unauthorized": 0}
    failed_repos = []
    new_forks = set()
    
    for i, repo_url in enumerate(repos_needing_fork, 1):
        progress = f"[{i}/{len(repos_needing_fork)}]"
        
        status, msg = fork_repo(repo_url)
        
        if status == "success":
            print(f"{progress} [OK] {repo_url}")
            stats["success"] += 1
            new_forks.add(normalize_url(repo_url))
            
        elif status == "skip":
            print(f"{progress} [SKIP] {repo_url}")
            stats["skip"] += 1
            new_forks.add(normalize_url(repo_url))
            
        elif status == "blocked":
            print(f"{progress} [BLOCKED] {repo_url}")
            stats["blocked"] += 1
            
        elif status == "notfound":
            print(f"{progress} [404] {repo_url}")
            stats["notfound"] += 1
            
        elif status == "ratelimit":
            print(f"{progress} [RATE LIMIT] czekam {RATE_LIMIT_WAIT}s...")
            time.sleep(RATE_LIMIT_WAIT)
            status2, msg2 = fork_repo(repo_url)
            if status2 == "success":
                print(f"         [OK po ponowieniu] {repo_url}")
                stats["success"] += 1
                new_forks.add(normalize_url(repo_url))
            else:
                print(f"         [BŁĄD] {repo_url}")
                stats["ratelimit"] += 1
                failed_repos.append(repo_url)
                
        elif status == "unauthorized":
            print(f"{progress} [UNAUTHORIZED] {repo_url}")
            stats["unauthorized"] += 1
            print("\n[ERROR] Utrata połączenia z GitHub!")
            print("Zaloguj się ponownie: gh auth login")
            failed_repos.append(repo_url)
            # Przerwij - nie ma sensu kontynuować bez autoryzacji
            break
            
        else:
            print(f"{progress} [ERROR] {repo_url}: {msg[:50]}")
            stats["error"] += 1
            failed_repos.append(repo_url)
        
        if i < len(repos_needing_fork) and status not in ("ratelimit", "unauthorized"):
            time.sleep(FORK_DELAY)
    
    # 8. Zaktualizuj cache z nowymi forkami
    if new_forks:
        all_forks = existing_forks | new_forks
        save_forks_cache(all_forks)
    
    # 9. Podsumowanie
    print("\n" + "=" * 60)
    print("[*] PODSUMOWANIE:")
    print(f"    ✅ Udane forki:     {stats['success']}")
    print(f"    ⏭️  Pominięte:       {stats['skip']}")
    print(f"    🚫 Zablokowane:     {stats['blocked']}")
    print(f"    ❓ Nie istnieją:    {stats['notfound']}")
    print(f"    ⚠️  Rate limit:      {stats['ratelimit']}")
    print(f"    🔒 Brak autoryzacji: {stats['unauthorized']}")
    print(f"    ❌ Inne błędy:      {stats['error']}")
    print(f"    ---")
    print(f"    📁 Już na GitHub:   {len(already_forked)}")
    print("=" * 60)
    
    if failed_repos:
        print(f"\n[*] Nieudane ({len(failed_repos)}):")
        for r in failed_repos[:10]:
            print(f"    - {r}")
    
    # Jeśli utracono autoryzację - zakończ z kodem błędu
    if stats['unauthorized'] > 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] Przerwano (Ctrl+C)")
        sys.exit(0)
