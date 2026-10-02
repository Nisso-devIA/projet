#!/usr/bin/env python3
"""Post Discord live notification (embed). Skipped by orchestrator when title is offline."""
import json
import os
import sys
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
    title = os.environ.get("DISCORD_LIVE_TITLE", "").strip() or "Live"
    game = os.environ.get("DISCORD_LIVE_GAME", "").strip() or "Jeu non spécifié"
    login = os.environ.get("TWITCH_LOGIN", "zaeldryk")

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
                STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                STATE_FILE.write_text(
                    json.dumps(
                        {"channel_id": channel_id, "message_id": message_id},
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Discord HTTP {e.code}: {err}") from e


if __name__ == "__main__":
    main()
