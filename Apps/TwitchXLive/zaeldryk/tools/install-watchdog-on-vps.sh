#!/bin/bash
# One-shot finish install for service watchdog
set -euo pipefail
CHANNEL_ID="1541249740145172581"
stamp=$(date +%Y-%m-%d_%H%M)
B="/home/ubuntu/backups/${stamp}_watchdog"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/config/discord.env "$B/"
crontab -l > "$B/crontab.txt" 2>/dev/null || true

install -m 755 /tmp/service-watchdog.sh /home/ubuntu/zaeldryk/tools/service-watchdog.sh
sudo install -m 644 /tmp/zaeldryk-watchdog.service /etc/systemd/system/zaeldryk-watchdog.service
sudo install -m 644 /tmp/zaeldryk-watchdog.timer /etc/systemd/system/zaeldryk-watchdog.timer

if grep -q '^DISCORD_ALERT_CHANNEL_ID=' /home/ubuntu/zaeldryk/config/discord.env; then
  sed -i "s/^DISCORD_ALERT_CHANNEL_ID=.*/DISCORD_ALERT_CHANNEL_ID=${CHANNEL_ID}/" /home/ubuntu/zaeldryk/config/discord.env
else
  printf '\nDISCORD_ALERT_CHANNEL_ID=%s\n' "$CHANNEL_ID" >> /home/ubuntu/zaeldryk/config/discord.env
fi

sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-watchdog.timer

# Seed healthy state (no spam)
/home/ubuntu/zaeldryk/tools/service-watchdog.sh

# Send confirmation ping
# shellcheck disable=SC1091
source /home/ubuntu/zaeldryk/lib/common.sh
# shellcheck disable=SC1090
set -a; source /home/ubuntu/zaeldryk/config/discord.env; set +a
payload=$(jq -nc --arg c $'✅ Watchdog VPS Zaelrys activé\nSurveillance: `zaeldryk-live`, `zaeldryk-discord`, `twitch-offline` (si mode offline/ending)\nSalon: #📝-logs — check chaque minute' '{content:$c}')
code=$(curl -s -o /tmp/zael-watchdog-discord.out -w "%{http_code}" \
  -X POST "https://discord.com/api/v10/channels/${DISCORD_ALERT_CHANNEL_ID}/messages" \
  -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
  -H "User-Agent: DiscordBot (https://zaelrys.local/watchdog, 1.0)" \
  -H "Content-Type: application/json" \
  -d "$payload")
echo "TEST_MSG_HTTP=$code"
head -c 120 /tmp/zael-watchdog-discord.out; echo
systemctl list-timers zaeldryk-watchdog.timer --no-pager
echo "STATE=$(cat /home/ubuntu/zaeldryk/state/service-watchdog.json)"
echo "BACKUP=$B"
