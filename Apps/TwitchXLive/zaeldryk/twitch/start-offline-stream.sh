#!/bin/bash
# Wrapper used by twitch-offline.service — keeps stream key out of the unit file
set -euo pipefail
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
STREAM_ENV="${ZAEL_ROOT}/config/stream.env"
MEDIA="${OFFLINE_MEDIA:-/home/ubuntu/thanks.mp4}"

if [[ ! -f "$STREAM_ENV" ]]; then
  echo "Missing $STREAM_ENV" >&2
  exit 1
fi
# shellcheck disable=SC1090
set -a
source "$STREAM_ENV"
set +a

: "${TWITCH_STREAM_KEY:?TWITCH_STREAM_KEY missing}"

exec /usr/bin/ffmpeg -re -stream_loop -1 -i "$MEDIA" \
  -c:v libx264 -preset veryfast -b:v 2500k -maxrate 2500k -bufsize 5000k \
  -pix_fmt yuv420p -g 60 -c:a aac -b:a 128k \
  -f flv "rtmp://live.twitch.tv/app/${TWITCH_STREAM_KEY}"
