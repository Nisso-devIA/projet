#!/bin/bash
# Daily password-expiry mail check (J-7 / J-2). Admin sur test-prod uniquement.
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd /var/www/miinarecettesclients-test
LINE=$(grep -E '^(CRON_SECRET|ADMIN_SECRET|SITE_SECRET)=' .env | head -1)
SECRET=${LINE#*=}
SECRET=${SECRET//$'\r'/}
SECRET=${SECRET//\"/}
SECRET=${SECRET//\'/}
if [ -z "$SECRET" ]; then
  echo "missing CRON_SECRET/ADMIN_SECRET/SITE_SECRET" >&2
  exit 1
fi
curl -fsS -H "Authorization: Bearer ${SECRET}" \
  "http://127.0.0.1:3005/api/cron/admin-password"
echo
