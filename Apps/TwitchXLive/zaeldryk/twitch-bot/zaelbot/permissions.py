"""Niveaux de permission du chat Twitch."""

from __future__ import annotations

LEVELS = {
    "everyone": 0,
    "sub": 1,
    "vip": 2,
    "mod": 3,
    "broadcaster": 4,
}


def permission_level(badges: set[str] | dict | None, *, is_mod: bool = False, is_sub: bool = False, is_vip: bool = False) -> str:
    names = set(badges or [])
    if isinstance(badges, dict):
        names = set(badges)
    if "broadcaster" in names:
        return "broadcaster"
    if is_mod or "moderator" in names:
        return "mod"
    if is_vip or "vip" in names:
        return "vip"
    if is_sub or "subscriber" in names or "founder" in names:
        return "sub"
    return "everyone"


def allows(user_level: str, required: str) -> bool:
    return LEVELS.get(user_level, 0) >= LEVELS.get(required, 0)


def is_exempt(user_level: str) -> bool:
    return allows(user_level, "vip")
