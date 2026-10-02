#!/usr/bin/env python3
"""Probe guild boost + tag-related API fields."""
import json
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
GUILD_ID = "867426693286461490"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")


def get(path: str):
    token = load_token()
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "ZaelrysProbe/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


g = get(f"/guilds/{GUILD_ID}?with_counts=true")
print("name", g.get("name"))
print("premium_tier", g.get("premium_tier"))
print("premium_subscription_count", g.get("premium_subscription_count"))
print("approximate_member_count", g.get("approximate_member_count"))
print("features", sorted(g.get("features", [])))
for k in sorted(g.keys()):
    if "tag" in k.lower() or "clan" in k.lower() or "badge" in k.lower() or "identity" in k.lower():
        print(k, g.get(k))

try:
    preview = get(f"/guilds/{GUILD_ID}/preview")
    print("preview_keys", sorted(preview.keys()))
    for k in sorted(preview.keys()):
        if "tag" in k.lower() or "clan" in k.lower() or "badge" in k.lower():
            print("preview", k, preview.get(k))
except Exception as e:
    print("preview_err", e)
