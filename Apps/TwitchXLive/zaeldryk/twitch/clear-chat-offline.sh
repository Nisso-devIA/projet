#!/bin/bash
set -u
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
# shellcheck disable=SC1091
source "$ZAEL_ROOT/lib/common.sh"

LOG="$ZAEL_LOGS/clear-chat.log"
if ! zael_fetch_stream; then
  zael_log "$LOG" "Helix illisible → pas de clear"
  exit 0
fi

if [[ "$IS_LIVE" != "0" ]]; then
  zael_log "$LOG" "Live encore en cours → pas de clear"
  exit 0
fi

if [[ "$STREAM_MODE" != "ending" ]]; then
  zael_log "$LOG" "Pas en mode ending → pas de clear"
  exit 0
fi

zael_log "$LOG" "Mode ending → Clear chat"
curl -s -X DELETE \
  "https://api.twitch.tv/helix/moderation/chat?broadcaster_id=$TWITCH_BROADCASTER_ID&moderator_id=$TWITCH_BROADCASTER_ID" \
  -H "Client-ID: $TWITCH_CLIENT_ID" \
  -H "Authorization: Bearer $(zael_token)" >>"$LOG"
echo >>"$LOG"
zael_log "$LOG" "Chat vidé"
