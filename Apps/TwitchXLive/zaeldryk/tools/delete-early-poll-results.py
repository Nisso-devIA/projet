#!/usr/bin/env python3
"""Delete prematurely published poll-result messages; allow auto-post at 24h close."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
STATE = ZAEL_ROOT / "state" / "live-polls.json"
API_BASE = "https://discord.com/api/v10"

# Messages posted by publish-poll-results.py (anonymous results)
RESULT_MSG_IDS = [
    "1542643650956099686",
    "1542643652055015614",
]
CHANNEL_SONDAGES_ID = "1542633689840877579"


def load_token() -> str:
    for line in DISCORD_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() in ("DISCORD_BOT_TOKEN", "DISCORD_TOKEN", "BOT_TOKEN", "TOKEN"):
            return v.strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN not found")


def delete_message(token: str, channel_id: str, message_id: str) -> None:
    req = Request(
        f"{API_BASE}/channels/{channel_id}/messages/{message_id}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "ZaeldrykPollCleanup/1.0",
        },
        method="DELETE",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            resp.read()
        print(f"deleted {message_id}")
    except HTTPError as e:
        if e.code == 404:
            print(f"already gone {message_id}")
        else:
            raise


def main() -> None:
    token = load_token()
    for mid in RESULT_MSG_IDS:
        delete_message(token, CHANNEL_SONDAGES_ID, mid)

    data = json.loads(STATE.read_text(encoding="utf-8"))
    for poll in data.values():
        poll.pop("results_posted", None)
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("cleared results_posted — will publish only at 24h close")


if __name__ == "__main__":
    main()
