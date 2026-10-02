#!/usr/bin/env python3
import json
import re
import urllib.request
from pathlib import Path

out = Path("/home/ubuntu/zaeldryk/youtube-clips/music")
out.mkdir(parents=True, exist_ok=True)
B = Path("/home/ubuntu/backups")
from datetime import datetime
bdir = B / datetime.utcnow().strftime("%Y-%m-%d_%H%M_youtube-clips-music-ncs")
bdir.mkdir(parents=True, exist_ok=True)
if (out / "manifest.json").exists():
    (bdir / "manifest.json").write_bytes((out / "manifest.json").read_bytes())
print("BACKUP", bdir)

ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

tracks = [
    ("https://ncs.io/onandon", "cartoon-on-on.mp3", "On & On", "Cartoon, Daniel Levi, Jeja", "https://ncs.io/onandon"),
    ("https://ncs.io/SkyHigh", "elektronomia-sky-high.mp3", "Sky High", "Elektronomia", "https://ncs.io/SkyHigh"),
    ("https://ncs.io/skyhigh", "elektronomia-sky-high.mp3", "Sky High", "Elektronomia", "https://ncs.io/SkyHigh"),
    ("https://ncs.io/blank", "disfigure-blank.mp3", "Blank", "Disfigure", "https://ncs.io/blank"),
    ("https://ncs.io/MyHeart", "different-heaven-my-heart.mp3", "My Heart", "Different Heaven, EH!DE", "https://ncs.io/MyHeart"),
    ("https://ncs.io/myheart", "different-heaven-my-heart.mp3", "My Heart", "Different Heaven, EH!DE", "https://ncs.io/MyHeart"),
    ("https://ncs.io/HeroesTonight", "janji-heroes-tonight.mp3", "Heroes Tonight", "Janji, Johnning", "https://ncs.io/HeroesTonight"),
]

# Known UUID from browser (fallback)
known = {
    "cartoon-on-on.mp3": "442dfd89-c291-41b4-b93a-18c0ff73c1dc",
}

ok = []
seen = set()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=ua)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


for page, fname, title, artist, credit in tracks:
    if fname in seen:
        continue
    uuid = known.get(fname)
    if not uuid:
        try:
            html = fetch(page).decode("utf-8", "ignore")
        except Exception as e:
            print("PAGE_FAIL", page, e)
            continue
        m = re.search(r"track/download/([a-f0-9-]{36})", html)
        if not m:
            print("NO_UUID", page)
            continue
        uuid = m.group(1)
    url = f"https://ncs.io/track/download/{uuid}"
    print("GET", title, url)
    try:
        data = fetch(url)
    except Exception as e:
        print("DL_FAIL", title, e)
        continue
    path = out / fname
    path.write_bytes(data)
    print("SIZE", len(data), fname)
    if len(data) > 100000:
        ok.append(
            {
                "file": fname,
                "title": title,
                "artist": artist,
                "credit_url": credit,
                "license": "NCS",
            }
        )
        seen.add(fname)
    else:
        print("TOO_SMALL", fname)

if not ok:
    raise SystemExit("no tracks downloaded")

(out / "manifest.json").write_text(json.dumps(ok, indent=2) + "\n", encoding="utf-8")
print("MANIFEST", len(ok))
for t in ok:
    print(" -", t["file"], t["title"])
