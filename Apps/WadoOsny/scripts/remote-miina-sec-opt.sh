#!/usr/bin/env bash
# Optimisations sécu Miina (VPS) — ne touche pas Wado app code
set -euo pipefail

STAMP="$(date +%Y-%m-%d_%H%M)"
B="/home/ubuntu/backups/${STAMP}_miina-sec-opt"
mkdir -p "$B"
sudo cp -a /etc/nginx "$B/nginx"
sudo cp -a /etc/fail2ban "$B/fail2ban" 2>/dev/null || true
crontab -l > "$B/crontab.txt" 2>/dev/null || true
echo "BACKUP $B"

# 1) Hide nginx version
sudo sed -i 's/^\s*server_tokens.*/	server_tokens off;/' /etc/nginx/nginx.conf
if ! grep -q 'server_tokens off' /etc/nginx/nginx.conf; then
  sudo sed -i '/http {/a\\tserver_tokens off;' /etc/nginx/nginx.conf
fi

# 2) Rate-limit zone for admin login
sudo tee /etc/nginx/conf.d/rate-limit.conf >/dev/null <<'EOF'
limit_req_zone $binary_remote_addr zone=adminlogin:10m rate=8r/m;
limit_conn_zone $binary_remote_addr zone=addr:10m;
EOF

# 3) Rewrite miina vhost: keep certbot SSL, dedupe headers (Next owns app headers),
#    HSTS + uploads headers at nginx, rate-limit admin login
sudo python3 <<'PY'
from pathlib import Path
import re

path = Path("/etc/nginx/sites-available/miina")
text = path.read_text()

# Extract SSL-related lines managed by certbot from the first server block
# Build a clean HTTPS server block + HTTP redirect.

https = r'''# Miina — hardened (certbot SSL preserved)
# Backup before edits under /home/ubuntu/backups/

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name xn--miina-ptisserie-9jb.fr miina-pâtisserie.fr www.xn--miina-ptisserie-9jb.fr;

    client_max_body_size 15m;
    limit_conn addr 40;

    # Transport only (app headers come from Next.js — avoid duplicates)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    ssl_certificate /etc/letsencrypt/live/xn--miina-ptisserie-9jb.fr/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/xn--miina-ptisserie-9jb.fr/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

    location /uploads/ {
        alias /var/www/miina/uploads/;
        expires 7d;
        add_header Cache-Control "public";
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        access_log off;
    }

    location ^~ /yasminamp-admin/login {
        limit_req zone=adminlogin burst=12 nodelay;
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_hide_header X-Powered-By;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_hide_header X-Powered-By;
    }
}

server {
    listen 80;
    listen [::]:80;
    server_name xn--miina-ptisserie-9jb.fr miina-pâtisserie.fr www.xn--miina-ptisserie-9jb.fr;
    return 301 https://$host$request_uri;
}
'''

Path("/tmp/miina.conf.hardened").write_text(https)
print("miina conf prepared")
PY

sudo cp /tmp/miina.conf.hardened /etc/nginx/sites-available/miina
sudo nginx -t
sudo systemctl reload nginx
echo NGINX_OK

# 4) Fail2ban — nginx jails + sshd
sudo tee /etc/fail2ban/jail.d/nginx-hardening.conf >/dev/null <<'EOF'
[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 5
findtime = 10m
bantime = 1h

[nginx-botsearch]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 10
findtime = 10m
bantime = 2h

[nginx-bad-request]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 20
findtime = 10m
bantime = 1h

[sshd]
enabled = true
maxretry = 4
findtime = 10m
bantime = 2h
EOF

sudo systemctl restart fail2ban
sleep 1
sudo fail2ban-client status
echo FAIL2BAN_OK

# 5) Ensure demo checkout off
if grep -q '^ALLOW_DEMO_CHECKOUT=' /var/www/miina/.env 2>/dev/null; then
  sed -i 's/^ALLOW_DEMO_CHECKOUT=.*/ALLOW_DEMO_CHECKOUT=false/' /var/www/miina/.env
else
  echo 'ALLOW_DEMO_CHECKOUT=false' >> /var/www/miina/.env
fi
echo DEMO_OFF

# 6) Unattended upgrades — ensure security origin
sudo tee /etc/apt/apt.conf.d/51miina-auto >/dev/null <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF

echo VERIFY
curl -skI https://xn--miina-ptisserie-9jb.fr/ | head -n 22
curl -skI https://xn--miina-ptisserie-9jb.fr/yasminamp-admin/login | head -n 15
ss -tlnp | grep 3000
sudo ufw status | head -10
sudo fail2ban-client status
pm2 list
