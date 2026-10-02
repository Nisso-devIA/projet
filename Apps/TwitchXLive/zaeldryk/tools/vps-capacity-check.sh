#!/usr/bin/env bash
# Quick capacity + stutter check for OVH VPS
set +e
echo "===== HOST / LOAD ====="
hostname
uptime
nproc
echo
free -h
echo
df -h / | tail -1
echo
swapon --show
echo

echo "===== TOP CPU ====="
ps aux --sort=-%cpu | head -12
echo
echo "===== TOP MEM ====="
ps aux --sort=-%mem | head -10
echo

echo "===== SERVICES ====="
for u in zaeldryk-live zaeldryk-discord moderation-bot offline-chatbot twitch-offline whatsapp-bot nginx; do
  printf "%-24s %s\n" "$u" "$(systemctl is-active $u 2>/dev/null)"
done
echo
echo "===== TIMERS (next) ====="
systemctl list-timers --no-pager | grep -E "zaeldryk|whatsapp|NEXT" | head -15
echo

echo "===== FFMPEG / STREAM ====="
if pgrep -af "ffmpeg.*thanks" >/dev/null; then
  echo "ffmpeg: RUNNING"
  pgrep -af "ffmpeg.*thanks" | sed -E 's/(live_[A-Za-z0-9_]+).*/live_***REDACTED***/'
  # CPU of ffmpeg
  ps -C ffmpeg -o pid,%cpu,%mem,etime,stat --no-headers 2>/dev/null
  # Dropped frames / speed from recent journal (no secrets)
  journalctl -u twitch-offline --since "10 min ago" --no-pager 2>/dev/null | \
    grep -E "fps=|speed=|drop=|dup=|error|Error|Failed" | tail -15
else
  echo "ffmpeg: DOWN"
fi
echo

echo "===== BOT LOGS (last connect / errors) ====="
echo "-- discord --"
tail -n 5 /home/ubuntu/zaeldryk/logs/discord-bot.log 2>/dev/null
echo "-- moderation --"
tail -n 5 /home/ubuntu/zaeldryk/logs/moderation-bot.log 2>/dev/null
echo "-- offline chatbot --"
tail -n 5 /home/ubuntu/zaeldryk/logs/offline-chatbot.log 2>/dev/null
echo "-- freegames --"
tail -n 3 /home/ubuntu/zaeldryk/logs/freegames-bot.log 2>/dev/null
echo "-- news --"
tail -n 3 /home/ubuntu/zaeldryk/logs/news-bot.log 2>/dev/null
echo "-- watchdog --"
tail -n 5 /home/ubuntu/zaeldryk/logs/service-watchdog.log 2>/dev/null
echo

echo "===== FAILED UNITS ====="
systemctl --failed --no-pager
echo

echo "===== LOAD SNAPSHOT (3s) ====="
# sample CPU idle
vmstat 1 3
echo
echo "===== iowait / steal ====="
# brief mpstat if available
command -v mpstat >/dev/null && mpstat 1 3 || true
echo

echo "===== DONE ====="
