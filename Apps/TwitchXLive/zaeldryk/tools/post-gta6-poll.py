#!/usr/bin/env python3
"""Post GTA VI poll in #💬-général."""
import json
import urllib.error
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541249730024186017"  # 💬-général
env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

payload = {
    "content": "🚗 **GTA VI** — vous êtes plutôt… ?",
    "poll": {
        "question": {"text": "GTA VI — ton plan ?"},
        "answers": [
            {"poll_media": {"text": "Précommande"}},
            {"poll_media": {"text": "Achat jour de sortie"}},
            {"poll_media": {"text": "Intéressé"}},
            {"poll_media": {"text": "Pas du tout intéressé"}},
        ],
        "duration": 168,  # 7 jours
        "allow_multiselect": False,
        "layout_type": 1,
    },
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
    data=data,
    headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "ZaelrysPoll/1.0",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read())
    print("posted", body.get("id"), "in", CHANNEL_ID)
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode("utf-8", errors="replace"))
    raise
