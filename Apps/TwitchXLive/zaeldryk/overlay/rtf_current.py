"""Cible de lurk RTF, lue sans rien écrire sur Discord."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
SELF_LOGIN = "zaeldryk"
SLOT_RE = re.compile(
    r"(\d{1,2})\s*h\s*(\d{1,2})?\s*[-–]\s*(\d{1,2})\s*h\s*(\d{1,2})?",
    re.IGNORECASE,
)
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


def _minutes(value: str | None) -> int:
    if not value:
        return 0
    return min(int(value), 59)


def _line_slot(line: str) -> tuple[int, int, int, int, str] | None:
    match = SLOT_RE.search(line or "")
    if not match:
        return None
    return (
        int(match.group(1)) % 24,
        _minutes(match.group(2)),
        int(match.group(3)) % 24,
        _minutes(match.group(4)),
        line,
    )


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


def planning_slots(messages: list[dict], mapping: dict[str, str]) -> list[dict]:
    """Créneaux français, un message par streamer ou une grille. Le plus récent gagne."""
    ordered = sorted(messages, key=lambda item: item.get("timestamp") or "")
    slots: dict[tuple[int, int, int, int], dict] = {}
    for item in ordered:
        content = item.get("content") or ""
        for line in content.splitlines():
            parsed = _line_slot(line)
            if parsed is None:
                continue
            start_h, start_m, end_h, end_m, text = parsed
            key = (start_h, start_m, end_h, end_m)
            if "annulation" in content.lower() or "annulation" in text.lower():
                slots[key] = {
                    "login": "",
                    "start_h": start_h,
                    "start_m": start_m,
                    "end_h": end_h,
                    "end_m": end_m,
                    "msg_id": str(item.get("id") or ""),
                }
                continue
            slots[key] = {
                "login": _person(text, item, mapping),
                "start_h": start_h,
                "start_m": start_m,
                "end_h": end_h,
                "end_m": end_m,
                "msg_id": str(item.get("id") or ""),
            }
    return list(slots.values())


def _window(moment: datetime, slot: dict) -> tuple[datetime, datetime]:
    start = moment.replace(hour=slot["start_h"], minute=slot["start_m"], second=0, microsecond=0)
    end = moment.replace(hour=slot["end_h"], minute=slot["end_m"], second=0, microsecond=0)
    if (slot["end_h"], slot["end_m"]) <= (slot["start_h"], slot["start_m"]):
        if (moment.hour, moment.minute) < (slot["end_h"], slot["end_m"]):
            start -= timedelta(days=1)
        else:
            end += timedelta(days=1)
    return start, end


def _occurrences(moment: datetime, slot: dict) -> list[tuple[datetime, datetime]]:
    start, end = _window(moment, slot)
    return [
        (start - timedelta(days=1), end - timedelta(days=1)),
        (start, end),
        (start + timedelta(days=1), end + timedelta(days=1)),
    ]


def _current_and_next(moment: datetime, slots: list[dict]) -> tuple[dict | None, datetime | None, dict | None, datetime | None]:
    current = None
    current_end = None
    for slot in slots:
        if not slot.get("login"):
            continue
        for start, end in _occurrences(moment, slot):
            if start <= moment < end and (current is None or start >= current[0]):
                current = (start, end, slot)
    if current:
        current_end = current[1]
    upcoming = None
    for slot in slots:
        if not slot.get("login"):
            continue
        for start, end in _occurrences(moment, slot):
            if current_end is not None and start < current_end:
                continue
            if current_end is None and start <= moment:
                continue
            if upcoming is None or start < upcoming[0]:
                upcoming = (start, end, slot)
    if current is None:
        return None, None, (upcoming[2] if upcoming else None), (upcoming[0] if upcoming else None)
    return current[2], current[0], (upcoming[2] if upcoming else None), (upcoming[0] if upcoming else None)


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


def build_snapshot(
    *,
    moment: datetime,
    slots: list[dict],
    announcement: dict,
    live: set[str],
    zaeldryk_live: bool,
) -> dict:
    current, current_start, nxt, next_start = _current_and_next(moment, slots)
    current_login = _usable((current or {}).get("login") or "")
    next_login = _usable((nxt or {}).get("login") or "")
    announced = _usable(announcement.get("login") or "")
    current_live = bool(current_login) and current_login in live
    announced_live = bool(announced) and announced in live
    same = bool(current_login) and current_login == announced
    if same and (current_live or announced_live):
        login, source, since, msg_id = current_login, "planning", (current_start.isoformat() if current_start else ""), (current or {}).get("msg_id") or ""
    elif current_login and current_live:
        login, source, since, msg_id = current_login, "planning", (current_start.isoformat() if current_start else ""), (current or {}).get("msg_id") or ""
    elif announced and announced_live:
        login, source, since, msg_id = announced, "announcement", announcement.get("since") or "", announcement.get("msg_id") or ""
    else:
        login, source, since, msg_id = "", "", "", announcement.get("msg_id") or (current or {}).get("msg_id") or ""
    return {
        "login": login,
        "since": since or None,
        "source": source,
        "source_msg_id": msg_id,
        "zaeldryk_live": bool(zaeldryk_live),
        "match": same,
        "current_slot": {
            "login": current_login,
            "start": current_start.isoformat() if current_start else None,
            "live": current_live,
        },
        "next_slot": {
            "login": next_login,
            "start": next_start.isoformat() if next_start else None,
            "live": bool(next_login) and next_login in live,
        },
        "announcement_login": announced,
    }
