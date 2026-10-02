#!/usr/bin/env python3
import json
import pathlib
import urllib.request

token = None
for line in pathlib.Path("/home/ubuntu/zaeldryk/config/discord.env").read_text().splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")

req = urllib.request.Request(
    f"https://discord.com/api/v10/guilds/867426693286461490/channels",
    headers={"Authorization": f"Bot {token}"},
)
chs = json.load(urllib.request.urlopen(req))
ids = {"1541251095492435978", "1541251096763179181", "1541251097962877010"}
for ch in chs:
    if ch.get("id") not in ids:
        continue
    n = ch["name"]
    print(ch["id"], repr(n), len(n), [hex(ord(c)) for c in n[:8]])
