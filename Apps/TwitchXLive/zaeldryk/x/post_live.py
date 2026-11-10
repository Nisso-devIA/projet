#!/usr/bin/env python3
"""Post one X live tweet per Twitch session, rotating three templates."""
from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TWITCH_URL = "https://www.twitch.tv/zaeldryk"
URL_WEIGHT = 23
TWEET_LIMIT = 280

TEMPLATES = (
    "🧚 HEY, LISTEN ! Zaeldryk est en LIVE 🔴\n"
    "⚔️ {titre}\n"
    "Hyrule n’attend pas. Prends ton épée, ton ocarina, et rejoins l’aventure 👇\n"
    "🎮 https://www.twitch.tv/zaeldryk",
    "🔴 LE LIVE EST LANCÉ\n"
    "Les donjons tremblent, les boss tombent… et c’est maintenant que ça se passe ⚔️🔥\n"
    "🗡️ {titre}\n"
    "Viens vivre ça en direct avec nous 👉 https://www.twitch.tv/zaeldryk",
    "🎮 ON EST LIVE ! 🔴\n"
    "{titre}\n"
    "Une place t’attend au coin du feu 🔥 Viens ⤵️\n"
    "https://www.twitch.tv/zaeldryk",
)

CONFIG = os.environ.get("X_CONFIG_PATH", "/home/ubuntu/x_config.env")
POST_ID_FILE = os.environ.get(
    "X_POST_ID_FILE", "/home/ubuntu/zaeldryk/state/last_x_post_id.txt"
)
STATE_FILE = Path(
    os.environ.get("X_LIVE_STATE_FILE", "/home/ubuntu/zaeldryk/state/last_x_live.json")
)
INDEX_FILE = Path(
    os.environ.get("X_TEMPLATE_INDEX_FILE", "/home/ubuntu/zaeldryk/state/x_template_index.txt")
)


def weighted_length(text: str) -> int:
    total = 0
    i = 0
    while i < len(text):
        if text.startswith(TWITCH_URL, i):
            total += URL_WEIGHT
            i += len(TWITCH_URL)
            continue
        total += 2 if ord(text[i]) > 0xFFFF else 1
        i += 1
    return total


def render_tweet(template: str, title: str) -> str:
    if "{titre}" not in template:
        return template
    full = template.replace("{titre}", title)
    if weighted_length(full) <= TWEET_LIMIT:
        return full
    best = template.replace("{titre}", "…")
    lo, hi = 0, len(title)
    while lo <= hi:
        mid = (lo + hi) // 2
        short = title[:mid].rstrip()
        candidate = f"{short}…" if short else "…"
        text = template.replace("{titre}", candidate)
        if weighted_length(text) <= TWEET_LIMIT:
            best = text
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def next_index(last: int | None) -> int:
    if last is None:
        return 0
    return (last + 1) % len(TEMPLATES)


def read_index(path: Path) -> int | None:
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw.isdigit():
        return None
    return int(raw)


def write_index(path: Path, index: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(index) + "\n", encoding="utf-8")


def _announce():
    path = Path(__file__).resolve().parents[1] / "discord" / "live-announce.py"
    spec = importlib.util.spec_from_file_location("live_announce", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def should_skip(state: dict, stream_id: str, started_at: str, now: datetime) -> bool:
    return _announce().already_announced(state, stream_id, started_at, now)


def load_env(path=CONFIG):
    env = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def main() -> int:
    title = sys.argv[1] if len(sys.argv) > 1 else "Live"
    stream_id = os.environ.get("X_STREAM_ID", "").strip()
    started_at = os.environ.get("X_STARTED_AT", "").strip()
    now = datetime.now(timezone.utc)
    announce = _announce()
    state = announce.load_state(STATE_FILE)
    if should_skip(state, stream_id, started_at, now):
        print("skip duplicate X post")
        return 0

    import tweepy

    index = next_index(read_index(INDEX_FILE))
    text = render_tweet(TEMPLATES[index], title)
    env = load_env()
    client = tweepy.Client(
        consumer_key=env["X_API_KEY"],
        consumer_secret=env["X_API_SECRET"],
        access_token=env["X_ACCESS_TOKEN"],
        access_token_secret=env["X_ACCESS_SECRET"],
    )
    resp = client.create_tweet(text=text)
    tweet_id = str(resp.data["id"])
    os.makedirs(os.path.dirname(POST_ID_FILE), exist_ok=True)
    with open(POST_ID_FILE, "w", encoding="utf-8") as handle:
        handle.write(tweet_id)
    with open("/home/ubuntu/last_x_post_id.txt", "w", encoding="utf-8") as handle:
        handle.write(tweet_id)
    announce.remember_message(
        state,
        channel_id="x",
        message_id=tweet_id,
        stream_id=stream_id,
        started_at=started_at,
        posted_at=now.isoformat(),
    )
    announce.save_state(STATE_FILE, state)
    write_index(INDEX_FILE, index)
    print(f"Posté : {tweet_id} template={index} chars={weighted_length(text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
