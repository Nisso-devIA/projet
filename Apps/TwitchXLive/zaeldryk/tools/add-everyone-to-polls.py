#!/usr/bin/env python3
"""Add @everyone content to existing live poll messages (display only, no re-ping)."""
import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
STATE = Path("/home/ubuntu/zaeldryk/state/live-polls.json")


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
        print("HTTP", e.code, e.read().decode("utf-8", errors="replace")[:300])
        return e.code, None


def main() -> None:
    polls = json.loads(STATE.read_text(encoding="utf-8"))
    for pid, poll in polls.items():
        ch = poll.get("channel_id")
        mid = poll.get("message_id")
        if not ch or not mid:
            continue
        status, _ = api(
            "PATCH",
            f"/channels/{ch}/messages/{mid}",
            {
                "content": "@everyone",
                "allowed_mentions": {"parse": []},  # no re-ping on edit
            },
        )
        print("updated", pid, mid, status)


if __name__ == "__main__":
    main()
