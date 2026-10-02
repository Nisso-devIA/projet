#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_fix-twitch-env"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/config/twitch.env "$B/"

python3 <<'PY'
from pathlib import Path
p = Path("/home/ubuntu/zaeldryk/config/twitch.env")
lines = p.read_text(encoding="utf-8").splitlines(True)
out = []
for line in lines:
    if line.startswith("DISCORD_REMINDER_MSG="):
        val = line.split("=", 1)[1].rstrip("\n")
        if not (val.startswith("'") or val.startswith('"')):
            safe = val.replace("'", "'\\''")
            line = f"DISCORD_REMINDER_MSG='{safe}'\n"
    out.append(line)
p.write_text("".join(out), encoding="utf-8")
print("fixed reminder quoting")
PY

# Ensure alert channel id
CHANNEL_ID="1541249740145172581"
if grep -q '^DISCORD_ALERT_CHANNEL_ID=' /home/ubuntu/zaeldryk/config/discord.env; then
  sed -i "s/^DISCORD_ALERT_CHANNEL_ID=.*/DISCORD_ALERT_CHANNEL_ID=${CHANNEL_ID}/" /home/ubuntu/zaeldryk/config/discord.env
else
  printf '\nDISCORD_ALERT_CHANNEL_ID=%s\n' "$CHANNEL_ID" >> /home/ubuntu/zaeldryk/config/discord.env
fi

# Ensure watchdog script is latest
if [[ -f /tmp/service-watchdog.sh ]]; then
  install -m 755 /tmp/service-watchdog.sh /home/ubuntu/zaeldryk/tools/service-watchdog.sh
fi

/home/ubuntu/zaeldryk/tools/service-watchdog.sh

# shellcheck disable=SC1091
source /home/ubuntu/zaeldryk/lib/common.sh
set -a
# shellcheck disable=SC1090
source /home/ubuntu/zaeldryk/config/discord.env
set +a

payload=$(jq -nc --arg c $'✅ Watchdog VPS Zaelrys activé\nSurveillance: `zaeldryk-live`, `zaeldryk-discord`, `twitch-offline` (si mode offline/ending)\nSalon: #📝-logs — check chaque minute' '{content:$c}')
code=$(curl -s -o /tmp/zael-watchdog-discord.out -w "%{http_code}" \
  -X POST "https://discord.com/api/v10/channels/${DISCORD_ALERT_CHANNEL_ID}/messages" \
  -H "Authorization: Bot ${DISCORD_BOT_TOKEN}" \
  -H "User-Agent: DiscordBot (https://zaelrys.local/watchdog, 1.0)" \
  -H "Content-Type: application/json" \
  -d "$payload")
echo "TEST_MSG_HTTP=$code"
head -c 180 /tmp/zael-watchdog-discord.out; echo

systemctl list-timers zaeldryk-watchdog.timer --no-pager || true
echo "STATE=$(cat /home/ubuntu/zaeldryk/state/service-watchdog.json 2>/dev/null || echo none)"
grep DISCORD_ALERT_CHANNEL_ID /home/ubuntu/zaeldryk/config/discord.env
sudo systemctl restart zaeldryk-live
sleep 2
systemctl is-active zaeldryk-live zaeldryk-watchdog.timer
echo "BACKUP=$B"
