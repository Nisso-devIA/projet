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

    @classmethod
    def from_dict(cls, raw: dict) -> "Timer":
        return cls(
            name=str(raw["name"]),
            message=str(raw["message"]),
            interval_seconds=float(raw.get("interval_seconds") or raw.get("interval") or 600),
            min_messages=int(raw.get("min_messages") or 5),
        )


class TimerScheduler:
    def __init__(self, timers: list[Timer]) -> None:
        self.timers = timers

    def on_chat_message(self) -> None:
        for timer in self.timers:
            timer.messages_since += 1

    def due(self, now: float) -> list[Timer]:
        ready = []
        for timer in self.timers:
            waited = timer.last_sent == 0 or now - timer.last_sent >= timer.interval_seconds
            if waited and timer.messages_since >= timer.min_messages:
                timer.last_sent = now
                timer.messages_since = 0
                ready.append(timer)
        return ready
