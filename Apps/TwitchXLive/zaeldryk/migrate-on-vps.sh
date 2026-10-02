#!/bin/bash
# One-shot migrate: build config from existing home scripts, install layout, switch systemd/cron.
# Does NOT print secrets.
set -euo pipefail

BAK="/home/ubuntu/backups/2026-08-25_1605_pre-refactor"
ROOT="/home/ubuntu/zaeldryk"
HOME_U="/home/ubuntu"

mkdir -p "$ROOT"/{config,lib,twitch,x,discord,state,logs,tools,systemd}

# --- Extract secrets from existing files into config (no echo) ---
OLD_REFRESH="$HOME_U/refresh-token.sh"
OLD_OFFLINE_UNIT="/etc/systemd/system/twitch-offline.service"

CLIENT_ID=$(grep -oP 'CLIENT_ID="\K[^"]+' "$HOME_U/smart-live-announce.sh" | head -1)
CLIENT_SECRET=$(grep -oP 'CLIENT_SECRET="\K[^"]+' "$OLD_REFRESH" | head -1 || true)
REFRESH_TOKEN=$(grep -oP 'REFRESH_TOKEN="\K[^"]+' "$OLD_REFRESH" | head -1 || true)
# stream key from ffmpeg ExecStart
STREAM_KEY=$(sudo grep -oP 'rtmp://live.twitch.tv/app/\K\S+' "$OLD_OFFLINE_UNIT" | head -1 || true)

umask 077
cat > "$ROOT/config/twitch.env" <<EOF
TWITCH_CLIENT_ID=${CLIENT_ID}
TWITCH_CLIENT_SECRET=${CLIENT_SECRET}
TWITCH_REFRESH_TOKEN=${REFRESH_TOKEN}
TWITCH_BROADCASTER_ID=426411773
TWITCH_LOGIN=zaeldryk
TWITCH_TOKEN_FILE=/home/ubuntu/twitch_token.txt
OFFLINE_SERVICE=twitch-offline.service
DISCORD_REMINDER_SECONDS=900
DISCORD_REMINDER_MSG='⚔️ Rejoins la communauté Zaelrys → https://discord.gg/tZt3G2jub57'
EOF
chmod 600 "$ROOT/config/twitch.env"

if [[ -n "${STREAM_KEY:-}" ]]; then
  cat > "$ROOT/config/stream.env" <<EOF
TWITCH_STREAM_KEY=${STREAM_KEY}
EOF
  chmod 600 "$ROOT/config/stream.env"
fi

# Copy bots into categories (keep originals in backup already)
cp -a "$HOME_U/zaeldryk-discord-bot.py" "$ROOT/discord/"
cp -a "$HOME_U/offline-chatbot.py" "$HOME_U/moderation-bot.py" "$ROOT/twitch/"

# One-shot Discord setup scripts
for f in create-counters.py create-departs.py create-passages-cat.py create-ranked.py \
         fix-departs-perms.py fix-ranked-readonly.py fix-stats-staff-only.py order-roles.py; do
  [[ -f "$HOME_U/$f" ]] && cp -a "$HOME_U/$f" "$ROOT/tools/"
done

# Compatibility wrappers (old cron/manual paths keep working)
install_wrapper() {
  local dest="$1" target="$2"
  cat > "$dest" <<EOF
#!/bin/bash
exec $target "\$@"
EOF
  chmod +x "$dest"
}

install_wrapper "$HOME_U/smart-live-announce.sh" "true  # moved to zaeldryk-live.service"
# Better: leave note wrappers that no-op with log
for name in smart-live-announce.sh end-live-message.sh x-live-watchdog.sh offline-watchdog.sh discord-reminder.sh; do
  cat > "$HOME_U/$name" <<EOF
#!/bin/bash
# Deprecated: logic moved to zaeldryk-live.service — safe no-op wrapper
echo "\$(date '+%Y-%m-%d %H:%M:%S') - noop (use zaeldryk-live.service)" >> /home/ubuntu/zaeldryk/logs/deprecated-wrappers.log
exit 0
EOF
  chmod +x "$HOME_U/$name"
done

install_wrapper "$HOME_U/refresh-token.sh" "$ROOT/twitch/refresh-token.sh"
install_wrapper "$HOME_U/delete-offline-vods.sh" "$ROOT/twitch/delete-offline-vods.sh"
install_wrapper "$HOME_U/clear-chat-offline.sh" "$ROOT/twitch/clear-chat-offline.sh"
install_wrapper "$HOME_U/reset-offline.sh" "$ROOT/twitch/reset-offline.sh"
install_wrapper "$HOME_U/x_post_live.py" "$ROOT/x/post_live.py"
# python wrappers need exec python - use shell shim
cat > "$HOME_U/x_post_live.py" <<'EOF'
#!/usr/bin/env python3
import runpy
runpy.run_path("/home/ubuntu/zaeldryk/x/post_live.py", run_name="__main__")
EOF
cat > "$HOME_U/x_delete_live.py" <<'EOF'
#!/usr/bin/env python3
import runpy
runpy.run_path("/home/ubuntu/zaeldryk/x/delete_live.py", run_name="__main__")
EOF
chmod +x "$HOME_U/x_post_live.py" "$HOME_U/x_delete_live.py"

# Seed mode from existing tmp files if any
if [[ -f /tmp/x_live_mode.txt ]]; then
  cp /tmp/x_live_mode.txt "$ROOT/state/mode.txt"
elif [[ -f /tmp/live_mode_end.txt ]]; then
  cp /tmp/live_mode_end.txt "$ROOT/state/mode.txt"
else
  echo "ending" > "$ROOT/state/mode.txt"
fi

# Install systemd units
sudo cp "$ROOT/systemd/"*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable zaeldryk-live.service
sudo systemctl restart zaeldryk-live.service
sudo systemctl restart twitch-offline.service offline-chatbot.service moderation-bot.service zaeldryk-discord.service

# Slim crontab
crontab "$ROOT/crontab.zaeldryk"

echo "Migration done."
echo "Check: systemctl status zaeldryk-live --no-pager"
echo "Logs:  $ROOT/logs/live-orchestrator.log"
