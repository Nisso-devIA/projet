"""Premier message d'un viewer. Les bots et le broadcaster ne sont pas salués."""

from __future__ import annotations

KNOWN_BOTS = {
    "nightbot",
    "streamelements",
    "streamlabs",
    "fossabot",
    "wizebot",
    "moobot",
    "soundalerts",
    "sery_bot",
}

DEFAULT_INVITE = "https://discord.gg/3vH2u7pme5"


def is_known_bot(login: str, bot_login: str = "") -> bool:
    name = (login or "").lower().lstrip("@")
    if not name:
        return False
    if bot_login and name == bot_login.lower():
        return True
    return name in KNOWN_BOTS


class FirstWelcome:
    def __init__(self, known: list[str] | None = None, invite: str = DEFAULT_INVITE, gap_seconds: float = 12) -> None:
        self.known = {item.lower() for item in (known or []) if item}
        self.invite = invite or DEFAULT_INVITE
        self.gap_seconds = gap_seconds
        self.last_sent: float | None = None
        self.dirty = False

    def consider(self, login: str, now: float, *, is_broadcaster: bool = False, bot_login: str = "") -> str | None:
        name = (login or "").strip().lstrip("@")
        key = name.lower()
        if not key or is_broadcaster or is_known_bot(key, bot_login) or key in self.known:
            return None
        self.known.add(key)
        self.dirty = True
        if self.last_sent is not None and now - self.last_sent < self.gap_seconds:
            return None
        self.last_sent = now
        return f"Bienvenue {name} ! Le Discord de la meute : {self.invite}"

    def export(self) -> dict:
        return {"logins": sorted(self.known)}
