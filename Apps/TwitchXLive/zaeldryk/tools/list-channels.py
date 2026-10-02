#!/usr/bin/env python3
"""List guild channels (filter optional)."""
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
req = urllib.request.Request(
    f"https://discord.com/api/v10/guilds/{GUILD_ID}/channels",
    headers={"Authorization": f"Bot {token}", "User-Agent": "list-channels"},
)
chs = json.load(urllib.request.urlopen(req))
for c in sorted(chs, key=lambda x: (x.get("parent_id") or "", x.get("position", 0))):
    name = c.get("name", "")
    if needle and needle not in name.lower():
        continue
    cid = c.get("id")
    if cid in ("1541251095492435978", "1541251096763179181", "1541251097962877010"):
        print(c.get("type"), repr(name), len(name), cid, c.get("parent_id"))
    else:
        print(c.get("type"), name, cid, c.get("parent_id"))
