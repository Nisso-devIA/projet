"""Members who have not passed the captcha.

The clock starts at deployment for people already in the server, and at
joined_at for people who arrive later. One DM after 24 h, a kick after 72 h.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands

GUILD_ID = 867426693286461490
REGLEMENT_CHANNEL_ID = 1541249727662784612
STAFF_CATEGORY_ID = 1541249736785403945
LOG_CHANNEL_NAME = "📋-logs-captcha"
STATE_PATH = Path("/home/ubuntu/zaeldryk/state/unverified.sqlite")
PARIS = ZoneInfo("Europe/Paris")
REMINDER_AFTER = timedelta(hours=24)
KICK_AFTER = timedelta(hours=72)
SCAN_INTERVAL_SECONDS = 15 * 60
DISCIPLE_ROLE = "🐺 Disciple"
STAFF_ROLES = (
    "⚔️ Sentinelle",
    "👑 Archonte de Zaeldryk",
    "🌑 Ombre",
)
KICK_REASON = "Captcha non validé après 72 h"
CAUSE_LEFT = "Parti de lui-même"
CAUSE_KICK = "Expulsé par le bot après 72 h"
RULES_URL = (
    f"https://discord.com/channels/{GUILD_ID}/{REGLEMENT_CHANNEL_ID}"
)

_started = False
_log_channel_id: int | None = None


def clock_start(joined_at: datetime, deployed_at: datetime) -> datetime:
    return max(_aware(joined_at), _aware(deployed_at))


def reminder_at(start: datetime) -> datetime:
    return start + REMINDER_AFTER


def kick_at(start: datetime) -> datetime:
    return start + KICK_AFTER


def is_due(moment: datetime, now: datetime) -> bool:
    return _aware(now) >= _aware(moment)


def is_kick_protected(role_names: set[str], *, is_bot: bool, is_owner: bool) -> bool:
    if is_bot or is_owner:
        return True
    return bool(role_names & set(STAFF_ROLES))


def can_view_unverified(
    role_names: set[str],
    *,
    administrator: bool,
    manage_guild: bool,
    manage_messages: bool,
) -> bool:
    if administrator or manage_guild or manage_messages:
        return True
    return bool(role_names & set(STAFF_ROLES))


def format_span(delta: timedelta) -> str:
    seconds = max(0, int(delta.total_seconds()))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days} j {hours} h"
    if hours:
        return f"{hours} h {minutes} min"
    return f"{minutes} min"


def format_paris(moment: datetime) -> str:
    local = _aware(moment).astimezone(PARIS)
    return local.strftime("%d/%m/%Y %H:%M")


def _aware(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


class UnverifiedStore:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    user_id INTEGER PRIMARY KEY,
                    reminded_at TEXT NOT NULL,
                    dm_ok INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS kicks (
                    user_id INTEGER PRIMARY KEY,
                    marked_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS departures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    joined_at TEXT,
                    left_at TEXT NOT NULL,
                    duration_seconds INTEGER,
                    cause TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def deployed_at(self, now: datetime | None = None) -> datetime:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'deployed_at'").fetchone()
            if row is not None:
                return datetime.fromisoformat(row["value"])
            moment = _aware(now or datetime.now(timezone.utc))
            conn.execute(
                "INSERT INTO meta (key, value) VALUES ('deployed_at', ?)",
                (moment.isoformat(),),
            )
            conn.commit()
            return moment

    def reminder_status(self, user_id: int) -> str:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT dm_ok FROM reminders WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return "non"
        if int(row["dm_ok"]):
            return "oui"
        return "non (DM fermés)"

    def mark_reminder(self, user_id: int, *, dm_ok: bool, when: datetime | None = None) -> None:
        moment = _aware(when or datetime.now(timezone.utc)).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO reminders (user_id, reminded_at, dm_ok)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    reminded_at = excluded.reminded_at,
                    dm_ok = excluded.dm_ok
                """,
                (user_id, moment, 1 if dm_ok else 0),
            )
            conn.commit()

    def already_reminded(self, user_id: int) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM reminders WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return row is not None

    def mark_bot_kick(self, user_id: int, when: datetime | None = None) -> None:
        moment = _aware(when or datetime.now(timezone.utc)).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO kicks (user_id, marked_at) VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET marked_at = excluded.marked_at
                """,
                (user_id, moment),
            )
            conn.commit()

    def consume_bot_kick(self, user_id: int) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT 1 FROM kicks WHERE user_id = ?", (user_id,)).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM kicks WHERE user_id = ?", (user_id,))
            conn.commit()
            return True

    def add_departure(
        self,
        user_id: int,
        username: str,
        joined_at: datetime | None,
        left_at: datetime,
        cause: str,
    ) -> None:
        duration = None
        joined_text = None
        if joined_at is not None:
            joined = _aware(joined_at)
            joined_text = joined.isoformat()
            duration = max(0, int((_aware(left_at) - joined).total_seconds()))
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO departures
                    (user_id, username, joined_at, left_at, duration_seconds, cause)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, username, joined_text, _aware(left_at).isoformat(), duration, cause),
            )
            conn.commit()

    def recent_departures(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._lock, self._connect() as conn:
            return conn.execute(
                """
                SELECT user_id, username, joined_at, left_at, duration_seconds, cause
                FROM departures
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()


