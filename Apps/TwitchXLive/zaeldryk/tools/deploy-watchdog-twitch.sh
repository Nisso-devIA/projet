#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_watchdog-twitch"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/tools/service-watchdog.sh "$B/"
install -m 755 /tmp/service-watchdog.sh /home/ubuntu/zaeldryk/tools/service-watchdog.sh

# Quick dry check: Twitch send path works (short ping only if TEST=1)
if [[ "${TEST_PING:-0}" == "1" ]]; then
  # shellcheck disable=SC1091
  source /home/ubuntu/zaeldryk/lib/common.sh
  # shellcheck disable=SC1090
  set -a; source /home/ubuntu/zaeldryk/config/discord.env; set +a
  tw="🧪 Watchdog: alerte Discord + Twitch OK"
  zael_send_chat "$tw" | head -c 200; echo
  payload=$(jq -nc --arg c "$tw" '{content:$c}')
  curl -s -o /tmp/zael-watchdog-discord.out -w "DC=%{http_code}\n" \
    -X POST "https://discord.com/api/v10/channels/${DISCORD_ALERT_CHANNEL_ID}/messages" \
    -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
    -H "User-Agent: DiscordBot (https://zaelrys.local/watchdog, 1.0)" \
    -H "Content-Type: application/json" \
    -d "$payload"
fi

# Normal seed run (no alert if all ok)
/home/ubuntu/zaeldryk/tools/service-watchdog.sh
echo "STATE=$(cat /home/ubuntu/zaeldryk/state/service-watchdog.json)"
echo "BACKUP=$B"
grep -n 'send_twitch' /home/ubuntu/zaeldryk/tools/service-watchdog.sh | head -3
