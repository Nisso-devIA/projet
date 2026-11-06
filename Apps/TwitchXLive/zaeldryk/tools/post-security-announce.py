#!/usr/bin/env python3
"""Post a one-off announcement in #📢-annonces."""
from announce_common import ANNONCES_CHANNEL_ID, post_announce

CONTENT = (
    "## Mise à jour du serveur Zaelrys\n\n"
    "Le Discord a été mis à jour avec **plus de sécurité** "
    "(vérification à l’arrivée, protections renforcées, outils staff).\n\n"
    "Les membres actuels ont été **migrés sans problème** — "
    "rien à faire de votre côté.\n\n"
    "Cette étape prépare l’activité à venir du serveur. "
    "Merci de faire partie de la communauté ⚔️"
)

if __name__ == "__main__":
    body = post_announce(CONTENT)
    print("posted", body.get("id"), "in", ANNONCES_CHANNEL_ID)
