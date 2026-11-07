#!/usr/bin/env python3
"""Pose un titre au hasard quand un live Zelda démarre. Une seule fois."""
from __future__ import annotations

import json
import random
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oot_titles import OOT_KEYS, OOT_TITLES

ROOT = Path("/home/ubuntu/zaeldryk")
LOG = ROOT / "logs" / "title-rotate.log"
PAUSE = re.compile(r"offline|ending|brb|fin de live|hors ligne", re.IGNORECASE)


def log(msg: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_env() -> dict:
    env = {}
    for raw in (ROOT / "config" / "twitch.env").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def token() -> str:
    raw = Path("/home/ubuntu/twitch_token.txt").read_text(encoding="utf-8").strip()
    return raw.replace("oauth:", "").splitlines()[0]


def helix(method: str, url: str, cid: str, tok: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    headers = {
        "Client-ID": cid,
        "Authorization": "Bearer " + tok,
        "User-Agent": "ZaelrysTitle/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Twitch HTTP {exc.code}: {err[:240]}") from exc


def is_oot(game: str, title: str) -> bool:
    blob = f"{game} {title}".lower()
    return any(key in blob for key in OOT_KEYS)


def pick_title(current: str) -> str:
    choices = [title for title in OOT_TITLES if title != current] or list(OOT_TITLES)
    return random.choice(choices)


def main() -> int:
    dry = "--dry-run" in sys.argv
    env = load_env()
    cid = env["TWITCH_CLIENT_ID"]
    tok = token()
    bid = env.get("TWITCH_BROADCASTER_ID", "426411773")
    status, payload = helix(
        "GET",
        f"https://api.twitch.tv/helix/streams?user_id={bid}",
        cid,
        tok,
    )
    if status != 200:
        raise SystemExit(f"Twitch streams HTTP {status}")
    rows = (payload or {}).get("data") or []
    if not rows:
        log("pas en live")
        return 0
    stream = rows[0]
    title = stream.get("title") or ""
    game = stream.get("game_name") or ""
    if PAUSE.search(title):
        log("titre de pause, laissé")
        return 0
    if not is_oot(game, title):
        log(f"autre jeu ({game}), laissé")
        return 0
    chosen = pick_title(title)
    log(f"{'aperçu' if dry else 'titre'} → {chosen}")
    if dry:
        return 0
    helix(
        "PATCH",
        f"https://api.twitch.tv/helix/channels?broadcaster_id={bid}",
        cid,
        tok,
        {"title": chosen},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
