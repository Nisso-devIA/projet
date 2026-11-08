#!/bin/bash
# Single live-state daemon: replaces smart-live / end-live / x-live / offline-watchdog spam.
set -uo pipefail

ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
# shellcheck disable=SC1091
source "$ZAEL_ROOT/lib/common.sh"

LOG="$ZAEL_LOGS/live-orchestrator.log"
POLL_INTERVAL="${POLL_INTERVAL:-10}"
COMPAT_X_ID="/home/ubuntu/last_x_post_id.txt"

ensure_x_id_link() {
  # Keep legacy path in sync for old tools
  if [[ -f "$X_POST_ID_FILE" && ! -e "$COMPAT_X_ID" ]]; then
    ln -sfn "$X_POST_ID_FILE" "$COMPAT_X_ID" 2>/dev/null || cp -a "$X_POST_ID_FILE" "$COMPAT_X_ID"
  fi
}

manage_offline_service() {
  local mode="$1"
  # Offline filler stream disabled → never start, stop if still running
  if [[ "${OFFLINE_STREAM_ENABLED}" != "1" ]]; then
    if systemctl is-active --quiet "$OFFLINE_SERVICE"; then
      zael_log "$LOG" "OFFLINE_STREAM_ENABLED=0 → stop $OFFLINE_SERVICE"
      sudo systemctl stop "$OFFLINE_SERVICE" || true
    fi
    return 0
  fi
  if [[ "$mode" == "live" ]]; then
    if systemctl is-active --quiet "$OFFLINE_SERVICE"; then
      zael_log "$LOG" "LIVE → stop $OFFLINE_SERVICE"
      sudo systemctl stop "$OFFLINE_SERVICE" || true
    fi
  elif [[ "$mode" == "offline" ]]; then
    if ! systemctl is-active --quiet "$OFFLINE_SERVICE"; then
      zael_log "$LOG" "OFFLINE → start $OFFLINE_SERVICE"
      sudo systemctl start "$OFFLINE_SERVICE" || true
    fi
  fi
  # mode ending: leave ffmpeg offline stream as-is
}

# Annonce début de live Discord : live.env + discord/live-announce.py (ignore offline/ending).

maybe_discord_live_announce() {
  if [[ "${DISCORD_LIVE_ENABLED}" != "1" ]]; then
    return 0
  fi
  zael_log "$LOG" "Discord live announce → $STREAM_TITLE"
  DISCORD_LIVE_TITLE="$STREAM_TITLE" DISCORD_LIVE_GAME="$STREAM_GAME" \
    /usr/bin/python3 "$DISCORD_LIVE_SCRIPT" >>"$LOG" 2>&1 || \
    zael_log "$LOG" "Discord live announce failed"
}

maybe_discord_live_delete() {
  if [[ "${DISCORD_LIVE_ENABLED}" != "1" ]]; then
    return 0
  fi
  if [[ ! -f "$ZAEL_STATE/last_discord_live_message.json" ]]; then
    return 0
  fi
  zael_log "$LOG" "Discord live announce delete"
  /usr/bin/python3 "$DISCORD_LIVE_DELETE_SCRIPT" >>"$LOG" 2>&1 || \
    zael_log "$LOG" "Discord live announce delete failed"
}

maybe_end_message() {
  zael_log "$LOG" "End-live chat message"
  zael_send_chat "Merci d'avoir regardé ! 🙏 À très bientôt 👋" >>"$LOG" 2>&1 || true
}

# End actions only after the stream is gone for several polls.
# A title with ending/brb/offline is still a live; one empty Helix reply is not.
END_OFFLINE_POLLS="${END_OFFLINE_POLLS:-6}"

update_end_message() {
  local count saw
  if [[ "$STREAM_MODE" == "live" || "$STREAM_MODE" == "ending" ]]; then
    echo 0 > "$ZAEL_STATE/offline_streak.txt"
    echo 1 > "$ZAEL_STATE/saw_live.txt"
    return 0
  fi
  if [[ "$STREAM_MODE" != "offline" ]]; then
    return 0
  fi
  count=$(cat "$ZAEL_STATE/offline_streak.txt" 2>/dev/null || echo 0)
  count=$((count + 1))
  echo "$count" > "$ZAEL_STATE/offline_streak.txt"
  saw=$(cat "$ZAEL_STATE/saw_live.txt" 2>/dev/null || echo 0)
  if [[ "$saw" != "1" ]]; then
    return 0
  fi
  if (( count == END_OFFLINE_POLLS )); then
    maybe_end_message
    maybe_youtube_clips_enqueue
    maybe_x_delete
    maybe_discord_live_delete
    echo 0 > "$ZAEL_STATE/saw_live.txt"
  fi
}

maybe_x_post() {
  local title="$1"
  if [[ "${X_ENABLED}" != "1" ]]; then
    return 0
  fi
  if [[ -f "$X_POST_ID_FILE" ]]; then
    return 0
  fi
  zael_log "$LOG" "X post → $title"
  X_CONFIG_PATH="$X_CONFIG" X_POST_ID_FILE="$X_POST_ID_FILE" \
    /usr/bin/python3 "$X_POST_SCRIPT" "$title" >>"$LOG" 2>&1 || \
    zael_log "$LOG" "X post failed (credits/auth?) — ignored"
  ensure_x_id_link
}

