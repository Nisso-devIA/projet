"""Titres Twitch pour un live Zelda Ocarina of Time."""
from __future__ import annotations

import json
import re

OOT_KEYS = ("ocarina", "oot", "zelda", "hyrule")
OOT_QUERY = "The Legend of Zelda: Ocarina of Time"
TITLE_LIMIT = 140
# Codes :emoji: Twitch/Discord. Les titres doivent porter le caractère lui-même.
SHORTCODE = re.compile(r":[a-z0-9_]+:", re.IGNORECASE)

# Invitation directe, tutoiement. Emojis Unicode, pas de « remake », pas de « Switch ».
OOT_TITLES = [
    "🧚 Hey Listen, je t'attends pour la suite de l'aventure, ne traîne pas 😉",
    "🍃 Hey Listen, la suite de l'aventure commence. Ramène-toi 😉",
    "🧚 Hey Listen, je suis en live. Viens, on continue ensemble ✨",
    "🍃 Hey Listen, je t'ai gardé la suite. Ne me laisse pas y aller seul 😉",
    "🧚 Hey Listen, on reprend l'aventure. Passe avant que je me perde 🧭",
    "🍃 Hey Listen, le live est ouvert. La quête n'attend que toi 😉",
    "🧚 Hey Listen, je continue. Tu arrives quand tu veux, mais là c'est mieux ✨",
    "🍃 Hey Listen, viens pour la suite. Le chat a le droit de me guider 🗺️",
    "🧚 Hey Listen, c'est reparti. Pose-toi, on avance 😉",
    "🍃 Hey Listen, je t'attends. L'aventure est meilleure à plusieurs ✨",
    "🧚 Hey Listen, ne traîne pas. La suite est en live 😉",
    "🍃 Hey Listen, direction le Village Cocorico. Je t'attends 😉",
]


def has_unicode_emoji(text: str) -> bool:
    return any(ord(ch) > 0xFFFF for ch in text)


def encode_channel_body(payload: dict) -> bytes:
    """JSON UTF-8. Les emojis restent des caractères, pas des codes :court:."""
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")
