#!/usr/bin/env bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_games-prompt-setup"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/discord/games-prompt.py \
  /home/ubuntu/zaeldryk/discord/run-games-prompt.sh \
  /home/ubuntu/zaeldryk/config/games-prompt.env \
  "$B/" 2>/dev/null || true
ls /etc/systemd/system/zaeldryk-games-prompt.* 2>/dev/null && \
  cp -a /etc/systemd/system/zaeldryk-games-prompt.* "$B/" || true

install -m 755 /tmp/games-prompt.py /home/ubuntu/zaeldryk/discord/games-prompt.py
install -m 755 /tmp/run-games-prompt.sh /home/ubuntu/zaeldryk/discord/run-games-prompt.sh
install -m 644 /tmp/games-prompt.env /home/ubuntu/zaeldryk/config/games-prompt.env
sudo install -m 644 /tmp/zaeldryk-games-prompt.service /etc/systemd/system/zaeldryk-games-prompt.service
sudo install -m 644 /tmp/zaeldryk-games-prompt.timer /etc/systemd/system/zaeldryk-games-prompt.timer
sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-games-prompt.timer
/home/ubuntu/zaeldryk/discord/run-games-prompt.sh
systemctl list-timers zaeldryk-games-prompt.timer --no-pager
tail -5 /home/ubuntu/zaeldryk/logs/games-prompt.log
echo "backup=$B"
