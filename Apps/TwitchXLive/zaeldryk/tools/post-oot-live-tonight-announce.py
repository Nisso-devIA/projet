#!/usr/bin/env python3
"""Annonce live OOT remake — univers Zelda (vert Kokiri / or Triforce / art officiel)."""
import json
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541249724902809692"
# Couleurs univers Ocarina of Time
KOKIRI_GREEN = 0x2E8B57  # forêt Kokiri / Link
TRIFORCE_GOLD = 0xF4C430  # Triforce
NAVI_BLUE = 0x4FC3F7  # Navi
HYRULE_NIGHT = 0x1A3A2A  # nuit Hyrule

# Key art officielle OOT remake (Nintendo CDN — OK 200)
ART_OOT = (
    "https://assets.nintendo.com/image/upload/c_fill,w_1200/q_auto:best/f_auto/"
    "dpr_2.0/store/software/switch2/70010000130792/"
    "21d17919819cffebda2817f9b0110116c28568e0b6fa30a9778f1679271be809"
)
# Lead Direct 40 ans (ambiance)
ART_LEAD = (
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/"
    "ncom/en_US/articles/2026/"
    "the-legend-of-zelda-40th-anniversary-celebration-revealed-in-new-nintendo-direct-presentation/"
    "zd_lead"
)

env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str, body=None):
    data = None
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "ZaelrysAnnounce/OOT/1.0",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


# Supprime l'ancienne annonce trop sobre si encore là
OLD_ID = "1567965543464566935"
try:
    api("DELETE", f"/channels/{CHANNEL_ID}/messages/{OLD_ID}")
    print("deleted old", OLD_ID)
except Exception as e:
    print("delete skip", e)

payload = {
    "content": (
        "@everyone\n\n"
        "# 🗡️ Hyrule t’appelle — LIVE CE SOIR\n\n"
        "Dans la forêt Kokiri, le vent murmure…\n"
        "**The Legend of Zelda: Ocarina of Time — Remake** ouvre ses portes ce soir sur Twitch.\n\n"
        "• **Heure :** autour de **22h–23h30**\n"
        "• **Jeu :** Ocarina of Time Remake (**Switch 2**)\n"
        "• **Chaîne :** Zaeldryk\n\n"
        "Prenez l’**Ocarina**, suivez **Navi**, et rejoignez le Triforce en live.\n"
        "👉 **https://twitch.tv/zaeldryk**\n\n"
        "_Hey! Listen!_ — On se retrouve à Hyrule 🐺"
    ),
    "allowed_mentions": {"parse": ["everyone"]},
    "embeds": [
        {
            "title": "⚔️ The Legend of Zelda: Ocarina of Time — Remake",
            "description": (
                "**Live spécial ce soir**\n\n"
                "🌲 Forêt Kokiri · 🏰 Château d’Hyrule · ⏳ Temple du Temps\n\n"
                "🕐 **22h – 23h30**\n"
                "🎮 Exclusivité **Nintendo Switch 2**\n\n"
                "[▶ Rejoindre le live Twitch](https://twitch.tv/zaeldryk)"
            ),
            "url": "https://twitch.tv/zaeldryk",
            "color": KOKIRI_GREEN,
            "image": {"url": ART_OOT},
            "footer": {
                "text": "Zaeldryk · Triforce Live · Ocarina of Time Remake"
            },
        },
        {
            "title": "✨ Le Triforce s’illumine",
            "description": (
                "**Courage · Sagesse · Force**\n\n"
                "Ce soir on ouvre l’aventure — soyez là pour le départ."
            ),
            "color": TRIFORCE_GOLD,
            "thumbnail": {"url": ART_LEAD},
        },
        {
            "title": "💎 Hey! Listen!",
            "description": (
                "Navi vous guide vers le stream.\n"
                "👉 https://twitch.tv/zaeldryk"
            ),
            "color": NAVI_BLUE,
        },
    ],
}

msg = api("POST", f"/channels/{CHANNEL_ID}/messages", payload)
print("posted", msg.get("id"), "in", CHANNEL_ID)
