#!/usr/bin/env python3
"""Annonce Zelda 40th Anniversary Direct — #📢-annonces."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## The Legend of Zelda — 40 ans : Direct aujourd’hui 16h ⚔️\n\n"
    "Nintendo diffuse **aujourd’hui** un Direct 100 % Zelda pour les **40 ans** de la saga.\n\n"
    "• **Quand :** mardi 8 septembre — **16h00** (heure FR)\n"
    "• **Durée :** ~30 min\n\n"
    "Annonces anniversaire, news franchise… et peut-être du lourd autour d’**Ocarina of Time**.\n\n"
    "👉 **Regarder en live (Nintendo FR) :** https://www.youtube.com/@NintendoFR\n\n"
    "_Bonus : demain 9 sept à 16h → Nintendo Direct général (~45 min)._"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
