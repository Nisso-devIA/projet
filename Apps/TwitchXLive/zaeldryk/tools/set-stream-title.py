#!/usr/bin/env python3
"""Pose titre + catégorie Twitch avant un live. --apply envoie, sinon aperçu."""
from __future__ import annotations

import json
import random
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oot_titles import OOT_KEYS, OOT_QUERY, OOT_TITLES, encode_channel_body

ROOT = Path("/home/ubuntu/zaeldryk")
BROADCASTER = "426411773"

PRESETS = [
    {
        "keys": OOT_KEYS,
        "query": OOT_QUERY,
        "titles": OOT_TITLES,
    },
    {
        "keys": ("witcher", "sorceleur"),
        "query": "The Witcher 3: Wild Hunt",
        "titles": [
            "The Witcher — contrats, griffons, et mauvaises décisions",
            "Sorceleur en live : je prends le contrat, je regrette après",
        ],
    },
    {
        "keys": ("odyssey", "mario"),
        "query": "Super Mario Odyssey",
        "titles": [
            "Mario Odyssey — les lunes, la casquette, le live",
            "Super Mario Odyssey en live : une lune de plus, un gouffre aussi",
        ],
    },
]


def load_env() -> dict:
    env = {}
    for line in (ROOT / "config" / "twitch.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def token() -> str:
    raw = Path("/home/ubuntu/twitch_token.txt").read_text(encoding="utf-8").strip()
    return raw.replace("oauth:", "").splitlines()[0]


def helix(method: str, url: str, cid: str, tok: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else encode_channel_body(body)
    headers = {
        "Client-ID": cid,
        "Authorization": "Bearer " + tok,
        "User-Agent": "ZaelrysGoLive/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Twitch HTTP {e.code}: {err[:240]}") from e


def preset_for(text: str) -> dict | None:
    low = text.lower()
    for item in PRESETS:
        if any(k in low for k in item["keys"]):
            return item
    return None


def search_game(query: str, cid: str, tok: str) -> tuple[str, str]:
    url = "https://api.twitch.tv/helix/search/categories?first=8&query=" + urllib.parse.quote(query)
    _, payload = helix("GET", url, cid, tok)
    rows = payload.get("data") or []
    if not rows:
        raise SystemExit(f"Catégorie introuvable : {query}")
    want = query.casefold()
    for row in rows:
        if row.get("name", "").casefold() == want:
            return row["id"], row["name"]
    return rows[0]["id"], rows[0]["name"]


def make_title(game_name: str, preset: dict | None) -> str:
    if preset:
        titles = preset["titles"]
        return random.choice(titles)[:140]
    short = game_name.strip()
    return f"{short} en live — première session, ça va déraper"[:140]


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv
    if not args:
        raise SystemExit("usage: set-stream-title.py <jeu> [--apply]")
    query = " ".join(args).strip()
    env = load_env()
    cid = env["TWITCH_CLIENT_ID"]
    tok = token()
    chosen = preset_for(query)
    game_query = chosen["query"] if chosen else query
    game_id, game_name = search_game(game_query, cid, tok)
    title = make_title(game_name, chosen)
    print("jeu", game_name)
    print("titre", title)
    if not apply:
        print("apercu")
        return
    bid = env.get("TWITCH_BROADCASTER_ID", BROADCASTER)
    helix(
        "PATCH",
        f"https://api.twitch.tv/helix/channels?broadcaster_id={bid}",
        cid,
        tok,
        {"title": title, "game_id": game_id},
    )
    print("applique")


if __name__ == "__main__":
    main()
