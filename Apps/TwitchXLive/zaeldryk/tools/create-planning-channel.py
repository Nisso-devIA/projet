#!/usr/bin/env python3
"""Salon #📅-planning — lecture seule (Disciple), bot + owner peuvent écrire."""
import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

GUILD_ID = 867426693286461490
CHANNEL_NAME = "📅-planning"
TOPIC = "Planning des lives Zaeldryk — lecture seule"
CATEGORY_COMMUNAUTE = "1541249728879267912"
DISCIPLE_ROLE = "1541249715973394473"
PARIS = ZoneInfo("Europe/Paris")

VIEW = 1 << 10
SEND = 1 << 11
MANAGE = 1 << 13
EMBED = 1 << 14
HISTORY = 1 << 16
THREADS = 1 << 35
THREAD_SEND = 1 << 38

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
    headers = {"Authorization": f"Bot {token}", "User-Agent": "ZaelrysPlanning/1.0"}
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

channels = api("GET", f"/guilds/{GUILD_ID}/channels")
existing = next(
    (
        c
        for c in channels
        if c.get("type") == 0 and c.get("name") in (CHANNEL_NAME, "planning", "📅-planning-lives")
    ),
    None,
)

read_only_deny = SEND | THREADS | THREAD_SEND
overwrite = [
    {"id": str(GUILD_ID), "type": 0, "deny": str(VIEW), "allow": "0"},
    {
        "id": DISCIPLE_ROLE,
        "type": 0,
        "allow": str(VIEW | HISTORY),
        "deny": str(read_only_deny),
    },
    {
        "id": str(owner_id),
        "type": 1,
        "allow": str(VIEW | HISTORY | SEND | EMBED | MANAGE),
        "deny": "0",
    },
    {
        "id": str(bot_id),
        "type": 1,
        "allow": str(VIEW | HISTORY | SEND | EMBED | MANAGE),
        "deny": "0",
    },
]

body = {
    "name": CHANNEL_NAME,
    "topic": TOPIC,
    "parent_id": CATEGORY_COMMUNAUTE,
    "permission_overwrites": overwrite,
}
if existing:
    ch_id = existing["id"]
    api("PATCH", f"/channels/{ch_id}", body)
    print("reuse", ch_id)
else:
    created = api("POST", f"/guilds/{GUILD_ID}/channels", {**body, "type": 0})
    ch_id = created["id"]
    print("created", ch_id)

def fetch_segments():
    cfg = {}
    for line in Path("/home/ubuntu/zaeldryk/config/twitch.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    token = Path(cfg.get("TWITCH_TOKEN_FILE", "/home/ubuntu/twitch_token.txt")).read_text(encoding="utf-8").strip()
    url = (
        "https://api.twitch.tv/helix/schedule?broadcaster_id="
        + cfg.get("TWITCH_BROADCASTER_ID", "426411773")
        + "&first=25"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Client-ID": cfg["TWITCH_CLIENT_ID"],
            "Authorization": f"Bearer {token}",
            "User-Agent": "ZaelrysPlanning/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    out = []
    for seg in (payload.get("data") or {}).get("segments") or []:
        if seg.get("cancelled_until") or not seg.get("start_time"):
            continue
        out.append(
            {
                "title": (seg.get("title") or "Live Zaeldryk").strip(),
                "game": (seg.get("category") or {}).get("name") or "",
                "start_time": seg["start_time"],
                "end_time": seg.get("end_time") or seg["start_time"],
                "is_recurring": bool(seg.get("is_recurring")),
            }
        )
    return out


segments = []
try:
    segments = fetch_segments()
except Exception as e:
    print("schedule fetch skip", e)

lines = [
    "📅 **Planning des lives**",
    "Salon en **lecture seule**. Les créneaux viennent du planning Twitch.",
    "",
]
if not segments:
    lines.append("_Aucun créneau pour l’instant._")
else:
    for seg in segments:
        start = datetime.fromisoformat(seg["start_time"].replace("Z", "+00:00")).astimezone(PARIS)
        end = datetime.fromisoformat(seg["end_time"].replace("Z", "+00:00")).astimezone(PARIS)
        days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        months = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre",
        ]
        when = f"{days[start.weekday()]} {start.day} {months[start.month - 1]} · {start.strftime('%Hh%M')}"
        if end.date() == start.date():
            when += f"–{end.strftime('%Hh%M')}"
        recur = " · chaque semaine" if seg.get("is_recurring") else ""
        lines.append(f"• **{seg['title']}** — {when}{recur}")
        if seg.get("game") and seg["game"] != "Non spécifié":
            lines.append(f"  {seg['game']}")
lines.append("")
lines.append("👉 https://twitch.tv/zaeldryk")

msg = api(
    "POST",
    f"/channels/{ch_id}/messages",
    {"content": "\n".join(lines)[:2000]},
)
try:
    api("PUT", f"/channels/{ch_id}/pins/{msg['id']}")
except Exception as e:
    print("pin skip", e)

sched = Path("/home/ubuntu/zaeldryk/config/schedule.env")
text = sched.read_text(encoding="utf-8") if sched.exists() else ""
kept = [ln for ln in text.splitlines() if not ln.startswith("PLANNING_CHANNEL_ID=")]
kept.append(f"PLANNING_CHANNEL_ID={ch_id}")
sched.write_text("\n".join(kept).strip() + "\n", encoding="utf-8")
sched.chmod(0o600)
print("channel", ch_id, "segments", len(segments))
