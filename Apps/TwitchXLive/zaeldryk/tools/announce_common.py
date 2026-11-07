"""Post #📢-annonces — format Zaelrys (texte, pas embed).

Modèle (comme post-stream-resume / post-security-announce) :
  @everyone
  ## Titre avec emoji ⚔️
  Paragraphe avec **mots importants**.
  • **Puce 1**
  • **Puce 2**
  Phrase — précision.
  👉 **Chaîne Twitch :** https://twitch.tv/zaeldryk
  Clôture 🐺
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ANNONCES_CHANNEL_ID = "1541249724902809692"
DISCORD_ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")


def load_discord_token() -> str:
    if not DISCORD_ENV.exists():
        raise SystemExit(f"discord.env missing: {DISCORD_ENV}")
    for line in DISCORD_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def post_announce(content: str, *, ping_everyone: bool = True) -> dict:
    """Envoie un message texte dans #annonces."""
    token = load_discord_token()
    body: dict = {"content": content}
    if ping_everyone:
        if "@everyone" not in content:
            body["content"] = f"@everyone\n\n{content.lstrip()}"
        body["allowed_mentions"] = {"parse": ["everyone"]}
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{ANNONCES_CHANNEL_ID}/messages",
        data=data,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "ZaelrysAnnounce/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())
