#!/usr/bin/env python3
"""Create private #deals-ps — owner + role Sentinelle + bot only."""
from pathlib import Path
import json
import urllib.request
import urllib.error

GUILD_ID = 867426693286461490
CHANNEL_NAME = "deals-ps"
TOPIC = "Alertes prix bas DualSense + cartes PSN (FR) — privé owner/Sentinelle"
OUT = Path("/tmp/deals-ps-channel-id.txt")
ENV_DISCORD = Path("/home/ubuntu/zaeldryk/config/discord.env")
ENV_DEALS = Path("/home/ubuntu/zaeldryk/config/deals-ps.env")

token = None
for line in ENV_DISCORD.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

UA = "ZaelDealsPS/1.0"
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
roles = api("GET", f"/guilds/{GUILD_ID}/roles")
staff = next((r for r in roles if r.get("name") == "⚔️ Sentinelle"), None)
if not staff:
    raise SystemExit("role ⚔️ Sentinelle not found")
staff_id = staff["id"]
print("owner", owner_id, "bot", bot_id, "staff", staff_id)

channels = api("GET", f"/guilds/{GUILD_ID}/channels")
existing = next(
    (c for c in channels if c.get("type") == 0 and c.get("name") in (CHANNEL_NAME, "💰-deals-ps")),
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
    {"id": str(staff_id), "type": 0, "allow": str(ALLOW), "deny": "0"},
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

OUT.write_text(ch_id + "\n", encoding="utf-8")
ENV_DEALS.parent.mkdir(parents=True, exist_ok=True)
ENV_DEALS.write_text(
    f"DISCORD_BOT_TOKEN={token}\n"
    f"DISCORD_DEALS_PS_CHANNEL_ID={ch_id}\n"
    f"STATE_FILE=/home/ubuntu/zaeldryk/state/deals-ps-fr.json\n"
    f"FETCH_MODE=jina\n",
    encoding="utf-8",
)
ENV_DEALS.chmod(0o600)
print("wrote", ENV_DEALS)

api(
    "POST",
    f"/channels/{ch_id}/messages",
    {
        "content": (
            "🔒 Salon **deals-ps** — visible pour owner + **⚔️ Sentinelle** + bot.\n"
            "Alertes **uniquement** sur nouveau prix bas : DualSense (tous modèles) + cartes PSN (tous montants).\n"
            "Sources : comparateurs FR (Idealo / Ledenicheur) via Jina."
        )
    },
)
print("CHANNEL_ID", ch_id)
