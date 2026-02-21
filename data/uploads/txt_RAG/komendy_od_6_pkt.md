
Zanim przejdziemy do konfiguracji OpenCode, musimy podnieść "podstawę" (Qdrant, Nextcloud, Backend), aby Twój nowy "Dowódca" miał co sterować. 
Krok 1: Szybki start usług "Bazowych" 

Uruchommy niezbędne kontenery (pamięć i chmura). 
bash
 
  
 ```bash

podman start qdrant nextcloud postgres_nextcloud

```
 
 

Sprawdźmy czy wstały: 
```bash
 
  
 
podman ps
 
```
 

Powinieneś zobaczyć te 3 kontenery. 
Krok 2: Restart "Mózgu" (LLM) 

Potrzebujemy też LLM-a na porcie 8081. Zróbmy to w tle: 
```bash
 
  
 
cd ~/KlimtechRAG/llama.cpp
./build/bin/llama-server -m models/LFM2-2.6B-Q5_K_M.gguf --host 0.0.0.0 --port 8081 -c 4096 -ngl 99 &
 
``` 
 
Krok 3: Restart Backend (API) 

Potrzebujemy API na porcie 8000. 
```bash
 
  
 
cd ~/KlimtechRAG/backend_app
python main.py &
 
``` 
 

(Poczekaj chwilę na log Uvicorn running...) 
Krok 4: Stworzenie narzędzia "KlimtechRAG" dla OpenCode 

Teraz stworzymy prosty skrypt, który OpenCode będzie uruchamiał. 

1. Stwórz folder na skrypty użytkownika: 
```bash
 
  
 
mkdir -p ~/bin
 
``` 
 

2. Stwórz plik skryptu klimtech_rag: 
```bash
 
  
 
nano ~/bin/klimtech_rag
 
``` 
 

3. Wklej do niego treść: 
```bash
 
  
 
#!/bin/bash
# Skrypt łączący OpenCode z KlimtechRAG
# Użycie: klimtech_rag "Pytanie użytkownika"

QUERY="$1"

curl -s -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"${QUERY}\"}"
 
 
``` 

4. Nadaj uprawnienia uruchamiania: 
```bash
 
  
 
chmod +x ~/bin/klimtech_rag
mv ~/bin/klimtech_rag ~/.opencode/bin/
``` 
 

5. Dodaj folder ~/bin do PATH (żeby system widział skrypt): 

Edytuj swój plik konfiguracyjny powłoki (np. .config/fish/config.fish jeśli używasz fish, lub .bashrc). 

Jeśli używasz fish (co sugeruje poprzednia sesja):
Wpisz w terminalu: 
```fish
 
  
 
set -Ux PATH ~/bin $PATH
 
``` 
 

(To doda folder do PATH w tej sesji). 
Krok 5: Test działania narzędzia w terminalu 

Zanim odpalimy OpenCode, sprawdźmy czy skrypt działa w "surowym" terminalu. 
bash
 
  
 
klimtech_rag "Testowe pytanie do RAG"
 
 
 

Powinieneś otrzymać odpowiedź JSON z odpowiedzią modelu. Jeśli to działa, możemy iść do OpenCode. 
Krok 6: Konfiguracja OpenCode 

To jest moment, w którym dołączymy ten skrypt do IDE. 

    Uruchom OpenCode. 
    Przejdź do Settings (Ustawienia) lub Preferences. 
    Szukaj sekcji Agents lub Tools (Narzędzia). 
    Dodaj nowe narzędzie (Add Tool / Command):
         Name: klimtech_rag
         Command: klimtech_rag "{{user_input}}"
         (Zależnie od wersji OpenCode może wymagać ścieżki pełnej: /home/lobo/bin/klimtech_rag "{{user_input}}").
         Description: "Zapytaj lokalną bazę wiedzy KlimtechRAG (Nextcloud, GitHub, Web)".
          

Pytanie: Widzisz w OpenCode sekcję do definiowania takich skryptów/agentów? Jak nazywa się ta zakładka? 
   
