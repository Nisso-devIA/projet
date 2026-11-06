#!/usr/bin/env python3
"""Annonce setup stream ~80% — #📢-annonces."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Les streams reprennent bientôt ⚔️\n\n"
    "Le setup avance bien — on est à environ **80 %** de la finalisation.\n\n"
    "• Derniers réglages en cours pour la **meilleure qualité possible**\n"
    "• Retour en live **très bientôt**\n"
    "• Horaire habituel autour de **22h–23h30**\n\n"
    "Restez branchés ici pour le planning.\n"
    "👉 **Chaîne Twitch :** https://twitch.tv/zaeldryk\n\n"
    "Merci de faire partie de la communauté 🐺"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
