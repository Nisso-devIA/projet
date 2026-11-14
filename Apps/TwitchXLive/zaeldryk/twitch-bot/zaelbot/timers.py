"""Messages automatiques, envoyés seulement si le chat a parlé."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Timer:
    name: str
    message: str
    interval_seconds: float
    min_messages: int
    last_sent: float = 0
    messages_since: int = 0
    start_offset_seconds: float = 0

    @classmethod
    def from_dict(cls, raw: dict) -> "Timer":
        return cls(
            name=str(raw["name"]),
            message=str(raw["message"]),
            interval_seconds=float(raw.get("interval_seconds") or raw.get("interval") or 600),
            min_messages=int(raw.get("min_messages") or 5),
            start_offset_seconds=float(raw.get("start_offset_seconds") or 0),
        )


class TimerScheduler:
    def __init__(self, timers: list[Timer], gap_seconds: float = 120) -> None:
        self.timers = timers
        self.gap_seconds = gap_seconds
        self.last_post = 0.0

    def on_chat_message(self) -> None:
        for timer in self.timers:
            timer.messages_since += 1

    def due(self, now: float) -> list[Timer]:
        if self.last_post and now - self.last_post < self.gap_seconds:
            return []
        ready = [
            timer
            for timer in self.timers
            if (timer.last_sent == 0 or now - timer.last_sent >= timer.interval_seconds)
            and timer.messages_since >= timer.min_messages
        ]
        if not ready:
            return []
        ready.sort(key=lambda timer: timer.last_sent)
        chosen = ready[0]
        chosen.last_sent = now
        chosen.messages_since = 0
        self.last_post = now
        return [chosen]
