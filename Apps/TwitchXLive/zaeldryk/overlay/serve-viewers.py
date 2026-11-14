#!/usr/bin/env python3
"""Pages OBS : spectateurs, objectif, alertes, chat et plaques du cadre."""
from __future__ import annotations

import hmac
import json
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from datetime import timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from rtf_current import (
    DAYS,
    PARIS,
    RAID_CHANNEL,
    SELF_LOGIN,
    announcement_target,
    build_snapshot,
    planning_slots,
)

ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
HTML = Path(__file__).with_name("viewers.html")
GOAL_HTML = Path(__file__).with_name("objectif.html")
FLUX_HTML = Path(__file__).with_name("flux.html")
CHAT_HTML = Path(__file__).with_name("chat.html")
SUB_HTML = Path(__file__).with_name("nom-sub.html")
DON_HTML = Path(__file__).with_name("nom-don.html")
FOLLOW_HTML = Path(__file__).with_name("nom-follow.html")
ACTIVITY_PATH = ROOT / "state" / "overlay-activity.json"
PORT = int(os.environ.get("VIEWERS_PORT", "8791"))
FOLLOW_GOAL = int(os.environ.get("FOLLOW_GOAL", "100"))
CACHE_SEC = 12
KEEP = 8
_cache = {"at": 0.0, "body": b'{"count":0,"live":false}'}
_followers = {"at": 0.0, "body": b'{"followers":0,"goal":100}'}
_lock = threading.Lock()
_chat: list[dict] = []
CHAT_KEEP = 30


