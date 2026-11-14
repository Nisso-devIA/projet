"""Cible de lurk RTF, lue sans rien écrire sur Discord."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
SELF_LOGIN = "zaeldryk"
SLOT_RE = re.compile(
    r"(\d{1,2})(?:\s*h\s*(\d{1,2})?)?\s*[-–]\s*(\d{1,2})(?:\s*h\s*(\d{1,2})?)?",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b")
NAMED_DAY_RE = re.compile(
    r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+(\d{1,2})\b",
    re.IGNORECASE,
)
WEEKDAY_INDEX = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}
DAY_NAMES = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
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
    if not re.fullmatch(r"[a-z0-9_]{2,25}", name) or name in SKIP_LOGINS:
        return ""
    return name


def _minutes(value: str | None) -> int:
    if not value:
        return 0
    return min(int(value), 59)


def _line_slot(line: str) -> tuple[int, int, int, int, str] | None:
    match = SLOT_RE.search(line or "")
    if not match or "h" not in match.group(0).lower():
        return None
    return (
        int(match.group(1)) % 24,
        _minutes(match.group(2)),
        int(match.group(3)) % 24,
        _minutes(match.group(4)),
        line,
    )


def resolve_login(discord_id: str, message: dict, mapping: dict[str, str], profiles: dict[str, dict] | None = None) -> str:
    """Login Twitch : compte lié, puis pseudo affiché. Jamais un username qui diffère de l'affichage."""
    profile = (profiles or {}).get(str(discord_id), {})
    mention = None
    for person in message.get("mentions") or []:
        if str(person.get("id")) == str(discord_id):
            mention = person
            break
    member = (mention or {}).get("member") or {}
    twitch = _usable(profile.get("twitch") or "")
    if twitch:
        return twitch
    mapped = _usable(mapping.get(str(discord_id), ""))
    if mapped:
        return mapped
    nick = _usable(profile.get("nick") or member.get("nick") or "")
    if nick:
        return nick
    global_name = profile.get("global_name") or (mention or {}).get("global_name") or ""
    shown = _usable(global_name)
    if shown:
        return shown
    username = profile.get("username") or (mention or {}).get("username") or ""
    if username and (not global_name or username.casefold() == str(global_name).casefold()):
        return _usable(username)
    return ""


def _person(line: str, message: dict, mapping: dict[str, str], profiles: dict[str, dict] | None = None) -> str:
    if "annulation" in (line or "").lower():
        return ""
    found = MENTION_RE.findall(line or "")
    if not found:
        return ""
    return resolve_login(found[-1], message, mapping, profiles)


def channel_weekday(channel_id: str) -> int | None:
    for weekday, stored in DAYS.items():
        if stored == str(channel_id):
            return weekday
    return None


def _week_bounds(moment: datetime) -> tuple[datetime.date, datetime.date]:
    start = moment.date() - timedelta(days=moment.weekday())
    return start, start + timedelta(days=6)


def message_date(message: dict, moment: datetime) -> datetime.date | None:
    """Date du créneau : en-tête daté, sinon le jour du salon dans la semaine en cours."""
    head = "\n".join((message.get("content") or "").splitlines()[:4])
    numbered = DATE_RE.search(head)
    if numbered:
        day, month, year = int(numbered.group(1)), int(numbered.group(2)), int(numbered.group(3))
        if year < 100:
            year += 2000
        try:
            return datetime(year, month, day).date()
        except ValueError:
            return None
    named = NAMED_DAY_RE.search(head)
    if named:
        weekday = WEEKDAY_INDEX[named.group(1).lower()]
        number = int(named.group(2))
        start, _end = _week_bounds(moment)
        for offset in range(-14, 21):
            candidate = start + timedelta(days=offset)
            if candidate.weekday() == weekday and candidate.day == number:
                return candidate
    weekday = channel_weekday(str(message.get("channel_id") or ""))
    start, _end = _week_bounds(moment)
    if weekday is None:
        return moment.date()
    return start + timedelta(days=weekday)


