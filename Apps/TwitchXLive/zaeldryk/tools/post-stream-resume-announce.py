#!/usr/bin/env python3
"""Post stream resume + Twitch rebrand announcement in #📢-annonces."""
import json
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541249724902809692"
env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

payload = {
    "content": (
        "@everyone\n\n"
        "## Les streams reprennent bientôt ⚔️\n\n"
        "La chaîne Twitch **Zaeldryk** a été mise à jour :\n"
        "• **Nouveau logo**\n"
        "• **Nouveau design** de la chaîne\n\n"
        "Les lives vont reprendre prochainement — horaire habituel autour de **22h–23h30**.\n"
        "👉 **Chaîne Twitch :** https://twitch.tv/zaeldryk\n\n"
        "Follow + Discord pour ne rien rater 🐺"
    ),
    "allowed_mentions": {"parse": ["everyone"]},
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
    data=data,
    headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "ZaelrysAnnounce/1.0",
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    body = json.loads(resp.read())
print("posted", body.get("id"), "in", CHANNEL_ID)
