#!/bin/bash
# Fix postgres_nextcloud container - naprawia problem z uprawnieniami

echo "=== Naprawianie postgres_nextcloud ==="

# 1. Usuń stary kontener
sudo podman rm -f postgres_nextcloud 2>/dev/null

# 2. Wyczyść katalog danych
sudo rm -rf /media/lobo/BACKUP/KlimtechRAG/data/nextcloud_db/*
sudo mkdir -p /media/lobo/BACKUP/KlimtechRAG/data/nextcloud_db
sudo chown 70:70 /media/lobo/BACKUP/KlimtechRAG/data/nextcloud_db

# 3. Uruchom postgres
sudo podman run -d \
  --name postgres_nextcloud \
  -e POSTGRES_PASSWORD=klimtech123 \
  -e POSTGRES_USER=admin \
  -e POSTGRES_DB=nextcloud \
  -v /media/lobo/BACKUP/KlimtechRAG/data/nextcloud_db:/var/lib/postgresql/data \
  docker.io/library/postgres:15

echo "=== Sprawdzanie statusu ==="
sleep 3
sudo podman ps | grep postgres
