#!/usr/bin/env bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_schedule-sync"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/discord/schedule-sync.py \
  /home/ubuntu/zaeldryk/discord/run-schedule-sync.sh \
  /home/ubuntu/zaeldryk/config/schedule.env 2>/dev/null "$B/" || true

install -m 755 /tmp/schedule-sync.py /home/ubuntu/zaeldryk/discord/schedule-sync.py
install -m 755 /tmp/run-schedule-sync.sh /home/ubuntu/zaeldryk/discord/run-schedule-sync.sh
if [[ -f /tmp/schedule.env ]]; then
  install -m 600 /tmp/schedule.env /home/ubuntu/zaeldryk/config/schedule.env
fi
sudo install -m 644 /tmp/zaeldryk-schedule-sync.service /etc/systemd/system/zaeldryk-schedule-sync.service
sudo install -m 644 /tmp/zaeldryk-schedule-sync.timer /etc/systemd/system/zaeldryk-schedule-sync.timer
sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-schedule-sync.timer
/home/ubuntu/zaeldryk/discord/run-schedule-sync.sh || true
systemctl list-timers zaeldryk-schedule-sync.timer --no-pager
echo "backup=$B"
