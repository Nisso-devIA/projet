#!/usr/bin/env python3
"""Annonce les copains Twitch dans #𝕋-twitch, au format du live Zaeldryk.

Le premier passage enregistre les lives déjà en cours sans rien poster.
Les suivants annoncent seulement un nouveau live. Pas de @everyone.
"""

from __future__ import annotations

import fcntl
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
LIST_PATH = Path(os.environ.get("COPAINS_LIST", Path(__file__).resolve().with_name("copains-live.json")))
STATE_PATH = ZAEL_ROOT / "state" / "copains-live.json"
LOCK_PATH = ZAEL_ROOT / "state" / "copains-live.lock"
LIVE_ENV = ZAEL_ROOT / "config" / "live.env"
TWITCH_ENV = ZAEL_ROOT / "config" / "twitch.env"
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
API = "https://discord.com/api/v10"


def load_env(path: Path) -> dict:
    cfg = {}
    if not path.exists():
        return cfg
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cfg[key.strip()] = value.strip().strip('"').strip("'")
    return cfg


def load_list(path: Path = LIST_PATH) -> tuple[str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    channel_id = str(data.get("channel_id") or "").strip()
    logins = []
    for raw in data.get("logins") or []:
        login = str(raw or "").strip().lstrip("@").lower()
        if login and login not in logins:
            logins.append(login)
    if not channel_id or not logins:
        raise SystemExit("liste copains incomplète")
    return channel_id, logins


def load_state(path: Path = STATE_PATH) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def plan(first_run: bool, previous_id: str, stream_id: str) -> str:
    """seed, post, skip, or offline. Le premier passage ne poste jamais."""
    if first_run:
        return "seed"
    if not stream_id:
        return "offline"
    if stream_id == previous_id:
        return "skip"
    return "post"


def friend_embed(display: str, login: str, title: str, game: str) -> dict:
    return {
        "title": f"🔴 {display} est en LIVE !",
        "description": title or "Live",
        "url": f"https://www.twitch.tv/{login}",
        "color": 0x9146FF,
        "fields": [{"name": "Jeu", "value": game or "Jeu non spécifié", "inline": True}],
        "image": {"url": f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{login}-440x248.jpg"},
        "footer": {"text": "La communauté Zaelrys"},
    }


def app_token(client_id: str, secret: str) -> str:
    form = urllib.parse.urlencode(
        {"client_id": client_id, "client_secret": secret, "grant_type": "client_credentials"}
    ).encode()
    request = urllib.request.Request("https://id.twitch.tv/oauth2/token", data=form, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    token = str(payload.get("access_token") or "")
    if not token:
        raise SystemExit("jeton Twitch absent")
    return token


def helix(client_id: str, token: str, path: str, query: list[tuple[str, str]]) -> dict:
    url = "https://api.twitch.tv/helix" + path + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url,
        headers={"Client-ID": client_id, "Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Helix HTTP {exc.code}") from exc


def twitch_rows(client_id: str, token: str, logins: list[str]) -> tuple[dict, dict]:
    users = helix(client_id, token, "/users", [("login", login) for login in logins])
    streams = helix(client_id, token, "/streams", [("user_login", login) for login in logins])
    by_login = {str(row.get("login") or "").lower(): row for row in users.get("data") or []}
    live = {str(row.get("user_login") or "").lower(): row for row in streams.get("data") or []}
    return by_login, live


def post_embed(token: str, channel_id: str, embed: dict) -> str:
    body = json.dumps({"embeds": [embed]}).encode()
    request = urllib.request.Request(
        f"{API}/channels/{channel_id}/messages",
        data=body,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "ZaelrysCopains/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Discord HTTP {exc.code}") from exc
    return str(payload.get("id") or "")


def run(first_run: bool | None = None) -> int:
    channel_id, logins = load_list()
    cfg = {**load_env(DISCORD_ENV), **load_env(LIVE_ENV), **load_env(TWITCH_ENV)}
    client_id = cfg.get("TWITCH_CLIENT_ID", "")
    secret = cfg.get("TWITCH_CLIENT_SECRET", "")
    discord_token = cfg.get("DISCORD_BOT_TOKEN", "")
    if not client_id or not secret or not discord_token:
        raise SystemExit("config Twitch ou Discord incomplète")
    token = app_token(client_id, secret)
    users, live = twitch_rows(client_id, token, logins)
    missing = [login for login in logins if login not in users]
    if missing:
        raise SystemExit("login Twitch introuvable: " + ", ".join(missing))
    state = load_state()
    seeding = not STATE_PATH.exists() if first_run is None else first_run
    for login in logins:
        profile = users[login]
        display = str(profile.get("display_name") or login)
        stream = live.get(login) or {}
        stream_id = str(stream.get("id") or "")
        previous = str((state.get(login) or {}).get("stream_id") or "")
        action = plan(seeding, previous, stream_id)
        entry = {"stream_id": stream_id, "display_name": display}
        if action == "post":
            game = str(stream.get("game_name") or "")
            title = str(stream.get("title") or "")
            entry["message_id"] = post_embed(
                discord_token, channel_id, friend_embed(display, login, title, game)
            )
            print(f"annonce {login} stream {stream_id}")
        elif action == "seed" and stream_id:
            print(f"{login} déjà en live, pas d'annonce, surveillance armée")
        elif action == "offline" or (action == "seed" and not stream_id):
            print(f"{login} hors live, surveillance armée")
        else:
            print(f"{login} déjà annoncé, surveillance armée")
        state[login] = entry
    save_state(state)
    print(f"salon {channel_id} logins {', '.join(logins)}")
    return 0


def main() -> int:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    handle = LOCK_PATH.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("déjà en cours")
        return 0
    try:
        return run()
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


if __name__ == "__main__":
    raise SystemExit(main())
