#!/usr/bin/env python3
"""Annonce lancement Miina Pâtisserie — #📢-annonces."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Miina Pâtisserie se lance ⚔️\n\n"
    "La famille s’agrandit : **Miina** lance sa pâtisserie.\n"
    "Allez lui apporter de la force, c’est de la **famille**.\n\n"
    "• **Instagram :** https://www.instagram.com/miina_patisserie/\n"
    "• **TikTok :** https://www.tiktok.com/@miinapatisserie\n"
    "• **Site :** https://xn--miina-ptisserie-9jb.fr/\n\n"
    "Merci de faire partie de la communauté 🐺"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
