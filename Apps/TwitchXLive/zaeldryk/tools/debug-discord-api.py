#!/usr/bin/env python3
from pathlib import Path
import json
import urllib.request
import urllib.error

p = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in p.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

print("token_len", len(token) if token else None)
print("has_cr", "\r" in (token or ""))

def get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bot {token}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.load(r)

try:
    status, me = get("https://discord.com/api/v10/users/@me")
    print("ME", status, me.get("username"), me.get("id"))
except urllib.error.HTTPError as e:
    print("ME_ERR", e.code, e.read()[:200])

try:
    status, chs = get("https://discord.com/api/v10/guilds/867426693286461490/channels")
    print("CH_COUNT", len(chs))
    for c in chs:
        n = c.get("name") or ""
        if "log" in n.lower() or "📝" in n or "bienvenue" in n.lower():
            print("HIT", c["id"], repr(n))
except urllib.error.HTTPError as e:
    print("CH_ERR", e.code, e.read()[:300])
