#!/bin/bash
# Refresh Twitch user access token; persist refresh token in twitch.env
set -u
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
# shellcheck disable=SC1091
source "$ZAEL_ROOT/lib/common.sh"

LOG="$ZAEL_LOGS/refresh-token.log"
CONFIG="$ZAEL_CONFIG"

if [[ -z "${TWITCH_CLIENT_SECRET:-}" || -z "${TWITCH_REFRESH_TOKEN:-}" ]]; then
  zael_log "$LOG" "Missing TWITCH_CLIENT_SECRET or TWITCH_REFRESH_TOKEN"
  exit 1
fi

RESPONSE=$(curl -s -X POST https://id.twitch.tv/oauth2/token \
  -d "client_id=$TWITCH_CLIENT_ID" \
  -d "client_secret=$TWITCH_CLIENT_SECRET" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$TWITCH_REFRESH_TOKEN")

NEW_ACCESS=$(echo "$RESPONSE" | jq -r '.access_token // empty')
NEW_REFRESH=$(echo "$RESPONSE" | jq -r '.refresh_token // empty')

if [[ -z "$NEW_ACCESS" ]]; then
  zael_log "$LOG" "Refresh failed: $RESPONSE"
  exit 1
fi

umask 077
echo "$NEW_ACCESS" > "$TWITCH_TOKEN_FILE"
chmod 600 "$TWITCH_TOKEN_FILE"

if [[ -n "$NEW_REFRESH" ]]; then
  tmp=$(mktemp)
  awk -v nr="$NEW_REFRESH" '
    BEGIN { updated=0 }
    /^TWITCH_REFRESH_TOKEN=/ { print "TWITCH_REFRESH_TOKEN=" nr; updated=1; next }
    { print }
    END { if (!updated) print "TWITCH_REFRESH_TOKEN=" nr }
  ' "$CONFIG" > "$tmp"
  mv "$tmp" "$CONFIG"
  chmod 600 "$CONFIG"
fi

zael_log "$LOG" "Token refreshed OK"
