#!/usr/bin/env python3
"""Pin official logo branding in social channels (visible when opening channel)."""
import json
import urllib.error
import urllib.request
from pathlib import Path

GUILD_ID = "867426693286461490"
ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")

CHANNELS = [
    {
        "id": "1541251095492435978",
        "emoji_id": "1542194105269092424",
        "emoji_name": "logo_twitch",
        "title": "Twitch — Zaeldryk",
        "url": "https://twitch.tv/zaeldryk",
    },
    {
        "id": "1541251096763179181",
        "emoji_id": "1542194109605748806",
        "emoji_name": "logo_youtube",
        "title": "YouTube — Zaeldryk",
        "url": "https://youtube.com/@zaeldryk",
    },
    {
        "id": "1541251097962877010",
        "emoji_id": "1542194115343556753",
        "emoji_name": "logo_x",
        "title": "X — Zaeldryk",
        "url": "https://x.com/zaeldryk",
    },
]

MARKER = "[zael-social-branding]"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str, body=None):
    token = load_token()
    data = None
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "ZaelrysSocialBrand/1.0",
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


def emoji_url(emoji_id: str) -> str:
    return f"https://cdn.discordapp.com/emojis/{emoji_id}.png?size=256&quality=lossless"


def main() -> None:
    for cfg in CHANNELS:
        ch_id = cfg["id"]
        _, pins = api("GET", f"/channels/{ch_id}/messages/pins")
        pin_list = pins if isinstance(pins, list) else []
        if any(MARKER in (m.get("content") or "") for m in pin_list if isinstance(m, dict)):
            print("skip", ch_id, "already pinned")
            continue

        embed = {
            "title": cfg["title"],
            "description": (
                f"Salon officiel **{cfg['title'].split(' — ')[0]}**.\n"
                f"🔗 {cfg['url']}\n\n"
                f"Emoji serveur : `:{cfg['emoji_name']}:`"
            ),
            "url": cfg["url"],
            "color": 0x9146FF if "Twitch" in cfg["title"] else (0xFF0000 if "YouTube" in cfg["title"] else 0x000000),
            "thumbnail": {"url": emoji_url(cfg["emoji_id"])},
        }
        _, msg = api(
            "POST",
            f"/channels/{ch_id}/messages",
            {"content": f"{MARKER}\u200b", "embeds": [embed]},
        )
        api("PUT", f"/channels/{ch_id}/pins/{msg['id']}")
        print("pinned", ch_id, msg["id"])


if __name__ == "__main__":
    main()
