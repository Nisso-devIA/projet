#!/bin/bash
# Shared helpers for ZAELDRYK Twitch automation
# shellcheck disable=SC2034

ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
ZAEL_CONFIG="${ZAEL_CONFIG:-$ZAEL_ROOT/config/twitch.env}"
ZAEL_LIVE_CONFIG="${ZAEL_LIVE_CONFIG:-$ZAEL_ROOT/config/live.env}"
ZAEL_STATE="${ZAEL_STATE:-$ZAEL_ROOT/state}"
ZAEL_LOGS="${ZAEL_LOGS:-$ZAEL_ROOT/logs}"

mkdir -p "$ZAEL_STATE" "$ZAEL_LOGS"

if [[ -f "$ZAEL_CONFIG" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ZAEL_CONFIG"
  set +a
fi

if [[ -f "$ZAEL_LIVE_CONFIG" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ZAEL_LIVE_CONFIG"
  set +a
fi

: "${TWITCH_CLIENT_ID:?TWITCH_CLIENT_ID missing in twitch.env}"
: "${TWITCH_BROADCASTER_ID:=426411773}"
: "${TWITCH_LOGIN:=zaeldryk}"
: "${TWITCH_TOKEN_FILE:=/home/ubuntu/twitch_token.txt}"
: "${OFFLINE_SERVICE:=twitch-offline.service}"
# 0 = pas de faux live offline (évite mails Twitch « est live » à chaque reset)
: "${OFFLINE_STREAM_ENABLED:=0}"
: "${OFFLINE_PATTERN:=offline|ending|brb|fin de live|hors ligne}"
: "${DISCORD_REMINDER_SECONDS:=900}"
: "${X_ENABLED:=0}"
: "${X_POST_SCRIPT:=$ZAEL_ROOT/x/post_live.py}"
: "${X_DELETE_SCRIPT:=$ZAEL_ROOT/x/delete_live.py}"
: "${X_POST_ID_FILE:=$ZAEL_STATE/last_x_post_id.txt}"
: "${X_CONFIG:=/home/ubuntu/x_config.env}"
: "${DISCORD_LIVE_ENABLED:=0}"
: "${DISCORD_LIVE_SCRIPT:=$ZAEL_ROOT/discord/live-announce.py}"
: "${DISCORD_LIVE_DELETE_SCRIPT:=$ZAEL_ROOT/discord/live-announce-delete.py}"
: "${WATCHDOG_OFFLINE_SILENCE_FILE:=$ZAEL_STATE/watchdog-silence-offline.txt}"
: "${WATCHDOG_ALERT_GRACE_SECONDS:=30}"
: "${YOUTUBE_CLIPS_ENABLED:=1}"
: "${YOUTUBE_CLIPS_SKIP_TITLE_PATTERN:=ending|offline|test|\\bend\\b}"
: "${YOUTUBE_CLIPS_ENQUEUE_SCRIPT:=$ZAEL_ROOT/youtube-clips/enqueue_job.py}"
: "${YOUTUBE_CLIPS_LAST_GOOD_TITLE:=$ZAEL_STATE/last_good_live_title.txt}"
: "${YOUTUBE_CLIPS_LAST_GOOD_META:=$ZAEL_STATE/last_good_live_meta.json}"

# Load youtube-clips.env if present
if [[ -f "$ZAEL_ROOT/config/youtube-clips.env" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ZAEL_ROOT/config/youtube-clips.env"
  set +a
fi

zael_log() {
  local file="$1"; shift
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$file"
}

# Suppress twitch-offline DOWN alerts during planned restarts (reset-offline cron).
zael_watchdog_silence_offline() {
  local seconds="${1:-180}"
  echo $(($(date +%s) + seconds)) > "$WATCHDOG_OFFLINE_SILENCE_FILE"
}

zael_watchdog_offline_silenced() {
  [[ -f "$WATCHDOG_OFFLINE_SILENCE_FILE" ]] && (( $(date +%s) < $(cat "$WATCHDOG_OFFLINE_SILENCE_FILE") ))
}

zael_token() {
  cat "$TWITCH_TOKEN_FILE"
}

zael_helix_get() {
  local path="$1"
  curl -s \
    -H "Client-ID: $TWITCH_CLIENT_ID" \
    -H "Authorization: Bearer $(zael_token)" \
    "https://api.twitch.tv/helix${path}"
}

zael_send_chat() {
  local message="$1"
  # JSON-escape via jq
  local payload
  payload=$(jq -nc \
    --arg b "$TWITCH_BROADCASTER_ID" \
    --arg m "$message" \
    '{broadcaster_id:$b, sender_id:$b, message:$m}')
  curl -s -X POST "https://api.twitch.tv/helix/chat/messages" \
    -H "Client-ID: $TWITCH_CLIENT_ID" \
    -H "Authorization: Bearer $(zael_token)" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

# Sets globals: STREAM_JSON IS_LIVE STREAM_TITLE STREAM_GAME STREAM_MODE
zael_fetch_stream() {
  STREAM_JSON=$(zael_helix_get "/streams?user_id=$TWITCH_BROADCASTER_ID")
  IS_LIVE=$(echo "$STREAM_JSON" | jq -r '.data | length')
  STREAM_TITLE=$(echo "$STREAM_JSON" | jq -r '.data[0].title // ""')
  STREAM_GAME=$(echo "$STREAM_JSON" | jq -r '.data[0].game_name // "Jeu non spécifié"')
  local title_lc
  title_lc=$(echo "$STREAM_TITLE" | tr '[:upper:]' '[:lower:]')

  if [[ "$IS_LIVE" == "0" ]]; then
    STREAM_MODE="offline"
  elif echo "$title_lc" | grep -qE "$OFFLINE_PATTERN"; then
    STREAM_MODE="ending"
  else
    STREAM_MODE="live"
  fi
}

zael_read_mode() {
  cat "$ZAEL_STATE/mode.txt" 2>/dev/null || echo "none"
}

zael_write_mode() {
  echo "$1" > "$ZAEL_STATE/mode.txt"
}
