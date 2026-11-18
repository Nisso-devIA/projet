"""Compteur de morts, un total par jeu, gardé dans data/."""

from __future__ import annotations


class DeathCounter:
    def __init__(self, game: str = "", counts: dict | None = None) -> None:
        self.game = (game or "").strip() or "Jeu inconnu"
        self.counts = {str(key): int(value) for key, value in (counts or {}).items()}

    def set_game(self, name: str) -> None:
        clean = " ".join((name or "").split())
        if clean:
            self.game = clean[:80]

    def total(self) -> int:
        return int(self.counts.get(self.game, 0))

    def add(self, delta: int = 1) -> int:
        value = max(0, self.total() + int(delta))
        self.counts[self.game] = value
        return value

    def reset(self) -> int:
        self.counts[self.game] = 0
        return 0

    def export(self) -> dict:
        return {"game": self.game, "counts": self.counts}

    @classmethod
    def from_dict(cls, raw: dict | None) -> "DeathCounter":
        raw = raw or {}
        counts = raw.get("counts") if isinstance(raw.get("counts"), dict) else {}
        return cls(str(raw.get("game") or ""), counts)
