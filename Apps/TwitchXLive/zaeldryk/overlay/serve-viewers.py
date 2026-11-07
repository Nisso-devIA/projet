#!/usr/bin/env python3
"""Page OBS : nombre de spectateurs Twitch, jeton lu seulement ici."""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
HTML = Path(__file__).with_name("viewers.html")
PORT = int(os.environ.get("VIEWERS_PORT", "8791"))
CACHE_SEC = 12
_cache = {"at": 0.0, "body": b'{"count":0,"live":false}'}


def load_env() -> dict:
    env = {}
    path = ROOT / "config" / "twitch.env"
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def token() -> str:
    raw = Path(os.environ.get("TWITCH_TOKEN_FILE", "/home/ubuntu/twitch_token.txt")).read_text(
        encoding="utf-8"
    )
    return raw.replace("oauth:", "").strip().splitlines()[0]


def live_count() -> dict:
    fake = os.environ.get("VIEWERS_FAKE", "").strip()
    if fake:
        return {"count": int(fake), "live": True}
    env = load_env()
    cid = env.get("TWITCH_CLIENT_ID", "")
    login = env.get("TWITCH_LOGIN", "zaeldryk")
    bid = env.get("TWITCH_BROADCASTER_ID", "")
    query = {"user_id": bid} if bid else {"user_login": login}
    url = "https://api.twitch.tv/helix/streams?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(
        url,
        headers={
            "Client-ID": cid,
            "Authorization": "Bearer " + token(),
            "User-Agent": "ZaelrysViewers/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    rows = payload.get("data") or []
    if not rows:
        return {"count": 0, "live": False}
    return {"count": int(rows[0].get("viewer_count") or 0), "live": True}


def cached_count() -> bytes:
    now = time.time()
    if now - _cache["at"] < CACHE_SEC:
        return _cache["body"]
    try:
        body = json.dumps(live_count()).encode("utf-8")
    except Exception:
        body = b'{"count":0,"live":false}'
    _cache["at"] = now
    _cache["body"] = body
    return body


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/count":
            data = cached_count()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path in {"/", "/viewers.html"}:
            data = HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(404)
        self.end_headers()


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"viewers overlay on :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
