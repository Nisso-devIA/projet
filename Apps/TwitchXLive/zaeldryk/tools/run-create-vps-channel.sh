#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_vps-channel"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/config/discord.env "$B/"
python3 /tmp/create-vps-channel.py
echo "BACKUP=$B"
grep DISCORD_ALERT_CHANNEL_ID /home/ubuntu/zaeldryk/config/discord.env
