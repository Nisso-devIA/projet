#!/usr/bin/env python3
"""Post a one-off announcement in #📢-annonces."""
import json
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541249724902809692"
env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

payload = {
    "content": (
        "@everyone\n\n"
        "## Mise à jour du serveur Zaelrys\n\n"
        "Le Discord a été mis à jour avec **plus de sécurité** "
        "(vérification à l’arrivée, protections renforcées, outils staff).\n\n"
        "Les membres actuels ont été **migrés sans problème** — "
        "rien à faire de votre côté.\n\n"
        "Cette étape prépare l’activité à venir du serveur. "
        "Merci de faire partie de la communauté ⚔️"
    ),
    "allowed_mentions": {"parse": ["everyone"]},
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
    data=data,
    headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "ZaelrysAnnounce/1.0",
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    body = json.loads(resp.read())
print("posted", body.get("id"), "in", CHANNEL_ID)
