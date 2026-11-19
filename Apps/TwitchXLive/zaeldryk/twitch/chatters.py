#!/usr/bin/env python3
"""Relève les chatters Helix pendant un live zaeldryk. N'écrit ni dans le chat ni sur Discord."""

from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
OUT_DIR = Path(os.environ.get("CHATTERS_DIR", ROOT / "chatters"))
BOT_ENV = Path(os.environ.get("TWITCH_BOT_ENV", ROOT / "twitch-bot" / ".env"))
STATS_PATH = Path(os.environ.get("LIVE_STATS", ROOT / "twitch-bot" / "data" / "live-stats.json"))
BROADCASTER_ID = "426411773"
SCOPE = "moderator:read:chatters"
INTERVAL_MINUTES = 1
EXCLUDED = {
    "zaeldryk",
    "zaeldryk_bot",
    "nightbot",
    "streamelements",
    "streamlabs",
    "fossabot",
    "wizebot",
    "moobot",
    "soundalerts",
    "sery_bot",
}


def load_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def plain_token(value: str) -> str:
    token = (value or "").strip()
    if token.lower().startswith("oauth:"):
        return token.split(":", 1)[1]
    return token


def keep_login(login: str) -> bool:
    name = (login or "").strip().lstrip("@").lower()
    return bool(name) and name not in EXCLUDED


def paris_day(started_at: str) -> str:
    try:
        moment = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        moment = datetime.now(PARIS)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=PARIS)
    return moment.astimezone(PARIS).date().isoformat()


def live_paths(day: str, stream_id: str) -> tuple[Path, Path]:
    stem = day
    plain_json = OUT_DIR / f"{day}.json"
    if plain_json.exists():
        try:
            current = json.loads(plain_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = {}
        if str(current.get("stream_id") or "") not in {"", stream_id}:
            stem = f"{day}-{stream_id}"
    return OUT_DIR / f"{stem}.json", OUT_DIR / f"{stem}.csv"


def apply_sample(viewers: dict, logins: list[str], seen_at: str, speakers: dict | None) -> dict:
    """Met à jour présences et lurkers. speakers=None si le bot n'a pas ce live."""
    for login in logins:
        if not keep_login(login):
            continue
        row = viewers.setdefault(
            login,
            {"login": login, "first_seen": seen_at, "last_seen": seen_at, "samples": 0},
        )
        if seen_at < row["first_seen"]:
            row["first_seen"] = seen_at
        if seen_at > row["last_seen"]:
            row["last_seen"] = seen_at
        row["samples"] = int(row.get("samples") or 0) + 1
        row["estimated_minutes"] = row["samples"] * INTERVAL_MINUTES
    if speakers is None:
        return viewers
    for row in viewers.values():
        messages = int(speakers.get(row["login"], 0))
        row["messages"] = messages
        row["lurker"] = messages == 0
    return viewers


def write_csv(path: Path, viewers: dict) -> None:
    rows = sorted(viewers.values(), key=lambda item: (-int(item.get("samples") or 0), item["login"]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["login", "first_seen", "last_seen", "samples", "estimated_minutes", "messages", "lurker"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "login": row["login"],
                    "first_seen": row.get("first_seen") or "",
                    "last_seen": row.get("last_seen") or "",
                    "samples": row.get("samples") or 0,
                    "estimated_minutes": row.get("estimated_minutes") or 0,
                    "messages": "" if "messages" not in row else row["messages"],
                    "lurker": "" if "lurker" not in row else ("oui" if row["lurker"] else "non"),
                }
            )


def summary_text(payload: dict) -> str:
    viewers = list((payload.get("viewers") or {}).values())
    lurkers = [row for row in viewers if row.get("lurker") is True]
    speakers = [row for row in viewers if row.get("lurker") is False]
    lines = [
        f"Live {payload.get('day') or '?'} stream {payload.get('stream_id') or '?'}",
        f"Relevés : {len(payload.get('samples') or [])} · chatters : {len(viewers)} · ont écrit : {len(speakers)} · lurkers : {len(lurkers)}",
    ]
    ordered = sorted(viewers, key=lambda item: (-int(item.get("estimated_minutes") or 0), item.get("login") or ""))
    for row in ordered[:15]:
        mark = "lurk" if row.get("lurker") else ("chat" if row.get("lurker") is False else "?")
        lines.append(
            f"{row.get('login')} · {row.get('estimated_minutes') or 0} min · {row.get('samples') or 0} relevés · {mark}"
        )
    if len(viewers) > 15:
        lines.append(f"… {len(viewers) - 15} autres")
    return "\n".join(lines)


def latest_payload() -> dict | None:
    files = sorted(OUT_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime)
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def http_json(method: str, url: str, headers: dict):
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:160]
        return exc.code, {"message": detail}


def validate(token: str) -> tuple[int, dict]:
    return http_json("GET", "https://id.twitch.tv/oauth2/validate", {"Authorization": "OAuth " + token})


def current_stream(client_id: str, token: str) -> dict | None:
    status, payload = http_json(
        "GET",
        "https://api.twitch.tv/helix/streams?" + urllib.parse.urlencode({"user_id": BROADCASTER_ID}),
        {"Client-ID": client_id, "Authorization": "Bearer " + token},
    )
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"streams HTTP {status}")
    rows = payload.get("data") or []
    return rows[0] if rows else None


