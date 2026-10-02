#!/usr/bin/env python3
"""Create #📊-sondages in COMMUNAUTÉ and move GTA VI poll there."""
import json
import urllib.error
import urllib.request
from pathlib import Path

GUILD_ID = 867426693286461490
CHANNEL_NAME = "📊-sondages"
TOPIC = "Sondages de la communauté Zaeldryk"
CATEGORY_COMMUNAUTE = "1541249728879267912"
GENERAL_ID = "1541249730024186017"
GTA_POLL_MSG = "1542632692158435418"
DISCIPLE_ROLE = "1541249715973394473"

env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method, path, body=None):
    data = None
    headers = {"Authorization": f"Bot {token}", "User-Agent": "ZaelrysSondage/1.0"}
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


_, channels = api("GET", f"/guilds/{GUILD_ID}/channels")
existing = next(
    (
        c
        for c in channels
        if c.get("type") == 0
        and (c.get("name") or "") in (CHANNEL_NAME, "sondage", "sondages", "📊-sondage")
    ),
    None,
)

_, me = api("GET", "/users/@me")
bot_id = me["id"]
print("bot_id", bot_id)

VIEW = 1 << 10
SEND = 1 << 11
MANAGE_MESSAGES = 1 << 13
EMBED = 1 << 14
ATTACH = 1 << 15
HISTORY = 1 << 16
ADD_REACTIONS = 1 << 6
SEND_POLLS = 1 << 49
disciple_allow = VIEW | SEND | EMBED | ATTACH | HISTORY | ADD_REACTIONS | SEND_POLLS

overwrite = [
    {"id": str(GUILD_ID), "type": 0, "deny": str(VIEW), "allow": "0"},
    {"id": DISCIPLE_ROLE, "type": 0, "allow": str(disciple_allow), "deny": "0"},
    {
        "id": bot_id,
        "type": 1,
        "allow": str(
            VIEW | SEND | EMBED | ATTACH | HISTORY | ADD_REACTIONS | SEND_POLLS | MANAGE_MESSAGES
        ),
        "deny": "0",
    },
]

if existing:
    ch_id = existing["id"]
    api(
        "PATCH",
        f"/channels/{ch_id}",
        {
            "name": CHANNEL_NAME,
            "topic": TOPIC,
            "parent_id": CATEGORY_COMMUNAUTE,
            "permission_overwrites": overwrite,
        },
    )
    print("reuse", ch_id)
else:
    _, created = api(
        "POST",
        f"/guilds/{GUILD_ID}/channels",
        {
            "name": CHANNEL_NAME,
            "type": 0,
            "topic": TOPIC,
            "parent_id": CATEGORY_COMMUNAUTE,
            "permission_overwrites": overwrite,
        },
    )
    ch_id = created["id"]
    print("created", ch_id)

# Intro message
api(
    "POST",
    f"/channels/{ch_id}/messages",
    {
        "content": (
            "📊 **Salon sondages**\n"
            "Les votes et questions de la communauté arrivent ici.\n"
            "_Un choix par sondage — merci de participer._"
        )
    },
)

# Move GTA poll: delete from général, recreate here
try:
    api("DELETE", f"/channels/{GENERAL_ID}/messages/{GTA_POLL_MSG}")
    print("deleted_old_poll", GTA_POLL_MSG)
except SystemExit as e:
    print("delete_old_poll_skip", e)

_, poll_msg = api(
    "POST",
    f"/channels/{ch_id}/messages",
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
print("poll_posted", poll_msg.get("id"), "channel", ch_id)
print("CHANNEL_ID", ch_id)
