"""Récapitulatif de fin de live, posté sur Discord sans mention globale."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone

from zaelbot.events import format_uptime

DEFAULT_RECAP_CHANNEL_ID = "1541249724902809692"


class LiveStats:
    def __init__(self, raw: dict | None = None) -> None:
        raw = raw or {}
        self.started_at = str(raw.get("started_at") or "")
        self.follows = int(raw.get("follows") or 0)
        self.subs = int(raw.get("subs") or 0)
        self.gifts = int(raw.get("gifts") or 0)
        self.raids = list(raw.get("raids") or [])
        self.chatters = {str(key): int(value) for key, value in (raw.get("chatters") or {}).items()}
        self.clip_ids = [str(item) for item in (raw.get("clip_ids") or [])]
        self.deaths = {str(key): int(value) for key, value in (raw.get("deaths") or {}).items()}
        self.recapped = bool(raw.get("recapped"))

    def begin(self, started_at: str) -> None:
        if started_at and started_at != self.started_at:
            self.__init__({"started_at": started_at})

    def add_chatter(self, login: str) -> None:
        key = (login or "").lower()
        if not key:
            return
        self.chatters[key] = self.chatters.get(key, 0) + 1

    def add_death(self, game: str, delta: int) -> None:
        name = game or "Jeu inconnu"
        self.deaths[name] = max(0, self.deaths.get(name, 0) + int(delta))

    def reset_deaths(self, game: str) -> None:
        name = game or "Jeu inconnu"
        self.deaths[name] = 0

    def note_event(self, kind: str, payload: dict) -> None:
        if kind == "follow":
            self.follows += 1
        elif kind in {"sub", "resub"}:
            self.subs += 1
        elif kind == "gift":
            try:
                self.gifts += int(payload.get("count") or 0)
            except (TypeError, ValueError):
                self.gifts += 0
        elif kind == "raid":
            self.raids.append({"user": payload.get("user") or "quelqu'un", "viewers": payload.get("viewers") or 0})

    def add_clip(self, clip_id: str) -> None:
        if clip_id and clip_id not in self.clip_ids:
            self.clip_ids.append(clip_id)

    def top_chatters(self, limit: int = 5) -> list[tuple[str, int]]:
        ordered = sorted(self.chatters.items(), key=lambda item: (-item[1], item[0]))
        return ordered[:limit]

    def export(self) -> dict:
        return {
            "started_at": self.started_at,
            "follows": self.follows,
            "subs": self.subs,
            "gifts": self.gifts,
            "raids": self.raids,
            "chatters": self.chatters,
            "clip_ids": self.clip_ids,
            "deaths": self.deaths,
            "recapped": self.recapped,
        }


def duration_text(started_at: str, ended: datetime | None = None) -> str:
    if not started_at:
        return "durée inconnue"
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return "durée inconnue"
    moment = ended or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return format_uptime(int((moment - start).total_seconds()))


def pick_top_clip(clips: list[dict]) -> dict | None:
    ranked = [clip for clip in clips if clip.get("id") or clip.get("url")]
    if not ranked:
        return None
    ranked.sort(key=lambda clip: int(clip.get("view_count") or 0), reverse=True)
    return ranked[0]


def clip_url(clip_id: str) -> str:
    return f"https://clips.twitch.tv/{clip_id}"


def build_recap(stats: LiveStats, top_clip: dict | None, ended: datetime | None = None) -> str:
    lines = [f"Fin du live. Durée : {duration_text(stats.started_at, ended)}."]
    lines.append(f"Nouveaux follows : {stats.follows}. Abonnements : {stats.subs}. Cadeaux : {stats.gifts}.")
    if stats.raids:
        raids = ", ".join(f"{item.get('user')} ({item.get('viewers')})" for item in stats.raids)
        lines.append(f"Raids : {raids}.")
    else:
        lines.append("Raids : aucun.")
    if any(stats.deaths.values()):
        deaths = ", ".join(f"{game} {count}" for game, count in stats.deaths.items() if count)
        lines.append(f"Morts : {deaths}.")
    else:
        lines.append("Morts : aucune.")
    chatters = stats.top_chatters()
    if chatters:
        lines.append("Chat : " + ", ".join(f"{name} ({count})" for name, count in chatters) + ".")
    if top_clip:
        url = top_clip.get("url") or clip_url(str(top_clip.get("id")))
        lines.append(f"Clip le plus vu : {url} ({int(top_clip.get('view_count') or 0)} vues).")
    else:
        lines.append("Pas de clip pendant ce live.")
    return "\n".join(lines)


def discord_payload(content: str) -> dict:
    cleaned = content.replace("@everyone", "").replace("@here", "")
    return {"content": cleaned[:1900], "allowed_mentions": {"parse": []}}


def post_webhook(url: str, content: str) -> int:
    """Envoie un message. L'URL n'est pas journalisée : elle contient le secret du webhook."""
    if not url:
        return 0
    data = json.dumps(discord_payload(content)).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "zaelbot"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status
    except Exception:
        return 0
