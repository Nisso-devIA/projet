#!/bin/bash
# Delete Offline/test VODs once they are at least 2 minutes old.
set -u
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
# shellcheck disable=SC1091
source "$ZAEL_ROOT/lib/common.sh"

LOG="$ZAEL_LOGS/delete-vods.log"
MIN_AGE_SECONDS="${VOD_DELETE_MIN_AGE_SECONDS:-120}"   # 2 min after appearance

zael_log "$LOG" "Recherche des VODs Offline (≥ ${MIN_AGE_SECONDS}s)..."

VIDEOS=$(zael_helix_get "/videos?user_id=$TWITCH_BROADCASTER_ID&first=20&type=archive")
NOW_EPOCH=$(date -u +%s)

# Offline / test titles only — never touch real live VODs (clips YouTube).
TO_DELETE=$(echo "$VIDEOS" | jq -r --argjson now "$NOW_EPOCH" --argjson min "$MIN_AGE_SECONDS" '
  .data[]?
  | select(.title | test("Offline|test|Test de stream"; "i"))
  | (.created_at // "") as $c
  | (try ($c | sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601) catch 0) as $ts
  | select($ts > 0 and ($now - $ts) >= $min)
  | "\(.id)\t\(.title)\t\($now - $ts)"
')

if [[ -z "$TO_DELETE" ]]; then
  zael_log "$LOG" "Aucun VOD Offline à supprimer (≥ ${MIN_AGE_SECONDS}s)"
  exit 0
fi

DELETED=0
while IFS=$'\t' read -r ID TITLE AGE; do
  [[ -z "$ID" ]] && continue
  zael_log "$LOG" "Suppression du VOD $ID (âge ${AGE}s) — $TITLE"
  curl -s -X DELETE "https://api.twitch.tv/helix/videos?id=$ID" \
    -H "Client-ID: $TWITCH_CLIENT_ID" \
    -H "Authorization: Bearer $(zael_token)" >>"$LOG"
  echo >>"$LOG"
  DELETED=$((DELETED + 1))
  sleep 1
done <<< "$TO_DELETE"

zael_log "$LOG" "Nettoyage terminé ($DELETED)"
