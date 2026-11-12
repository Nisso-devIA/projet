"""Règles de modération : haine, spam de bots, autopromo, vulgarités, liens et spam."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from zaelbot.normalize import contains_any, normalize_text
from zaelbot.permissions import allows
from zaelbot.wordlists import (
    HATE_WORDS,
    OWN_MARKERS,
    PROMO_PHRASES,
    SPAM_DOMAINS,
    SPAM_PHRASES,
    VULGAR_WORDS,
)

LINK_RE = re.compile(
    r"(https?://|www\.|discord\.gg/|discord\.com/invite/|\b[\w-]{2,}\.(?:com|net|gg|tv|fr|be|io|ly|me|org)\b)",
    re.IGNORECASE,
)
FOREIGN_SOCIAL_RE = re.compile(
    r"(?:twitch\.tv/|kick\.com/|tiktok\.com/@|youtube\.com/|youtu\.be/)([a-z0-9_]+)",
    re.IGNORECASE,
)
DISCORD_INVITE_RE = re.compile(r"(?:discord\.gg/|discord\.com/invite/)([a-z0-9]+)", re.IGNORECASE)
DAY = 86400


@dataclass
class ModerationConfig:
    links: bool = True
    spam: bool = True
    caps: bool = True
    words: bool = True
    hate: bool = True
    vulgar: bool = True
    spam_bots: bool = True
    promo: bool = True
    spam_max_messages: int = 5
    spam_window_seconds: float = 10
    repeat_count: int = 3
    caps_min_length: int = 25
    caps_ratio: float = 0.8
    caps_window_seconds: float = 1800
    banned_words: list[str] = field(default_factory=list)
    hate_words: list[str] = field(default_factory=lambda: list(HATE_WORDS))
    vulgar_words: list[str] = field(default_factory=lambda: list(VULGAR_WORDS))
    spam_phrases: list[str] = field(default_factory=lambda: list(SPAM_PHRASES))
    spam_domains: list[str] = field(default_factory=lambda: list(SPAM_DOMAINS))
    promo_phrases: list[str] = field(default_factory=lambda: list(PROMO_PHRASES))
    own_markers: list[str] = field(default_factory=lambda: list(OWN_MARKERS))
    timeouts_seconds: list[int] = field(default_factory=lambda: [60, 300, 600, 1800, 3600])
    permit_seconds: float = 60
    strike_decay_seconds: float = 1800
    vulgar_strike_days: int = 30

    @classmethod
    def from_dict(cls, raw: dict | None) -> "ModerationConfig":
        raw = raw or {}
        known = {key: raw[key] for key in raw if key in cls.__dataclass_fields__}
        config = cls(**known)
        if not config.hate_words:
            config.hate_words = list(HATE_WORDS)
        if not config.vulgar_words:
            config.vulgar_words = list(VULGAR_WORDS)
        return config


@dataclass
class ModAction:
    reason: str
    action: str
    duration: int
    strike: int
    warning: str
    delete: bool = True


class ModerationState:
    def __init__(self, config: ModerationConfig | None = None, strikes: dict | None = None) -> None:
        self.config = config or ModerationConfig()
        self.history: dict[str, list[tuple[float, str]]] = {}
        self.strikes: dict[str, tuple[int, float]] = {}
        self.caps_strikes: dict[str, tuple[int, float]] = {}
        self.permits: dict[str, tuple[float, int]] = {}
        self.vulgar_strikes: dict[str, dict] = dict(strikes or {})

    def export_strikes(self) -> dict:
        return self.vulgar_strikes

    def grant_permit(self, user: str, now: float) -> None:
        self.permits[user.lower()] = (now + self.config.permit_seconds, 1)

    def add_hate(self, word: str) -> str | None:
        clean = word.strip()
        if not clean:
            return "Précise le terme à interdire."
        if any(normalize_same(clean, existing) for existing in self.config.hate_words):
            return "Ce terme est déjà interdit."
        self.config.hate_words.append(clean)
        return None

    def remove_hate(self, word: str) -> str | None:
        clean = word.strip()
        kept = [item for item in self.config.hate_words if not normalize_same(clean, item)]
        if len(kept) == len(self.config.hate_words):
            return "Terme introuvable."
        self.config.hate_words = kept
        return None

    def inspect(
        self,
        user: str,
        text: str,
        now: float,
        *,
        level: str = "everyone",
        first_message: bool = False,
        exempt: bool | None = None,
    ) -> ModAction | None:
        if exempt is True:
            level = "mod"
        elif exempt is False:
            level = "everyone"
        body = text or ""
        hate_free = level in {"mod", "broadcaster"}
        ordinary_free = level in {"vip", "mod", "broadcaster"}

        if self.config.hate and not hate_free and contains_any(body, self.config.hate_words):
            return self._action("haine", "ban", 0, 1, f"@{user}, ces propos sont interdits. Tu es banni.")

        if not ordinary_free and self.config.spam_bots and self._is_spam_bot(body, first_message):
            return self._action("spam-bot", "ban", 0, 1, f"@{user}, ce message est du spam. Tu es banni.")

        if not ordinary_free and self.config.vulgar and contains_any(body, self.config.vulgar_words):
            strike = self._vulgar_strike(user, now)
            if strike >= 3:
                return self._action("vulgarite", "ban", 0, strike, f"@{user}, tu es banni après plusieurs insultes.")
            if strike == 2:
                return self._action("vulgarite", "timeout", 300, strike, f"@{user}, timeout de 5 minutes pour le langage.")
            return self._action("vulgarite", "warn", 0, strike, f"@{user}, ce langage n'est pas accepté ici.")

        if not ordinary_free and self.config.promo and self._is_promo(body):
            if self._consume_permit(user, now):
                return None
            return self._action(
                "autopromo",
                "warn",
                0,
                1,
                f"@{user}, la pub pour une autre chaîne ou un autre Discord n'est pas autorisée ici.",
            )

        if ordinary_free:
            return None

        if self.config.caps and _too_many_caps(body, self.config.caps_min_length, self.config.caps_ratio):
            return self._caps_action(user, now)

        reason = self._legacy_reason(user, body, now)
        if reason is None:
            return None
        strike = self._legacy_strike(user, now)
        return self._action(reason, "timeout", self._timeout_for(strike), strike, f"@{user}, ce message n'est pas autorisé.")

    def _action(
        self,
        reason: str,
        action: str,
        duration: int,
        strike: int,
        warning: str,
        *,
        delete: bool = True,
    ) -> ModAction:
        return ModAction(
            reason=reason,
            action=action,
            duration=duration,
            strike=strike,
            warning=warning,
            delete=delete,
        )

    def _caps_action(self, user: str, now: float) -> ModAction:
        strike = self._caps_strike(user, now)
        if strike <= 2:
            return self._action(
                "excès de majuscules",
                "warn",
                0,
                strike,
                f"@{user}, doucement sur les majuscules 😉",
                delete=False,
            )
        if strike == 3:
            return self._action(
                "excès de majuscules",
                "timeout",
                60,
                strike,
                f"@{user}, timeout de 60 secondes pour les majuscules.",
            )
        return self._action(
            "excès de majuscules",
            "timeout",
            300,
            strike,
            f"@{user}, timeout de 5 minutes pour les majuscules.",
        )

    def _caps_strike(self, user: str, now: float) -> int:
        key = user.lower()
        count, last = self.caps_strikes.get(key, (0, 0.0))
        if last and now - last > self.config.caps_window_seconds:
            count = 0
        count += 1
        self.caps_strikes[key] = (count, now)
        return count

    def _vulgar_strike(self, user: str, now: float) -> int:
        key = user.lower()
        record = self.vulgar_strikes.get(key)
        decay = self.config.vulgar_strike_days * DAY
        count = 0
        if record and now - float(record.get("at") or 0) <= decay:
            count = int(record.get("count") or 0)
        count += 1
        self.vulgar_strikes[key] = {"count": count, "at": now}
        return count

    def _is_spam_bot(self, text: str, first_message: bool) -> bool:
        if contains_any(text, self.config.spam_phrases):
            return True
        if contains_any(text, self.config.spam_domains):
            return True
        if first_message and LINK_RE.search(text) and contains_any(text, ["viewers", "followers", "primes"]):
            return True
        return False

    def _is_promo(self, text: str) -> bool:
        if contains_any(text, self.config.promo_phrases):
            return True
        folded = text.casefold()
        for marker in self.config.own_markers:
            folded = folded.replace(marker.casefold(), " ")
        if DISCORD_INVITE_RE.search(folded):
            return True
        for match in FOREIGN_SOCIAL_RE.finditer(folded):
            if match.group(1) not in {"zaeldryk"}:
                return True
        return False

    def _consume_permit(self, user: str, now: float) -> bool:
        key = user.lower()
        slot = self.permits.get(key)
        if slot is None or now > slot[0] or slot[1] <= 0:
            return False
        self.permits[key] = (slot[0], slot[1] - 1)
        return True

    def _legacy_strike(self, user: str, now: float) -> int:
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

    def _legacy_reason(self, user: str, text: str, now: float) -> str | None:
        lowered = text.casefold()
        if self.config.words:
            for word in self.config.banned_words:
                needle = word.casefold().strip()
                if needle and re.search(rf"\b{re.escape(needle)}\b", lowered):
                    return "mot interdit"
        if self.config.links and LINK_RE.search(text) and not self._only_own_links(text):
            if self._consume_permit(user, now):
                return None
            return "lien non autorisé"
        if self.config.spam and self._is_spam(user, text, now):
            return "spam"
        self._remember(user, text, now)
        return None

    def _only_own_links(self, text: str) -> bool:
        return not self._is_promo(text) and any(marker.casefold() in text.casefold() for marker in self.config.own_markers)

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


def normalize_same(left: str, right: str) -> bool:
    return normalize_text(left) == normalize_text(right)


def _too_many_caps(text: str, min_length: int, ratio: float) -> bool:
    if len(text) < min_length:
        return False
    letters = [char for char in text if char.isalpha()]
    if len(letters) < min_length:
        return False
    upper = sum(1 for char in letters if char.isupper())
    return upper / len(letters) >= ratio


def sanction_line(user: str, rule: str, action: str, stamp: str) -> str:
    """Journal d'une sanction, sans le texte du message."""
    return f"{stamp} user={user} rule={rule} action={action}\n"


def hate_command(state: ModerationState, name: str, args: str, level: str) -> str:
    if not allows(level, "mod"):
        return "Réservé aux modérateurs."
    if name == "addhate":
        error = state.add_hate(args)
        return error or "Terme ajouté à la liste des propos interdits."
    if name == "delhate":
        error = state.remove_hate(args)
        return error or "Terme retiré de la liste."
    return "Commande inconnue."
