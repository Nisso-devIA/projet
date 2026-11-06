#!/usr/bin/env python3
"""Sync Twitch stream schedule → Discord server events (replaces Streamcord schedule sync)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
TWITCH_ENV = ZAEL_ROOT / "config" / "twitch.env"
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
SCHEDULE_ENV = ZAEL_ROOT / "config" / "schedule.env"
STATE_FILE = ZAEL_ROOT / "state" / "twitch-discord-schedule.json"
LOG_FILE = ZAEL_ROOT / "logs" / "schedule-sync.log"
DISCORD_API = "https://discord.com/api/v10"
TWITCH_API = "https://api.twitch.tv/helix"

ENTITY_EXTERNAL = 3
PRIVACY_GUILD_ONLY = 2
STATUS_SCHEDULED = 1


def log(msg: str) -> None:
    line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} - {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_env(path: Path) -> Dict[str, str]:
    cfg: Dict[str, str] = {}
    if not path.exists():
        return cfg
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def http_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: Optional[dict] = None,
) -> Tuple[int, Any]:
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return e.code, err_body


def parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone(timezone.utc)


def fetch_twitch_segments(cfg: Dict[str, str]) -> List[Dict[str, Any]]:
    token_file = cfg.get("TWITCH_TOKEN_FILE", "/home/ubuntu/twitch_token.txt")
    token = Path(token_file).read_text(encoding="utf-8").strip()
    broadcaster_id = cfg.get("TWITCH_BROADCASTER_ID", "426411773")
    first = cfg.get("SCHEDULE_TWITCH_FIRST", "25")

    url = f"{TWITCH_API}/schedule?broadcaster_id={broadcaster_id}&first={first}"
    status, payload = http_json(
        "GET",
        url,
        {
            "Client-ID": cfg["TWITCH_CLIENT_ID"],
            "Authorization": f"Bearer {token}",
            "User-Agent": "ZaelrysScheduleSync/1.0",
        },
    )
    if status == 404:
        log("Twitch: aucun créneau planifié (configure le planning sur dashboard Twitch)")
        return []
    if status != 200:
        raise RuntimeError(f"Twitch schedule HTTP {status}: {payload}")

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    segments = data.get("segments") or []
    out: List[Dict[str, Any]] = []
    for seg in segments:
        if seg.get("cancelled_until"):
            continue
        seg_id = seg.get("id")
        start = seg.get("start_time")
        end = seg.get("end_time")
        title = (seg.get("title") or "Live Zaeldryk").strip()
        if not seg_id or not start or not end:
            continue
        out.append(
            {
                "id": str(seg_id),
                "start_time": start,
                "end_time": end,
                "title": title,
                "game": (seg.get("category") or {}).get("name") or "Non spécifié",
                "is_recurring": bool(seg.get("is_recurring")),
            }
        )
    return out


def fetch_discord_events(token: str, guild_id: str) -> List[Dict[str, Any]]:
    status, payload = http_json(
        "GET",
        f"{DISCORD_API}/guilds/{guild_id}/scheduled-events",
        {
            "Authorization": f"Bot {token}",
            "User-Agent": "ZaelrysScheduleSync/1.0",
        },
    )
    if status != 200:
        raise RuntimeError(f"Discord list events HTTP {status}: {payload}")
    return payload if isinstance(payload, list) else []


def load_state() -> Dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items()}
    except json.JSONDecodeError:
        return {}


def save_state(mapping: Dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def event_payload(seg: Dict[str, Any], cfg: Dict[str, str]) -> dict:
    login = cfg.get("TWITCH_LOGIN", "zaeldryk")
    url = f"https://www.twitch.tv/{login}"
    game = seg["game"]
    desc = (
        f"Stream planifié sur Twitch.\n\n"
        f"🎮 **Jeu :** {game}\n"
        f"🔗 **Chaîne :** {url}\n\n"
        f"_Sync auto Zaeldryk · segment {seg['id']}_"
    )
    if len(desc) > 1000:
        desc = desc[:997] + "..."
    name = seg["title"]
    if len(name) > 100:
        name = name[:97] + "..."
    return {
        "name": name,
        "description": desc,
        "privacy_level": PRIVACY_GUILD_ONLY,
        "scheduled_start_time": seg["start_time"],
        "scheduled_end_time": seg["end_time"],
        "entity_type": ENTITY_EXTERNAL,
        "entity_metadata": {"location": url},
    }


def create_event(token: str, guild_id: str, body: dict) -> str:
    status, payload = http_json(
        "POST",
        f"{DISCORD_API}/guilds/{guild_id}/scheduled-events",
        {
            "Authorization": f"Bot {token}",
            "User-Agent": "ZaelrysScheduleSync/1.0",
        },
        body,
    )
    if status not in (200, 201):
        raise RuntimeError(f"Discord create event HTTP {status}: {payload}")
    return str(payload["id"])


def update_event(token: str, guild_id: str, event_id: str, body: dict) -> None:
    status, payload = http_json(
        "PATCH",
        f"{DISCORD_API}/guilds/{guild_id}/scheduled-events/{event_id}",
        {
            "Authorization": f"Bot {token}",
            "User-Agent": "ZaelrysScheduleSync/1.0",
        },
        body,
    )
    if status != 200:
        raise RuntimeError(f"Discord update event HTTP {status}: {payload}")


def delete_event(token: str, guild_id: str, event_id: str) -> None:
    status, payload = http_json(
        "DELETE",
        f"{DISCORD_API}/guilds/{guild_id}/scheduled-events/{event_id}",
        {
            "Authorization": f"Bot {token}",
            "User-Agent": "ZaelrysScheduleSync/1.0",
        },
    )
    if status not in (204, 200):
        if status == 404:
            return
        raise RuntimeError(f"Discord delete event HTTP {status}: {payload}")


def event_needs_update(existing: Dict[str, Any], desired: dict) -> bool:
    checks = (
        existing.get("name") != desired["name"],
        existing.get("scheduled_start_time") != desired["scheduled_start_time"],
        existing.get("scheduled_end_time") != desired["scheduled_end_time"],
        (existing.get("description") or "") != desired["description"],
        (existing.get("entity_metadata") or {}).get("location")
        != desired["entity_metadata"]["location"],
    )
    return any(checks)


def main() -> None:
    cfg = {**load_env(TWITCH_ENV), **load_env(DISCORD_ENV), **load_env(SCHEDULE_ENV)}
    if cfg.get("SCHEDULE_SYNC_ENABLED", "0") != "1":
        log("schedule sync disabled")
        return

    token = cfg.get("DISCORD_BOT_TOKEN")
    guild_id = cfg.get("DISCORD_GUILD_ID", "867426693286461490")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN missing")

    segments = fetch_twitch_segments(cfg)
    log(f"Twitch segments: {len(segments)}")

    discord_events = fetch_discord_events(token, guild_id)
    by_id = {str(e["id"]): e for e in discord_events}
    mapping = load_state()
    seen_twitch: set[str] = set()

    created = updated = deleted = 0
    for seg in segments:
        seen_twitch.add(seg["id"])
        desired = event_payload(seg, cfg)
        event_id = mapping.get(seg["id"])

        if event_id and event_id in by_id:
            existing = by_id[event_id]
            if existing.get("status") == STATUS_SCHEDULED and event_needs_update(
                existing, desired
            ):
                update_event(token, guild_id, event_id, desired)
                updated += 1
                log(f"updated discord event {event_id} ← twitch {seg['id']}")
            continue

        if event_id and event_id not in by_id:
            del mapping[seg["id"]]
            event_id = None

        if not event_id:
            new_id = create_event(token, guild_id, desired)
            mapping[seg["id"]] = new_id
            created += 1
            log(f"created discord event {new_id} ← twitch {seg['id']} @ {seg['start_time']}")

    for twitch_id, event_id in list(mapping.items()):
        if twitch_id in seen_twitch:
            continue
        ev = by_id.get(event_id)
        if ev and ev.get("status") == STATUS_SCHEDULED:
            delete_event(token, guild_id, event_id)
            deleted += 1
            log(f"deleted discord event {event_id} (twitch segment {twitch_id} gone)")
        del mapping[twitch_id]

    save_state(mapping)
    log(f"done created={created} updated={updated} deleted={deleted} mapped={len(mapping)}")
    refresh_planning_poster()


def refresh_planning_poster() -> None:
    py = ZAEL_ROOT / "venv-micromania" / "bin" / "python"
    script = ZAEL_ROOT / "tools" / "render-planning-poster.py"
    if not py.exists() or not script.exists():
        log("planning poster skipped")
        return
    proc = subprocess.run(
        [str(py), str(script), "--post"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    line = (proc.stdout or proc.stderr or "").strip().splitlines()
    log("planning " + (line[-1] if line else f"exit {proc.returncode}"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"ERROR {exc}")
        raise SystemExit(1) from exc
