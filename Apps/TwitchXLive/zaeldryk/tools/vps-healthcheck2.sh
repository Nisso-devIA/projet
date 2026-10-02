#!/usr/bin/env bash
set +e
echo "===== DISCORD BOT STDOUT / LOG FILES ====="
ls -la /home/ubuntu/zaeldryk/logs/ 2>/dev/null
for f in /home/ubuntu/zaeldryk/logs/*discord* /home/ubuntu/zaeldryk/logs/*bot* /tmp/*discord*; do
  [[ -f "$f" ]] || continue
  echo "--- $f ---"
  tail -n 20 "$f"
done
echo
echo "===== SYSTEMD EXEC STATUS ====="
for u in zaeldryk-discord moderation-bot offline-chatbot whatsapp-bot twitch-offline zaeldryk-live; do
  echo "--- $u ---"
  systemctl show "$u" -p ActiveState -p SubState -p Result -p ExecMainStatus -p NRestarts --no-pager 2>/dev/null
  # recent stderr from MainPID if any
done
echo
echo "===== DISCORD BOT RECENT OUTPUT (std*) ====="
# Check if StandardOutput is journal or file
systemctl cat zaeldryk-discord.service 2>/dev/null | head -40
echo
echo "===== WHATSAPP SERVICE ====="
systemctl cat whatsapp-bot.service 2>/dev/null | head -30
ls -la /home/ubuntu/whatsapp-bot/logs 2>/dev/null | head
tail -n 30 /home/ubuntu/whatsapp-bot/logs/*.log 2>/dev/null | tail -40
echo
echo "===== MODERATION / OFFLINE SERVICE FILES ====="
systemctl cat moderation-bot.service 2>/dev/null | head -25
systemctl cat offline-chatbot.service 2>/dev/null | head -25
echo
echo "===== TEST NEWS SERVICE ONCE ====="
systemctl start zaeldryk-news.service
sleep 3
systemctl status zaeldryk-news.service --no-pager | head -20
tail -n 8 /home/ubuntu/zaeldryk/logs/news-bot.log
echo
echo "===== WATCHDOG LAST RUN RESULT ====="
journalctl -u zaeldryk-watchdog.service -n 5 --no-pager
echo
echo "===== YOUTUBE CLIPS ENV CRLF ====="
file /home/ubuntu/zaeldryk/config/youtube-clips.env 2>/dev/null
od -c /home/ubuntu/zaeldryk/config/youtube-clips.env 2>/dev/null | head -3
echo
echo "===== TWITCH LIVE STATUS (API soft) ====="
# Don't print secrets — just whether stream key process is encoding
pgrep -af "ffmpeg.*thanks.mp4" >/dev/null && echo "offline stream ffmpeg: RUNNING" || echo "offline stream ffmpeg: DOWN"
pgrep -af zaeldryk-discord-bot.py >/dev/null && echo "discord bot process: RUNNING" || echo "discord bot process: DOWN"
pgrep -af moderation-bot.py >/dev/null && echo "moderation process: RUNNING" || echo "moderation process: DOWN"
pgrep -af offline-chatbot.py >/dev/null && echo "offline chatbot process: RUNNING" || echo "offline chatbot process: DOWN"
pgrep -af "whatsapp-bot/src/index.js" >/dev/null && echo "whatsapp process: RUNNING" || echo "whatsapp process: DOWN"
