#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_disable-prod-admin"
mkdir -p "$B"

for APP in /var/www/miinarecettesclients /var/www/miinarecettesclients-test; do
  cp -a "$APP/src/middleware.ts" "$APP/src/lib/mail.ts" "$APP/src/lib/welcome-email.ts" "$B/" 2>/dev/null || true
  cp /tmp/admin-config.ts "$APP/src/lib/admin-config.ts"
  cp /tmp/middleware.ts "$APP/src/middleware.ts"
  cp /tmp/mail.ts "$APP/src/lib/mail.ts"
  cp /tmp/welcome-email.ts "$APP/src/lib/welcome-email.ts"
done

cp -a /etc/nginx/sites-enabled/miinarecettesclients "$B/nginx-miinarecettesclients.bak"
cp -a /var/www/miinarecettesclients/scripts/cron-admin-password.sh "$B/cron-admin-password.sh.bak"
cp /tmp/cron-admin-password.sh /var/www/miinarecettesclients/scripts/cron-admin-password.sh
chmod +x /var/www/miinarecettesclients/scripts/cron-admin-password.sh

PROD_ENV=/var/www/miinarecettesclients/.env
TEST_ENV=/var/www/miinarecettesclients-test/.env

if grep -q '^ADMIN_ENABLED=' "$PROD_ENV"; then
  sed -i 's/^ADMIN_ENABLED=.*/ADMIN_ENABLED=0/' "$PROD_ENV"
else
  echo 'ADMIN_ENABLED=0' >> "$PROD_ENV"
fi

if grep -q '^CLIENT_PUBLIC_URL=' "$TEST_ENV"; then
  sed -i 's|^CLIENT_PUBLIC_URL=.*|CLIENT_PUBLIC_URL=https://miinarecettesclients.xn--miina-ptisserie-9jb.fr|' "$TEST_ENV"
else
  echo 'CLIENT_PUBLIC_URL=https://miinarecettesclients.xn--miina-ptisserie-9jb.fr' >> "$TEST_ENV"
fi

if grep -q '^ADMIN_CHANGE_PASSWORD_URL=' "$TEST_ENV"; then
  sed -i 's|^ADMIN_CHANGE_PASSWORD_URL=.*|ADMIN_CHANGE_PASSWORD_URL=https://test-prod.xn--miina-ptisserie-9jb.fr/miina-admin/change-password|' "$TEST_ENV"
else
  echo 'ADMIN_CHANGE_PASSWORD_URL=https://test-prod.xn--miina-ptisserie-9jb.fr/miina-admin/change-password' >> "$TEST_ENV"
fi

sudo python3 <<'PY'
from pathlib import Path
p = Path("/etc/nginx/sites-enabled/miinarecettesclients")
text = p.read_text()
old = """    location ^~ /miina-admin/login {
        limit_req zone=adminlogin burst=12 nodelay;
        proxy_pass http://127.0.0.1:3004;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_hide_header X-Powered-By;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location ^~ /api/admin/login {
        limit_req zone=adminlogin burst=12 nodelay;
        proxy_pass http://127.0.0.1:3004;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_hide_header X-Powered-By;
    }

"""
new = """    location ^~ /miina-admin {
        return 404;
    }

    location ^~ /api/admin {
        return 404;
    }

    location ^~ /admin {
        return 404;
    }

"""
if old not in text:
    raise SystemExit("nginx pattern not found")
p.write_text(text.replace(old, new))
PY

sudo nginx -t
sudo systemctl reload nginx

cd /var/www/miinarecettesclients
npm run build
pm2 restart miinarecettesclients

cd /var/www/miinarecettesclients-test
npm run build
pm2 restart miinarecettesclients-test

echo prod_admin_disabled_ok
