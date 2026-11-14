"""Cible de lurk RTF, lue sans rien écrire sur Discord."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
SELF_LOGIN = "zaeldryk"
SLOT_RE = re.compile(r"(\d{1,2})\s*h\s*[-–]\s*(\d{1,2})\s*h", re.IGNORECASE)
MENTION_RE = re.compile(r"<@!?(\d+)>")
TWITCH_RE = re.compile(r"twitch\.tv/([A-Za-z0-9_]+)", re.IGNORECASE)
NAME_RE = re.compile(r"raid avec\s+([A-Za-z0-9_]+)", re.IGNORECASE)
SKIP_LOGINS = {"videos", "directory", "settings", "subscriptions", "popout", SELF_LOGIN}

DAYS = {
    0: "935435092732551168",
    1: "935435128803573810",
    2: "935435168859189258",
    3: "935435201029505054",
    4: "935435251797344316",
    5: "1462488655690993714",
    6: "935435311377416232",
}
RAID_CHANNEL = "1025044604728381520"


def _usable(login: str) -> str:
    name = (login or "").strip().lower()
    if not name or name in SKIP_LOGINS:
        return ""
    return name


def is_grid(content: str) -> bool:
    return len(SLOT_RE.findall(content or "")) >= 3


def _line_slot(line: str) -> tuple[int, str] | None:
    match = SLOT_RE.search(line or "")
    if not match:
        return None
    return int(match.group(1)) % 24, line


def _person(line: str, message: dict, mapping: dict[str, str]) -> str:
    if "annulation" in (line or "").lower():
        return ""
    found = MENTION_RE.findall(line or "")
    if not found:
        return ""
    discord_id = found[-1]
    mapped = _usable(mapping.get(discord_id, ""))
    if mapped:
        return mapped
    for person in message.get("mentions") or []:
        if str(person.get("id")) == discord_id:
            return _usable(person.get("username") or "")
    return ""


def planning_slots(messages: list[dict], mapping: dict[str, str]) -> dict[int, dict]:
    """Heure française de début -> {login, msg_id}. Les corrections après la grille gagnent."""
    ordered = sorted(messages, key=lambda item: item.get("timestamp") or "")
    grids = [item for item in ordered if is_grid(item.get("content") or "")]
    if not grids:
        return {}
    grid = grids[-1]
    slots: dict[int, dict] = {}
    for line in (grid.get("content") or "").splitlines():
        parsed = _line_slot(line)
        if parsed is None:
            continue
        hour, text = parsed
        slots[hour] = {"login": _person(text, grid, mapping), "msg_id": str(grid.get("id") or "")}
    for item in ordered:
        if (item.get("timestamp") or "") <= (grid.get("timestamp") or ""):
            continue
        content = item.get("content") or ""
        for line in content.splitlines():
            parsed = _line_slot(line)
            if parsed is None:
                continue
            hour, text = parsed
            if "annulation" in content.lower() or "annulation" in text.lower():
                slots[hour] = {"login": "", "msg_id": str(item.get("id") or "")}
                continue
            slots[hour] = {"login": _person(text, item, mapping), "msg_id": str(item.get("id") or "")}
    return slots


def announcement_target(messages: list[dict]) -> dict:
    """Dernier message qui nomme une chaîne Twitch."""
    ordered = sorted(messages, key=lambda item: item.get("timestamp") or "", reverse=True)
    for item in ordered:
        chunks = [item.get("content") or ""]
        for embed in item.get("embeds") or []:
            chunks.append(embed.get("url") or "")
            chunks.append(embed.get("title") or "")
        text = "\n".join(chunks)
        match = TWITCH_RE.search(text) or NAME_RE.search(text)
        if not match:
            continue
        return {
            "login": _usable(match.group(1)),
            "msg_id": str(item.get("id") or ""),
            "since": item.get("timestamp") or "",
        }
    return {"login": "", "msg_id": "", "since": ""}


def slot_start(moment: datetime, hour: int) -> datetime:
    start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if hour < moment.hour:
        start += timedelta(days=1)
    return start.replace(hour=hour)


def build_snapshot(
    *,
    moment: datetime,
    slots: dict[int, dict],
    announcement: dict,
    live: set[str],
    zaeldryk_live: bool,
) -> dict:
    current_hour = moment.hour
    next_hour = (current_hour + 1) % 24
    current = slots.get(current_hour) or {"login": "", "msg_id": ""}
    nxt = slots.get(next_hour) or {"login": "", "msg_id": ""}
    current_login = _usable(current.get("login") or "")
    next_login = _usable(nxt.get("login") or "")
    announced = _usable(announcement.get("login") or "")
    current_live = current_login in live
    if current_login and current_live:
        login, source, since, msg_id = current_login, "planning", slot_start(moment, current_hour).isoformat(), current.get("msg_id") or ""
    elif announced and announced in live:
        login, source, since, msg_id = announced, "announcement", announcement.get("since") or "", announcement.get("msg_id") or ""
    else:
        login, source, since, msg_id = "", "", "", announcement.get("msg_id") or current.get("msg_id") or ""
    return {
        "login": login,
        "since": since or None,
        "source": source,
        "source_msg_id": msg_id,
        "zaeldryk_live": bool(zaeldryk_live),
        "current_slot": {
            "login": current_login,
            "start": slot_start(moment, current_hour).isoformat(),
            "live": current_live,
        },
        "next_slot": {
            "login": next_login,
            "start": slot_start(moment, next_hour).isoformat(),
            "live": bool(next_login) and next_login in live,
        },
    }
