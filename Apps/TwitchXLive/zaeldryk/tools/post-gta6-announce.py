#!/usr/bin/env python3
"""Post GTA 6 Extended Look announcement in #📢-annonces."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Grand Theft Auto VI — Extended Look (gameplay) 🚗\n\n"
    "Rockstar vient de sortir un **Extended Look** officiel de **GTA 6** "
    "(~26 min de gameplay, capturé sur PS5).\n\n"
    "• **Sortie du jeu :** 19 novembre 2026 (PS5 & Xbox Series X|S)\n\n"
    "👉 **Netflix (dispo) :** https://www.netflix.com/title/83035795\n"
    "▶️ **YouTube Rockstar :** https://www.youtube.com/@RockstarGames\n"
    "🌐 **Page officielle :** https://www.rockstargames.com/VI\n\n"
    "Bon visionnage ⚔️"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
