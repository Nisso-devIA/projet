#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_news-bot"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/config/news.env "$B/" 2>/dev/null || true

install -m 755 /tmp/news-post.py /home/ubuntu/zaeldryk/discord/news-post.py
install -m 755 /tmp/run-news-post.sh /home/ubuntu/zaeldryk/discord/run-news-post.sh
if [[ ! -f /home/ubuntu/zaeldryk/config/news.env ]]; then
  install -m 644 /tmp/news.env /home/ubuntu/zaeldryk/config/news.env
fi
sudo install -m 644 /tmp/zaeldryk-news.service /etc/systemd/system/zaeldryk-news.service
sudo install -m 644 /tmp/zaeldryk-news.timer /etc/systemd/system/zaeldryk-news.timer

sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-news.timer
/home/ubuntu/zaeldryk/discord/run-news-post.sh
systemctl list-timers zaeldryk-news.timer --no-pager
tail -8 /home/ubuntu/zaeldryk/logs/news-bot.log
echo "BACKUP=$B"
