KLIMTECHRAG - INSTALACJA NEXTCLOUD (Wersja poprawna po testach)
==================================================================
Data: 2026-03-19
Status: PRZETESTOWANE I DZIAŁAJĄCE

⚠️ WAŻNE OSTRZEŻENIA PRZED STARTEM:
====================================
1. NIE MAPUJ /var/www/html/data na exFAT! exFAT nie obsługuje chown/chmod.
   BŁĄD: "rsync: chown '/var/www/html/data' failed: Operation not permitted"
   ROZWIĄZANIE: Użyj Named Volume (klimtech_nextcloud_data)

2. NIE MAPUJ /var/www/html na exFAT! Brak plików Nextcloud (version.php missing).
   ROZWIĄZANIE: Nie mapuj - zostaw w kontenerze

3. Jeśli wystąpi błąd "permission denied for table oc_migrations":
   ROZWIĄZANIE: Wyczyść oba wolumeny (postgres + nextcloud_data)


KROK 1: Usuń stare Pody i kontenery
=====================================
podman stop -a
podman rm -fa
podman pod rm -fa

KROK 2: Usuń stare wolumeny (JEŚLI BYŁY PROBLEMY)
==================================================
⚠️ Wykonaj TYLKO jeśli wystąpiły błędy uprawnień PostgreSQL!

podman volume rm klimtech_postgres_data klimtech_nextcloud_data 2>/dev/null

KROK 3: Utwórz świeże wolumeny
===============================
podman volume create klimtech_postgres_data
podman volume create klimtech_nextcloud_data

KROK 4: Utwórz Pod
==================
podman pod create --name klimtech_pod -p 8081:80

KROK 5: Uruchom PostgreSQL
===========================
podman run -d --name postgres_nextcloud --pod klimtech_pod --restart always \
    -e POSTGRES_DB=nextcloud \
    -e POSTGRES_USER=nextcloud \
    -e POSTGRES_PASSWORD=klimtech123 \
    -v klimtech_postgres_data:/var/lib/postgresql/data \
    docker.io/library/postgres:16

KROK 6: Czekaj 5s na start PostgreSQL
======================================
sleep 5

KROK 7: Uruchom Nextcloud (Named Volume, NIE exFAT!)
====================================================
⚠️ KRITYCZNE: Używamy Named Volume, NIE ścieżki na exFAT!

podman run -d --name nextcloud --pod klimtech_pod --restart always \
    -e POSTGRES_HOST="localhost" \
    -e POSTGRES_DB=nextcloud \
    -e POSTGRES_USER=nextcloud \
    -e POSTGRES_PASSWORD=klimtech123 \
    -e NEXTCLOUD_TRUSTED_DOMAINS="192.168.31.70 localhost" \
    -e NEXTCLOUD_ADMIN_USER="admin" \
    -e NEXTCLOUD_ADMIN_PASSWORD="klimtech123" \
    -v klimtech_nextcloud_data:/var/www/html/data \
    docker.io/library/nextcloud:32

KROK 8: Czekaj 45s na instalację Nextcloud
===========================================
echo "Czekam 45s na instalację..." && sleep 45

KROK 9: Sprawdź czy instalacja się powiodła
===========================================
podman logs nextcloud 2>&1 | grep -E "(successfully installed|error)"

# Powinno pokazać: "Nextcloud was successfully installed"

KROK 10: NAPRAWA custom_apps (PRZED instalacją apps)
=====================================================
⚠️ BEZ TEGO KROKU app:install zwróci błąd:
"App directory '/var/www/html/custom_apps' not found!"

podman exec -u root nextcloud mkdir -p /var/www/html/custom_apps
podman exec -u root nextcloud chown www-data:www-data /var/www/html/custom_apps

KROK 11: Instalacja aplikacji AI
=================================
podman exec -u www-data nextcloud php occ app:install integration_openai
podman exec -u www-data nextcloud php occ app:install assistant

KROK 12: Konfiguracja systemowa
================================
podman exec -u www-data nextcloud php occ config:system:set check_data_directory_permissions --value=false --type=boolean
podman exec -u www-data nextcloud php occ config:system:set filelocking.enabled --value=false --type=boolean
podman exec -u www-data nextcloud php occ config:system:set allow_local_remote_servers --value=true --type=boolean
podman exec -u www-data nextcloud php occ config:system:set overwriteprotocol --value="https"
podman exec -u www-data nextcloud php occ config:system:set overwritehost --value="192.168.31.70:8444"

KROK 13: Weryfikacja
====================
# Status kontenerów
podman ps

# Status Nextcloud
podman exec -u www-data nextcloud php occ status

# Test HTTP (powinno zwrócić 302)
curl -s -o /dev/null -w "%{http_code}" http://192.168.31.70:8081


===============================================================================
PODSUMOWANIE BŁĘDÓW I ROZWIĄZAŃ
===============================================================================

BŁĄD 1: exFAT - rsync chown failed
----------------------------------
Objaw:
  rsync: [generator] chown "/var/www/html/data" failed: Operation not permitted (1)
  rsync error: some files/attrs were not transferred

Przyczyna:
  exFAT nie obsługuje uprawnień Unix (chown/chmod)
  Kontener jako www-data (UID 33) nie może zmienić właściciela plików

Rozwiązanie:
  Użyj Named Volume zamiast bind mount na exFAT:
  -v klimtech_nextcloud_data:/var/www/html/data  (DOBRZE)
  -v /media/lobo/.../nextcloud_data:/var/www/html/data  (ŹLE!)


