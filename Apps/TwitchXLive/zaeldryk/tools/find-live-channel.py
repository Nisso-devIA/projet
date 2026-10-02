#!/usr/bin/env python3
"""Find Discord channel for live announcements."""
import json
import sys
import urllib.request
from pathlib import Path

GUILD_ID = 867426693286461490
env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("no token")

needle = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
keywords = ("live", "direct", "twitch", "stream", "lives")

req = urllib.request.Request(
    f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels",
    headers={"Authorization": f"Bot {token}", "User-Agent": "find-live"},
)
chs = json.load(urllib.request.urlopen(req))
text = [c for c in chs if c.get("type") == 0]
if needle:
    text = [c for c in text if needle in c.get("name", "").lower()]
else:
    scored = []
    for c in text:
        name = c.get("name", "").lower()
        score = sum(1 for k in keywords if k in name)
        if score:
            scored.append((score, c))
    scored.sort(key=lambda x: (-x[0], x[1].get("position", 0)))
    for score, c in scored:
        print(f"match score={score}", c.get("name"), c.get("id"))
    if scored:
        best = scored[0][1]
        print("SUGGESTED_ID", best.get("id"), best.get("name"))
        sys.exit(0)
    text = text

for c in sorted(text, key=lambda x: x.get("position", 0)):
    print(c.get("name"), c.get("id"))
