#!/usr/bin/env bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_live-announce"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/twitch/live-orchestrator.sh \
  /home/ubuntu/zaeldryk/lib/common.sh \
  /home/ubuntu/zaeldryk/discord/live-announce.py \
  /home/ubuntu/zaeldryk/discord/live-announce-delete.py \
  /home/ubuntu/zaeldryk/config/live.env 2>/dev/null "$B/" || true

install -m 755 /tmp/live-announce.py /home/ubuntu/zaeldryk/discord/live-announce.py
install -m 755 /tmp/live-announce-delete.py /home/ubuntu/zaeldryk/discord/live-announce-delete.py
install -m 755 /tmp/live-orchestrator.sh /home/ubuntu/zaeldryk/twitch/live-orchestrator.sh
install -m 644 /tmp/common.sh /home/ubuntu/zaeldryk/lib/common.sh
if [[ -f /tmp/live.env ]]; then
  install -m 600 /tmp/live.env /home/ubuntu/zaeldryk/config/live.env
fi

sudo systemctl restart zaeldryk-live.service
systemctl is-active zaeldryk-live.service
echo "backup=$B"
