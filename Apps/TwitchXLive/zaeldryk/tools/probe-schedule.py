#!/usr/bin/env python3
import json
import urllib.request
from pathlib import Path

root = Path("/home/ubuntu/zaeldryk")
twitch = {}
for line in (root / "config/twitch.env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        twitch[k.strip()] = v.strip().strip('"').strip("'")

token = Path(twitch["TWITCH_TOKEN_FILE"]).read_text().strip()
bid = twitch.get("TWITCH_BROADCASTER_ID", "426411773")

req = urllib.request.Request(
    f"https://api.twitch.tv/helix/schedule?broadcaster_id={bid}&first=25",
    headers={
        "Client-ID": twitch["TWITCH_CLIENT_ID"],
        "Authorization": f"Bearer {token}",
    },
)
print("=== TWITCH SCHEDULE ===")
try:
    with urllib.request.urlopen(req) as resp:
        print(json.dumps(json.load(resp), indent=2)[:4000])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:500])

discord_token = None
for line in (root / "config/discord.env").read_text().splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        discord_token = line.split("=", 1)[1].strip().strip('"').strip("'")
req2 = urllib.request.Request(
    "https://discord.com/api/v10/guilds/867426693286461490/scheduled-events",
    headers={"Authorization": f"Bot {discord_token}", "User-Agent": "probe"},
)
print("\n=== DISCORD EVENTS ===")
try:
    print(json.dumps(json.load(urllib.request.urlopen(req2)), indent=2)[:2000])
except Exception as e:
    print("ERR", e)
