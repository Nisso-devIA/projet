#!/usr/bin/env python3
"""Lock #📊-sondages: members vote only; staff (+ bot) can post."""
import json
import urllib.error
import urllib.request
from pathlib import Path

GUILD_ID = "867426693286461490"
CHANNEL_ID = "1542633689840877579"
DISCIPLE_ROLE = "1541249715973394473"
ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")

VIEW = 1 << 10
SEND = 1 << 11
MANAGE_MESSAGES = 1 << 13
EMBED = 1 << 14
ATTACH = 1 << 15
HISTORY = 1 << 16
ADD_REACTIONS = 1 << 6
SEND_POLLS = 1 << 49
CREATE_PUBLIC_THREADS = 1 << 35
CREATE_PRIVATE_THREADS = 1 << 36
SEND_MESSAGES_IN_THREADS = 1 << 38
USE_EXTERNAL_EMOJIS = 1 << 18
USE_EXTERNAL_STICKERS = 1 << 37
ATTACH_FILES = ATTACH
MENTION_EVERYONE = 1 << 17


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str, body=None):
    data = None
    headers = {"Authorization": f"Bot {load_token()}", "User-Agent": "ZaelrysSondageLock/1.0"}
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


def main() -> None:
    _, me = api("GET", "/users/@me")
    bot_id = me["id"]

    roles = api("GET", f"/guilds/{GUILD_ID}/roles")[1]
    staff = next((r for r in roles if r.get("name") == "⚔️ Sentinelle"), None)
    # Also treat Archonte / owner-like roles if present
    archonte = next((r for r in roles if "Archonte" in (r.get("name") or "")), None)
    print("staff", staff and staff.get("id"), staff and staff.get("name"))
    print("archonte", archonte and archonte.get("id"), archonte and archonte.get("name"))

    # Members (Disciple): see + read history + vote (no send / no create poll / no threads)
    disciple_deny = (
        SEND
        | SEND_POLLS
        | EMBED
        | ATTACH_FILES
        | ADD_REACTIONS
        | CREATE_PUBLIC_THREADS
        | CREATE_PRIVATE_THREADS
        | SEND_MESSAGES_IN_THREADS
        | MENTION_EVERYONE
        | USE_EXTERNAL_EMOJIS
        | USE_EXTERNAL_STICKERS
    )
    disciple_allow = VIEW | HISTORY

    staff_allow = (
        VIEW
        | SEND
        | EMBED
        | ATTACH_FILES
        | HISTORY
        | ADD_REACTIONS
        | SEND_POLLS
        | MANAGE_MESSAGES
        | CREATE_PUBLIC_THREADS
        | SEND_MESSAGES_IN_THREADS
        | MENTION_EVERYONE
    )

    bot_allow = staff_allow

    overwrites = [
        {"id": GUILD_ID, "type": 0, "deny": str(VIEW), "allow": "0"},
        {
            "id": DISCIPLE_ROLE,
            "type": 0,
            "allow": str(disciple_allow),
            "deny": str(disciple_deny),
        },
        {
            "id": bot_id,
            "type": 1,
            "allow": str(bot_allow),
            "deny": "0",
        },
    ]
    if staff:
        overwrites.append(
            {"id": staff["id"], "type": 0, "allow": str(staff_allow), "deny": "0"}
        )
    if archonte:
        overwrites.append(
            {"id": archonte["id"], "type": 0, "allow": str(staff_allow), "deny": "0"}
        )

    status, ch = api(
        "PATCH",
        f"/channels/{CHANNEL_ID}",
        {
            "topic": "Sondages uniquement — votez ici, pas d’échange (staff seulement pour poster)",
            "permission_overwrites": overwrites,
            "rate_limit_per_user": 0,
        },
    )
    print("OK", status, ch.get("name"))


if __name__ == "__main__":
    main()
