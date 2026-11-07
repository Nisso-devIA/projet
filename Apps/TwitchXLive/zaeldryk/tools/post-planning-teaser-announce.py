#!/usr/bin/env python3
"""Teaser planning lives — #📢-annonces (format texte Zaelrys)."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Planning des lives — en préparation ⚔️\n\n"
    "Je peaufine en ce moment le **calendrier des streams à venir**.\n\n"
    "• Les **créneaux** seront annoncés ici dès qu’ils sont fixés\n"
    "• Le setup stream continue d’être **finalisé** pour la meilleure qualité possible\n\n"
    "Restez branchés sur le Discord — la reprise approche.\n"
    "👉 **Chaîne Twitch :** https://twitch.tv/zaeldryk\n\n"
    "Merci de faire partie de la communauté 🐺"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
