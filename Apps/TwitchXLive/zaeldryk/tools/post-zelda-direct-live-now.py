#!/usr/bin/env python3
"""Annonce : Zelda Direct a commencé — #📢-annonces."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Zelda Direct — c’est parti ⚔️\n\n"
    "**Le Nintendo Direct Zelda 40 ans a commencé.**\n\n"
    "👉 **Branche-toi maintenant :** https://www.youtube.com/@NintendoFR\n\n"
    "Bon direct 🐺"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
