#!/bin/bash
# Fetch official NCS releases (audio) for youtube-clips.
# Use WITH credit (NCS terms). Not for redistribution as a package.
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
MUSIC=/home/ubuntu/zaeldryk/youtube-clips/music
mkdir -p "$MUSIC"
cd "$MUSIC"
B="/home/ubuntu/backups/$(date +%Y-%m-%d_%H%M)_youtube-clips-music"
mkdir -p "$B"
cp -a manifest.json "$B/" 2>/dev/null || true
echo "BACKUP=$B"

command -v yt-dlp >/dev/null
command -v ffmpeg >/dev/null

# Official NCS YouTube uploads only (url|basename|title|artist|credit)
TRACKS=(
  "https://www.youtube.com/watch?v=K4DyBUG242c|cartoon-on-on|On & On|Cartoon, Daniel Levi|https://ncs.io/onandon"
  "https://www.youtube.com/watch?v=tgIqecROs5A|elektronomia-sky-high|Sky High|Elektronomia|https://ncs.io/SkyHigh"
  "https://www.youtube.com/watch?v=3nQNiWdeH2Q|janji-heroes-tonight|Heroes Tonight|Janji, Johnning|https://ncs.io/HeroesTonight"
  "https://www.youtube.com/watch?v=p7ZsBPK656s|disfigure-blank|Blank|Disfigure|https://ncs.io/blank"
  "https://www.youtube.com/watch?v=QzsXtYD8g9Y|different-heaven-my-heart|My Heart|Different Heaven, EH!DE|https://ncs.io/MyHeart"
)

for row in "${TRACKS[@]}"; do
  IFS='|' read -r url base title artist credit <<<"$row"
  out="${base}.mp3"
  if [[ -f "$out" && $(stat -c%s "$out") -gt 100000 ]]; then
    echo "skip existing $out"
    continue
  fi
  echo "download $title — $artist"
  yt-dlp -x --audio-format mp3 --audio-quality 5 \
    -o "${base}.%(ext)s" \
    --no-playlist \
    "$url"
done

python3 - <<'PY'
import json
from pathlib import Path
music = Path("/home/ubuntu/zaeldryk/youtube-clips/music")
catalog = [
  ("cartoon-on-on.mp3", "On & On", "Cartoon, Daniel Levi", "https://ncs.io/onandon"),
  ("elektronomia-sky-high.mp3", "Sky High", "Elektronomia", "https://ncs.io/SkyHigh"),
  ("janji-heroes-tonight.mp3", "Heroes Tonight", "Janji, Johnning", "https://ncs.io/HeroesTonight"),
  ("disfigure-blank.mp3", "Blank", "Disfigure", "https://ncs.io/blank"),
  ("different-heaven-my-heart.mp3", "My Heart", "Different Heaven, EH!DE", "https://ncs.io/MyHeart"),
]
tracks = []
for fname, title, artist, url in catalog:
  p = music / fname
  if p.is_file() and p.stat().st_size > 100000:
    tracks.append({
      "file": fname,
      "title": title,
      "artist": artist,
      "credit_url": url,
      "license": "NCS",
    })
if not tracks:
  raise SystemExit("no NCS files downloaded")
(music / "manifest.json").write_text(json.dumps(tracks, indent=2) + "\n", encoding="utf-8")
print(f"manifest tracks={len(tracks)}")
for t in tracks:
  print(" -", t["file"], "|", t["title"], "-", t["artist"])
PY
echo DONE
