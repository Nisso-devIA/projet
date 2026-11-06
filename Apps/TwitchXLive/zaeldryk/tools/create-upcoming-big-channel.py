#!/usr/bin/env python3
"""Create private #sorties-big — owner + bot only (pas Sentinelle)."""
from pathlib import Path
import json
import urllib.request
import urllib.error

GUILD_ID = 867426693286461490
CHANNEL_NAME = "sorties-big"
TOPIC = "Alertes sorties Switch 2 / PS5 — gros titres style Zelda / Odyssey / Witcher (privé owner)"
OUT = Path("/tmp/upcoming-big-channel-id.txt")
ENV_DISCORD = Path("/home/ubuntu/zaeldryk/config/discord.env")
ENV_OUT = Path("/home/ubuntu/zaeldryk/config/upcoming-big.env")

token = None
for line in ENV_DISCORD.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

UA = "ZaelUpcomingBig/1.0"
VIEW = 1 << 10
SEND = 1 << 11
EMBED = 1 << 14
ATTACH = 1 << 15
HISTORY = 1 << 16
ALLOW = VIEW | SEND | EMBED | ATTACH | HISTORY


def api(method, path, body=None):
    data = None
    headers = {"Authorization": f"Bot {token}", "User-Agent": UA}
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
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


guild = api("GET", f"/guilds/{GUILD_ID}")
owner_id = guild["owner_id"]
me = api("GET", "/users/@me")
bot_id = me["id"]
print("owner", owner_id, "bot", bot_id)

channels = api("GET", f"/guilds/{GUILD_ID}/channels")
existing = next(
    (
        c
        for c in channels
        if c.get("type") == 0
        and c.get("name") in (CHANNEL_NAME, "🎮-sorties-big", "sorties-aaa")
    ),
    None,
)

category_id = None
for c in channels:
    if c.get("type") == 4:
        n = (c.get("name") or "").lower()
        if any(x in n for x in ("staff", "modo", "admin", "privé", "prive", "équipe", "equipe", "vps")):
            category_id = c["id"]
            break

overwrite = [
    {"id": str(GUILD_ID), "type": 0, "deny": str(VIEW), "allow": "0"},
    {"id": str(owner_id), "type": 1, "allow": str(ALLOW), "deny": "0"},
    {"id": str(bot_id), "type": 1, "allow": str(ALLOW), "deny": "0"},
]

if existing:
    ch_id = existing["id"]
    body = {
        "name": CHANNEL_NAME,
        "topic": TOPIC,
        "permission_overwrites": overwrite,
    }
    if category_id and not existing.get("parent_id"):
        body["parent_id"] = category_id
    api("PATCH", f"/channels/{ch_id}", body)
    print("reuse", ch_id)
else:
    body = {
        "name": CHANNEL_NAME,
        "type": 0,
        "topic": TOPIC,
        "permission_overwrites": overwrite,
    }
    if category_id:
        body["parent_id"] = category_id
    created = api("POST", f"/guilds/{GUILD_ID}/channels", body)
    ch_id = created["id"]
    print("created", ch_id)

OUT.write_text(str(ch_id) + "\n", encoding="utf-8")
ENV_OUT.parent.mkdir(parents=True, exist_ok=True)
ENV_OUT.write_text(
    f"DISCORD_UPCOMING_BIG_CHANNEL_ID={ch_id}\n"
    f"STATE_FILE=/home/ubuntu/zaeldryk/state/upcoming-big.json\n",
    encoding="utf-8",
)
ENV_OUT.chmod(0o600)
print("wrote", ENV_OUT)

api(
    "POST",
    f"/channels/{ch_id}/messages",
    {
        "content": (
            "🔒 Salon **sorties-big** — visible **toi + bot** uniquement.\n"
            "Alertes : sorties / annonces **Switch 2** & **PS5** dans le style "
            "Zelda / Odyssey / Witcher / Bananza…\n"
            "Ensuite : **nouveautés seulement**."
        )
    },
)
print("ok", ch_id)
