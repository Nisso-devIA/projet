#!/usr/bin/env python3
"""Queue GTA 6 tonight-watch live poll + short announce."""
import json
import urllib.error
import urllib.request
from pathlib import Path

SONDAGES_ID = "1542633689840877579"
ANNONCES_ID = "1541249724902809692"
PENDING = Path("/home/ubuntu/zaeldryk/state/pending-poll.json")
ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")


def api(method: str, path: str, body=None):
    data = None
    headers = {"Authorization": f"Bot {load_token()}", "User-Agent": "Zaelrys/1.0"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code}: {err}") from e


pending = {
    "channel_id": SONDAGES_ID,
    "question": "GTA VI — tu regardes le gameplay ce soir ?",
    "options": [
        "Oui, je regarde",
        "Peut-être",
        "Non",
    ],
    "delete_message_ids": [],
}
PENDING.parent.mkdir(parents=True, exist_ok=True)
PENDING.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
print("queued", PENDING)

status, msg = api(
    "POST",
    f"/channels/{ANNONCES_ID}/messages",
    {
        "content": "@everyone",
        "allowed_mentions": {"parse": ["everyone"]},
        "embeds": [
            {
                "title": "🎬 GTA VI — Extended Look ce soir",
                "description": (
                    "Qui va regarder le **gameplay GTA VI** ce soir ?\n\n"
                    f"👉 Vote ici : <#{SONDAGES_ID}>\n\n"
                    "🔗 Netflix (dispo) : https://www.netflix.com/title/83035795\n"
                    "▶️ YouTube Rockstar (gratuit ~03h) : https://www.youtube.com/@RockstarGames"
                ),
                "color": 0xFC47A8,
                "footer": {"text": "Zaeldryk — Sondage"},
            }
        ],
    },
)
print("announce", status, msg.get("id"))
