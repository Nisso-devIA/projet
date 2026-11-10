"""Payload for the #📖-règlement message. The banner is a large embed image."""

from __future__ import annotations

from pathlib import Path

BANNER_FILENAME = "reglement-banner.jpg"
BANNER_PATH = Path("/home/ubuntu/zaeldryk/discord/assets") / BANNER_FILENAME
RULES_COLOR = 15844367
RULES_TITLE = "📜 Règlement du Royaume ZAELDRYK"
RULES_DESCRIPTION = (
    "1. Respecte tous les membres — aucune insulte, harcèlement ou discrimination\n"
    "2. Pas de spam, flood ou publicité sans autorisation\n"
    "3. Pas de contenu NSFW / choquant\n"
    "4. Les liens sont réservés au staff\n"
    "5. Respecte les salons et les décisions des Sentinelles\n"
    "6. Amuse-toi et reste dans l’esprit de la communauté\n"
    "\n"
    "⚔️ En restant ici, tu acceptes ces règles.\n"
    "Le non-respect peut entraîner un timeout ou un bannissement."
)
RULES_FOOTER = "Clique sur le bouton pour rejoindre la communauté"


def rules_embed_dict() -> dict:
    return {
        "title": RULES_TITLE,
        "description": RULES_DESCRIPTION,
        "color": RULES_COLOR,
        "footer": {"text": RULES_FOOTER},
        "image": {"url": f"attachment://{BANNER_FILENAME}"},
    }
