#!/usr/bin/env python3
"""Annonce setup stream bientôt finalisé — #📢-annonces."""
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
            "title": "Setup stream — bientôt prêt",
            "description": (
                "Le setup stream est **presque finalisé**.\n\n"
                "Derniers tests en cours pour vous offrir la **meilleure qualité possible** "
                "dès le retour en live.\n\n"
                "Follow la chaîne Twitch et restez branchés ici sur le Discord — "
                "ça arrive bientôt.\n\n"
                "https://www.twitch.tv/zaeldryk"
            ),
            "color": 0x9146FF,
            "footer": {"text": "Zaeldryk — Stream"},
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
