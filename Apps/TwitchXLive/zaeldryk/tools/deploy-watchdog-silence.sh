#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_watchdog-silence"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/lib/common.sh /home/ubuntu/zaeldryk/twitch/reset-offline.sh /home/ubuntu/zaeldryk/tools/service-watchdog.sh "$B/"
install -m 644 /tmp/common.sh /home/ubuntu/zaeldryk/lib/common.sh
install -m 755 /tmp/reset-offline.sh /home/ubuntu/zaeldryk/twitch/reset-offline.sh
install -m 755 /tmp/service-watchdog.sh /home/ubuntu/zaeldryk/tools/service-watchdog.sh
grep -n 'watchdog_silence\|silenced' /home/ubuntu/zaeldryk/lib/common.sh /home/ubuntu/zaeldryk/twitch/reset-offline.sh /home/ubuntu/zaeldryk/tools/service-watchdog.sh
echo "BACKUP=$B"
