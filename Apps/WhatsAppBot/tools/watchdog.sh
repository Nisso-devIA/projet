#!/bin/bash
# Vérifie le bot, alerte le propriétaire sur WhatsApp si KO, puis relance si besoin.
set -euo pipefail
ROOT="${WHATSAPP_BOT_ROOT:-/home/ubuntu/whatsapp-bot}"
cd "$ROOT"

HOST="$(hostname -s 2>/dev/null || hostname)"
NOW="$(date -Is)"

code=0
node tools/check-bot.js || code=$?

if [ "$code" -eq 1 ]; then
  echo "$NOW DOWN -> alerte + restart"
  node tools/send-owner-alert.js "🚨 WhatsApp Bot KO sur ${HOST} (${NOW}). Relance automatique en cours…" || true
  echo "{\"downAt\":\"${NOW}\",\"host\":\"${HOST}\"}" > "$ROOT/state/down-event.json"
  sudo systemctl restart whatsapp-bot.service
  sleep 8
  node tools/check-bot.js || true
elif [ "$code" -eq 2 ]; then
  echo "$NOW WARN -> WhatsApp déconnecté"
  ALERT_KIND=warn node tools/send-owner-alert.js "⚠️ WhatsApp Bot déconnecté sur ${HOST} (${NOW}). Le processus tourne mais WhatsApp ne répond pas." || true
fi

exit 0
