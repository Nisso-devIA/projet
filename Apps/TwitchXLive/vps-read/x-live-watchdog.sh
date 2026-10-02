#!/bin/bash
# Post on X when real live; delete when title is OFFLINE/ending or stream gone.
# Reuses Twitch token + x_post_live.py / x_delete_live.py already on this VPS.

CLIENT_ID="j2eaj1gxokr77a3lrzso63tr6wvk22"
ACCESS_TOKEN=$(cat /home/ubuntu/twitch_token.txt)
BROADCASTER_ID="426411773"
LOG="/home/ubuntu/x-live-watchdog.log"
MODE_FILE="/tmp/x_live_mode.txt"
POST_ID_FILE="/home/ubuntu/last_x_post_id.txt"

PREV_MODE=$(cat "$MODE_FILE" 2>/dev/null || echo "none")

RESPONSE=$(curl -s -H "Client-ID: $CLIENT_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://api.twitch.tv/helix/streams?user_id=$BROADCASTER_ID")

IS_LIVE=$(echo "$RESPONSE" | jq -r '.data | length')
TITLE=$(echo "$RESPONSE" | jq -r '.data[0].title // ""')
TITLE_LC=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]')

if [ "$IS_LIVE" = "0" ]; then
  CURRENT_MODE="offline"
elif echo "$TITLE_LC" | grep -qE "offline|ending|brb|fin de live|hors ligne"; then
  CURRENT_MODE="ending"
else
  CURRENT_MODE="live"
fi

echo "$CURRENT_MODE" > "$MODE_FILE"

# Real live → post once
if [ "$CURRENT_MODE" = "live" ] && [ ! -f "$POST_ID_FILE" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - LIVE → post X | $TITLE" >> "$LOG"
  /usr/bin/python3 /home/ubuntu/x_post_live.py "$TITLE" >> "$LOG" 2>&1
fi

# Offline / ending (title OFFLINE) → delete post if any
if [ "$CURRENT_MODE" != "live" ] && [ -f "$POST_ID_FILE" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $CURRENT_MODE → delete X | $TITLE" >> "$LOG"
  /usr/bin/python3 /home/ubuntu/x_delete_live.py >> "$LOG" 2>&1
fi

# Quiet heartbeat when nothing changes (optional debug)
if [ "$PREV_MODE" != "$CURRENT_MODE" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') - mode $PREV_MODE → $CURRENT_MODE" >> "$LOG"
fi
