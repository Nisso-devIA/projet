#!/usr/bin/env python3
"""Delete Discord live announcement posted by live-announce.py."""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
LIVE_ENV = ZAEL_ROOT / "config" / "live.env"
STATE_FILE = ZAEL_ROOT / "state" / "last_discord_live_message.json"
API = "https://discord.com/api/v10"


def load_env(path: Path) -> dict:
    cfg = {}
    if not path.exists():
        return cfg
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def main() -> None:
    if not STATE_FILE.exists():
        print("no message to delete")
        return

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        STATE_FILE.unlink(missing_ok=True)
        print("cleared corrupt state")
        return

    message_id = state.get("message_id")
    channel_id = state.get("channel_id")
    if not message_id or not channel_id:
        STATE_FILE.unlink(missing_ok=True)
        print("cleared invalid state")
        return

    cfg = {**load_env(DISCORD_ENV), **load_env(LIVE_ENV)}
    token = cfg.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN missing")

    req = urllib.request.Request(
        f"{API}/channels/{channel_id}/messages/{message_id}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "ZaelrysLiveAnnounce/1.0",
        },
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        print("deleted", message_id, "from", channel_id)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("already gone", message_id)
        else:
            err = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"Discord HTTP {e.code}: {err}") from e
    finally:
        STATE_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
