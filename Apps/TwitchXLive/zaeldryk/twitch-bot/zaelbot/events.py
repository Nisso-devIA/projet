"""Textes des événements Twitch et du relais TikTok."""

from __future__ import annotations


DEFAULT_TEMPLATES = {
    "follow": "Merci pour le follow {user} ! Bienvenue dans la meute.",
    "sub": "Merci pour l'abonnement {user} !",
    "resub": "Merci {user} pour {months} mois d'abonnement !",
    "gift": "Merci {user} pour {count} abonnement(s) offert(s) !",
    "raid": "Bienvenue à {user} et aux {viewers} raideurs !",
    "bits": "Merci {user} pour {bits} bits !",
}


def raid_thanks_text(name: str, viewers) -> str:
    """Message du broadcaster. Un seul viewer : « 1 guerrier »."""
    login = str(name or "").strip().lstrip("@") or "quelqu'un"
    try:
        count = int(viewers)
    except (TypeError, ValueError):
        count = 0
    if count < 0:
        count = 0
    noun = "guerrier" if count == 1 else "guerriers"
    return (
        "🐺 Bienvenue au royaume de Zaelys, la meute de @"
        f"{login} ! Merci pour ce raid de {count} {noun} ⚔️"
    )


def render_event(kind: str, payload: dict, templates: dict | None = None) -> str | None:
    book = dict(DEFAULT_TEMPLATES)
    if templates:
        book.update(templates)
    template = book.get(kind)
    if not template:
        return None
    values = {
        "user": str(payload.get("user") or "quelqu'un"),
        "months": str(payload.get("months") or ""),
        "count": str(payload.get("count") or ""),
        "viewers": str(payload.get("viewers") or "0"),
        "bits": str(payload.get("bits") or "0"),
    }
    return template.format(**values)


def event_from_notification(event_type: str, event: dict) -> tuple[str, dict] | None:
    if event_type == "channel.follow":
        return "follow", {"user": event.get("user_name") or event.get("user_login")}
    if event_type == "channel.subscribe":
        if event.get("is_gift"):
            return None
        return "sub", {"user": event.get("user_name")}
    if event_type == "channel.subscription.message":
        return "resub", {
            "user": event.get("user_name"),
            "months": event.get("cumulative_months") or event.get("duration_months"),
        }
    if event_type == "channel.subscription.gift":
        return "gift", {"user": event.get("user_name"), "count": event.get("total")}
    if event_type == "channel.raid":
        return "raid", {
            "user": event.get("from_broadcaster_user_name"),
            "viewers": event.get("viewers"),
            "from_id": event.get("from_broadcaster_user_id"),
        }
    if event_type == "channel.cheer":
        return "bits", {"user": event.get("user_name"), "bits": event.get("bits")}
    return None


def tiktok_line(author: str, text: str, *, max_length: int = 180) -> str | None:
    message = " ".join((text or "").split())
    name = " ".join((author or "").split()) or "tiktok"
    if not message:
        return None
    if len(message) > max_length:
        message = message[: max_length - 1].rstrip() + "…"
    return f"🎵 {name} : {message}"


def format_uptime(total_seconds: int) -> str:
    seconds = max(0, int(total_seconds))
    hours, rem = divmod(seconds, 3600)
    minutes = rem // 60
    if hours:
        return f"{hours} h {minutes} min"
    return f"{minutes} min"
