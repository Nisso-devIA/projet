#!/usr/bin/env bash
# Deploy deals-ps channel + watcher (does NOT touch /opt/sentinelle).
set -euo pipefail

ZAEL=/home/ubuntu/zaeldryk
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_deals-ps-fr"
mkdir -p "$B" "$ZAEL/logs" "$ZAEL/state" "$ZAEL/config" "$ZAEL/tools" "$ZAEL/systemd"

cp -a "$ZAEL/tools/create-deals-ps-channel.py" "$B/" 2>/dev/null || true
cp -a "$ZAEL/tools/deals-ps-fr-watch.py" "$B/" 2>/dev/null || true
cp -a "$ZAEL/tools/deals-ps-fr-watch.mjs" "$B/" 2>/dev/null || true
cp -a "$ZAEL/config/deals-ps.env" "$B/" 2>/dev/null || true
cp -a /etc/systemd/system/deals-ps-fr.service "$B/" 2>/dev/null || true
cp -a /etc/systemd/system/deals-ps-fr.timer "$B/" 2>/dev/null || true
systemctl is-active sentinelle > "$B/sentinelle-before.txt" || true
echo "backup $B"

python3 "$ZAEL/tools/create-deals-ps-channel.py"

install -m 644 "$ZAEL/systemd/deals-ps-fr.service" /etc/systemd/system/deals-ps-fr.service
install -m 644 "$ZAEL/systemd/deals-ps-fr.timer" /etc/systemd/system/deals-ps-fr.timer
systemctl daemon-reload
systemctl enable --now deals-ps-fr.timer
# first run now
systemctl start deals-ps-fr.service || true
sleep 2
systemctl is-active sentinelle 2>/dev/null || echo "sentinelle: n/a"
systemctl list-timers deals-ps-fr.timer --no-pager || true
echo "==== log (tail) ===="
tail -n 60 "$ZAEL/logs/deals-ps-fr.log" || true
