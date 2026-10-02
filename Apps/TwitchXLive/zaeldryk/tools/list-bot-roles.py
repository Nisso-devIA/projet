#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

token = [
    l.split("=", 1)[1].strip().strip('"').strip("'")
    for l in Path("/home/ubuntu/zaeldryk/config/discord.env").read_text().splitlines()
    if l.startswith("DISCORD_BOT_TOKEN=")
][0]
G = "867426693286461490"
h = {"Authorization": "Bot " + token, "User-Agent": "check"}
bot = json.load(
    urllib.request.urlopen(
        urllib.request.Request("https://discord.com/api/v10/users/@me", headers=h)
    )
)
roles = json.load(
    urllib.request.urlopen(
        urllib.request.Request(f"https://discord.com/api/v10/guilds/{G}/roles", headers=h)
    )
)
mem = json.load(
    urllib.request.urlopen(
        urllib.request.Request(
            f"https://discord.com/api/v10/guilds/{G}/members/{bot['id']}", headers=h
        )
    )
)
role_map = {r["id"]: r for r in roles}
print("bot_id", bot["id"], bot.get("username"))
print("bot_roles:")
for rid in mem.get("roles", []):
    r = role_map.get(rid, {})
    print(" ", r.get("position"), r.get("name"), rid)