STORE = UnverifiedStore()


def member_role_names(member: discord.Member) -> set[str]:
    return {role.name for role in member.roles}


def has_disciple(member: discord.Member) -> bool:
    return DISCIPLE_ROLE in member_role_names(member)


def protected_member(member: discord.Member) -> bool:
    return is_kick_protected(
        member_role_names(member),
        is_bot=member.bot,
        is_owner=member.guild is not None and member.id == member.guild.owner_id,
    )


def staff_member(member: discord.Member) -> bool:
    perms = member.guild_permissions
    return can_view_unverified(
        member_role_names(member),
        administrator=perms.administrator,
        manage_guild=perms.manage_guild,
        manage_messages=perms.manage_messages,
    )


def reminder_text(display_name: str) -> str:
    return (
        f"Salut {display_name} 🐺\n\n"
        "Tu as rejoint le Royaume ZAELDRYK, mais la vérification n’est pas encore faite.\n\n"
        "Va dans 📖-règlement et clique sur « J'accepte le règlement » :\n"
        f"{RULES_URL}\n\n"
        "Sans captcha au bout de 72 h, tu seras retiré du serveur. "
        "Tu pourras revenir quand tu veux et recommencer.\n\n"
        "À bientôt parmi les Zaelrys ⚔️"
    )


def register_unverified_commands(bot) -> None:
    @bot.tree.command(
        name="non-verifies",
        description="Membres sans captcha, ou les derniers départs",
        guild=discord.Object(id=GUILD_ID),
    )
    @app_commands.describe(partis="Afficher les 20 derniers départs sans captcha")
    async def non_verifies_cmd(interaction: discord.Interaction, partis: bool = False):
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user):
            await interaction.response.send_message("Réservé au staff.", ephemeral=True)
            return
        if partis:
            await interaction.response.send_message(
                embed=_departures_embed(),
                ephemeral=True,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Serveur introuvable.", ephemeral=True)
            return
        lines, mentions = _pending_lines(guild)
        embed = discord.Embed(
            title=f"Sans captcha · {len(lines)}",
            description=("\n\n".join(lines) if lines else "Tout le monde est vérifié.")[:4000],
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=mentions),
        )


def _pending_lines(guild: discord.Guild) -> tuple[list[str], list[discord.Member]]:
    deployed = STORE.deployed_at()
    rows = []
    for member in guild.members:
        if member.bot or has_disciple(member) or member.joined_at is None:
            continue
        if member.id == guild.owner_id:
            continue
        start = clock_start(member.joined_at, deployed)
        rows.append((kick_at(start), member, start))
    rows.sort(key=lambda item: item[0])
    lines = []
    mentions = []
    for due, member, start in rows:
        reminder = STORE.reminder_status(member.id)
        if protected_member(member):
            kick_line = "Expulsion : non concerné"
        else:
            kick_line = f"Expulsion prévue : {format_paris(due)} (Paris)"
        lines.append(
            f"{member.mention}\n"
            f"Arrivée : {format_paris(member.joined_at)} (Paris) · "
            f"depuis {format_span(datetime.now(timezone.utc) - _aware(member.joined_at))}\n"
            f"Rappel : {reminder}\n"
            f"{kick_line}"
        )
        mentions.append(member)
    return lines, mentions


def _departures_embed() -> discord.Embed:
    rows = STORE.recent_departures(20)
    if not rows:
        return discord.Embed(
            title="Départs sans captcha",
            description="Aucun départ enregistré.",
            color=discord.Color.gold(),
        )
    lines = []
    for row in rows:
        joined = "inconnue"
        if row["joined_at"]:
            joined = format_paris(datetime.fromisoformat(row["joined_at"]))
        left = format_paris(datetime.fromisoformat(row["left_at"]))
        if row["duration_seconds"] is None:
            stayed = "durée inconnue"
        else:
            stayed = format_span(timedelta(seconds=int(row["duration_seconds"])))
        lines.append(
            f"**{row['username']}** (`{row['user_id']}`)\n"
            f"Arrivée : {joined} · resté {stayed}\n"
            f"Parti le {left} (Paris) · {row['cause']}"
        )
    return discord.Embed(
        title="20 derniers départs sans captcha",
        description="\n\n".join(lines)[:4000],
        color=discord.Color.gold(),
    )


async def ensure_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    global _log_channel_id
    found = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if found is not None:
        _log_channel_id = found.id
        return found
    category = guild.get_channel(STAFF_CATEGORY_ID)
    if category is None:
        print("Captcha log category missing", flush=True)
        return None
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
    }
    disciple = discord.utils.get(guild.roles, name=DISCIPLE_ROLE)
    if disciple is not None:
        overwrites[disciple] = discord.PermissionOverwrite(view_channel=False)
    for name in STAFF_ROLES:
        role = discord.utils.get(guild.roles, name=name)
        if role is not None:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True,
                send_messages=True,
            )
    channel = await guild.create_text_channel(
        LOG_CHANNEL_NAME,
        category=category,
        overwrites=overwrites,
        topic="Départs des membres qui n’ont pas validé le captcha",
        reason="Journal staff des départs sans captcha",
    )
    _log_channel_id = channel.id
    print(f"Captcha departure log created: {channel.name}={channel.id}", flush=True)
    return channel


