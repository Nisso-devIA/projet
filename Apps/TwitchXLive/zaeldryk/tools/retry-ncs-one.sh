#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
python3 -m pip install -U -q yt-dlp
yt-dlp --version
MUSIC=/home/ubuntu/zaeldryk/youtube-clips/music
cd "$MUSIC"

try_one() {
  local url="$1" base="$2"
  echo "TRY $base"
  yt-dlp -x --audio-format mp3 --audio-quality 5 \
    --extractor-args "youtube:player_client=android" \
    -o "${base}.%(ext)s" \
    --no-playlist \
    "$url"
}

try_one "https://www.youtube.com/watch?v=K4DyBUG242c" "cartoon-on-on" || \
try_one "https://soundcloud.com/nocopyrightsounds/cartoon-on-on-feat-daniel-levi-ncs-release" "cartoon-on-on" || true

ls -lh cartoon-on-on* 2>/dev/null || echo "NO_FILE"
