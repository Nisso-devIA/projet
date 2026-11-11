"""Liens, spam, majuscules, mots bannis et timeouts progressifs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

LINK_RE = re.compile(
    r"(https?://|www\.|discord\.gg/|discord\.com/invite/|\b[\w-]{2,}\.(?:com|net|gg|tv|fr|be|io|ly|me|org)\b)",
    re.IGNORECASE,
)


@dataclass
class ModerationConfig:
    links: bool = True
    spam: bool = True
    caps: bool = True
    words: bool = True
    spam_max_messages: int = 5
    spam_window_seconds: float = 10
    repeat_count: int = 3
    caps_min_length: int = 12
    caps_ratio: float = 0.7
    banned_words: list[str] = field(default_factory=list)
    timeouts_seconds: list[int] = field(default_factory=lambda: [60, 300, 600, 1800, 3600])
    permit_seconds: float = 60
    strike_decay_seconds: float = 1800

    @classmethod
    def from_dict(cls, raw: dict | None) -> "ModerationConfig":
        raw = raw or {}
        known = {key: raw[key] for key in raw if key in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class ModAction:
    reason: str
    duration: int
    strike: int


class ModerationState:
    def __init__(self, config: ModerationConfig | None = None) -> None:
        self.config = config or ModerationConfig()
        self.history: dict[str, list[tuple[float, str]]] = {}
        self.strikes: dict[str, tuple[int, float]] = {}
        self.permits: dict[str, tuple[float, int]] = {}

    def grant_permit(self, user: str, now: float) -> None:
        self.permits[user.lower()] = (now + self.config.permit_seconds, 1)

    def _consume_permit(self, user: str, now: float) -> bool:
        key = user.lower()
        slot = self.permits.get(key)
        if slot is None or now > slot[0] or slot[1] <= 0:
            return False
        self.permits[key] = (slot[0], slot[1] - 1)
        return True

    def _strike(self, user: str, now: float) -> int:
        count, last = self.strikes.get(user.lower(), (0, 0))
        if last and now - last > self.config.strike_decay_seconds:
            count = 0
        count += 1
        self.strikes[user.lower()] = (count, now)
        return count

    def _timeout_for(self, strike: int) -> int:
        ladder = self.config.timeouts_seconds or [60]
        index = min(strike, len(ladder)) - 1
        return int(ladder[max(0, index)])

    def inspect(self, user: str, text: str, now: float, *, exempt: bool) -> ModAction | None:
        if exempt:
            return None
        reason = self._reason(user, text or "", now)
        if reason is None:
            return None
        strike = self._strike(user, now)
        return ModAction(reason=reason, duration=self._timeout_for(strike), strike=strike)

    def _reason(self, user: str, text: str, now: float) -> str | None:
        lowered = text.casefold()
        if self.config.words:
            for word in self.config.banned_words:
                needle = word.casefold().strip()
                if needle and re.search(rf"\b{re.escape(needle)}\b", lowered):
                    return "mot interdit"
        if self.config.links and LINK_RE.search(text):
            if self._consume_permit(user, now):
                return None
            return "lien non autorisé"
        if self.config.caps and _too_many_caps(text, self.config.caps_min_length, self.config.caps_ratio):
            return "excès de majuscules"
        if self.config.spam and self._is_spam(user, text, now):
            return "spam"
        self._remember(user, text, now)
        return None

    def _remember(self, user: str, text: str, now: float) -> None:
        key = user.lower()
        bucket = [item for item in self.history.get(key, []) if now - item[0] <= self.config.spam_window_seconds]
        bucket.append((now, " ".join(text.casefold().split())))
        self.history[key] = bucket

    def _is_spam(self, user: str, text: str, now: float) -> bool:
        key = user.lower()
        normalized = " ".join(text.casefold().split())
        bucket = [item for item in self.history.get(key, []) if now - item[0] <= self.config.spam_window_seconds]
        if len(bucket) + 1 >= self.config.spam_max_messages:
            self.history[key] = bucket + [(now, normalized)]
            return True
        recent = [item[1] for item in bucket] + [normalized]
        if self.config.repeat_count > 1 and len(recent) >= self.config.repeat_count:
            if recent[-self.config.repeat_count :] == [normalized] * self.config.repeat_count:
                self.history[key] = bucket + [(now, normalized)]
                return True
        return False


def _too_many_caps(text: str, min_length: int, ratio: float) -> bool:
    if len(text) < min_length:
        return False
    letters = [char for char in text if char.isalpha()]
    if len(letters) < min_length:
        return False
    upper = sum(1 for char in letters if char.isupper())
    return upper / len(letters) >= ratio
