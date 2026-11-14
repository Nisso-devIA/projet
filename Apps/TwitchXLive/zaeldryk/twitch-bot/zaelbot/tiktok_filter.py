"""Filtre anti-spam du relais TikTok, sans connexion réseau."""

from __future__ import annotations


class TikTokFilter:
    def __init__(self, *, repeat_seconds: float = 20) -> None:
        self.repeat_seconds = repeat_seconds
        self.last: dict[str, tuple[str, float]] = {}

    def accept(self, author: str, text: str, now: float) -> bool:
        key = author.casefold()
        previous = self.last.get(key)
        if previous and previous[0] == text and now - previous[1] < self.repeat_seconds:
            return False
        self.last[key] = (text, now)
        return True
