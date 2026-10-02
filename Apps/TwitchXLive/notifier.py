#!/usr/bin/env python3
"""
Twitch → X live notifier for zaeldryk.

- When the stream is live AND the title does NOT contain OFFLINE → post on X (once).
- When the title contains OFFLINE, or the stream is gone → delete that X post.

The VPS can keep a “fake live” with title OFFLINE; we key off the title, not Helix is_live alone.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
import tweepy
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "state.json"
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("twitch-x-live")

TWITCH_LOGIN = os.getenv("TWITCH_LOGIN", "zaeldryk").strip().lower()
OFFLINE_MARKER = os.getenv("OFFLINE_MARKER", "OFFLINE").strip().upper()
POLL_INTERVAL = max(15, int(os.getenv("POLL_INTERVAL", "30")))
CHANNEL_URL = f"https://www.twitch.tv/{TWITCH_LOGIN}"


def require_env(*keys: str) -> None:
    missing = [k for k in keys if not os.getenv(k)]
    if missing:
        log.error("Missing env vars: %s (copy .env.example → .env)", ", ".join(missing))
        sys.exit(1)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


class TwitchClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._token_expires_at = 0.0

    def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        r = requests.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + int(data.get("expires_in", 3600))
        return self._token

    def get_stream(self) -> dict | None:
        """Return Helix stream object or None if not broadcasting."""
        token = self._ensure_token()
        r = requests.get(
            "https://api.twitch.tv/helix/streams",
            params={"user_login": TWITCH_LOGIN},
            headers={
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {token}",
            },
            timeout=20,
        )
        r.raise_for_status()
        rows = r.json().get("data") or []
        return rows[0] if rows else None


class XClient:
    def __init__(self) -> None:
        self.client = tweepy.Client(
            consumer_key=os.environ["X_API_KEY"],
            consumer_secret=os.environ["X_API_SECRET"],
            access_token=os.environ["X_ACCESS_TOKEN"],
            access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
            wait_on_rate_limit=True,
        )

    def create_post(self, text: str) -> str:
        resp = self.client.create_tweet(text=text)
        post_id = str(resp.data["id"])
        log.info("Posted on X: https://x.com/i/status/%s", post_id)
        return post_id

    def delete_post(self, post_id: str) -> None:
        self.client.delete_tweet(post_id)
        log.info("Deleted X post %s", post_id)


def build_post_text(title: str) -> str:
    clean = " ".join(title.split())
    return f"🔴 LIVE — {clean}\n{CHANNEL_URL}"


def is_effectively_offline(stream: dict | None) -> bool:
    if not stream:
        return True
    title = (stream.get("title") or "").upper()
    return OFFLINE_MARKER in title


def tick(twitch: TwitchClient, x: XClient) -> None:
    state = load_state()
    post_id = state.get("post_id")
    stream = twitch.get_stream()
    title = (stream or {}).get("title") or ""

    if is_effectively_offline(stream):
        reason = "no stream" if not stream else f"title contains {OFFLINE_MARKER!r}"
        log.info("Offline (%s). Title=%r", reason, title)
        if post_id:
            try:
                x.delete_post(post_id)
            except tweepy.TweepyException as exc:
                # Already gone / not found → clear local state anyway
                log.warning("Delete failed (%s); clearing local state", exc)
            state.pop("post_id", None)
            state.pop("posted_title", None)
            save_state(state)
        return

    log.info("Live. Title=%r", title)
    if post_id:
        return

    text = build_post_text(title)
    if len(text) > 280:
        # Keep URL + prefix; trim title
        prefix = "🔴 LIVE — "
        suffix = f"\n{CHANNEL_URL}"
        max_title = 280 - len(prefix) - len(suffix)
        text = f"{prefix}{title[:max_title].rstrip()}{suffix}"

    new_id = x.create_post(text)
    state["post_id"] = new_id
    state["posted_title"] = title
    save_state(state)


def main() -> None:
    require_env(
        "TWITCH_CLIENT_ID",
        "TWITCH_CLIENT_SECRET",
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
    )
    twitch = TwitchClient(
        os.environ["TWITCH_CLIENT_ID"],
        os.environ["TWITCH_CLIENT_SECRET"],
    )
    x = XClient()
    log.info(
        "Watching https://www.twitch.tv/%s every %ss (marker=%s)",
        TWITCH_LOGIN,
        POLL_INTERVAL,
        OFFLINE_MARKER,
    )
    while True:
        try:
            tick(twitch, x)
        except requests.RequestException as exc:
            log.error("Twitch/HTTP error: %s", exc)
        except tweepy.TweepyException as exc:
            log.error("X API error: %s", exc)
        except Exception as exc:  # noqa: BLE001 — keep daemon alive
            log.exception("Unexpected error: %s", exc)
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
