#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_watchdog-no-twitch-chat"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/tools/service-watchdog.sh "$B/"
cp -a /home/ubuntu/zaeldryk/state/service-watchdog.json "$B/" 2>/dev/null || true
install -m 755 /tmp/service-watchdog.sh /home/ubuntu/zaeldryk/tools/service-watchdog.sh
/home/ubuntu/zaeldryk/tools/service-watchdog.sh
echo "STATE=$(cat /home/ubuntu/zaeldryk/state/service-watchdog.json)"
# Confirm no twitch chat send
if grep -q send_twitch /home/ubuntu/zaeldryk/tools/service-watchdog.sh; then
  echo "ERROR: send_twitch still present"
  exit 1
fi
# Confirm Twitch bots monitored
grep -E 'moderation-bot|offline-chatbot' /home/ubuntu/zaeldryk/tools/service-watchdog.sh | head -5
# Notify Discord of updated scope
# shellcheck disable=SC1091
source /home/ubuntu/zaeldryk/lib/common.sh
set -a; source /home/ubuntu/zaeldryk/config/discord.env; set +a
payload=$(jq -nc --arg c $'🔧 Watchdog mis à jour\n• Plus aucun message dans le chat Twitch\n• Surveillance Discord: `zaeldryk-live`, `zaeldryk-discord`, `moderation-bot`, `offline-chatbot`, `twitch-offline` (hors live)' '{content:$c}')
curl -s -o /tmp/zael-watchdog-discord.out -w "DC=%{http_code}\n" \
  -X POST "https://discord.com/api/v10/channels/${DISCORD_ALERT_CHANNEL_ID}/messages" \
  -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
  -H "User-Agent: DiscordBot (https://zaelrys.local/watchdog, 1.0)" \
  -H "Content-Type: application/json" \
  -d "$payload"
echo "BACKUP=$B"
