#!/usr/bin/env python3
"""Modèle — copier pour une nouvelle annonce #📢-annonces (texte Zaelrys)."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Titre de l’annonce ⚔️\n\n"
    "Phrase d’intro avec **mots importants**.\n\n"
    "• **Point 1**\n"
    "• **Point 2**\n\n"
    "Précision — détail.\n"
    "👉 **Lien :** https://example.com\n\n"
    "Merci de faire partie de la communauté 🐺"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