def _effective(message: dict) -> str:
    return message.get("edited_timestamp") or message.get("timestamp") or ""


def planning_slots(
    messages: list[dict],
    mapping: dict[str, str],
    profiles: dict[str, dict] | None = None,
    moment: datetime | None = None,
) -> list[dict]:
    """Créneaux de la semaine. Une date dans le message prime sur le salon."""
    anchor = moment or datetime.now(PARIS)
    week_start, week_end = _week_bounds(anchor)
    grouped: dict[datetime.date, list[tuple[str, dict, list[tuple[int, int, int, int, str]], bool]]] = {}
    for item in messages:
        lines = []
        for line in (item.get("content") or "").splitlines():
            parsed = _line_slot(line)
            if parsed is not None:
                lines.append(parsed)
        if not lines:
            continue
        when = message_date(item, anchor)
        if when is None or not (week_start <= when <= week_end):
            continue
        grouped.setdefault(when, []).append((_effective(item), item, lines, len(lines) >= 3))
    slots: list[dict] = []
    for when, events in grouped.items():
        events.sort(key=lambda event: event[0])
        bucket: dict[tuple[int, int, int, int], dict] = {}
        for _stamp, item, lines, full in events:
            if full:
                bucket = {}
            content = item.get("content") or ""
            for start_h, start_m, end_h, end_m, text in lines:
                key = (start_h, start_m, end_h, end_m)
                cancelled = "annulation" in content.lower() or "annulation" in text.lower()
                bucket[key] = {
                    "login": "" if cancelled else _person(text, item, mapping, profiles),
                    "start_h": start_h,
                    "start_m": start_m,
                    "end_h": end_h,
                    "end_m": end_m,
                    "msg_id": str(item.get("id") or ""),
                    "date": when,
                }
        slots.extend(bucket.values())
    return slots


def _window(slot: dict, moment: datetime) -> tuple[datetime, datetime]:
    day = slot.get("date") or moment.date()
    start = datetime(day.year, day.month, day.day, slot["start_h"], slot["start_m"], tzinfo=PARIS)
    end = datetime(day.year, day.month, day.day, slot["end_h"], slot["end_m"], tzinfo=PARIS)
    if end <= start:
        end += timedelta(days=1)
    return start, end


def _current_and_next(moment: datetime, slots: list[dict]) -> tuple[dict | None, datetime | None, dict | None, datetime | None]:
    current = None
    for slot in slots:
        if not slot.get("login"):
            continue
        start, end = _window(slot, moment)
        if start <= moment < end and (current is None or start >= current[0]):
            current = (start, end, slot)
    upcoming = None
    current_end = current[1] if current else None
    for slot in slots:
        if not slot.get("login"):
            continue
        start, _end = _window(slot, moment)
        if current_end is not None and start < current_end:
            continue
        if current_end is None and start <= moment:
            continue
        if upcoming is None or start < upcoming[0]:
            upcoming = (start, slot)
    if current is None:
        return None, None, (upcoming[1] if upcoming else None), (upcoming[0] if upcoming else None)
    return current[2], current[0], (upcoming[1] if upcoming else None), (upcoming[0] if upcoming else None)


def week_rows(slots: list[dict]) -> list[dict]:
    rows = []
    for slot in slots:
        if not slot.get("login") or not slot.get("date"):
            continue
        rows.append(
            {
                "day": DAY_NAMES[slot["date"].weekday()],
                "date": slot["date"].isoformat(),
                "start": f"{slot['start_h']:02d}:{slot['start_m']:02d}",
                "end": f"{slot['end_h']:02d}:{slot['end_m']:02d}",
                "login": slot["login"],
            }
        )
    rows.sort(key=lambda row: (row["date"], row["start"], row["login"]))
    return rows


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
        "week": week_rows(slots),
    }
