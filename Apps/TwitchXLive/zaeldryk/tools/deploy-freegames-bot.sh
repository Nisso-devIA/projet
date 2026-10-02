#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_freegames-bot"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/config/freegames.env "$B/" 2>/dev/null || true

install -m 755 /tmp/free-games-post.py /home/ubuntu/zaeldryk/discord/free-games-post.py
install -m 755 /tmp/run-free-games-post.sh /home/ubuntu/zaeldryk/discord/run-free-games-post.sh
python3 /tmp/create-free-games-channel.py
sudo install -m 644 /tmp/zaeldryk-freegames.service /etc/systemd/system/zaeldryk-freegames.service
sudo install -m 644 /tmp/zaeldryk-freegames.timer /etc/systemd/system/zaeldryk-freegames.timer
sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-freegames.timer
/home/ubuntu/zaeldryk/discord/run-free-games-post.sh
systemctl list-timers zaeldryk-freegames.timer --no-pager
tail -10 /home/ubuntu/zaeldryk/logs/freegames-bot.log
grep FREEGAMES_CHANNEL /home/ubuntu/zaeldryk/config/freegames.env
echo "BACKUP=$B"
