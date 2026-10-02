#!/bin/bash
set -euo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

STAMP=$(date +%Y-%m-%d_%H%M)
B=/home/ubuntu/backups/${STAMP}_admin-pwd-expiry
mkdir -p "$B"
cp -a /var/www/miinarecettesclients/.env "$B/" 2>/dev/null || true
crontab -l > "$B/crontab.txt" 2>/dev/null || true
echo "BACKUP $B"

python3 <<'PY'
from pathlib import Path
espace = Path("/var/www/miinarecettesclients/.env")
miina = Path("/var/www/miina/.env")
keys = {}
for line in miina.read_text().splitlines():
    if line.startswith((
        "RESEND_API_KEY=",
        "EMAIL_FROM=",
        "EMAIL_REPLY_TO=",
        "ADMIN_ALERT_EMAIL=",
        "ORDER_NOTIFY_EMAIL=",
    )):
        k, _, v = line.partition("=")
        keys[k] = v
text = espace.read_text() if espace.exists() else ""
lines = text.splitlines()
have = {l.split("=", 1)[0] for l in lines if "=" in l and not l.strip().startswith("#")}
out = list(lines)
for k, v in keys.items():
    if k not in have:
        out.append(f"{k}={v}")
        print("ADDED", k)
    else:
        print("KEEP", k)
if "ADMIN_ALERT_EMAIL" not in have and "ADMIN_NOTIFY_EMAIL" not in have:
    out.append("ADMIN_ALERT_EMAIL=")
    print("ADDED ADMIN_ALERT_EMAIL empty")
if "ADMIN_CHANGE_PASSWORD_URL" not in have:
    out.append(
        "ADMIN_CHANGE_PASSWORD_URL=https://miinarecettesclients.xn--miina-ptisserie-9jb.fr/miina-admin/change-password"
    )
    print("ADDED ADMIN_CHANGE_PASSWORD_URL")
espace.write_text("\n".join(out) + "\n")
print("ENV_UPDATED")
PY

chmod +x /var/www/miinarecettesclients/scripts/cron-admin-password.sh
chmod +x /var/www/miinarecettesclients/scripts/notify-admin-password-expiry.mjs 2>/dev/null || true

# Remplace l’ancien cron node .mjs ; aligné racine → 15 8 * * *
CRON_LINE='15 8 * * * /var/www/miinarecettesclients/scripts/cron-admin-password.sh >> /home/ubuntu/backups/admin-pwd-expiry-recettes.log 2>&1'
(
  crontab -l 2>/dev/null \
    | grep -v notify-admin-password-expiry \
    | grep -v cron-admin-password.sh \
    | grep -v 'miinarecettesclients.*admin-password' \
    || true
  echo "$CRON_LINE"
) | crontab -
echo CRON_OK
crontab -l | grep -E 'admin-password|notify-admin' || true

echo DONE
