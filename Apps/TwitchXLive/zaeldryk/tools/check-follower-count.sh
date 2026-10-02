#!/usr/bin/env bash
set -euo pipefail
# shellcheck disable=SC1091
source /home/ubuntu/zaeldryk/config/twitch.env
source /home/ubuntu/zaeldryk/lib/common.sh 2>/dev/null || true
TOKEN_FILE="${TWITCH_TOKEN_FILE:-/home/ubuntu/zaeldryk/state/twitch_token.txt}"
TOKEN=$(tr -d '\r\n' < "$TOKEN_FILE" 2>/dev/null || true)
if [[ -z "${TOKEN:-}" ]]; then
  echo "no token"
  exit 1
fi
echo "login=$TWITCH_LOGIN id=$TWITCH_BROADCASTER_ID"
curl -s -H "Client-ID: $TWITCH_CLIENT_ID" -H "Authorization: Bearer $TOKEN" \
  "https://api.twitch.tv/helix/channels/followers?broadcaster_id=$TWITCH_BROADCASTER_ID&first=1" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print("api_followers_total", d.get("total")); print("api_message", d.get("message") or d.get("error") or "ok")'
