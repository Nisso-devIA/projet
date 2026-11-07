#!/usr/bin/env python3
"""Remove Twitch link from Zelda Direct announce."""
import json
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541249724902809692"
MESSAGE_ID = "1546661044095684719"
env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

payload = {
    "embeds": [
        {
            "title": "The Legend of Zelda — 40 ans : Direct aujourd’hui 16h",
            "description": (
                "Nintendo diffuse **aujourd’hui** un Direct 100 % Zelda "
                "pour les **40 ans** de la saga.\n\n"
                "**Quand :** mardi 8 septembre — **16h00** (heure FR)\n"
                "**Durée :** ~30 min\n\n"
                "Annonces anniversaire, news franchise… et peut-être du lourd "
                "autour d’**Ocarina of Time**.\n\n"
                "Regarder en live (Nintendo FR) :\n"
                "https://www.youtube.com/@NintendoFR\n\n"
                "_Bonus : demain 9 sept à 16h → Nintendo Direct général (~45 min)._"
            ),
            "color": 0x00A651,
            "footer": {"text": "Zaeldryk — Annonce gaming"},
        }
    ],
}

data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages/{MESSAGE_ID}",
    data=data,
    headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "ZaelrysAnnounce/1.0",
    },
    method="PATCH",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    body = json.loads(resp.read())
print("updated", body.get("id"))
