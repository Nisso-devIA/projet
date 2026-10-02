#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_discord-captcha"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/discord/zaeldryk-discord-bot.py "$B/"
install -m 644 /tmp/zaeldryk-discord-bot.py /home/ubuntu/zaeldryk/discord/zaeldryk-discord-bot.py
python3 -m py_compile /home/ubuntu/zaeldryk/discord/zaeldryk-discord-bot.py
sudo systemctl restart zaeldryk-discord
sleep 3
systemctl is-active zaeldryk-discord
grep -n 'CaptchaModal\|CAPTCHA_MAX' /home/ubuntu/zaeldryk/discord/zaeldryk-discord-bot.py | head -5
echo "BACKUP=$B"
