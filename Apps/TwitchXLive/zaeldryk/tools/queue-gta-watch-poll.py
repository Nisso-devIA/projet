#!/usr/bin/env python3
"""Queue GTA 6 tonight-watch live poll + short announce."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from announce_common import post_announce  # noqa: E402

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

ANNOUNCE = (
    "## GTA VI — Extended Look ce soir 🚗\n\n"
    "Qui va regarder le **gameplay GTA VI** ce soir ?\n\n"
    f"👉 **Vote ici :** <#{SONDAGES_ID}>\n\n"
    "• **Netflix :** https://www.netflix.com/title/83035795\n"
    "• **YouTube Rockstar :** https://www.youtube.com/@RockstarGames\n\n"
    "Merci de faire partie de la communauté 🐺"
)
msg = post_announce(ANNOUNCE)
print("announce", msg.get("id"))