async def start_unverified_watch(bot) -> None:
    global _started
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("Unverified watch: guild not cached", flush=True)
        return
    deployed = STORE.deployed_at()
    try:
        channel = await ensure_log_channel(guild)
        if channel is not None:
            print(f"Captcha departure log: {channel.name}={channel.id}", flush=True)
    except Exception as exc:
        print(f"Captcha log channel error: {exc}", flush=True)
    pending = _unverified_members(guild)
    first_reminder, first_kick = _earliest_deadlines(pending, deployed)
    print(f"Unverified humans: {len(pending)}", flush=True)
    if first_reminder is not None:
        print(f"First reminder at {format_paris(first_reminder)} Paris", flush=True)
        print(f"First kick at {format_paris(first_kick)} Paris", flush=True)
    if _started:
        return
    _started = True
    bot.loop.create_task(_watch_loop(bot))
    print("Unverified watch registered", flush=True)


def _unverified_members(guild: discord.Guild) -> list[discord.Member]:
    return [
        member
        for member in guild.members
        if not member.bot and not has_disciple(member) and member.joined_at is not None
    ]


def _earliest_deadlines(members: list[discord.Member], deployed: datetime):
    reminders = []
    kicks = []
    for member in members:
        if protected_member(member):
            continue
        start = clock_start(member.joined_at, deployed)
        reminders.append(reminder_at(start))
        kicks.append(kick_at(start))
    if not reminders:
        return None, None
    return min(reminders), min(kicks)


async def _watch_loop(bot) -> None:
    import asyncio

    await bot.wait_until_ready()
    await asyncio.sleep(20)
    while not bot.is_closed():
        try:
            await scan_unverified(bot)
        except Exception as exc:
            print(f"Unverified scan error: {exc}", flush=True)
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


async def scan_unverified(bot) -> None:
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return
    if not guild.chunked:
        await guild.chunk()
    deployed = STORE.deployed_at()
    now = datetime.now(timezone.utc)
    for member in list(guild.members):
        if member.bot or has_disciple(member) or member.joined_at is None:
            continue
        if protected_member(member):
            continue
        start = clock_start(member.joined_at, deployed)
        if is_due(kick_at(start), now):
            await _kick(member)
            continue
        if is_due(reminder_at(start), now) and not STORE.already_reminded(member.id):
            await _remind(member)


async def _remind(member: discord.Member) -> None:
    try:
        await member.send(reminder_text(member.display_name))
    except discord.Forbidden:
        STORE.mark_reminder(member.id, dm_ok=False)
        print(f"Unverified reminder DM closed {member.id}", flush=True)
        return
    except discord.HTTPException as exc:
        print(f"Unverified reminder error {member.id}: {exc}", flush=True)
        return
    STORE.mark_reminder(member.id, dm_ok=True)
    print(f"Unverified reminder sent {member.id}", flush=True)


async def _kick(member: discord.Member) -> None:
    fresh = member.guild.get_member(member.id)
    if fresh is None or fresh.bot or has_disciple(fresh) or protected_member(fresh):
        return
    STORE.mark_bot_kick(fresh.id)
    try:
        await fresh.kick(reason=KICK_REASON)
    except discord.HTTPException as exc:
        STORE.consume_bot_kick(fresh.id)
        print(f"Unverified kick error {fresh.id}: {exc}", flush=True)
        return
    print(f"Unverified kick {fresh.id}", flush=True)


async def record_unverified_departure(member: discord.Member) -> None:
    if member.bot or has_disciple(member):
        return
    cause = CAUSE_KICK if STORE.consume_bot_kick(member.id) else CAUSE_LEFT
    left_at = datetime.now(timezone.utc)
    STORE.add_departure(member.id, str(member), member.joined_at, left_at, cause)
    await _post_departure(member, left_at, cause)


async def _post_departure(member: discord.Member, left_at: datetime, cause: str) -> None:
    channel = None
    if _log_channel_id is not None:
        channel = member.guild.get_channel(_log_channel_id)
    if channel is None:
        channel = await ensure_log_channel(member.guild)
    if channel is None:
        print(f"Captcha departure not posted {member.id}", flush=True)
        return
    if member.joined_at is None:
        arrived = "inconnue"
        stayed = "inconnue"
    else:
        arrived = f"{format_paris(member.joined_at)} (Paris)"
        stayed = format_span(left_at - _aware(member.joined_at))
    embed = discord.Embed(
        title="Départ sans captcha",
        description=(
            f"**{member}**\n"
            f"ID : `{member.id}`\n"
            f"Arrivée : {arrived}\n"
            f"Durée : {stayed}\n"
            f"Cause : {cause}"
        ),
        color=discord.Color.gold(),
    )
    try:
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException as exc:
        print(f"Captcha departure post error {member.id}: {exc}", flush=True)
