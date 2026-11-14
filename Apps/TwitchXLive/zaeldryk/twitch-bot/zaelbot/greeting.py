"""Message de respect envoyé une seule fois par live."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

DEFAULT_RULES_TEXT = (
    "🐺 Bienvenue dans la meute ! Ici on reste respectueux : zéro racisme, "
    "zéro discrimination, zéro insulte et pas de pub sans autorisation. "
    "Toute haine = ban direct. Amusez-vous bien et bon live ⚔️"
)
DEFAULT_DELAY_SECONDS = 120


class LiveGreeting:
    def __init__(self, text: str, delay_seconds: int = DEFAULT_DELAY_SECONDS, sent_ids: list[str] | None = None) -> None:
        self.text = text or DEFAULT_RULES_TEXT
        self.delay_seconds = delay_seconds
        self.sent = set(sent_ids or [])
        self.pending: set[str] = set()

    def claim(self, stream_id: str) -> bool:
        if not stream_id or stream_id in self.sent or stream_id in self.pending:
            return False
        self.pending.add(stream_id)
        return True

    def mark_sent(self, stream_id: str) -> None:
        self.pending.discard(stream_id)
        self.sent.add(stream_id)

    def cancel(self, stream_id: str) -> None:
        self.pending.discard(stream_id)
        self.sent.discard(stream_id)

    def wait_seconds(self, started_at: datetime, now: datetime) -> float:
        start = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
        current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        due = start + timedelta(seconds=self.delay_seconds)
        return max(0.0, (due - current).total_seconds())