def _read_env_file(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_env() -> dict:
    env = _read_env_file(ROOT / "config" / "twitch.env")
    env.update(_read_env_file(Path(__file__).resolve().parent / ".env"))
    return env


def token() -> str:
    raw = Path(os.environ.get("TWITCH_TOKEN_FILE", "/home/ubuntu/twitch_token.txt")).read_text(
        encoding="utf-8"
    )
    return raw.replace("oauth:", "").strip().splitlines()[0]


def login_name() -> str:
    return load_env().get("TWITCH_LOGIN", "zaeldryk").lower()


def empty_activity() -> dict:
    return {"followers": [], "subs": [], "donations": []}


def load_activity() -> dict:
    if not ACTIVITY_PATH.exists():
        return empty_activity()
    try:
        data = json.loads(ACTIVITY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty_activity()
    base = empty_activity()
    for key in base:
        if isinstance(data.get(key), list):
            base[key] = data[key][:KEEP]
    return base


def save_activity(data: dict) -> None:
    ACTIVITY_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVITY_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def remember(kind: str, item: dict) -> None:
    with _lock:
        data = load_activity()
        rows = data[kind]
        if any(row.get("name") == item["name"] and row.get("at") == item["at"] for row in rows):
            return
        rows.insert(0, item)
        data[kind] = rows[:KEEP]
        save_activity(data)


def parse_tags(line: str) -> tuple[dict, str]:
    tags: dict[str, str] = {}
    rest = line
    if line.startswith("@"):
        raw, _, rest = line[1:].partition(" ")
        for part in raw.split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            tags[key] = value.replace("\\s", " ").replace("\\:", ";")
    return tags, rest


def handle_irc_line(line: str) -> dict | None:
    """Retourne un événement suivi, sub ou don. None sinon."""
    tags, rest = parse_tags(line)
    upper = rest.upper()
    if " USERNOTICE " in upper:
        kind = tags.get("msg-id", "")
        name = tags.get("display-name") or tags.get("login") or ""
        if not name or kind not in {"sub", "resub", "subgift", "anonsubgift"}:
            return None
        plan = tags.get("msg-param-sub-plan", "")
        return {
            "bucket": "subs",
            "name": name,
            "prime": plan.lower() == "prime",
            "gift": kind in {"subgift", "anonsubgift"},
            "plan": plan,
            "bits": 0,
        }
    if " PRIVMSG " in upper and tags.get("bits"):
        name = tags.get("display-name") or ""
        if not name:
            return None
        try:
            bits = int(tags["bits"])
        except ValueError:
            return None
        return {"bucket": "donations", "name": name, "prime": False, "gift": False, "bits": bits}
    return None


def chat_from_line(line: str) -> dict | None:
    """Message public du chat. None pour tout le reste."""
    tags, rest = parse_tags(line)
    marker = " PRIVMSG "
    pos = rest.upper().find(marker)
    if pos < 0:
        return None
    name = tags.get("display-name") or tags.get("login") or ""
    if not name:
        return None
    _, sep, message = rest[pos + len(marker) :].partition(" :")
    if not sep:
        return None
    message = message.replace("\x01ACTION ", "").replace("\x01", "").strip()
    if not message:
        return None
    return {"name": name[:40], "text": message[:220]}


def remember_chat(item: dict) -> None:
    with _lock:
        _chat.append({"name": item["name"], "text": item["text"]})
        del _chat[:-CHAT_KEEP]


def chat_body() -> bytes:
    with _lock:
        rows = list(_chat)
    return json.dumps({"messages": rows}, ensure_ascii=False).encode("utf-8")


def note_event(event: dict) -> None:
    now = datetime.now(timezone.utc).isoformat()
    if event["bucket"] == "subs":
        remember(
            "subs",
            {
                "name": event["name"],
                "at": now,
                "prime": bool(event["prime"]),
                "gift": bool(event["gift"]),
                "plan": event.get("plan") or "",
            },
        )
        return
    remember(
        "donations",
        {"name": event["name"], "at": now, "bits": int(event["bits"]), "prime": False},
    )


def refresh_followers() -> None:
    fake = os.environ.get("FOLLOW_NAMES", "").strip()
    if fake:
        for name in [part.strip() for part in fake.split(",") if part.strip()]:
            remember("followers", {"name": name, "at": name})
        return
    try:
        env = load_env()
        cid = env.get("TWITCH_CLIENT_ID", "")
        bid = env.get("TWITCH_BROADCASTER_ID", "426411773")
        url = "https://api.twitch.tv/helix/channels/followers?" + urllib.parse.urlencode(
            {"broadcaster_id": bid, "first": "5"}
        )
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
    except Exception:
        return
    for row in reversed(payload.get("data") or []):
        name = row.get("user_name") or ""
        followed = row.get("followed_at") or datetime.now(timezone.utc).isoformat()
        if name:
            remember("followers", {"name": name, "at": followed})


def irc_loop() -> None:
    while True:
        try:
            run_irc()
        except Exception as exc:
            print(f"irc: {type(exc).__name__}", flush=True)
        time.sleep(8)


def run_irc() -> None:
    login = login_name()
    raw = socket.create_connection(("irc.chat.twitch.tv", 6697), timeout=30)
    sock = ssl.create_default_context().wrap_socket(raw, server_hostname="irc.chat.twitch.tv")
    sock.settimeout(120)

    def send(line: str) -> None:
        sock.sendall((line + "\r\n").encode("utf-8"))

    send("CAP REQ :twitch.tv/tags twitch.tv/commands")
    send("PASS oauth:" + token())
    send("NICK " + login)
    send("JOIN #" + login)
    print("irc joined", flush=True)
    buf = ""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk.decode("utf-8", "replace")
        while "\r\n" in buf:
            line, buf = buf.split("\r\n", 1)
            if line.startswith("PING"):
                send("PONG :tmi.twitch.tv")
                continue
            spoken = chat_from_line(line)
            if spoken:
                remember_chat(spoken)
            event = handle_irc_line(line)
            if event:
                note_event(event)
                print(f"activite {event['bucket']} prime={event['prime']}", flush=True)


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


def follower_goal() -> dict:
    fake = os.environ.get("FOLLOW_FAKE", "").strip()
    goal = FOLLOW_GOAL
    if fake:
        return {"followers": int(fake), "goal": goal}
    env = load_env()
    cid = env.get("TWITCH_CLIENT_ID", "")
    bid = env.get("TWITCH_BROADCASTER_ID", "426411773")
    url = "https://api.twitch.tv/helix/channels/followers?" + urllib.parse.urlencode(
        {"broadcaster_id": bid, "first": "1"}
    )
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
    return {"followers": int(payload.get("total") or 0), "goal": goal}


def cached_followers() -> bytes:
    now = time.time()
    if now - _followers["at"] < CACHE_SEC:
        return _followers["body"]
    try:
        body = json.dumps(follower_goal()).encode("utf-8")
    except Exception:
        body = json.dumps({"followers": 0, "goal": FOLLOW_GOAL}).encode("utf-8")
    _followers["at"] = now
    _followers["body"] = body
    return body


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


_follow_refresh = {"at": 0.0}


def activity_body() -> bytes:
    now = time.time()
    if now - _follow_refresh["at"] >= CACHE_SEC:
        refresh_followers()
        _follow_refresh["at"] = now
    with _lock:
        data = load_activity()
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


_rtf_body = json.dumps(
    {
        "login": "",
        "since": None,
        "source": "",
        "source_msg_id": "",
        "zaeldryk_live": False,
        "match": False,
        "current_slot": {"login": "", "start": None, "live": False},
        "next_slot": {"login": "", "start": None, "live": False},
        "announcement_login": "",
    }
).encode()
_rtf_lock = threading.Lock()


def rtf_key() -> str:
    return load_env().get("RTF_LURK_KEY", "")


def discord_user_token() -> str:
    env = _read_env_file(Path(os.environ.get("RTF_DISCORD_ENV", "/home/ubuntu/autobump/bump.env")))
    return env.get("DISCORD_USER_TOKEN", "")


def _discord_messages(channel_id: str) -> list[dict]:
    token_value = discord_user_token()
    if not token_value:
        raise RuntimeError("discord")
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=30",
        headers={
            "Authorization": token_value,
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode())
    return payload if isinstance(payload, list) else []


def _live_logins(logins: list[str]) -> set[str]:
    names = [name for name in dict.fromkeys(logins) if name]
    if not names:
        return set()
    env = load_env()
    query = urllib.parse.urlencode([("user_login", name) for name in names])
    request = urllib.request.Request(
        "https://api.twitch.tv/helix/streams?" + query,
        headers={
            "Client-ID": env.get("TWITCH_CLIENT_ID", ""),
            "Authorization": "Bearer " + token(),
            "User-Agent": "ZaelrysViewers/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode())
    return {str(row.get("user_login") or "").lower() for row in payload.get("data") or []}


def refresh_rtf() -> None:
    global _rtf_body
    moment = datetime.now(PARIS)
    channel_id = DAYS[moment.weekday()]
    mapping_path = ROOT / "config" / "rtf-twitch-map.json"
    mapping = {}
    if mapping_path.exists():
        mapping = {str(key): str(value).lower() for key, value in json.loads(mapping_path.read_text()).items()}
    slots = planning_slots(_discord_messages(channel_id), mapping)
    announcement = announcement_target(_discord_messages(RAID_CHANNEL))
    names = [slot.get("login") or "" for slot in slots]
    names.append(announcement.get("login") or "")
    names.append(SELF_LOGIN)
    live = _live_logins(names)
    snapshot = build_snapshot(
        moment=moment,
        slots=slots,
        announcement=announcement,
        live=live,
        zaeldryk_live=SELF_LOGIN in live,
    )
    body = json.dumps(snapshot, ensure_ascii=False).encode()
    with _rtf_lock:
        _rtf_body = body


def rtf_loop() -> None:
    while True:
        try:
            refresh_rtf()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError, OSError) as exc:
            print(f"rtf: {type(exc).__name__}", flush=True)
        time.sleep(60)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, data: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        if path == "/rtf-current":
            given = (urllib.parse.parse_qs(parsed.query).get("key") or [""])[0]
            expected = rtf_key()
            if not expected or not hmac.compare_digest(given, expected):
                self.send_response(403)
                self.end_headers()
                return
            with _rtf_lock:
                body = _rtf_body
            self._send(body, "application/json; charset=utf-8")
            return
        if path.startswith("/sounds/"):
            name = Path(path).name
            sound = Path(__file__).resolve().parent / "sounds" / name
            if sound.suffix.lower() not in {".wav", ".mp3", ".ogg"} or not sound.is_file():
                self.send_response(404)
                self.end_headers()
                return
            kind = "audio/wav" if sound.suffix.lower() == ".wav" else "audio/mpeg"
            self._send(sound.read_bytes(), kind)
            return
        pages = {
            "/count": lambda: self._send(cached_count(), "application/json; charset=utf-8"),
            "/followers": lambda: self._send(cached_followers(), "application/json; charset=utf-8"),
            "/activity": lambda: self._send(activity_body(), "application/json; charset=utf-8"),
            "/": lambda: self._send(HTML.read_bytes(), "text/html; charset=utf-8"),
            "/viewers.html": lambda: self._send(HTML.read_bytes(), "text/html; charset=utf-8"),
            "/objectif": lambda: self._send(GOAL_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/objectif.html": lambda: self._send(GOAL_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/flux": lambda: self._send(FLUX_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/flux.html": lambda: self._send(FLUX_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/messages": lambda: self._send(chat_body(), "application/json; charset=utf-8"),
            "/chat": lambda: self._send(CHAT_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/chat.html": lambda: self._send(CHAT_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/nom-sub": lambda: self._send(SUB_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/nom-don": lambda: self._send(DON_HTML.read_bytes(), "text/html; charset=utf-8"),
            "/nom-follow": lambda: self._send(FOLLOW_HTML.read_bytes(), "text/html; charset=utf-8"),
        }
        handler = pages.get(path)
        if handler is None:
            self.send_response(404)
            self.end_headers()
            return
        handler()


def main() -> None:
    threading.Thread(target=irc_loop, daemon=True).start()
    threading.Thread(target=rtf_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"viewers overlay on :{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
