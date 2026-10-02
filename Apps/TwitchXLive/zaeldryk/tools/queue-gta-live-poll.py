#!/usr/bin/env python3
"""Queue GTA VI live poll + delete native Discord polls in #📊-sondages."""
import json
import urllib.error
import urllib.request
from pathlib import Path

CHANNEL_ID = "1542633689840877579"
PENDING = Path("/home/ubuntu/zaeldryk/state/pending-poll.json")
ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")


def api(method: str, path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {load_token()}", "User-Agent": "Zaelrys/1.0"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, path, e.read().decode("utf-8", errors="replace")[:200])
        return None


msgs = api("GET", f"/channels/{CHANNEL_ID}/messages?limit=20") or []
delete_ids = []
for m in msgs:
    if m.get("poll"):
        delete_ids.append(m["id"])
        print("will_delete_poll", m["id"])
    # also remove old lock notice / intro if we want clean - keep them

pending = {
    "channel_id": CHANNEL_ID,
    "question": "GTA VI",
    "options": [
        "Précommande",
        "Achat jour de sortie",
        "Intéressé",
        "Pas du tout intéressé",
    ],
    "delete_message_ids": delete_ids,
}
PENDING.parent.mkdir(parents=True, exist_ok=True)
PENDING.write_text(json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", PENDING)
print(pending)
