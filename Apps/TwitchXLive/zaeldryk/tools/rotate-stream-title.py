#!/usr/bin/env python3
"""Change le titre Twitch toutes les 12 min pendant un live Zelda OOT.

OBS continue d'envoyer l'image. Seul le titre affiché sur Twitch tourne.
Un titre de pause (offline, ending, brb, fin de live) n'est pas écrasé.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oot_titles import OOT_KEYS, OOT_TITLES

ROOT = Path("/home/ubuntu/zaeldryk")
STATE = ROOT / "state" / "title-rotation.json"
LOG = ROOT / "logs" / "title-rotate.log"
INTERVAL_SEC = 12 * 60
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
        "User-Agent": "ZaelrysTitleRotate/1.0",
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


def next_title(current: str, index: int) -> tuple[str, int]:
    titles = OOT_TITLES
    if current in titles:
        nxt = (titles.index(current) + 1) % len(titles)
        return titles[nxt], nxt
    nxt = index % len(titles)
    if titles[nxt] == current:
        nxt = (nxt + 1) % len(titles)
    return titles[nxt], nxt


def load_state() -> dict:
    if not STATE.exists():
        return {"index": 0, "at": ""}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"index": 0, "at": ""}


def too_soon(state: dict) -> bool:
    raw = str(state.get("at") or "")
    if not raw:
        return False
    try:
        last = datetime.fromisoformat(raw)
    except ValueError:
        return False
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).total_seconds() < INTERVAL_SEC


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
        log("titre de pause, rotation laissée")
        return 0
    if not is_oot(game, title):
        log(f"autre jeu ({game}), rotation laissée")
        return 0
    state = load_state()
    if too_soon(state) and not dry:
        log("dernier changement trop récent")
        return 0
    chosen, index = next_title(title, int(state.get("index") or 0))
    if chosen == title:
        log("titre déjà en place")
        return 0
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
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(
        json.dumps(
            {"index": index, "at": datetime.now(timezone.utc).isoformat(), "title": chosen},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
