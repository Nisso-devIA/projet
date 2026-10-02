#!/usr/bin/env python3
"""Post GTA 6 Extended Look announcement in #📢-annonces."""
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
    "content": "@everyone",
    "allowed_mentions": {"parse": ["everyone"]},
    "embeds": [
        {
            "title": "🚗 Grand Theft Auto VI — Extended Look (gameplay)",
            "description": (
                "Rockstar vient de sortir un **Extended Look** officiel de **GTA 6** "
                "(~26 min de gameplay, capturé sur PS5).\n\n"
                "**Sortie du jeu :** 19 novembre 2026 (PS5 & Xbox Series X|S)\n\n"
                "🎬 **Regarder maintenant (Netflix) :**\n"
                "https://www.netflix.com/title/83035795\n\n"
                "▶️ **Gratuit un peu plus tard (YouTube Rockstar) :**\n"
                "https://www.youtube.com/@RockstarGames\n"
                "_(disponible ~03h00 France, 28 août)_\n\n"
                "🌐 Page officielle :\n"
                "https://www.rockstargames.com/VI"
            ),
            "color": 0xFC47A8,
            "footer": {"text": "Zaeldryk — Annonce gaming"},
        }
    ],
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