BŁĄD 2: version.php not found
-----------------------------
Objaw:
  Failed to open stream: No such file or directory for version.php

Przyczyna:
  Mapowanie całego /var/www/html na exFAT powoduje pusty katalog
  Entrypoint nie instaluje plików gdy katalog nie jest pusty

Rozwiązanie:
  NIE mapuj /var/www/html - zostaw w kontenerze


BŁĄD 3: custom_apps not found
-----------------------------
Objaw:
  App directory "/var/www/html/custom_apps" not found!

Przyczyna:
  Nextcloud oczekuje katalogu custom_apps który nie istnieje domyślnie

Rozwiązanie:
  Utwórz katalog przed instalacją apps:
  podman exec -u root nextcloud mkdir -p /var/www/html/custom_apps
  podman exec -u root nextcloud chown www-data:www-data /var/www/html/custom_apps


BŁĄD 4: permission denied for table oc_migrations
-------------------------------------------------
Objaw:
  SQLSTATE[42501]: Insufficient privilege: 7 ERROR: permission denied for table oc_migrations

Przyczyna:
  Stary wolumen Nextcloud ma dane z poprzedniej instalacji z innymi uprawnieniami
  Konflikt między starymi danymi a nową instalacją

Rozwiązanie:
  Wyczyść OBA wolumeny przed ponowną instalacją:
  podman volume rm klimtech_postgres_data klimtech_nextcloud_data
  podman volume create klimtech_postgres_data
  podman volume create klimtech_nextcloud_data


===============================================================================
ARCHITEKTURA KOŃCOWA
===============================================================================

Pod 'klimtech_pod' (wspólna sieć localhost, port 8081:80)
├── nextcloud (Apache + PHP)
│   └── Dane: Named Volume 'klimtech_nextcloud_data' → ext4
└── postgres_nextcloud
    └── Dane: Named Volume 'klimtech_postgres_data' → ext4

Wolumeny (zarządzane przez Podman, na ext4):
- klimtech_postgres_data (~500MB)
- klimtech_nextcloud_data (~100MB na start)

Login: admin / klimtech123
URL: http://192.168.31.70:8081


===============================================================================
KONFIGURACJA AI W NEXTCLOUD (PO ZALOGOWANIU)
===============================================================================

1. Zaloguj się: http://192.168.31.70:8081 (admin / klimtech123)
2. Admin → Artificial Intelligence → OpenAI Local → Włącz
3. Konfiguracja:
   - Service URL: http://192.168.31.70:8000
   - API Key: sk-local
   - Model: klimtech-bielik
4. Zapisz i przetestuj w Asystencie

===============================================================================
urrent Issues Identified                                                                              
                                                                                                            
     1. Restart Flag Placement Error: Both PostgreSQL and Nextcloud containers are failing because --       
     restart always is placed AFTER the image name instead of before it                                     
     2. Container Startup Failures: PostgreSQL exits with status 1, Nextcloud with status 127               
     3. Missing qdrant and n8n containers: Script tries to start non-existent containers                    
     4. LLM Server Memory Issues: Models exceeding available GPU memory (not library dependency issue       
     as previously thought)                                                                                 
                                                                                                            
     Fix Plan                                                                                               
                                                                                                            
     Phase 1: Fix Container Startup Issues                                                                  
     1. Fix restart flag placement in start_klimtech_v3.py:                                                 
        - Move --restart always to BEFORE the image name in PostgreSQL command (line 140-141)               
        - Move --restart always to BEFORE the image name in Nextcloud command (line 183-184)                
                                                                                                            
     2. Add qdrant and n8n container creation:                                                              
        - Add podman run commands for qdrant container before trying to start it                            
        - Add podman run commands for n8n container before trying to start it                               
                                                                                                            
     Phase 2: Volume and Pod Management                                                                     
     3. Ensure proper volume setup:                                                                         
        - Confirm klimtech_postgres_data and klimtech_nextcloud_data volumes exist (✅ already done)        
        - Consider volume recreation if migration errors persist                                            
                                                                                                            
     4. Fix pod naming consistency:                                                                         
        - Ensure consistent use of POD_NAME = "klimtech_pod" throughout the script                          
                                                                                                            
     Phase 3: Post-Installation Cleanup                                                                     
     5. Remove hardcoded credentials:                                                                       
        - After successful Nextcloud installation, manually remove lines 178-180 (NEXTCLOUD_ADMIN_USER      
     and NEXTCLOUD_ADMIN_PASSWORD)                                                                          
                                                                                                            
     Phase 4: Address LLM Server Issues                                                                     
     6. Fix memory allocation issues:                                                                       
        - Reduce model size or increase context window for GPU memory constraints                           
        - Or adjust n_gpu_layers parameter to use less GPU memory                                           
                                                                                                            
     Implementation Order                                                                                   
     1. Fix restart flag placement (critical - containers won't start otherwise)                            
     2. Add missing container creation commands                                                             
     3. Test Nextcloud accessibility via browser                                                            
     4. Remove hardcoded admin credentials                                                                  
     5. Address LLM server memory issues separately                                                         
                                                                                                            
     The restart flag fix is the most critical issue as it prevents containers from starting at all.        
     Once that's fixed, Nextcloud should be accessible via browser at https://<IP>:8444.                    
                                                                                                   
