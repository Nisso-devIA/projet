#!/bin/bash
set -u
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
# shellcheck disable=SC1091
source "$ZAEL_ROOT/lib/common.sh"

LOG="$ZAEL_LOGS/delete-vods.log"
zael_log "$LOG" "Recherche des VODs Offline..."

VIDEOS=$(zael_helix_get "/videos?user_id=$TWITCH_BROADCASTER_ID&first=20&type=archive")
IDS=$(echo "$VIDEOS" | jq -r '.data[]? | select(.title | test("Offline|test|Test de stream"; "i")) | .id')

if [[ -z "$IDS" ]]; then
  zael_log "$LOG" "Aucun VOD Offline trouvé"
  exit 0
fi

for ID in $IDS; do
  zael_log "$LOG" "Suppression du VOD $ID"
  curl -s -X DELETE "https://api.twitch.tv/helix/videos?id=$ID" \
    -H "Client-ID: $TWITCH_CLIENT_ID" \
    -H "Authorization: Bearer $(zael_token)" >>"$LOG"
  echo >>"$LOG"
  sleep 1
done

zael_log "$LOG" "Nettoyage terminé"
