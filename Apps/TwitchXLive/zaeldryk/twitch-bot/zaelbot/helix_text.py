"""Mise en forme des réponses Helix, sans appel réseau."""

from __future__ import annotations

from datetime import datetime, timezone


def uptime_text(started_at: str | None, now: datetime) -> str:
    if not started_at:
        return "Le live n'est pas en cours."
    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    seconds = int((current - started).total_seconds())
    if seconds < 0:
        return "Le live n'est pas en cours."
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    if hours:
        return f"En live depuis {hours} h {minutes} min."
    return f"En live depuis {minutes} min."


def followage_text(login: str, followed_at: str | None, now: datetime) -> str:
    if not followed_at:
        return f"{login} ne follow pas la chaîne."
    followed = datetime.fromisoformat(followed_at.replace("Z", "+00:00"))
    current = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    days = max(0, (current - followed).days)
    return f"{login} follow depuis {days} jour(s)."


def shoutout_text(login: str) -> str:
    return f"Allez voir https://twitch.tv/{login.lower()} !"
