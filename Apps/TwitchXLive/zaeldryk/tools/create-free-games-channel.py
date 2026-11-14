#!/usr/bin/env python3
"""Create #🎁-jeux-gratuits channel for free game announcements."""
from pathlib import Path
import json
import urllib.request
import urllib.error

GUILD_ID = 867426693286461490
CHANNEL_NAME = "🎁-jeux-gratuits"
TOPIC = "Jeux gratuits Epic, PlayStation, Xbox, Steam, GOG…"
VIEW = 1 << 10
SEND = 1 << 11
MANAGE_MESSAGES = 1 << 13
HISTORY = 1 << 16
# Same overwrites as #🔔-actualités / #📢-annonces: hidden until 🐺 Disciple.
ROLE_OVERWRITES = {
    "🐺 Disciple": (VIEW | HISTORY, 0),
    "⚔️ Sentinelle": (VIEW | SEND | MANAGE_MESSAGES, 0),
    "👑 Archonte de Zaeldryk": (VIEW | SEND, 0),
    "🌑 Ombre": (VIEW | SEND, 0),
}

env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

UA = "DiscordBot (https://zaelrys.local/free-games, 1.0)"


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
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return resp.status, json.loads(raw) if raw else None


def member_overwrites(roles):
    by_name = {role["name"]: role["id"] for role in roles}
    overwrites = [
        {"id": str(GUILD_ID), "type": 0, "allow": "0", "deny": str(VIEW)},
    ]
    for name, (allow, deny) in ROLE_OVERWRITES.items():
        role_id = by_name.get(name)
        if not role_id:
            print("missing role", name)
            continue
        overwrites.append(
            {
                "id": str(role_id),
                "type": 0,
                "allow": str(allow),
                "deny": str(deny),
            }
        )
    return overwrites


_, roles = api("GET", f"/guilds/{GUILD_ID}/roles")
overwrites = member_overwrites(roles)
_, channels = api("GET", f"/guilds/{GUILD_ID}/channels")
existing = next(
    (c for c in channels if c.get("type") == 0 and c.get("name") == CHANNEL_NAME),
    None,
)

# Same category as actualités if possible
parent_id = None
for c in channels:
    if c.get("type") == 0 and "actualit" in (c.get("name") or "").lower():
        parent_id = c.get("parent_id")
        break
if not parent_id:
    for c in channels:
        if c.get("type") == 4 and "commun" in (c.get("name") or "").lower():
            parent_id = c["id"]
            break

if existing:
    ch_id = existing["id"]
    body = {
        "name": CHANNEL_NAME,
        "topic": TOPIC,
        "permission_overwrites": overwrites,
    }
    if parent_id and not existing.get("parent_id"):
        body["parent_id"] = parent_id
    api("PATCH", f"/channels/{ch_id}", body)
    print("reuse", ch_id)
else:
    body = {
        "name": CHANNEL_NAME,
        "type": 0,
        "topic": TOPIC,
        "permission_overwrites": overwrites,
    }
    if parent_id:
        body["parent_id"] = parent_id
    _, created = api("POST", f"/guilds/{GUILD_ID}/channels", body)
    ch_id = created["id"]
    print("created", ch_id)

# Update freegames.env
fg = Path("/home/ubuntu/zaeldryk/config/freegames.env")
lines = []
if fg.exists():
    for line in fg.read_text(encoding="utf-8").splitlines(True):
        if not line.startswith("FREEGAMES_CHANNEL_ID="):
            lines.append(line)
else:
    lines = [
        "# Salon jeux gratuits (stores)\n",
        "FREEGAMES_MAX_PER_STORE=5\n",
    ]
lines.append(f"FREEGAMES_CHANNEL_ID={ch_id}\n")
fg.write_text("".join(lines), encoding="utf-8")
print("FREEGAMES_CHANNEL_ID", ch_id)

msg = {
    "content": (
        "🎁 **Salon jeux gratuits** — annonces auto :\n"
        "• **Epic Games** — chaque semaine (jeudi)\n"
        "• **PlayStation Plus** — jeux du mois\n"
        "• **GOG**, **Steam** — promos gratuites détectées\n"
        "• **Xbox Game Pass** — ajouts / promos (toutes versions) via Xbox Wire\n"
        "_Games with Gold est terminé — non surveillé._"
    )
}
api("POST", f"/channels/{ch_id}/messages", msg)
