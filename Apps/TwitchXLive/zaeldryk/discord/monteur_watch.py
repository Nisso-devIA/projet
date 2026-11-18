"""Alertes privées si un monteur touche au serveur. Aucun message public."""
from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import discord

GUILD_ID = 867426693286461490
MONTEUR_ROLE_ID = 1572574656576098335
OWNER_ID = 558595717610995712
PARIS = ZoneInfo("Europe/Paris")
WINDOW_SECONDS = 60

SENSITIVE_ACTIONS = {
    "role_create",
    "role_update",
    "role_delete",
    "channel_create",
    "channel_update",
    "channel_delete",
    "overwrite_create",
    "overwrite_update",
    "overwrite_delete",
    "member_role_update",
    "webhook_create",
    "webhook_update",
    "invite_create",
    "bot_add",
    "integration_create",
    "integration_update",
    "ban",
    "kick",
    "message_bulk_delete",
    "guild_update",
}

DANGEROUS_BITS = (
    ("administrateur", 1 << 3),
    ("gérer le serveur", 1 << 5),
    ("gérer les rôles", 1 << 28),
    ("gérer les salons", 1 << 4),
    ("gérer les webhooks", 1 << 29),
    ("bannir", 1 << 2),
    ("expulser", 1 << 1),
)

_pending: dict[tuple, dict] = {}


def action_name(entry) -> str:
    action = getattr(entry, "action", None)
    return getattr(action, "name", "") or ""


def has_monteur(member) -> bool:
    roles = getattr(member, "roles", None) or []
    for role in roles:
        if getattr(role, "id", None) == MONTEUR_ROLE_ID:
            return True
    return False


def dangerous_names(permissions) -> list[str]:
    try:
        value = int(permissions)
    except (TypeError, ValueError):
        value = int(getattr(permissions, "value", 0) or 0)
    return [label for label, bit in DANGEROUS_BITS if value & bit]


def added_roles(entry) -> list:
    before = list(getattr(entry.before, "roles", None) or [])
    after = list(getattr(entry.after, "roles", None) or [])
    before_ids = {getattr(role, "id", role) for role in before}
    return [role for role in after if getattr(role, "id", role) not in before_ids]


def is_timeout(entry) -> bool:
    after = getattr(entry.after, "communication_disabled_until", None)
    return after is not None


def target_label(entry) -> str:
    target = getattr(entry, "target", None)
    if target is None:
        return "inconnu"
    name = getattr(target, "name", None) or getattr(target, "display_name", None) or "cible"
    ident = getattr(target, "id", None)
    if ident:
        return f"{name} ({ident})"
    return str(name)


def should_alert(entry, actor_is_monteur: bool) -> str | None:
    """Retourne le motif, ou None si l'entrée ne concerne pas le monteur."""
    name = action_name(entry)
    if name == "member_role_update":
        risky = []
        for role in added_roles(entry):
            risky.extend(dangerous_names(getattr(role, "permissions", 0)))
        target = getattr(entry, "target", None)
        if risky and (has_monteur(target) or any(getattr(role, "id", None) == MONTEUR_ROLE_ID for role in added_roles(entry))):
            return "rôle dangereux ajouté au monteur : " + ", ".join(dict.fromkeys(risky))
    if not actor_is_monteur:
        return None
    if name == "member_update":
        return "timeout" if is_timeout(entry) else None
    if name in SENSITIVE_ACTIONS:
        return name.replace("_", " ")
    return None


def alert_text(entry, reason: str, when: datetime, count: int) -> str:
    actor = getattr(entry, "user", None)
    who = "inconnu"
    if actor is not None:
        who = f"{getattr(actor, 'name', 'inconnu')} ({getattr(actor, 'id', '?')})"
    lines = [
        "Alerte monteur",
        f"Qui : {who}",
        f"Quoi : {reason}",
        f"Où : {target_label(entry)}",
        f"Heure : {when.strftime('%Y-%m-%d %H:%M')} Europe/Paris",
    ]
    if count > 1:
        lines.append(f"Répété {count} fois en 1 minute.")
    return "\n".join(lines)


async def _flush(bot, key: tuple, window: float) -> None:
    await asyncio.sleep(window)
    slot = _pending.pop(key, None)
    if slot is None:
        return
    text = alert_text(slot["entry"], slot["reason"], slot["when"], slot["count"])
    try:
        owner = bot.get_user(OWNER_ID) or await bot.fetch_user(OWNER_ID)
        await owner.send(text)
    except (discord.HTTPException, discord.Forbidden) as exc:
        print(f"Monteur alert DM failed: {type(exc).__name__}", flush=True)


def queue_alert(bot, entry, reason: str, window: float = WINDOW_SECONDS) -> None:
    actor = getattr(entry, "user", None)
    target = getattr(entry, "target", None)
    key = (
        getattr(actor, "id", 0),
        reason,
        getattr(target, "id", 0),
    )
    slot = _pending.get(key)
    if slot is None:
        when = datetime.now(PARIS)
        _pending[key] = {
            "entry": entry,
            "reason": reason,
            "when": when,
            "count": 1,
            "task": asyncio.create_task(_flush(bot, key, window)),
        }
        return
    slot["count"] += 1


async def handle_entry(bot, entry) -> None:
    guild = getattr(entry, "guild", None)
    if guild is None or getattr(guild, "id", None) != GUILD_ID:
        return
    actor = getattr(entry, "user", None)
    reason = should_alert(entry, has_monteur(actor))
    if reason is None:
        return
    queue_alert(bot, entry, reason)


def register_monteur_watch(bot) -> None:
    """Branche le journal d'audit. N'envoie rien au démarrage."""

    @bot.listen("on_audit_log_entry_create")
    async def on_audit_log_entry_create(entry):
        try:
            await handle_entry(bot, entry)
        except Exception as exc:
            print(f"Monteur watch error: {type(exc).__name__}", flush=True)

    print("Monteur watch registered", flush=True)
