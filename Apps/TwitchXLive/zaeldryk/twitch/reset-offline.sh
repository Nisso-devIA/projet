#!/bin/bash
# Periodic soft-restart of offline ending stream + delayed VOD cleanup.
# No-op when OFFLINE_STREAM_ENABLED!=1 (no fake live → no Twitch emails).
set -u
ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
# shellcheck disable=SC1091
source "$ZAEL_ROOT/lib/common.sh"

LOG="$ZAEL_LOGS/reset-offline.log"
WAIT_AFTER_RESET="${VOD_DELETE_WAIT_SECONDS:-120}"
RETRY_COUNT="${VOD_DELETE_RETRIES:-3}"
RETRY_GAP="${VOD_DELETE_RETRY_GAP:-60}"

if [[ "${OFFLINE_STREAM_ENABLED}" != "1" ]]; then
  zael_log "$LOG" "OFFLINE_STREAM_ENABLED≠1 → skip reset (purge VOD only)"
  "$ZAEL_ROOT/twitch/delete-offline-vods.sh" || true
  exit 0
fi

zael_log "$LOG" "Reset offline en cours..."

if ! zael_fetch_stream; then
  zael_log "$LOG" "Helix illisible → skip reset"
  exit 0
fi
if [[ "$STREAM_MODE" == "live" ]]; then
  zael_log "$LOG" "Vrai LIVE en cours → skip reset"
  exit 0
fi

zael_watchdog_silence_offline "${WATCHDOG_OFFLINE_SILENCE_SECONDS:-180}"
zael_log "$LOG" "Watchdog silence offline ${WATCHDOG_OFFLINE_SILENCE_SECONDS:-180}s"

sudo systemctl restart "$OFFLINE_SERVICE"
if systemctl is-active --quiet "$OFFLINE_SERVICE"; then
  zael_log "$LOG" "Service $OFFLINE_SERVICE redémarré OK (nouveau segment 2h)"
else
  zael_log "$LOG" "Erreur : $OFFLINE_SERVICE non actif"
fi

zael_log "$LOG" "Attente ${WAIT_AFTER_RESET}s avant suppression VOD (Twitch finalize)"
sleep "$WAIT_AFTER_RESET"

attempt=1
while (( attempt <= RETRY_COUNT )); do
  zael_log "$LOG" "Delete VOD après reset (essai $attempt/$RETRY_COUNT)"
  "$ZAEL_ROOT/twitch/delete-offline-vods.sh"
  if (( attempt == RETRY_COUNT )); then
    break
  fi
  zael_log "$LOG" "Pause ${RETRY_GAP}s avant retry (si VOD pas encore listable)"
  sleep "$RETRY_GAP"
  attempt=$((attempt + 1))
done

zael_log "$LOG" "Fin reset — filet : cron delete-offline-vods chaque minute"
