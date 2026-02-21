# Git i GitHub CLI - Komendy

## Inicjalizacja repozytorium

```bash
git init                          # Inicjuje nowe repozytorium git w obecnym katalogu
git clone <url>                   # Klonuje repozytorium z GitHub
```

## Konfiguracja użytkownika

```bash
git config --global user.email "twoj@email.com"    # Ustawia email
git config --global user.name "Twoje Imie"         # Ustawia nazwę
git config --list                                  # Pokazuje aktualną konfigurację
```

## Dodawanie i commitowanie

```bash
git add .                         # Dodaje wszystkie zmienione pliki do indeksu
git add plik.txt                  # Dodaje konkretny plik
git add *.py                      # Dodaje wszystkie pliki .py
git commit -m "Opis zmian"        # Tworzy commit z opisem
git commit --amend -m "Nowy opis" # Zmienia opis ostatniego commita
```

## Status i podgląd

```bash
git status                        # Pokazuje status plików (zmienione, dodane, nieśledzone)
git ls-files                      # Lista plików w repozytorium
git log --oneline                 # Historia commitów (skrócona)
git diff                          # Pokazuje zmiany w plikach
git diff --staged                 # Pokazuje zmiany w dodanych plikach
```

## Praca z .gitignore

```bash
# Tworzenie .gitignore (w fish):
echo "venv/
llama.cpp/
data/
__pycache__/
*.pyc
logs/
.env
*.log" > .gitignore
```

### Wzorce w .gitignore:

```
folder/              # Ignoruje cały folder
*.pyc                # Ignoruje wszystkie pliki z rozszerzeniem .pyc
*.log                # Ignoruje wszystkie pliki .log
.env                 # Ignoruje konkretny plik
data/*.txt           # Ignoruje pliki .txt w folderze data
!data/wazne.txt     # Wyjątek - NIE ignoruj tego pliku
**/temp/             # Ignoruje folder temp w dowolnym miejscu
```

## Usuwanie plików z repozytorium

```bash
git rm plik.txt                   # Usuwa plik z repo i z dysku
git rm -r folder/                 # Usuwa folder
git rm -r --cached .              # Usuwa WSZYSTKIE pliki z indeksu (zostają na dysku)
git rm --cached plik.txt          # Usuwa plik z indeksu, zostaje na dysku
```

## Remote - zdalne repozytoria

```bash
git remote -v                     # Pokazuje listę zdalnych repozytoriów
git remote add origin <url>       # Dodaje zdalne repo jako "origin"
git remote set-url origin <url>   # Zmienia URL repozytorium
git remote remove origin          # Usuwa zdalne repo
```

## Push i Pull

```bash
git push                          # Wysyła commity do remote
git push -u origin main           # Wysyła i ustawia upstream (pierwszy raz)
git push --force                  # Wymusza push (nadpisuje historię - ostrożnie!)
git pull                          # Pobiera zmiany z remote
git pull origin main              # Pobiera z konkretnego brancha
```

## Branches - gałęzie

```bash
git branch                        # Lista gałęzi lokalnych
git branch nazwa                  # Tworzy nową gałąź
git branch -M main                # Zmienia nazwę obecnej gałęzi na "main"
git checkout nazwa                # Przełącza na gałąź
git checkout -b nowa              # Tworzy i przełącza na nową gałąź
git merge nazwa                   # Scala gałąź z obecną
git branch -d nazwa               # Usuwa gałąź
```

## GitHub CLI (gh)

### Autoryzacja

```bash
gh auth login                     # Logowanie do GitHub
gh auth status                    # Sprawdza status autoryzacji
gh auth logout                    # Wylogowanie
```

### Repozytoria

```bash
gh repo create nazwa              # Tworzy nowe repo na GitHub
gh repo create nazwa --public     # Repo publiczne
gh repo create nazwa --private    # Repo prywatne
gh repo create nazwa --public --source=. --push  # Tworzy i od razu wysyła
gh repo delete nazwa              # Usuwa repo
gh repo list                      # Lista twoich repozytoriów
gh repo view                      # Pokazuje info o repo
gh repo clone nazwa               # Klonuje repo
gh repo edit --visibility private # Zmienia widoczność na prywatną
gh repo edit --visibility public  # Zmienia widoczność na publiczną
```

### Pull Requests

```bash
gh pr create                      # Tworzy nowy PR
gh pr list                        # Lista PR
gh pr view 123                    # Pokazuje PR #123
gh pr merge 123                   # Scala PR #123
gh pr close 123                   # Zamyka PR #123
```

### Issues

```bash
gh issue create                   # Tworzy nowe issue
gh issue list                     # Lista issues
gh issue view 123                 # Pokazuje issue #123
gh issue close 123                # Zamyka issue #123
```

## Przykładowy workflow

### Nowy projekt:

```bash
cd moj_projekt
git init
git config user.email "twoj@email.com"
git config user.name "Twoje Imie"

# Stwórz .gitignore
echo "venv/
__pycache__/
*.pyc
.env" > .gitignore

git add .
git commit -m "Initial commit"
gh auth login
gh repo create moj_projekt --private --source=. --push
```

### Codzienna praca:

```bash
git status                        # Sprawdź co się zmieniło
git add .                         # Dodaj zmiany
git commit -m "Opis zmian"        # Commit
git push                          # Wyślij na GitHub
```

### Naprawienie błędu (dodano za duże pliki):

```bash
# Dodaj foldery do .gitignore
echo "duzy_folder/" >> .gitignore

# Usuń wszystko z indeksu
git rm -r --cached .

# Dodaj ponownie (bez ignorowanych)
git add .

# Zmień ostatni commit
git commit --amend -m "Poprawiony commit"

# Wyślij z nadpisaniem
git push --force
```

## Przydatne opcje

```bash
git log --oneline --graph         # Historia z grafem
git log -5                        # Ostatnie 5 commitów
git show                          # Pokazuje ostatni commit
git blame plik.txt                # Pokazuje kto co zmienił w pliku
git reset HEAD~1                  # Cofa ostatni commit (pliki zostają)
git reset --hard HEAD~1           # Cofa ostatni commit (pliki też!)
git stash                         # Chowa zmiany tymczasowo
git stash pop                     # Przywraca schowane zmiany
```
