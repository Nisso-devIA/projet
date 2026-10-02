#!/usr/bin/env python3
"""Download additional NCS tracks and merge into music/manifest.json."""
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

out = Path("/home/ubuntu/zaeldryk/youtube-clips/music")
out.mkdir(parents=True, exist_ok=True)
bdir = Path("/home/ubuntu/backups") / datetime.utcnow().strftime(
    "%Y-%m-%d_%H%M_youtube-clips-music-ncs-more"
)
bdir.mkdir(parents=True, exist_ok=True)
manifest_path = out / "manifest.json"
if manifest_path.exists():
    (bdir / "manifest.json").write_bytes(manifest_path.read_bytes())
print("BACKUP", bdir)

ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# At least 6 new popular NCS releases (page URL, file, title, artist, credit)
NEW = [
    ("https://ncs.io/invincible", "deaf-kev-invincible.mp3", "Invincible", "DEAF KEV", "https://ncs.io/invincible"),
    ("https://ncs.io/INVINCIBLE", "deaf-kev-invincible.mp3", "Invincible", "DEAF KEV", "https://ncs.io/invincible"),
    ("https://ncs.io/Fearless", "lost-sky-fearless.mp3", "Fearless", "Lost Sky", "https://ncs.io/Fearless"),
    ("https://ncs.io/Spectre", "alan-walker-spectre.mp3", "Spectre", "Alan Walker", "https://ncs.io/Spectre"),
    ("https://ncs.io/WhyDoI", "unknown-brain-why-do-i.mp3", "Why Do I", "Unknown Brain, Bri Tolani", "https://ncs.io/WhyDoI"),
    ("https://ncs.io/Mortals", "warriyo-mortals.mp3", "Mortals", "Warriyo, Laura Brehm", "https://ncs.io/Mortals"),
    ("https://ncs.io/Cradles", "sub-urban-cradles.mp3", "Cradles", "Sub Urban", "https://ncs.io/Cradles"),
    ("https://ncs.io/Shine", "spektrem-shine.mp3", "Shine", "Spektrem", "https://ncs.io/Shine"),
    ("https://ncs.io/Superhero", "unknown-brain-superhero.mp3", "Superhero", "Unknown Brain, Chris Linton", "https://ncs.io/Superhero"),
    ("https://ncs.io/LightItUp", "robin-hustin-light-it-up.mp3", "Light It Up", "Robin Hustin, TobiMorrow, Jex", "https://ncs.io/LightItUp"),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=ua)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


existing = []
if manifest_path.exists():
    existing = json.loads(manifest_path.read_text(encoding="utf-8"))
by_file = {t["file"]: t for t in existing if isinstance(t, dict) and t.get("file")}

added = 0
seen_try = set()
for page, fname, title, artist, credit in NEW:
    if fname in seen_try:
        continue
    seen_try.add(fname)
    path = out / fname
    if path.is_file() and path.stat().st_size > 100000 and fname in by_file:
        print("SKIP", fname)
        continue
    uuid = None
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
    if len(data) < 100000:
        print("TOO_SMALL", fname, len(data))
        continue
    path.write_bytes(data)
    by_file[fname] = {
        "file": fname,
        "title": title,
        "artist": artist,
        "credit_url": credit,
        "license": "NCS",
    }
    added += 1
    print("OK", fname, len(data))

merged = list(by_file.values())
# Prefer NCS only (drop placeholder beds if any remain)
merged = [t for t in merged if t.get("license") == "NCS" or not str(t.get("file", "")).startswith("ncs-bed-")]
manifest_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
print("ADDED", added)
print("TOTAL", len(merged))
for t in merged:
    print(" -", t["file"], "|", t["title"])
if added < 6:
    raise SystemExit(f"only added {added}, need at least 6")