def fetch_chatters(client_id: str, token: str, moderator_id: str) -> tuple[int, list[str]]:
    logins: list[str] = []
    cursor = ""
    status = 0
    for _ in range(20):
        query = {"broadcaster_id": BROADCASTER_ID, "moderator_id": moderator_id, "first": "1000"}
        if cursor:
            query["after"] = cursor
        status, payload = http_json(
            "GET",
            "https://api.twitch.tv/helix/chat/chatters?" + urllib.parse.urlencode(query),
            {"Client-ID": client_id, "Authorization": "Bearer " + token},
        )
        if status != 200 or not isinstance(payload, dict):
            return status, []
        for row in payload.get("data") or []:
            name = str(row.get("user_login") or "").lower()
            if keep_login(name):
                logins.append(name)
        cursor = str((payload.get("pagination") or {}).get("cursor") or "")
        if not cursor:
            break
    return status, logins


def speakers_for(stream_id: str) -> dict | None:
    if not STATS_PATH.exists():
        return None
    try:
        data = json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if str(data.get("stream_id") or "") != stream_id:
        return None
    raw = data.get("chatters") or {}
    return {str(key).lower(): int(value) for key, value in raw.items()}


def record(stream: dict, logins: list[str]) -> Path:
    stream_id = str(stream.get("id") or "")
    started = str(stream.get("started_at") or "")
    day = paris_day(started)
    json_path, csv_path = live_paths(day, stream_id)
    payload = {}
    if json_path.exists():
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    if str(payload.get("stream_id") or "") not in {"", stream_id}:
        payload = {}
    seen_at = datetime.now(PARIS).isoformat(timespec="seconds")
    samples = list(payload.get("samples") or [])
    samples.append(seen_at)
    viewers = apply_sample(dict(payload.get("viewers") or {}), logins, seen_at, speakers_for(stream_id))
    payload = {
        "stream_id": stream_id,
        "started_at": started,
        "day": json_path.stem if json_path.stem == day else day,
        "broadcaster_id": BROADCASTER_ID,
        "interval_minutes": INTERVAL_MINUTES,
        "samples": samples,
        "viewers": viewers,
    }
    payload["day"] = day
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, viewers)
    return json_path


def check(client_id: str, token: str) -> int:
    status, info = validate(token)
    if status != 200 or not isinstance(info, dict):
        print(f"jeton HTTP {status}")
        return 1
    scopes = info.get("scopes") or []
    has_scope = SCOPE in scopes
    print(
        "login",
        info.get("login"),
        "user",
        info.get("user_id"),
        "scope",
        SCOPE,
        "présent" if has_scope else "manquant",
    )
    try:
        stream = current_stream(client_id, token)
    except RuntimeError as exc:
        print(exc)
        return 1
    print("zaeldryk", "en live" if stream else "hors live")
    if not has_scope:
        code, _payload = fetch_chatters(client_id, token, str(info.get("user_id") or ""))
        print(f"GET /chat/chatters HTTP {code}")
        return 0
    if not stream:
        print("pas de relevé : hors live")
        return 0
    code, logins = fetch_chatters(client_id, token, str(info.get("user_id") or ""))
    print(f"GET /chat/chatters HTTP {code} chatters {len(logins)}")
    if code == 200:
        path = record(stream, logins)
        print("fichier", path)
    return 0 if code == 200 else 1


def sample(client_id: str, token: str) -> int:
    status, info = validate(token)
    if status != 200 or not isinstance(info, dict):
        print(f"jeton HTTP {status}")
        return 1
    try:
        stream = current_stream(client_id, token)
    except RuntimeError as exc:
        print(exc)
        return 1
    if not stream:
        print("zaeldryk hors live, pas de relevé")
        return 0
    if SCOPE not in (info.get("scopes") or []):
        print(f"scope {SCOPE} manquant sur {info.get('login')}, relevé non fait")
        return 0
    code, logins = fetch_chatters(client_id, token, str(info.get("user_id") or ""))
    if code != 200:
        print(f"GET /chat/chatters HTTP {code}")
        return 1
    path = record(stream, logins)
    print(f"relevé {len(logins)} chatters → {path.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if args.summary:
        payload = latest_payload()
        if payload is None:
            print("aucun relevé")
            return 0
        print(summary_text(payload))
        return 0
    env = load_env(BOT_ENV)
    client_id = env.get("TWITCH_CLIENT_ID", "")
    token = plain_token(env.get("TWITCH_BOT_ACCESS_TOKEN", ""))
    if not client_id or not token:
        print("jeton bot absent")
        return 1
    if args.check:
        return check(client_id, token)
    return sample(client_id, token)


if __name__ == "__main__":
    raise SystemExit(main())
