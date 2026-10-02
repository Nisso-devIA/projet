#!/usr/bin/env python3
from pathlib import Path
import json
import urllib.request

token = None
for line in Path("/home/ubuntu/zaeldryk/config/discord.env").read_text().splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")

req = urllib.request.Request(
    "https://discord.com/api/v10/guilds/867426693286461490/channels",
    headers={"Authorization": f"Bot {token}", "User-Agent": "news-bot"},
)
chs = json.load(urllib.request.urlopen(req, timeout=20))
for c in chs:
    n = (c.get("name") or "").lower()
    if "actu" in n or "news" in n or "gaming" in n or "high" in n:
        print(c["id"], repr(c.get("name")))
