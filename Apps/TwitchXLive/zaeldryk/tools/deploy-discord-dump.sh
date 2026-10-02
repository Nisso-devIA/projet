#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_discord-dump-setup"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/discord/server-dump.py /home/ubuntu/zaeldryk/discord/run-server-dump.sh "$B/" 2>/dev/null || true
ls /etc/systemd/system/zaeldryk-discord-dump.* 2>/dev/null && cp -a /etc/systemd/system/zaeldryk-discord-dump.* "$B/" || true

install -m 755 /tmp/server-dump.py /home/ubuntu/zaeldryk/discord/server-dump.py
install -m 755 /tmp/run-server-dump.sh /home/ubuntu/zaeldryk/discord/run-server-dump.sh
sudo install -m 644 /tmp/zaeldryk-discord-dump.service /etc/systemd/system/zaeldryk-discord-dump.service
sudo install -m 644 /tmp/zaeldryk-discord-dump.timer /etc/systemd/system/zaeldryk-discord-dump.timer

sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-discord-dump.timer
# First manual run (may take 1-2 min) — stop stray runs first
pkill -f 'zaeldryk/discord/server-dump.py' 2>/dev/null || true
sleep 2
rm -f /home/ubuntu/backups/discord-dumps/.dump.lock
rm -rf /home/ubuntu/backups/discord-dumps/2026-08-25_2036
/home/ubuntu/zaeldryk/discord/run-server-dump.sh
systemctl list-timers zaeldryk-discord-dump.timer --no-pager
ls -lh /home/ubuntu/backups/discord-dumps/*.tar.gz 2>/dev/null | tail -3
tail -5 /home/ubuntu/zaeldryk/logs/discord-dump.log
echo "BACKUP=$B"
