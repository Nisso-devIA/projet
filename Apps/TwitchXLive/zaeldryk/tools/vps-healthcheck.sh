#!/usr/bin/env bash
# Health check all Zaeldryk / related bots on VPS
set +e
echo "===== HOST ====="
hostname
uptime
free -h | head -2
df -h / | tail -1
echo

echo "===== SERVICES ====="
UNITS=(
  zaeldryk-live
  zaeldryk-discord
  zaeldryk-watchdog
  moderation-bot
  offline-chatbot
  twitch-offline
  whatsapp-bot
  zaeldryk-youtube-clips
  nginx
)
for u in "${UNITS[@]}"; do
  st=$(systemctl is-active "$u" 2>/dev/null || echo missing)
  en=$(systemctl is-enabled "$u" 2>/dev/null || echo n/a)
  printf "%-28s %-12s %s\n" "$u" "$st" "$en"
done
echo

echo "===== TIMERS ====="
systemctl list-timers --all --no-pager 2>/dev/null | grep -E "zaeldryk|freegames|news|games|watchdog|youtube|dump|schedule|NEXT" || true
echo
echo "Timer unit files:"
ls /etc/systemd/system/zaeldryk-*.timer /etc/systemd/system/zaeldryk-*.service 2>/dev/null
echo

echo "===== FAILED ====="
systemctl --failed --no-pager 2>/dev/null
echo

echo "===== PROCESSES (bots) ====="
ps aux | grep -E "zaeldryk-discord-bot|discord-bot|free-games|news-post|whatsapp|offline|moderation|live-orchestrator|ffmpeg|youtube" | grep -v grep | head -50
echo

echo "===== DISCORD BOT JOURNAL ====="
journalctl -u zaeldryk-discord -n 30 --no-pager 2>/dev/null
echo

echo "===== LIVE ORCHESTRATOR JOURNAL ====="
journalctl -u zaeldryk-live -n 20 --no-pager 2>/dev/null
echo

echo "===== TWITCH OFFLINE JOURNAL ====="
journalctl -u twitch-offline -n 15 --no-pager 2>/dev/null
echo

echo "===== MODERATION JOURNAL ====="
journalctl -u moderation-bot -n 15 --no-pager 2>/dev/null
echo

echo "===== OFFLINE CHATBOT JOURNAL ====="
journalctl -u offline-chatbot -n 15 --no-pager 2>/dev/null
echo

echo "===== WHATSAPP JOURNAL ====="
journalctl -u whatsapp-bot -n 20 --no-pager 2>/dev/null
echo

echo "===== FREEGAMES LAST LOG ====="
tail -n 25 /home/ubuntu/zaeldryk/logs/freegames-bot.log 2>/dev/null || echo "(no freegames log)"
echo

echo "===== NEWS LAST LOG ====="
tail -n 25 /home/ubuntu/zaeldryk/logs/news-bot.log 2>/dev/null || echo "(no news log)"
echo

echo "===== WATCHDOG / YOUTUBE ====="
systemctl status zaeldryk-watchdog.timer zaeldryk-watchdog.service --no-pager 2>/dev/null | head -40
systemctl status zaeldryk-youtube-clips --no-pager 2>/dev/null | head -25
echo

echo "===== CONFIG PRESENT? ====="
for f in discord.env twitch.env freegames.env news.env; do
  p="/home/ubuntu/zaeldryk/config/$f"
  if [[ -f "$p" ]]; then
    sz=$(wc -c < "$p")
    echo "OK  $f ($sz bytes)"
  else
    echo "MISSING $f"
  fi
done
[[ -f /home/ubuntu/twitch_token.txt ]] && echo "OK  twitch_token.txt" || echo "MISSING twitch_token.txt"
echo

echo "===== QUICK FUNCTIONAL: Discord gateway ping via bot process ====="
# If discord bot is running and recently logged Ready / Live polls
journalctl -u zaeldryk-discord --since "2 hours ago" --no-pager 2>/dev/null | grep -Ei "ready|logged in|live poll|error|traceback|exception|invalid.?token|401|403" | tail -30
echo

echo "===== CRON ====="
crontab -l 2>/dev/null || echo "(no user crontab)"
echo

echo "===== DONE ====="
