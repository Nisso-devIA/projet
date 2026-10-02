#!/usr/bin/env bash
set -euo pipefail

STAMP="${1:-2026-08-29_1614}"
B="/home/ubuntu/backups/${STAMP}_cyber-hardening"
mkdir -p "$B"
sudo cp /etc/nginx/sites-available/miina "$B/miina.conf.before-headers" 2>/dev/null || true
sudo cp /tmp/wado-osny.conf /etc/nginx/sites-available/wado-osny

sudo python3 <<'PY'
from pathlib import Path

src = Path("/etc/nginx/sites-available/miina")
text = src.read_text()
marker = "    client_max_body_size 15m;\n"
headers = (
    "    client_max_body_size 15m;\n"
    "\n"
    '    add_header X-Frame-Options "DENY" always;\n'
    '    add_header X-Content-Type-Options "nosniff" always;\n'
    '    add_header Referrer-Policy "strict-origin-when-cross-origin" always;\n'
    '    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;\n'
    '    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;\n'
)
if 'Strict-Transport-Security' in text and 'X-Frame-Options' in text:
    print("Miina headers already present — skip inject")
else:
    if marker not in text:
        raise SystemExit("marker not found in miina conf")
    text = text.replace(marker, headers, 1)
    old_uploads = (
        "    location /uploads/ {\n"
        "        alias /var/www/miina/uploads/;\n"
        "        expires 7d;\n"
        '        add_header Cache-Control "public";\n'
        "        access_log off;\n"
        "    }"
    )
    uploads = (
        "    location /uploads/ {\n"
        "        alias /var/www/miina/uploads/;\n"
        "        expires 7d;\n"
        '        add_header Cache-Control "public";\n'
        '        add_header X-Frame-Options "DENY" always;\n'
        '        add_header X-Content-Type-Options "nosniff" always;\n'
        "        access_log off;\n"
        "    }"
    )
    if old_uploads in text:
        text = text.replace(old_uploads, uploads, 1)
    Path("/tmp/miina.conf.new").write_text(text)
    print("Miina headers prepared")
PY

if [ -f /tmp/miina.conf.new ]; then
  sudo cp /tmp/miina.conf.new /etc/nginx/sites-available/miina
fi

sudo nginx -t
sudo systemctl reload nginx
echo NGINX_OK

sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status verbose
echo UFW_OK

sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y fail2ban
sudo systemctl enable --now fail2ban
sudo systemctl restart fail2ban
sudo fail2ban-client status
sudo fail2ban-client status sshd || true
echo FAIL2BAN_OK

echo "==== VERIFY ===="
ss -tlnp | grep -E ':(22|80|443|3000|3003)\s' || true
curl -sI http://127.0.0.1:3000/ | head -n 3
curl -sI http://127.0.0.1:3003/ | head -n 3
curl -skI https://127.0.0.1/ -H 'Host: xn--miina-ptisserie-9jb.fr' | head -n 15
curl -sI http://127.0.0.1/ -H 'Host: wado-osny.fr' | head -n 15
pm2 list
