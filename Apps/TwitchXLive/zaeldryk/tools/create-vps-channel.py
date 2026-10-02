#!/usr/bin/env python3
"""Create a private VPS alerts channel visible only to guild owner + bot."""
from pathlib import Path
import json
import urllib.request
import urllib.error

GUILD_ID = 867426693286461490
CHANNEL_NAME = "🖥️-vps"
TOPIC = "Alertes services VPS Zaelrys (privé)"

env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

UA = "DiscordBot (https://zaelrys.local/watchdog, 1.0)"


def api(method, path, body=None):
    data = None
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": UA,
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
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


# Guild owner
_, guild = api("GET", f"/guilds/{GUILD_ID}")
owner_id = guild["owner_id"]
print("owner_id", owner_id)

# Bot user
_, me = api("GET", "/users/@me")
bot_id = me["id"]
print("bot_id", bot_id)

# Existing channels — reuse if already present
_, channels = api("GET", f"/guilds/{GUILD_ID}/channels")
existing = next(
    (c for c in channels if c.get("type") == 0 and c.get("name") in (CHANNEL_NAME, "vps", "🖥️-vps")),
    None,
)

# Find a sensible parent category (prefer staff/admin-like, else none)
category_id = None
for c in channels:
    if c.get("type") == 4:
        n = (c.get("name") or "").lower()
        if any(x in n for x in ("staff", "modo", "admin", "logs", "équipe", "equipe", "privé", "prive")):
            category_id = c["id"]
            print("category", c["id"], c.get("name"))
            break

overwrite = [
    {
        "id": str(GUILD_ID),  # @everyone
        "type": 0,
        "deny": str(1 << 10),  # VIEW_CHANNEL
        "allow": "0",
    },
    {
        "id": str(owner_id),
        "type": 1,  # member
        "allow": str((1 << 10) | (1 << 11) | (1 << 14)),  # VIEW + SEND + READ_HISTORY? SEND=1<<11, READ_MESSAGE_HISTORY=1<<16
        "deny": "0",
    },
    {
        "id": str(bot_id),
        "type": 1,
        "allow": str((1 << 10) | (1 << 11) | (1 << 14) | (1 << 16)),  # VIEW SEND EMBED HISTORY
        "deny": "0",
    },
]
# Fix owner allow: VIEW(10) SEND(11) EMBED(14) ATTACH(15) HISTORY(16)
overwrite[1]["allow"] = str((1 << 10) | (1 << 11) | (1 << 14) | (1 << 15) | (1 << 16))

if existing:
    ch_id = existing["id"]
    print("reuse_channel", ch_id, existing.get("name"))
    api(
        "PATCH",
        f"/channels/{ch_id}",
        {
            "name": CHANNEL_NAME,
            "topic": TOPIC,
            "permission_overwrites": overwrite,
            **({"parent_id": category_id} if category_id and not existing.get("parent_id") else {}),
        },
    )
else:
    body = {
        "name": CHANNEL_NAME,
        "type": 0,
        "topic": TOPIC,
        "permission_overwrites": overwrite,
    }
    if category_id:
        body["parent_id"] = category_id
    _, created = api("POST", f"/guilds/{GUILD_ID}/channels", body)
    ch_id = created["id"]
    print("created_channel", ch_id, created.get("name"))

# Update discord.env
lines = env.read_text(encoding="utf-8").splitlines(True)
out = []
found = False
for line in lines:
    if line.startswith("DISCORD_ALERT_CHANNEL_ID="):
        out.append(f"DISCORD_ALERT_CHANNEL_ID={ch_id}\n")
        found = True
    else:
        out.append(line)
if not found:
    out.append(f"\nDISCORD_ALERT_CHANNEL_ID={ch_id}\n")
env.write_text("".join(out), encoding="utf-8")
print("updated discord.env")

# Confirmation message
msg = {
    "content": (
        f"🔒 Salon **VPS** prêt — visible uniquement pour toi + le bot.\n"
        f"Les alertes services (`zaeldryk-live`, `zaeldryk-discord`, `twitch-offline`) arrivent ici."
    )
}
status, posted = api("POST", f"/channels/{ch_id}/messages", msg)
print("confirm_msg", status, posted.get("id"))
print("CHANNEL_ID", ch_id)
