#!/usr/bin/env python3
"""Post Discord live notification (embed). Skipped by orchestrator when title is offline."""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
LIVE_ENV = ZAEL_ROOT / "config" / "live.env"
STATE_FILE = ZAEL_ROOT / "state" / "last_discord_live_message.json"
API = "https://discord.com/api/v10"


DEDUPE_WINDOW = timedelta(minutes=10)
LIVE_TITLE_MARK = "est en LIVE"


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


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp


def message_ids(state: dict) -> list[str]:
    found: list[str] = []
    for raw in state.get("message_ids") or []:
        mid = str(raw or "").strip()
        if mid and mid not in found:
            found.append(mid)
    legacy = str(state.get("message_id") or "").strip()
    if legacy and legacy not in found:
        found.append(legacy)
    return found


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    data["message_ids"] = message_ids(data)
    if data["message_ids"]:
        data["message_id"] = data["message_ids"][-1]
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ids = message_ids(state)
    payload = {
        "channel_id": state.get("channel_id") or "",
        "message_id": ids[-1] if ids else "",
        "message_ids": ids,
        "stream_id": state.get("stream_id") or "",
        "started_at": state.get("started_at") or "",
        "posted_at": state.get("posted_at") or "",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def already_announced(state: dict, stream_id: str, started_at: str, now: datetime) -> bool:
    """True when this live session already has an announcement."""
    if not message_ids(state):
        return False
    if stream_id and state.get("stream_id") == stream_id:
        return True
    if started_at and state.get("started_at") == started_at:
        return True
    if stream_id or started_at:
        return False
    posted = parse_time(str(state.get("posted_at") or ""))
    return bool(posted and now - posted < DEDUPE_WINDOW)


def remember_message(
    state: dict,
    *,
    channel_id: str,
    message_id: str,
    stream_id: str,
    started_at: str,
    posted_at: str,
) -> dict:
    ids = message_ids(state)
    if message_id and message_id not in ids:
        ids.append(message_id)
    state["channel_id"] = channel_id
    state["message_ids"] = ids
    state["message_id"] = ids[-1] if ids else ""
    if stream_id:
        state["stream_id"] = stream_id
    if started_at:
        state["started_at"] = started_at
    state["posted_at"] = posted_at
    return state


def is_own_live_embed(message: dict, bot_id: str) -> bool:
    author = message.get("author") or {}
    if str(author.get("id") or "") != str(bot_id) or not author.get("bot"):
        return False
    if message.get("webhook_id"):
        return False
    for embed in message.get("embeds") or []:
        if LIVE_TITLE_MARK in str(embed.get("title") or ""):
            return True
    return False


def main() -> None:
    title = os.environ.get("DISCORD_LIVE_TITLE", "").strip() or "Live"
    game = os.environ.get("DISCORD_LIVE_GAME", "").strip() or "Jeu non spécifié"
    login = os.environ.get("TWITCH_LOGIN", "zaeldryk")
    stream_id = os.environ.get("DISCORD_LIVE_STREAM_ID", "").strip()
    started_at = os.environ.get("DISCORD_LIVE_STARTED_AT", "").strip()
    now = datetime.now(timezone.utc)
    state = load_state(STATE_FILE)
    if already_announced(state, stream_id, started_at, now):
        print("skip duplicate live announcement", stream_id or started_at or "recent")
        return

    cfg = {**load_env(DISCORD_ENV), **load_env(LIVE_ENV)}
    token = cfg.get("DISCORD_BOT_TOKEN")
    channel_id = cfg.get("DISCORD_LIVE_CHANNEL_ID")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN missing")
    if not channel_id:
        raise SystemExit("DISCORD_LIVE_CHANNEL_ID missing in live.env")

    twitch_url = f"https://www.twitch.tv/{login}"
    thumb = f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{login.lower()}-440x248.jpg"

    ping = (cfg.get("DISCORD_LIVE_PING") or "everyone").lower()
    content = ""
    allowed: dict = {"parse": []}
    if ping == "everyone":
        content = "@everyone"
        allowed["parse"] = ["everyone"]
    elif ping == "here":
        content = "@here"
        allowed["parse"] = ["everyone"]  # @here uses everyone parse bucket
    elif ping.startswith("<@&") and ping.endswith(">"):
        content = ping

    embed = {
        "title": "🔴 Zaeldryk est en LIVE !",
        "description": title,
        "url": twitch_url,
        "color": 0x9146FF,
        "fields": [{"name": "Jeu", "value": game, "inline": True}],
        "image": {"url": thumb},
        "footer": {"text": "La communauté Zaelrys"},
    }

    payload = {"embeds": [embed]}
    if content:
        payload["content"] = content
        payload["allowed_mentions"] = allowed

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API}/channels/{channel_id}/messages",
        data=data,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "ZaelrysLiveAnnounce/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            message_id = body.get("id")
            print("posted", message_id, "channel", channel_id)
            if message_id:
                remember_message(
                    state,
                    channel_id=channel_id,
                    message_id=str(message_id),
                    stream_id=stream_id,
                    started_at=started_at,
                    posted_at=now.isoformat(),
                )
                save_state(STATE_FILE, state)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Discord HTTP {e.code}: {err}") from e


if __name__ == "__main__":
    main()
