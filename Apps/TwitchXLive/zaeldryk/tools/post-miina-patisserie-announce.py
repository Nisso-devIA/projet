#!/usr/bin/env python3
"""Annonce lancement Miina Pâtisserie — #📢-annonces."""
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
            "title": "Miina Pâtisserie se lance",
            "description": (
                "La famille s’agrandit : **Miina** lance sa pâtisserie.\n"
                "Allez lui apporter de la force, c’est de la **famille**.\n\n"
                "Instagram\n"
                "https://www.instagram.com/miina_patisserie/\n\n"
                "TikTok\n"
                "https://www.tiktok.com/@miinapatisserie\n\n"
                "Site\n"
                "https://xn--miina-ptisserie-9jb.fr/"
            ),
            "color": 0xE8A0BF,
            "footer": {"text": "Zaeldryk — Famille"},
        }
    ],
}

data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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