maybe_x_delete() {
  if [[ "${X_ENABLED}" != "1" ]]; then
    rm -f "$X_POST_ID_FILE" "$COMPAT_X_ID"
    return 0
  fi
  if [[ ! -f "$X_POST_ID_FILE" && ! -f "$COMPAT_X_ID" ]]; then
    return 0
  fi
  # Prefer new state file; fall back to legacy
  if [[ ! -f "$X_POST_ID_FILE" && -f "$COMPAT_X_ID" ]]; then
    cp -a "$COMPAT_X_ID" "$X_POST_ID_FILE"
  fi
  zael_log "$LOG" "X delete"
  X_CONFIG_PATH="$X_CONFIG" X_POST_ID_FILE="$X_POST_ID_FILE" \
    /usr/bin/python3 "$X_DELETE_SCRIPT" >>"$LOG" 2>&1 || \
    zael_log "$LOG" "X delete failed — clearing local id"
  rm -f "$X_POST_ID_FILE" "$COMPAT_X_ID"
}

maybe_discord_reminder() {
  local now last
  now=$(date +%s)
  last=$(cat "$ZAEL_STATE/last_discord_reminder.txt" 2>/dev/null || echo 0)
  if (( now - last < DISCORD_REMINDER_SECONDS )); then
    return 0
  fi
  local msg="${DISCORD_REMINDER_MSG:-⚔️ Rejoins la communauté Zaelrys → https://discord.gg/3vH2u7pme5}"
  zael_log "$LOG" "Discord reminder in Twitch chat"
  zael_send_chat "$msg" >>"$LOG" 2>&1 || true
  echo "$now" > "$ZAEL_STATE/last_discord_reminder.txt"
}

# Remember last non-skip live title (ending/offline/test/end ignored).
maybe_youtube_clips_remember_title() {
  if [[ "${YOUTUBE_CLIPS_ENABLED}" != "1" ]]; then
    return 0
  fi
  if [[ "$STREAM_MODE" != "live" ]]; then
    return 0
  fi
  local title_lc
  title_lc=$(echo "$STREAM_TITLE" | tr '[:upper:]' '[:lower:]')
  if echo "$title_lc" | grep -qE "$YOUTUBE_CLIPS_SKIP_TITLE_PATTERN"; then
    return 0
  fi
  printf '%s\n' "$STREAM_TITLE" > "$YOUTUBE_CLIPS_LAST_GOOD_TITLE"
  jq -nc \
    --arg title "$STREAM_TITLE" \
    --arg game "${STREAM_GAME:-}" \
    --arg started "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{title:$title, game:$game, started_at:$started}' \
    > "$YOUTUBE_CLIPS_LAST_GOOD_META" 2>/dev/null || \
    printf '{"title":"%s","game":"%s"}\n' "$STREAM_TITLE" "${STREAM_GAME:-}" \
      > "$YOUTUBE_CLIPS_LAST_GOOD_META"
}

maybe_youtube_clips_enqueue() {
  if [[ "${YOUTUBE_CLIPS_ENABLED}" != "1" ]]; then
    return 0
  fi
  if [[ ! -f "$YOUTUBE_CLIPS_ENQUEUE_SCRIPT" ]]; then
    zael_log "$LOG" "youtube-clips enqueue script missing — skipped"
    return 0
  fi
  zael_log "$LOG" "YouTube clips enqueue (last good title)"
  /usr/bin/python3 "$YOUTUBE_CLIPS_ENQUEUE_SCRIPT" >>"$LOG" 2>&1 || \
    zael_log "$LOG" "YouTube clips enqueue failed"
}

tick() {
  if ! zael_fetch_stream; then
    zael_log "$LOG" "Helix streams illisible — mode inchangé"
    return 1
  fi
  local prev
  prev=$(zael_read_mode)
  manage_offline_service "$STREAM_MODE"

  if [[ "$prev" != "$STREAM_MODE" ]]; then
    zael_log "$LOG" "mode $prev → $STREAM_MODE | title=$STREAM_TITLE"

    if [[ "$STREAM_MODE" == "live" ]]; then
      /usr/bin/python3 "$ZAEL_ROOT/tools/rotate-stream-title.py" >>"$LOG" 2>&1 || \
        zael_log "$LOG" "titre au hasard ignoré"
      maybe_discord_live_announce
      maybe_x_post "$STREAM_TITLE"
    fi

    zael_write_mode "$STREAM_MODE"
  else
    # keep file fresh even if unchanged
    zael_write_mode "$STREAM_MODE"
  fi

  if [[ "$STREAM_MODE" == "live" ]]; then
    maybe_discord_reminder
    maybe_youtube_clips_remember_title
  fi

  update_end_message
}

if [[ "${ZAEL_ORCH_SOURCE_ONLY:-}" == "1" ]]; then
  return 0 2>/dev/null || exit 0
fi

zael_log "$LOG" "Orchestrator started (poll=${POLL_INTERVAL}s)"
while true; do
  if ! tick; then
    zael_log "$LOG" "tick error (token/network?) — retrying"
  fi
  sleep "$POLL_INTERVAL"
done
