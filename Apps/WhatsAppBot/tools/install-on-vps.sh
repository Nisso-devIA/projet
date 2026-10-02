#!/bin/bash
# Install / update WhatsApp bot systemd units on the VPS.
set -euo pipefail

ROOT="/home/ubuntu/whatsapp-bot"
STAMP="$(date +%Y-%m-%d_%H%M)"
B="/home/ubuntu/backups/${STAMP}_whatsapp-bot"
mkdir -p "$B"
crontab -l > "$B/crontab.txt" 2>/dev/null || true
if [ -d "$ROOT" ]; then
  cp -a "$ROOT" "$B/whatsapp-bot" 2>/dev/null || true
fi
sudo cp -a /etc/systemd/system/whatsapp-bot.service "$B/" 2>/dev/null || true
sudo cp -a /etc/systemd/system/whatsapp-bot-watchdog.service "$B/" 2>/dev/null || true
sudo cp -a /etc/systemd/system/whatsapp-bot-watchdog.timer "$B/" 2>/dev/null || true
echo "BACKUP=$B"

mkdir -p "$ROOT/logs" "$ROOT/state" "$ROOT/tmp"
chmod +x "$ROOT/tools/watchdog.sh"

NODE_BIN="$(command -v node || true)"
if [ -z "$NODE_BIN" ]; then
  echo "Node.js introuvable" >&2
  exit 1
fi
sed -i "s|^ExecStart=.*|ExecStart=${NODE_BIN} ${ROOT}/src/index.js|" "$ROOT/systemd/whatsapp-bot.service"

sudo install -m 644 "$ROOT/systemd/whatsapp-bot.service" /etc/systemd/system/whatsapp-bot.service
sudo install -m 644 "$ROOT/systemd/whatsapp-bot-watchdog.service" /etc/systemd/system/whatsapp-bot-watchdog.service
sudo install -m 644 "$ROOT/systemd/whatsapp-bot-watchdog.timer" /etc/systemd/system/whatsapp-bot-watchdog.timer

sudo systemctl daemon-reload
sudo systemctl enable --now whatsapp-bot.service
sudo systemctl enable --now whatsapp-bot-watchdog.timer

sleep 3
sudo systemctl --no-pager --full status whatsapp-bot.service || true
sudo systemctl list-timers whatsapp-bot-watchdog.timer --no-pager || true
node "$ROOT/tools/check-bot.js" || true
echo "INSTALL_OK"
