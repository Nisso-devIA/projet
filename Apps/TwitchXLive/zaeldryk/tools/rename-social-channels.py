#!/usr/bin/env python3
"""Rename social channels with double-struck prefix; remove pinned branding."""
import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
MARKER = "[zael-social-branding]"

CHANNELS = {
    "1541251095492435978": "𝕋-twitch",
    "1541251096763179181": "𝕐-youtube",
    "1541251097962877010": "𝕏-twitter",
}


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str, body=None):
    token = load_token()
    data = None
    headers = {"Authorization": f"Bot {token}", "User-Agent": "ZaelrysSocialRename/1.0"}
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


def cleanup_pins(channel_id: str) -> None:
    _, pins = api("GET", f"/channels/{channel_id}/messages/pins")
    pin_list = pins if isinstance(pins, list) else []
    for msg in pin_list:
        if not isinstance(msg, dict):
            continue
        if MARKER not in (msg.get("content") or ""):
            continue
        mid = msg["id"]
        try:
            api("DELETE", f"/channels/{channel_id}/pins/{mid}")
        except SystemExit:
            pass
        api("DELETE", f"/channels/{channel_id}/messages/{mid}")
        print("deleted pin", channel_id, mid)


def rename_channel(channel_id: str, name: str) -> None:
    status, ch = api("PATCH", f"/channels/{channel_id}", {"name": name})
    print("renamed", channel_id, status, ch.get("name"))


def main() -> None:
    for ch_id, name in CHANNELS.items():
        cleanup_pins(ch_id)
        rename_channel(ch_id, name)
    print("done")


if __name__ == "__main__":
    main()
