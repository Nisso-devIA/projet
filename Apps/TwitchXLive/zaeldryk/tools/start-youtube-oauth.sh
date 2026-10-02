#!/bin/bash
set -euo pipefail
LOG=/home/ubuntu/zaeldryk/logs/youtube-oauth-setup.log
PIDFILE=/home/ubuntu/zaeldryk/state/youtube-oauth.pid
mkdir -p /home/ubuntu/zaeldryk/logs /home/ubuntu/zaeldryk/state

if [[ -f "$PIDFILE" ]]; then
  old=$(cat "$PIDFILE" || true)
  if [[ -n "${old:-}" ]] && kill -0 "$old" 2>/dev/null; then
    kill "$old" || true
    sleep 1
  fi
fi

: > "$LOG"
nohup python3 /home/ubuntu/zaeldryk/tools/youtube-oauth-remote.py \
  --client-secrets /home/ubuntu/zaeldryk/config/twitch-youtube.json \
  --out /home/ubuntu/zaeldryk/config/youtube-oauth.json \
  --port 8090 >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
sleep 2
echo "PID=$(cat "$PIDFILE")"
cat "$LOG"
