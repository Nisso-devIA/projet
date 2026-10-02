#!/bin/bash
set -euo pipefail
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_youtube-clips-fullauto"
mkdir -p "$B"
cp -a /home/ubuntu/zaeldryk/config/youtube-clips.env "$B/"
sed -i 's/^YOUTUBE_CLIPS_DRY_RUN=.*/YOUTUBE_CLIPS_DRY_RUN=0/' /home/ubuntu/zaeldryk/config/youtube-clips.env
grep -E '^(YOUTUBE_CLIPS_ENABLED|YOUTUBE_CLIPS_DRY_RUN|YOUTUBE_CLIPS_SKIP)=' /home/ubuntu/zaeldryk/config/youtube-clips.env
test -f /home/ubuntu/zaeldryk/config/youtube-oauth.json && echo OAUTH_OK
test -f /home/ubuntu/zaeldryk/youtube-clips/music/manifest.json && echo MUSIC_OK
systemctl is-enabled zaeldryk-youtube-clips.timer
echo "BACKUP=$B"
