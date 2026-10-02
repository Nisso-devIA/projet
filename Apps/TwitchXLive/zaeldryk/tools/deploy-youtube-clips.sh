#!/usr/bin/env bash
# Deploy youtube-clips pipeline on the VPS. Run ON the VPS after syncing files.
# Always creates a timestamped backup first.
set -euo pipefail

ZAEL_ROOT="${ZAEL_ROOT:-/home/ubuntu/zaeldryk}"
SRC="${1:-}"
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_youtube-clips"
mkdir -p "$B"

# Backup existing
for p in \
  "$ZAEL_ROOT/twitch/live-orchestrator.sh" \
  "$ZAEL_ROOT/lib/common.sh" \
  "$ZAEL_ROOT/youtube-clips" \
  "$ZAEL_ROOT/config/youtube-clips.env" \
  /etc/systemd/system/zaeldryk-youtube-clips.service \
  /etc/systemd/system/zaeldryk-youtube-clips.timer
do
  if [[ -e "$p" ]]; then
    cp -a "$p" "$B/" 2>/dev/null || sudo cp -a "$p" "$B/" || true
  fi
done
echo "BACKUP=$B"

if [[ -z "$SRC" ]]; then
  # Default: files already under ZAEL_ROOT (git pull / scp into place)
  SRC="$ZAEL_ROOT"
fi

mkdir -p "$ZAEL_ROOT/youtube-clips/music" "$ZAEL_ROOT/youtube-clips/work" \
  "$ZAEL_ROOT/state/youtube-clips-queue" "$ZAEL_ROOT/logs" "$ZAEL_ROOT/config"

# If deploying from a synced tree that includes Apps/TwitchXLive/zaeldryk
if [[ -d "$SRC/youtube-clips" ]]; then
  rsync -a --delete \
    --exclude 'work/' \
    --exclude 'music/*.mp3' \
    --exclude 'music/*.wav' \
    --exclude 'music/manifest.json' \
    "$SRC/youtube-clips/" "$ZAEL_ROOT/youtube-clips/"
fi
if [[ -f "$SRC/config/youtube-clips.env.example" && ! -f "$ZAEL_ROOT/config/youtube-clips.env" ]]; then
  install -m 600 "$SRC/config/youtube-clips.env.example" "$ZAEL_ROOT/config/youtube-clips.env"
fi
if [[ -f "$SRC/twitch/live-orchestrator.sh" ]]; then
  install -m 755 "$SRC/twitch/live-orchestrator.sh" "$ZAEL_ROOT/twitch/live-orchestrator.sh"
fi
if [[ -f "$SRC/lib/common.sh" ]]; then
  install -m 644 "$SRC/lib/common.sh" "$ZAEL_ROOT/lib/common.sh"
fi

chmod +x "$ZAEL_ROOT/youtube-clips/run-youtube-clips.sh" \
  "$ZAEL_ROOT/youtube-clips/queue_worker.py" \
  "$ZAEL_ROOT/youtube-clips/enqueue_job.py" 2>/dev/null || true

# Music manifest example only if missing
if [[ ! -f "$ZAEL_ROOT/youtube-clips/music/manifest.json" \
   && -f "$ZAEL_ROOT/youtube-clips/music/manifest.json.example" ]]; then
  cp "$ZAEL_ROOT/youtube-clips/music/manifest.json.example" \
     "$ZAEL_ROOT/youtube-clips/music/manifest.json"
  echo "NOTE: edit youtube-clips/music/manifest.json and add NCS files"
fi

# Python deps
python3 -m pip install --user -q -r "$ZAEL_ROOT/youtube-clips/requirements.txt" || \
  pip3 install --user -q -r "$ZAEL_ROOT/youtube-clips/requirements.txt"

sudo install -m 644 "$ZAEL_ROOT/systemd/zaeldryk-youtube-clips.service" \
  /etc/systemd/system/zaeldryk-youtube-clips.service
sudo install -m 644 "$ZAEL_ROOT/systemd/zaeldryk-youtube-clips.timer" \
  /etc/systemd/system/zaeldryk-youtube-clips.timer

# Prefer systemd units from SRC if present
if [[ -f "$SRC/systemd/zaeldryk-youtube-clips.service" ]]; then
  sudo install -m 644 "$SRC/systemd/zaeldryk-youtube-clips.service" \
    /etc/systemd/system/zaeldryk-youtube-clips.service
fi
if [[ -f "$SRC/systemd/zaeldryk-youtube-clips.timer" ]]; then
  sudo install -m 644 "$SRC/systemd/zaeldryk-youtube-clips.timer" \
    /etc/systemd/system/zaeldryk-youtube-clips.timer
fi

sudo systemctl daemon-reload
sudo systemctl enable --now zaeldryk-youtube-clips.timer

# Restart live orchestrator if unit exists (picks up hook)
if systemctl list-unit-files | grep -q zaeldryk-live.service; then
  sudo systemctl restart zaeldryk-live.service || true
  systemctl is-active zaeldryk-live.service || true
fi

systemctl list-timers zaeldryk-youtube-clips.timer --no-pager
echo "Deploy OK. Set YOUTUBE_CLIPS_DRY_RUN=1 for first test."
echo "Need: config/youtube-oauth.json + music files + manifest.json"
