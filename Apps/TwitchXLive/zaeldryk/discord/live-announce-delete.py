#!/usr/bin/env python3
"""Delete every Discord live announcement recorded for the session."""
import importlib.util
import json
import urllib.error
import urllib.request
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "live_announce", Path(__file__).resolve().with_name("live-announce.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
API = _mod.API
DISCORD_ENV = _mod.DISCORD_ENV
LIVE_ENV = _mod.LIVE_ENV
STATE_FILE = _mod.STATE_FILE
is_own_live_embed = _mod.is_own_live_embed
load_env = _mod.load_env
load_state = _mod.load_state
message_ids = _mod.message_ids


def api(method: str, path: str, token: str):
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "ZaelrysLiveAnnounce/1.0",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            body = json.loads(raw) if raw else {}
            return resp.status, body
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def delete_one(token: str, channel_id: str, message_id: str) -> str:
    status, _ = api("DELETE", f"/channels/{channel_id}/messages/{message_id}", token)
    if status in (200, 204):
        print("deleted", message_id, "from", channel_id)
        return "deleted"
    if status == 404:
        print("already gone", message_id)
        return "gone"
    raise SystemExit(f"Discord HTTP {status} deleting {message_id}")


def sweep_own_live_messages(token: str, channel_id: str, bot_id: str, seen: set[str]) -> None:
    status, messages = api("GET", f"/channels/{channel_id}/messages?limit=50", token)
    if status != 200 or not isinstance(messages, list):
        print("sweep skipped", status)
        return
    for message in messages:
        mid = str(message.get("id") or "")
        if not mid or mid in seen or not is_own_live_embed(message, bot_id):
            continue
        delete_one(token, channel_id, mid)
        seen.add(mid)


def main() -> None:
    cfg = {**load_env(DISCORD_ENV), **load_env(LIVE_ENV)}
    token = cfg.get("DISCORD_BOT_TOKEN")
    channel_id = cfg.get("DISCORD_LIVE_CHANNEL_ID")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN missing")
    if not channel_id:
        raise SystemExit("DISCORD_LIVE_CHANNEL_ID missing in live.env")

    state = load_state(STATE_FILE)
    recorded = message_ids(state)
    if state.get("channel_id"):
        channel_id = str(state["channel_id"])
    seen: set[str] = set()
    for mid in recorded:
        delete_one(token, channel_id, mid)
        seen.add(mid)

    status, me = api("GET", "/users/@me", token)
    bot_id = str((me or {}).get("id") or "") if status == 200 else ""
    if bot_id:
        sweep_own_live_messages(token, channel_id, bot_id, seen)
    else:
        print("sweep skipped, bot id unavailable", status)

    STATE_FILE.unlink(missing_ok=True)
    print("state cleared", len(seen))


if __name__ == "__main__":
    main()
