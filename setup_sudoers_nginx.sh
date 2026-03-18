#!/bin/bash
# Skrypt do utworzenia wpisu sudoers dla nginx (KlimtechRAG)
# Uruchom: sudo bash setup_sudoers_nginx.sh

echo 'lobo ALL=(ALL) NOPASSWD: /usr/sbin/nginx, /usr/bin/pkill -9 merecat, /usr/bin/pkill -9 nginx, /bin/cp * /etc/nginx/sites-available/klimtech, /bin/ln -sf /etc/nginx/sites-available/klimtech /etc/nginx/sites-enabled/klimtech, /bin/rm /etc/nginx/sites-enabled/default' > /etc/sudoers.d/klimtech-nginx
chmod 440 /etc/sudoers.d/klimtech-nginx
echo "OK - wpis sudoers utworzony"
