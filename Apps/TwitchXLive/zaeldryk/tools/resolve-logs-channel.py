#!/usr/bin/env python3
import json
import os
import urllib.request

env_path = "/home/ubuntu/zaeldryk/config/discord.env"
token = None
with open(env_path, encoding="utf-8") as f:
    for line in f:
        if line.startswith("DISCORD_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")
            break
if not token:
    raise SystemExit("no token")

req = urllib.request.Request(
    "https://discord.com/api/v10/guilds/867426693286461490/channels",
    headers={"Authorization": f"Bot {token}"},
)
with urllib.request.urlopen(req, timeout=20) as resp:
    channels = json.load(resp)

for c in channels:
    name = c.get("name") or ""
    if "logs" in name.lower() or name == "📝-logs":
        print(f"{c['id']}\t{name}")
