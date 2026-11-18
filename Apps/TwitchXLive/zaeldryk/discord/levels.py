"""XP, levels and rank roles for Zaeldryk Guardian.

Everyone starts at 0. Text and voice gains are stored in SQLite.
The level curve matches the usual MEE6 step: 5*L^2 + 50*L + 100.
"""

from __future__ import annotations

import random
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import discord
from discord import app_commands

GUILD_ID = 867426693286461490
REGLEMENT_CHANNEL_ID = 1541249727662784612  # 📖-règlement
COMMANDES_CHANNEL_ID = 1541249735883624568  # 🤖-commandes
LEVEL_CHANNEL_ID = 1541398657851461662  # 📊-level
AFK_CHANNEL_ID = 1541249742409961512  # 🎙️ AFK
STATE_PATH = Path("/home/ubuntu/zaeldryk/state/levels.sqlite")

TEXT_XP_MIN = 15
TEXT_XP_MAX = 25
TEXT_COOLDOWN_SECONDS = 60
TEXT_MIN_CHARS = 3
VOICE_XP_PER_MINUTE = 10
IGNORED_TEXT_CHANNELS = {REGLEMENT_CHANNEL_ID, COMMANDES_CHANNEL_ID}

# Highest rank last. Colours stay on the black/gold theme. No extra permissions.
RANK_LADDER = (
    (5, "🐾 Louveteau", 0x8D6E63),
    (10, "🏹 Éclaireur", 0xC9A227),
    (20, "🗡️ Chasseur", 0xF1C40F),
    (30, "🛡️ Gardien du Royaume", 0x2B2B2B),
    (50, "🌕 Alpha", 0xFFD700),
)
STAFF_ROLE_NAMES = (
    "🌑 Ombre",
    "⚔️ Sentinelle",
    "👑 Archonte de Zaeldryk",
    "BOT_modération",
)


def xp_to_next(level: int) -> int:
    """XP required to leave `level` for the next one."""
    return 5 * level * level + 50 * level + 100


def total_xp_for_level(level: int) -> int:
    total = 0
    for current in range(level):
        total += xp_to_next(current)
    return total


def level_from_xp(xp: int) -> int:
    level = 0
    remaining = max(0, xp)
    while remaining >= xp_to_next(level):
        remaining -= xp_to_next(level)
        level += 1
    return level


def progress_in_level(xp: int) -> tuple[int, int, int]:
    """Return level, XP into the current level, and XP needed to advance."""
    level = level_from_xp(xp)
    base = total_xp_for_level(level)
    return level, xp - base, xp_to_next(level)


