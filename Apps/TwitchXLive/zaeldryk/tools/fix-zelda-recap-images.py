#!/usr/bin/env python3
"""Update Zelda Direct recap with official Nintendo press images."""
import json
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541249724902809692"
MESSAGE_ID = "1546970072302751765"

# Official article assets (Nintendo.com — 40th Anniversary Direct, 2026-09-08)
BASE = (
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/"
    "ncom/en_US/articles/2026/"
    "the-legend-of-zelda-40th-anniversary-celebration-revealed-in-new-nintendo-direct-presentation/"
)
IMG_LEAD = BASE + "zd_lead"
IMG_CONSOLE = BASE + "zd_1"
IMG_MOVIE = BASE + "1920x1080_movie"
IMG_GAME = (
    "https://assets.nintendo.com/image/upload/c_fill,w_1200/q_auto:best/f_auto/"
    "dpr_2.0/store/software/switch2/70010000130792/"
    "21d17919819cffebda2817f9b0110116c28568e0b6fa30a9778f1679271be809"
)

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
            "title": "Zelda Direct — les annonces à retenir",
            "description": (
                "Récap du **Direct 40 ans de Zelda** : console collector, remake et film.\n\n"
                "**Console collector Switch 2**\n"
                "Nintendo Switch 2 – The Legend of Zelda – 40th Anniversary Edition "
                "(+ Pro Controller & étui assortis, motif Triforce).\n"
                "**Dispo le 29 octobre 2026.**\n\n"
                "**The Legend of Zelda: Ocarina of Time** (remake)\n"
                "Remake exclusif **Switch 2** — visuels refaits, cutscenes doublées, orchestre…\n"
                "**Sortie le 5 novembre 2026.**\n\n"
                "**Le film *The Legend of Zelda* (live-action)**\n"
                "Nintendo × Sony Pictures — Link & Zelda à l’écran.\n"
                "**Sortie cinéma mondiale : 30 avril 2027.**\n\n"
                "Replay : https://www.youtube.com/@NintendoFR\n"
                "Infos : https://zelda40th.nintendo.com"
            ),
            "color": 0x00A651,
            "image": {"url": IMG_LEAD},
            "footer": {"text": "Zaeldryk — Annonce gaming · images © Nintendo"},
        },
        {
            "title": "Switch 2 — 40th Anniversary Edition",
            "description": "**29 octobre 2026** · console + accessoires Triforce",
            "color": 0x00A651,
            "image": {"url": IMG_CONSOLE},
        },
        {
            "title": "Ocarina of Time — Switch 2",
            "description": "**5 novembre 2026** · exclusif Switch 2",
            "color": 0x00A651,
            "image": {"url": IMG_GAME},
        },
        {
            "title": "Film The Legend of Zelda",
            "description": "**30 avril 2027** · Nintendo × Sony Pictures",
            "color": 0x00A651,
            "image": {"url": IMG_MOVIE},
        },
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
print("updated", body.get("id"), "embeds", len(body.get("embeds") or []))
