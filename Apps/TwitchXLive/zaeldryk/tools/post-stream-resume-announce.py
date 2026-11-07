#!/usr/bin/env python3
"""Post stream resume + Twitch rebrand announcement in #📢-annonces."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Les streams reprennent bientôt ⚔️\n\n"
    "La chaîne Twitch **Zaeldryk** a été mise à jour :\n"
    "• **Nouveau logo**\n"
    "• **Nouveau design** de la chaîne\n\n"
    "Les lives vont reprendre prochainement — horaire habituel autour de **22h–23h30**.\n"
    "👉 **Chaîne Twitch :** https://twitch.tv/zaeldryk\n\n"
    "Follow + Discord pour ne rien rater 🐺"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
