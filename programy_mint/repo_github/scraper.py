import requests
from bs4 import BeautifulSoup
import re
import time

# Konfiguracja
START_URL = "https://githubawesome.com/tag/github-trending-weekly/"
OUTPUT_FILE = "repo_list1.txt"

def get_html_content(url):
    """Pobiera zawartość HTML strony."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas pobierania {url}: {e}")
        return None

def extract_github_links(text):
    """Wyciąga unikalne linki do repozytoriów GitHub z tekstu."""
    # Szuka wzorca: github.com/wlasciciel/repozytorium
    # Ignoruje linki do issue, pull requests itp., które mają więcej niż 2 slashe po domenie
    pattern = r'https://github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)'
    matches = re.findall(pattern, text)
    
    # Tworzymy pełne linki i usuwamy duplikaty
    valid_links = set()
    for match in matches:
        link = f"https://github.com/{match}"
        valid_links.add(link)
        
    return list(valid_links)

def main():
    print(f"[*] Pobieranie listy wpisów z: {START_URL}")
    html = get_html_content(START_URL)
    
    if not html:
        print("Nie udało się pobrać strony głównej.")
        return

    soup = BeautifulSoup(html, 'html.parser')
    
    # Znajdź linki do poszczególnych postów (wpisów tygodniowych)
    post_links = []
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if "/github-trending-weekly-" in href and "tag" not in href:
            if not href.startswith('http'):
                href = "https://githubawesome.com" + href
            post_links.append(href)

    # Usuń duplikaty postów
    post_links = list(set(post_links))
    print(f"[*] Znaleziono {len(post_links)} wpisów do przeszukania.")

    all_github_repos = set()

    # Iteracja przez każdy post i szukanie linków do GitHub
    for post_url in post_links:
        print(f"[-] Przeszukiwanie wpisu: {post_url}")
        post_html = get_html_content(post_url)
        if post_html:
            links = extract_github_links(post_html)
            for link in links:
                all_github_repos.add(link)
        time.sleep(1)  # Krótka przerwa, by nie blokować serwera

    print(f"\n[*] Znaleziono łącznie {len(all_github_repos)} unikalnych repozytoriów.")

    # Zapis do pliku
    with open(OUTPUT_FILE, 'w') as f:
        for repo in sorted(all_github_repos):
            f.write(repo + '\n')
    
    print(f"[*] Zapisano listę do pliku: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