def progress_bar(into: int, need: int, width: int = 12) -> str:
    if need <= 0:
        return "█" * width
    filled = int(round(max(0, min(need, into)) / need * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def rank_index_for_level(level: int) -> int | None:
    earned = [index for index, (threshold, _name, _color) in enumerate(RANK_LADDER) if level >= threshold]
    if not earned:
        return None
    return earned[-1]


def text_xp_allowed(content: str, channel_id: int | None, parent_id: int | None, author_is_bot: bool) -> bool:
    if author_is_bot:
        return False
    if channel_id in IGNORED_TEXT_CHANNELS or parent_id in IGNORED_TEXT_CHANNELS:
        return False
    return len((content or "").strip()) >= TEXT_MIN_CHARS


def cooldown_elapsed(last_at: float | None, now: float, cooldown: float = TEXT_COOLDOWN_SECONDS) -> bool:
    if last_at is None:
        return True
    return now - last_at >= cooldown


def voice_xp_allowed(
    *,
    channel_id: int,
    afk_channel_id: int | None,
    non_bot_members: int,
    self_muted: bool,
    self_deafened: bool,
    author_is_bot: bool,
) -> bool:
    if author_is_bot or self_muted or self_deafened:
        return False
    if channel_id == AFK_CHANNEL_ID or (afk_channel_id is not None and channel_id == afk_channel_id):
        return False
    return non_bot_members >= 2


@dataclass
class XpGain:
    user_id: int
    old_xp: int
    new_xp: int
    old_level: int
    new_level: int
    amount: int


class LevelStore:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS members (
                    user_id INTEGER PRIMARY KEY,
                    xp INTEGER NOT NULL DEFAULT 0,
                    last_text_at REAL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, user_id: int) -> tuple[int, float | None]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT xp, last_text_at FROM members WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return 0, None
        return int(row["xp"]), row["last_text_at"]

    def grant_text(self, user_id: int, now: float | None = None) -> XpGain | None:
        moment = time.time() if now is None else now
        amount = random.randint(TEXT_XP_MIN, TEXT_XP_MAX)
        return self._grant(user_id, amount, moment, enforce_text_cooldown=True)

    def grant_voice(self, user_id: int) -> XpGain | None:
        return self._grant(user_id, VOICE_XP_PER_MINUTE, time.time(), enforce_text_cooldown=False)

    def _grant(
        self,
        user_id: int,
        amount: int,
        now: float,
        *,
        enforce_text_cooldown: bool,
    ) -> XpGain | None:
        with self._lock, self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT xp, last_text_at FROM members WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            old_xp = int(row["xp"]) if row else 0
            last_text = row["last_text_at"] if row else None
            if enforce_text_cooldown and not cooldown_elapsed(last_text, now):
                conn.rollback()
                return None
            new_xp = old_xp + amount
            if row is None:
                conn.execute(
                    "INSERT INTO members (user_id, xp, last_text_at) VALUES (?, ?, ?)",
                    (user_id, new_xp, now if enforce_text_cooldown else None),
                )
            elif enforce_text_cooldown:
                conn.execute(
                    "UPDATE members SET xp = ?, last_text_at = ? WHERE user_id = ?",
                    (new_xp, now, user_id),
                )
            else:
                conn.execute(
                    "UPDATE members SET xp = ? WHERE user_id = ?",
                    (new_xp, user_id),
                )
            conn.commit()
        return XpGain(
            user_id=user_id,
            old_xp=old_xp,
            new_xp=new_xp,
            old_level=level_from_xp(old_xp),
            new_level=level_from_xp(new_xp),
            amount=amount,
        )

    def position(self, user_id: int, xp: int) -> int:
        """1-based place among members who have XP. Ties break toward the smaller id."""
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1 + COUNT(*) AS place
                FROM members
                WHERE xp > 0 AND (xp > ? OR (xp = ? AND user_id < ?))
                """,
                (xp, xp, user_id),
            ).fetchone()
        return int(row["place"])

    def top(self, limit: int = 10) -> list[tuple[int, int]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT user_id, xp FROM members
                WHERE xp > 0
                ORDER BY xp DESC, user_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [(int(row["user_id"]), int(row["xp"])) for row in rows]


STORE = LevelStore()


def register_level_commands(bot) -> None:
    @bot.tree.command(
        name="rang",
        description="Niveau, XP et place sur le serveur",
        guild=discord.Object(id=GUILD_ID),
    )
    @app_commands.describe(membre="Membre à consulter")
    async def rang_cmd(interaction: discord.Interaction, membre: discord.Member | None = None):
        target = membre or interaction.user
        if not isinstance(target, discord.Member):
            await interaction.response.send_message("Membre introuvable.", ephemeral=True)
            return
        xp, _last = STORE.get(target.id)
        level, into, need = progress_in_level(xp)
        place = STORE.position(target.id, xp) if xp > 0 else None
        rank = rank_index_for_level(level)
        rank_name = RANK_LADDER[rank][1] if rank is not None else "Aucun rang"
        place_line = f"Place : **#{place}**" if place else "Place : pas encore classé"
        embed = discord.Embed(
            title=f"Niveau {level}",
            description=(
                f"{target.mention}\n"
                f"{progress_bar(into, need)} **{into}**/{need} XP\n"
                f"Total : **{xp}** XP\n"
                f"Rang : **{rank_name}**\n"
                f"{place_line}"
            ),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=[target]),
        )

    @bot.tree.command(
        name="classement",
        description="Les 10 membres avec le plus d'XP",
        guild=discord.Object(id=GUILD_ID),
    )
    async def classement_cmd(interaction: discord.Interaction):
        rows = STORE.top(10)
        if not rows:
            await interaction.response.send_message(
                "Personne n'a encore d'XP.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        lines = []
        for index, (user_id, xp) in enumerate(rows, start=1):
            level = level_from_xp(xp)
            member = interaction.guild.get_member(user_id) if interaction.guild else None
            name = member.display_name if member else f"Membre {user_id}"
            lines.append(f"**{index}.** {name} — niveau **{level}** · {xp} XP")
        embed = discord.Embed(
            title="Classement",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def ensure_rank_roles(guild) -> list:
    import discord

    by_name = {role.name: role for role in guild.roles}
    ordered = []
    for _threshold, name, color in RANK_LADDER:
        role = by_name.get(name)
        if role is None:
            role = await guild.create_role(
                name=name,
                permissions=discord.Permissions.none(),
                colour=discord.Color(color),
                hoist=False,
                mentionable=False,
                reason="Rôle de niveau Zaeldryk",
            )
        ordered.append(role)
    await _place_rank_roles(guild, ordered)
    return ordered


async def _place_rank_roles(guild, ordered_low_to_high) -> None:
    rank_ids = {role.id for role in ordered_low_to_high}
    others = [role for role in guild.roles if not role.is_default() and role.id not in rank_ids]
    others.sort(key=lambda role: role.position)
    insert_at = len(others)
    for index, role in enumerate(others):
        if role.name in STAFF_ROLE_NAMES:
            insert_at = index
            break
    sequence = others[:insert_at] + list(ordered_low_to_high) + others[insert_at:]
    positions = {role: index + 1 for index, role in enumerate(sequence)}
    try:
        await guild.edit_role_positions(positions=positions, reason="Rôles de niveau sous le staff")
    except Exception as exc:
        print(f"Rank role position error: {exc}", flush=True)


def _ignored_channel(channel) -> bool:
    channel_id = getattr(channel, "id", None)
    parent = getattr(channel, "parent_id", None)
    if parent is None and getattr(channel, "parent", None) is not None:
        parent = channel.parent.id
    return channel_id in IGNORED_TEXT_CHANNELS or parent in IGNORED_TEXT_CHANNELS


async def _announce_and_sync(member, gain: XpGain) -> None:
    if gain.new_level <= gain.old_level:
        return
    try:
        await _sync_rank_role(member, gain.new_level)
    except Exception as exc:
        print(f"Rank role sync error {member.id}: {exc}", flush=True)
    channel = member.guild.get_channel(LEVEL_CHANNEL_ID)
    if channel is None:
        try:
            channel = await member.guild.fetch_channel(LEVEL_CHANNEL_ID)
        except Exception as exc:
            print(f"Level channel missing: {exc}", flush=True)
            return
    import discord

    embed = discord.Embed(
        description=f"🐺 {member.mention} passe niveau {gain.new_level} !",
        color=discord.Color.gold(),
    )
    try:
        await channel.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=[member]),
        )
    except Exception as exc:
        print(f"Level-up announce error: {exc}", flush=True)


async def _sync_rank_role(member, level: int) -> None:
    wanted_index = rank_index_for_level(level)
    wanted_name = RANK_LADDER[wanted_index][1] if wanted_index is not None else None
    roles_by_name = {role.name: role for role in member.guild.roles}
    wanted = roles_by_name.get(wanted_name) if wanted_name else None
    current = [roles_by_name[name] for _t, name, _c in RANK_LADDER if name in roles_by_name and roles_by_name[name] in member.roles]
    remove = [role for role in current if wanted is None or role.id != wanted.id]
    if remove:
        await member.remove_roles(*remove, reason="Niveau Zaeldryk")
    if wanted is not None and wanted not in member.roles:
        await member.add_roles(wanted, reason="Niveau Zaeldryk")


async def handle_text_xp(message) -> None:
    if message.guild is None or message.guild.id != GUILD_ID:
        return
    parent_id = getattr(message.channel, "parent_id", None)
    if parent_id is None and getattr(message.channel, "parent", None) is not None:
        parent_id = message.channel.parent.id
    if not text_xp_allowed(
        message.content or "",
        getattr(message.channel, "id", None),
        parent_id,
        message.author.bot,
    ):
        return
    gain = STORE.grant_text(message.author.id)
    if gain is None or gain.new_level <= gain.old_level:
        return
    await _announce_and_sync(message.author, gain)


_voice_started = False


async def start_level_system(bot) -> None:
    global _voice_started
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("Level system: guild not cached", flush=True)
        return
    try:
        roles = await ensure_rank_roles(guild)
        summary = ", ".join(f"{role.name}={role.id}" for role in roles)
        print(f"Rank roles ready: {summary}", flush=True)
    except Exception as exc:
        print(f"Rank role setup error: {exc}", flush=True)
    if _voice_started:
        return
    _voice_started = True
    bot.loop.create_task(_voice_loop(bot))
    print("Level system registered", flush=True)


async def _voice_loop(bot) -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        await _sleep(60)
        if bot.is_closed():
            return
        guild = bot.get_guild(GUILD_ID)
        if guild is None:
            continue
        afk_id = guild.afk_channel.id if guild.afk_channel else None
        for channel in getattr(guild, "voice_channels", []):
            humans = [member for member in channel.members if not member.bot]
            for member in humans:
                voice = member.voice
                if voice is None:
                    continue
                if not voice_xp_allowed(
                    channel_id=channel.id,
                    afk_channel_id=afk_id,
                    non_bot_members=len(humans),
                    self_muted=bool(voice.self_mute),
                    self_deafened=bool(voice.self_deaf),
                    author_is_bot=member.bot,
                ):
                    continue
                try:
                    gain = STORE.grant_voice(member.id)
                except Exception as exc:
                    print(f"Voice XP error {member.id}: {exc}", flush=True)
                    continue
                if gain and gain.new_level > gain.old_level:
                    await _announce_and_sync(member, gain)


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
