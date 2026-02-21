 # [!NOTE] 1 Nazwa projektu: ["KlimtechRAG"]
 # 2 Projekt :  [Połączenie programów : llama.cpp Haystack, Doclin,LlamaIndex, offline‑friendly baza RAG, n8n, (OpenCode https://opencode.ai/ ), Nexcloud, GitHub, GitLab,Podman - open source container tools, web‑search.]
 # 3 Platforma/Technologia: [Haystack, Docling, LlamaIndex, n8n,OpenCode (https://opencode.ai/), Python3, Ubuntu 24.04.3 LTS, Seagate Dysk Ssd Firecuda 540 1TB PCIe M.2, Procesor AMD Ryzen 9 9950X Tray Socket AM5 | 64MB | 5.7GHz, Płyta główna ATX Gigabyte X870 GAMING X WIFI7, Pamięć RAM DDR5 GOODRAM UDIMM 2x16GB 7200MHz CL34 IRDM ]
 
 ## 4 Cel projektu/koncepcja:
 
 # * Lokalny model językowy llama.cpp wszystkim sterujący działający na localhost.
 # * "RAG jako Serwis" (RAG-as-a-Service) dla IDE. Zamiast tradycyjnego serwera WWW, chodzi o zbudowanie backend-a, który wygląda jak rozszerzenie systemu OpenCode.
 # * n8n wykorzystywany do automatyzacji procesów ;powiadomienia na aplikację Signal, Telegram. Obsługa poczty e-mail. Zintegrowanie z Nexcloud jako prywatną Chmurą niezależną od bazy  RAG ale z możliwością dodawania plików z prywatnej chmury Nexcloud do bazy RAG.
 # * Pobieranie do bazy RAG z konta na GitHub Fork-ów  i repozytoriów oraz synchronizacja z lokalną bazą. 
 # * Przeszukiwanie całej platwormy GitHub, GitLab w celu wyszukiwania kodu dla OpenCode i zapisywania wyszukiwania do bazy RAG
 # * Możliwość przeszukiwania stron WWW (web‑search)
 
 
 ## 5 Najważniejsze założenia i zasady:
 # [Wypunktuj wszystkie twarde reguły. Np.:]
 # * Użytkownik: Wpisuje w terminalu OpenCode: Wytłumacz mi jak skonfigurować X w naszym projekcie lub Znajdź błąd w pliku PDF z dokumentacją.
 # * OpenCode (Agent): Rozpoznaje, że potrzebuje kontekstu z dokumentacji Twojej firmy.
 # * Narzędzie (Tool): Wywołuje lokalny endpoint HTTP (Haystack API).
 # * Haystack: Używa Docling do parsowania, a potem LlamaIndex/Haystack do wyszukania odpowiedzi i generowania.
 # * Wynik: Wraca do terminala OpenCode jako gotowa odpowiedź lub kontekst do wklejenia w kodzie.
 # * Przeszukiwanie stron WWW i zewnętrznych chmur w celu szukania informacji i kodu.
 # * Wszystko dzieje się na localhost
 # * Stworzenie lokalnej bazy GitHub (git clone, pbieranie repozytorium i synchronizacja lokalnego repozytorium z cmurą GitHub)
 
 ## 6 Typowe zadania i workflow:
 # [Jakie zadania będę zlecać ? Np.:]
 > Tworzenie kodu za pomiocą aplikacji OpenCode.
 > Tłumaczenie tekstów np: z języka angielskiego na język polski.
 > Tworzenie baz danych RAG
 > użytkowanie Nexcloud jako prywatnego serwera dla plików wideo, .pdf etc.
 > przeszukiwanie sieci i zewnętrznych serwerów oraz pobieranie, sortowanie pobranych danych z internetu w celu tworzenia własnej bazy RAG.
 > n8n ma wiele zastosowań ale na początku wystarczy aby np: odbierał pocztę, wysyła powiadomienia e-mail lub do aplikacji Signal lub Telegram.
  
 ## 7 Datkowe linki do stron progragramów które będą użyte do projektu:
   > Llama.cpp : (https://github.com/ggml-org/llama.cpp).
   > Haystack :(https://github.com/deepset-ai), (https://github.com/deepset-ai/haystack")
   > Docling : (https://github.com/docling-project), (https://github.com/docling-project/docling)
   > LlamaIndex : (https://github.com/run-llama), (https://github.com/run-llama/LlamaIndexTS)
   > n8n : (https://github.com/n8n-io), (https://github.com/n8n-io/n8n),(https://docs.n8n.io/)
   > OpenCode : (https://opencode.ai/), (https://github.com/anomalyco/opencode), (https://github.com/anomalyco)
   > Nexcloud : (https://nextcloud.com/), (https://docs.nextcloud.com/server/latest/admin_manual/), (https://docs.nextcloud.com/server/latest/user_manual/en/), (https://docs.nextcloud.com/server/latest/developer_manual/)
   > Github :(https://github.com/), (https://docs.github.com/en)
   > GitLab : (https://about.gitlab.com/), (https://docs.gitlab.com/)
   > Podman - open source container tools, web‑search. : (https://podman.io/), (https://blog.podman.io/), (https://podman.io/docs), (https://github.com/containers/), (https://github.com/containers/podman)







[To jest zakończenie sukcesem fazy budowy infrastruktury! 🚀 

Sprawdźmy, co właśnie osiągnąłeś: 

    Nextcloud -> Backend: Plik wrzucony do chmury został przez backend przeczytany, przetworzony przez Doclinga i zapisany w Qdrant. 
    RAG + Web Search: Odpowiedź o dokumencie została wygenerowana na podstawie połączenia lokalnych danych z danymi z sieci (widzimy logi z Wikipedia/Grokipedia). 
    Pełna Automatyzacja: Masz n8n, który potrafi pytać o pogodę, i Nextcloud, który przechowuje wiedzę. 

Status Projektu "KlimtechRAG" 

Wszystkie główne elementy z planu (Punkty 1-5) są zrealizowane i działające offline: 
Element
 	
Status
 	
Technologia
 
 Mózg (LLM)	✅ Działa	Llama.cpp + LFM2-2.6B na AMD RX580 
Baza Wiedzy	✅ Działa	Qdrant (Wektory), Nextcloud (Pliki PDF) 
Inteligentny Parser	✅ Działa	Docling (PDF -> Markdown) 
Web Search	✅ Działa	DuckDuckGo (Hybrydowy RAG) 
Integracja Kodu	✅ Działa	Skrypt Python (GitHub repo) 
Automatyzacja	✅ Działa	n8n (Podłączony do Backendu) 
Interfejs	✅ Działa	Nextcloud (Web) + n8n (Chat) 
 
  
Co dalej? (Pomysły na rozwój) 

Jesteś na bardzo zaawansowanym etapie. Masz prywatną, offline chmurę AI. Oto 3 ścieżki rozwoju, które możesz teraz obrać: 

1. Pełna automatyzacja Nextcloud -> RAG:
Obecnie ręcznie wywołujesz curl, żeby dodać plik z Nextcloud. Możemy napisać skrypt "Watchdog" (Pies warty), który będzie monitorował folder RAG_Dane i od razu wysyłał nowe pliki do backendu. Dzięki temu: wrzucasz PDF do chmury -> minuta później system o nim wie. 

2. Integracja z OpenCode (zgodnie z oryginałem):
Zamiast n8n, możemy skonfigurować Twój terminal OpenCode, żeby używał endpointu http://localhost:8000/query jako domyślnego narzędzia (Tool). Wtedy w terminalu wpisujesz: Opisz mi dokument z Nextcloud, a OpenCode (IDE) dzwoni do Twojego RAG i zwraca wynik w edytorze kodu. 

3. Kolejne repozytoria GitHuba:
Twoj skrypt ingest_repo.py jest gotowy. Możesz teraz wrzucać do niego każde repozytorium (np. dokumentację sprzętu, instrukcje obsługi), które chcesz mieć w głowie. 

Masz już funkcjonalny prototyp systemu, o którym marzą duże firmy. Co chcesz robić dalej? ]