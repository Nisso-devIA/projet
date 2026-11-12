#!/usr/bin/env python3
"""Raid Twitch automatique vers la tranche 23h-00h du planning RTF.

Lecture Discord en lecture seule. Aucun message Discord. Le POST /raids
n'est fait que si RTF_RAID_ENABLED=1 et RTF_RAID_DRY_RUN=0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
TWITCH_ENV = ROOT / "config" / "twitch.env"
RAID_ENV = ROOT / "config" / "rtf-raid.env"
DISCORD_USER_ENV = Path(
    os.environ.get("RTF_DISCORD_ENV", "/home/ubuntu/autobump/bump.env")
)
MAP_PATH = Path(os.environ.get("RTF_MAP", ROOT / "config" / "rtf-twitch-map.json"))
STATE_PATH = ROOT / "state" / "rtf-raid.json"
LOG_PATH = ROOT / "logs" / "rtf-raid.log"
TOKEN_FILE = Path(os.environ.get("TWITCH_TOKEN_FILE", "/home/ubuntu/twitch_token.txt"))
BROADCASTER_ID = "426411773"
FROM_LOGIN = "zaeldryk"
GUILD_ID = "935417890654547989"

DAYS = {
    0: ("lundi", "935435092732551168"),
    1: ("mardi", "935435128803573810"),
    2: ("mercredi", "935435168859189258"),
    3: ("jeudi", "935435201029505054"),
    4: ("vendredi", "935435251797344316"),
    5: ("samedi", "1462488655690993714"),
    6: ("dimanche", "935435311377416232"),
}

SLOT_RE = re.compile(r"(\d{1,2})\s*h\s*[-–]\s*(\d{1,2})\s*h", re.IGNORECASE)
MENTION_RE = re.compile(r"<@!?(\d+)>")
RAID_SCOPE = "channel:manage:raids"
KEEP_SCOPES = [
    "chat:read",
    "chat:edit",
    "channel:manage:broadcast",
    "channel:manage:videos",
    "moderator:manage:chat_messages",
    "moderator:read:followers",
    "user:write:chat",
    RAID_SCOPE,
]


def log(message: str) -> None:
    stamp = datetime.now(PARIS).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} Europe/Paris {message}"
    print(line)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def enabled() -> bool:
    return load_env(RAID_ENV).get("RTF_RAID_ENABLED", "0") == "1"


def dry_run(forced: bool = False) -> bool:
    if forced:
        return True
    return load_env(RAID_ENV).get("RTF_RAID_DRY_RUN", "1") != "0"


def load_map() -> dict:
    if not MAP_PATH.exists():
        return {}
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return {str(key): str(value).strip().lower() for key, value in data.items()}


def is_grid(content: str) -> bool:
    return len(SLOT_RE.findall(content or "")) >= 3


def slot_line(content: str, start_hour: int = 23, end_hour: int = 0) -> str | None:
    for line in (content or "").splitlines():
        match = SLOT_RE.search(line)
        if not match:
            continue
        if int(match.group(1)) == start_hour and int(match.group(2)) == end_hour:
            return line
    return None


def user_on_line(line: str | None) -> str | None:
    if not line:
        return None
    if "annulation" in line.lower():
        return None
    found = MENTION_RE.findall(line)
    return found[-1] if found else None


def parse_target(messages: list[dict]) -> str | None:
    """Discord user id for 23h-00h, after the latest grid and later corrections."""
    ordered = sorted(messages, key=lambda item: item.get("timestamp") or "")
    grids = [item for item in ordered if is_grid(item.get("content") or "")]
    if not grids:
        return None
    grid = grids[-1]
    target = user_on_line(slot_line(grid.get("content") or ""))
    for item in ordered:
        if (item.get("timestamp") or "") <= (grid.get("timestamp") or ""):
            continue
        content = item.get("content") or ""
        line = slot_line(content)
        if line is None:
            continue
        if "annulation" in content.lower() or "annulation" in line.lower():
            target = None
            continue
        target = user_on_line(line)
    return target


def discord_headers(token: str) -> dict:
    return {
        "Authorization": token,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    }


def http_json(method: str, url: str, headers: dict, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:180]
        return exc.code, detail


def read_day_messages(token: str, channel_id: str) -> list[dict]:
    status, payload = http_json(
        "GET",
        f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=15",
        discord_headers(token),
    )
    if status != 200 or not isinstance(payload, list):
        raise RuntimeError(f"lecture planning HTTP {status}")
    return payload


def twitch_token() -> str:
    raw = TOKEN_FILE.read_text(encoding="utf-8").strip().replace("oauth:", "")
    return raw.splitlines()[0].strip()


def client_id() -> str:
    return load_env(TWITCH_ENV).get("TWITCH_CLIENT_ID", "")


def validate_token() -> dict:
    status, payload = http_json(
        "GET",
        "https://id.twitch.tv/oauth2/validate",
        {"Authorization": "OAuth " + twitch_token()},
    )
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"jeton Twitch HTTP {status}")
    return payload


def has_raid_scope(payload: dict | None = None) -> bool:
    data = payload if payload is not None else validate_token()
    return RAID_SCOPE in (data.get("scopes") or [])


def authorize_url() -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id(),
            "redirect_uri": "http://localhost:17563/callback",
            "response_type": "code",
            "scope": " ".join(KEEP_SCOPES),
        }
    )
    return "https://id.twitch.tv/oauth2/authorize?" + query


def helix(method: str, path: str, query: dict | None = None):
    url = "https://api.twitch.tv/helix" + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    return http_json(
        method,
        url,
        {
            "Client-ID": client_id(),
            "Authorization": "Bearer " + twitch_token(),
        },
    )


def stream_live(login: str) -> bool:
    status, payload = helix("GET", "/streams", {"user_login": login})
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"streams HTTP {status}")
    return bool(payload.get("data"))


def user_id_for_login(login: str) -> str | None:
    status, payload = helix("GET", "/users", {"login": login})
    if status != 200 or not isinstance(payload, dict):
        return None
    rows = payload.get("data") or []
    if not rows:
        return None
    return str(rows[0].get("id") or "") or None


def login_from_profile(token: str, discord_id: str) -> str | None:
    status, payload = http_json(
        "GET",
        f"https://discord.com/api/v10/users/{discord_id}/profile?guild_id={GUILD_ID}",
        discord_headers(token),
    )
    if status != 200 or not isinstance(payload, dict):
        return None
    user = payload.get("user") or {}
    accounts = user.get("connected_accounts") or payload.get("connected_accounts") or []
    for account in accounts:
        if str(account.get("type") or "").lower() == "twitch" and account.get("name"):
            return str(account["name"]).lower()
    return None


def resolve_login(token: str, discord_id: str, mention_name: str = "") -> tuple[str | None, str]:
    mapped = load_map().get(discord_id)
    if mapped:
        return mapped, "table"
    try:
        connected = login_from_profile(token, discord_id)
    except Exception:
        connected = None
    if connected and user_id_for_login(connected):
        return connected, "connexion"
    guess = (mention_name or "").strip().lower()
    if guess and user_id_for_login(guess):
        return guess, "pseudo"
    return None, "inconnu"


def mention_name(messages: list[dict], discord_id: str) -> str:
    for item in messages:
        for person in item.get("mentions") or []:
            if str(person.get("id")) == discord_id:
                return person.get("username") or ""
    return ""


def prepare(token: str, when: datetime | None = None) -> dict:
    moment = when or datetime.now(PARIS)
    day_name, channel_id = DAYS[moment.weekday()]
    messages = read_day_messages(token, channel_id)
    discord_id = parse_target(messages)
    login, source = (None, "vide")
    if discord_id:
        login, source = resolve_login(token, discord_id, mention_name(messages, discord_id))
    state = {
        "date": moment.date().isoformat(),
        "day": day_name,
        "channel_id": channel_id,
        "discord_id": discord_id,
        "twitch_login": login,
        "source": source,
        "prepared_at": moment.isoformat(),
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(STATE_PATH, 0o600)
    if not discord_id:
        log(f"prepare {day_name}: tranche 23h-00h vide, pas de raid")
    elif not login:
        log(f"prepare {day_name}: discord {discord_id} sans login Twitch, pas de raid")
    else:
        log(f"prepare {day_name}: cible {login} ({source})")
    return state


def start_raid(to_id: str) -> tuple[int, str]:
    status, payload = helix(
        "POST",
        "/raids",
        {"from_broadcaster_id": BROADCASTER_ID, "to_broadcaster_id": to_id},
    )
    if isinstance(payload, dict):
        return status, "ok" if status in (200, 202) else "refus"
    return status, "refus"


def fire(token: str, forced_dry: bool = False) -> int:
    state_path_data = prepare(token)
    login = state_path_data.get("twitch_login")
    if not login:
        log("pas de cible, pas de raid")
        return 0
    zael_live = stream_live(FROM_LOGIN)
    target_live = stream_live(login)
    if not zael_live:
        log(f"zaeldryk hors live, pas de raid vers {login}")
        return 0
    if not target_live:
        log(f"{login} hors live, pas de raid")
        return 0
    armed = enabled() and has_raid_scope() and not dry_run(forced_dry)
    if not armed:
        reason = "dry-run"
        if not enabled():
            reason = "désactivé"
        elif not has_raid_scope():
            reason = "scope manquant"
        log(f"{reason} : raid zaeldryk -> {login} non envoyé")
        return 0
    to_id = user_id_for_login(login)
    if not to_id:
        log(f"{login} introuvable sur Twitch, pas de raid")
        return 0
    status, _ = start_raid(to_id)
    log(f"raid zaeldryk -> {login} HTTP {status}")
    return 0 if status in (200, 202) else 1


def due(kind: str, moment: datetime) -> bool:
    """True only at 22:50 or 23:00 Europe/Paris, whichever the timer asked for."""
    if kind == "prepare":
        return moment.hour == 22 and moment.minute in (49, 50, 51)
    return moment.hour == 23 and moment.minute in (0, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--fire", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    now = datetime.now(PARIS)
    if not args.dry_run:
        if args.prepare and not due("prepare", now):
            return 0
        if args.fire and not due("fire", now):
            return 0
    token = load_env(DISCORD_USER_ENV).get("DISCORD_USER_TOKEN", "")
    if not token:
        log("DISCORD_USER_TOKEN absent, arrêt")
        return 1
    if args.prepare or not args.fire:
        prepare(token)
    if args.fire or args.dry_run:
        return fire(token, forced_dry=args.dry_run or not args.fire)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
