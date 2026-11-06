#!/usr/bin/env python3
"""Annonce récap Zelda Direct — #📢-annonces (texte + URLs images)."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

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

CONTENT = (
    "## Zelda Direct — les annonces à retenir ⚔️\n\n"
    "Récap du **Direct 40 ans de Zelda** : console collector, remake et film.\n\n"
    "**Console collector Switch 2**\n"
    "Nintendo Switch 2 – The Legend of Zelda – 40th Anniversary Edition "
    "(+ Pro Controller & étui assortis, motif Triforce).\n"
    "• **Dispo le 29 octobre 2026.**\n"
    f"{IMG_CONSOLE}\n\n"
    "**The Legend of Zelda: Ocarina of Time** (remake)\n"
    "Remake exclusif **Switch 2** — visuels refaits, cutscenes doublées, orchestre…\n"
    "• **Sortie le 5 novembre 2026.**\n"
    f"{IMG_GAME}\n\n"
    "**Le film *The Legend of Zelda* (live-action)**\n"
    "Nintendo × Sony Pictures — Link & Zelda à l’écran.\n"
    "• **Sortie cinéma mondiale : 30 avril 2027.**\n"
    f"{IMG_MOVIE}\n\n"
    "👉 **Replay :** https://www.youtube.com/@NintendoFR\n"
    "🌐 **Infos :** https://zelda40th.nintendo.com\n\n"
    f"{IMG_LEAD}\n\n"
    "_Images © Nintendo_"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
