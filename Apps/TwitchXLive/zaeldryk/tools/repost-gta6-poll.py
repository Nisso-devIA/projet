#!/usr/bin/env python3
"""Replace GTA VI poll with cleaner question text."""
import json
import urllib.error
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541249730024186017"
OLD_MSG_ID = "1542632321562320926"
env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str, body=None):
    data = None
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "ZaelrysPoll/1.0",
    }
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
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


api("DELETE", f"/channels/{CHANNEL_ID}/messages/{OLD_MSG_ID}")
print("deleted", OLD_MSG_ID)

status, body = api(
    "POST",
    f"/channels/{CHANNEL_ID}/messages",
    {
        "content": "🚗 **GTA VI**",
        "poll": {
            "question": {"text": "GTA VI"},
            "answers": [
                {"poll_media": {"text": "Précommande"}},
                {"poll_media": {"text": "Achat jour de sortie"}},
                {"poll_media": {"text": "Intéressé"}},
                {"poll_media": {"text": "Pas du tout intéressé"}},
            ],
            "duration": 168,
            "allow_multiselect": False,
            "layout_type": 1,
        },
    },
)
print("posted", body.get("id"), status)
