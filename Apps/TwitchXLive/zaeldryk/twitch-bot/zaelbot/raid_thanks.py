"""Remerciement de raid entrant, une fois par id d'événement EventSub."""

from __future__ import annotations

from zaelbot.events import raid_thanks_text


class SeenRaids:
    def __init__(self, ids: list[str] | None = None, limit: int = 400) -> None:
        self.limit = limit
        self.ids: list[str] = []
        self._known: set[str] = set()
        for item in ids or []:
            self._remember(str(item))

    def _remember(self, event_id: str) -> None:
        if not event_id or event_id in self._known:
            return
        self._known.add(event_id)
        self.ids.append(event_id)
        overflow = len(self.ids) - self.limit
        if overflow > 0:
            for dropped in self.ids[:overflow]:
                self._known.discard(dropped)
            self.ids = self.ids[overflow:]

    def claim(self, event_id: str, name: str, viewers) -> str | None:
        event_id = str(event_id or "").strip()
        if not event_id or event_id in self._known:
            return None
        self._remember(event_id)
        return raid_thanks_text(name, viewers)

    def export(self) -> dict:
        return {"ids": list(self.ids)}


def chat_body(broadcaster_id: str, message: str) -> dict:
    return {
        "broadcaster_id": broadcaster_id,
        "sender_id": broadcaster_id,
        "message": message,
    }
