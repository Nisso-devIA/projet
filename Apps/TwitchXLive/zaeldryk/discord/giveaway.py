"""Giveaways du royaume. La logique ne contacte pas Discord."""

from __future__ import annotations

import json
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from discord import app_commands

GUILD_ID = 867426693286461490
DEFAULT_CHANNEL_ID = 1571186470696259584
STATE_PATH = Path("/home/ubuntu/zaeldryk/state/giveaways.json")
JOIN_PREFIX = "giveaway_join:"
EMBED_COLOR = 15844367
MIN_SECONDS = 60
MAX_SECONDS = 14 * 24 * 3600

_DURATION = re.compile(
    r"^\s*(\d+)\s*(m|min|mins|minute|minutes|h|heure|heures|j|jour|jours|d|day|days)?\s*$",
    re.IGNORECASE,
)


def is_giveaway_admin(is_owner: bool, administrator: bool) -> bool:
    return bool(is_owner or administrator)


def parse_duration(raw: str) -> int | None:
    match = _DURATION.match(raw or "")
    if not match:
        return None
    amount = int(match.group(1))
    unit = (match.group(2) or "m").lower()
    if unit.startswith("h"):
        seconds = amount * 3600
    elif unit.startswith("j") or unit.startswith("d"):
        seconds = amount * 86400
    else:
        seconds = amount * 60
    if seconds < MIN_SECONDS or seconds > MAX_SECONDS:
        return None
    return seconds


def has_twitch_link(accounts) -> bool:
    for item in accounts or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("type") or item.get("platform") or "").lower()
        if kind == "twitch" and item.get("name"):
            return True
    return False


def twitch_from_profile(profile: dict | None) -> bool:
    if not isinstance(profile, dict):
        return False
    accounts = profile.get("connected_accounts") or profile.get("connections") or []
    return has_twitch_link(accounts)


def draw_winners(participants, count: int, rng=None) -> list[str]:
    pool = list(dict.fromkeys(str(item) for item in participants))
    if not pool or count <= 0:
        return []
    rng = rng or random
    return rng.sample(pool, min(int(count), len(pool)))


def reroll_winners(participants, previous, count: int, rng=None) -> list[str]:
    previous_ids = {str(item) for item in previous or []}
    fresh = [item for item in dict.fromkeys(str(p) for p in participants) if item not in previous_ids]
    if len(fresh) >= max(1, int(count)):
        return draw_winners(fresh, count, rng)
    return draw_winners(participants, count, rng)


def _ends_at(item: dict) -> datetime:
    raw = datetime.fromisoformat(item["ends_at"])
    if raw.tzinfo is None:
        raw = raw.replace(tzinfo=timezone.utc)
    return raw


def embed_dict(item: dict) -> dict:
    participants = item.get("participants") or []
    status = item.get("status") or "open"
    lines = [
        f"**Lot :** {item.get('prize') or '—'}",
        f"**Gagnants :** {int(item.get('winners_count') or 1)}",
        f"**Participants :** {len(participants)}",
    ]
    if item.get("twitch_required"):
        lines.append("**Condition :** compte Twitch lié à Discord")
    if status == "open":
        lines.append(f"**Fin :** <t:{int(_ends_at(item).timestamp())}:R>")
    elif status == "ended":
        winners = item.get("winners") or []
        shown = ", ".join(f"<@{winner}>" for winner in winners) if winners else "aucun participant"
        lines.append(f"**Gagnant(s) :** {shown}")
    else:
        lines.append("**Statut :** annulé")
    return {
        "title": "🐺 Zaelys — Giveaway",
        "description": "\n".join(lines),
        "color": EMBED_COLOR,
        "footer": {"text": "Royaume de Zaelys"},
    }


def end_announcement(item: dict) -> tuple[str, dict]:
    winners = [str(winner) for winner in item.get("winners") or []]
    if winners:
        content = "🎉 Giveaway terminé. Félicitations " + ", ".join(f"<@{winner}>" for winner in winners) + " !"
        mentions = {"parse": [], "users": winners}
    else:
        content = "🎉 Giveaway terminé. Personne n'a participé."
        mentions = {"parse": []}
    if item.get("ping_everyone"):
        content = "@everyone " + content
        mentions["parse"] = ["everyone"]
    return content, mentions


def start_content(ping_everyone: bool) -> tuple[str, dict]:
    if ping_everyone:
        return "@everyone", {"parse": ["everyone"]}
    return "", {"parse": []}


class GiveawayStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> dict:
        if not self.path.exists():
            return {"giveaways": []}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"giveaways": []}
        if not isinstance(raw, dict):
            return {"giveaways": []}
        items = raw.get("giveaways")
        if not isinstance(items, list):
            raw["giveaways"] = []
        return raw

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def all(self) -> list[dict]:
        return list(self.load().get("giveaways") or [])

    def upsert(self, item: dict) -> dict:
        data = self.load()
        items = data["giveaways"]
        for index, existing in enumerate(items):
            if existing.get("id") == item.get("id"):
                items[index] = item
                break
        else:
            items.append(item)
        self.save(data)
        return item

    def find(self, ident: str) -> dict | None:
        ident = str(ident or "").strip()
        if not ident:
            return None
        for item in self.all():
            if item.get("id") == ident or str(item.get("message_id") or "") == ident:
                return item
        return None

    def create(
        self,
        *,
        guild_id: int,
        channel_id: int,
        prize: str,
        winners_count: int,
        seconds: int,
        host_id: int,
        twitch_required: bool,
        ping_everyone: bool,
        now: datetime | None = None,
    ) -> dict:
        moment = now or datetime.now(timezone.utc)
        item = {
            "id": uuid.uuid4().hex[:12],
            "guild_id": str(guild_id),
            "channel_id": str(channel_id),
            "message_id": "",
            "prize": prize.strip(),
            "winners_count": int(winners_count),
            "host_id": str(host_id),
            "ends_at": (moment + timedelta(seconds=int(seconds))).isoformat(),
            "twitch_required": bool(twitch_required),
            "ping_everyone": bool(ping_everyone),
            "status": "open",
            "participants": [],
            "winners": [],
            "created_at": moment.isoformat(),
        }
        return self.upsert(item)

    def toggle(self, ident: str, user_id: int) -> tuple[dict | None, str]:
        item = self.find(ident)
        if item is None or item.get("status") != "open":
            return item, "closed"
        uid = str(user_id)
        people = [str(person) for person in item.get("participants") or []]
        if uid in people:
            people = [person for person in people if person != uid]
            action = "left"
        else:
            people.append(uid)
            action = "joined"
        item["participants"] = people
        self.upsert(item)
        return item, action

    def resolve(self, guild_id: int, ident: str | None, statuses: set[str]) -> tuple[dict | None, str | None]:
        items = [
            item
            for item in self.all()
            if str(item.get("guild_id")) == str(guild_id) and item.get("status") in statuses
        ]
        if ident:
            found = self.find(ident)
            if found is None or found.get("status") not in statuses or str(found.get("guild_id")) != str(guild_id):
                return None, "introuvable"
            return found, None
        if len(items) == 1:
            return items[0], None
        if not items:
            return None, "aucun"
        return None, "plusieurs"

    def finish(self, ident: str, rng=None) -> dict | None:
        item = self.find(ident)
        if item is None or item.get("status") != "open":
            return None
        item["winners"] = draw_winners(item.get("participants") or [], int(item.get("winners_count") or 1), rng)
        item["status"] = "ended"
        return self.upsert(item)

    def reroll(self, ident: str, rng=None) -> dict | None:
        item = self.find(ident)
        if item is None or item.get("status") != "ended":
            return None
        item["winners"] = reroll_winners(
            item.get("participants") or [],
            item.get("winners") or [],
            int(item.get("winners_count") or 1),
            rng,
        )
        return self.upsert(item)

    def cancel(self, ident: str) -> dict | None:
        item = self.find(ident)
        if item is None or item.get("status") != "open":
            return None
        item["status"] = "cancelled"
        item["winners"] = []
        return self.upsert(item)

    def attach_message(self, ident: str, message_id: int) -> dict | None:
        item = self.find(ident)
        if item is None:
            return None
        item["message_id"] = str(message_id)
        return self.upsert(item)

    def due(self, now: datetime) -> list[dict]:
        ready = []
        for item in self.all():
            if item.get("status") != "open":
                continue
            if _ends_at(item) <= now:
                ready.append(item)
        return ready

    def open_items(self) -> list[dict]:
        return [item for item in self.all() if item.get("status") == "open"]


STORE = GiveawayStore(STATE_PATH)


def register_giveaway(bot) -> None:
    """Enregistre /giveaway. N'envoie rien."""
    group = app_commands.Group(
        name="giveaway",
        description="Giveaways du royaume de Zaelys",
    )

    def admin_only(interaction) -> bool:
        user = interaction.user
        owner = bool(getattr(user, "guild", None) and user.id == user.guild.owner_id)
        perms = getattr(user, "guild_permissions", None)
        return is_giveaway_admin(owner, bool(perms and perms.administrator))

    @group.command(name="start", description="Ouvre un giveaway")
    @app_commands.describe(
        lot="Le lot à gagner",
        duree="Durée : 30m, 2h ou 1j",
        gagnants="Nombre de gagnants",
        salon="Salon du message. Par défaut : 🎉-giveaway",
        twitch="Exiger un compte Twitch lié au profil Discord",
        everyone="Mentionner @everyone. Non par défaut",
    )
    async def start_cmd(
        interaction,
        lot: str,
        duree: str,
        gagnants: app_commands.Range[int, 1, 20] = 1,
        salon: discord.TextChannel | None = None,
        twitch: bool = False,
        everyone: bool = False,
    ):
        if not admin_only(interaction):
            await interaction.response.send_message("Réservé aux administrateurs.", ephemeral=True)
            return
        seconds = parse_duration(duree)
        if seconds is None:
            await interaction.response.send_message(
                "Durée invalide. Exemples : 30m, 2h, 1j.",
                ephemeral=True,
            )
            return
        channel = salon
        if channel is None and interaction.guild is not None:
            channel = interaction.guild.get_channel(DEFAULT_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Salon invalide.", ephemeral=True)
            return
        item = STORE.create(
            guild_id=interaction.guild_id or GUILD_ID,
            channel_id=channel.id,
            prize=lot,
            winners_count=int(gagnants),
            seconds=seconds,
            host_id=interaction.user.id,
            twitch_required=twitch,
            ping_everyone=everyone,
        )
        content, _mentions = start_content(everyone)
        await interaction.response.defer(ephemeral=True)
        message = await channel.send(
            content=content or None,
            embed=_discord_embed(item),
            view=JoinView(item["id"]),
            allowed_mentions=discord.AllowedMentions(everyone=everyone, roles=False, users=False),
        )
        STORE.attach_message(item["id"], message.id)
        bot.add_view(JoinView(item["id"]))
        await interaction.followup.send(
            f"Giveaway ouvert : {message.jump_url}",
            ephemeral=True,
        )

    @group.command(name="end", description="Tire les gagnants maintenant")
    @app_commands.describe(identifiant="Id du giveaway ou du message. Optionnel s'il n'y en a qu'un")
    async def end_cmd(interaction, identifiant: str | None = None):
        await _close_command(interaction, identifiant, "end")

    @group.command(name="reroll", description="Retire de nouveaux gagnants")
    @app_commands.describe(identifiant="Id du giveaway ou du message. Optionnel s'il n'y en a qu'un")
    async def reroll_cmd(interaction, identifiant: str | None = None):
        await _close_command(interaction, identifiant, "reroll")

    @group.command(name="cancel", description="Annule un giveaway ouvert")
    @app_commands.describe(identifiant="Id du giveaway ou du message. Optionnel s'il n'y en a qu'un")
    async def cancel_cmd(interaction, identifiant: str | None = None):
        await _close_command(interaction, identifiant, "cancel")

    async def _close_command(interaction, identifiant: str | None, action: str):
        if not admin_only(interaction):
            await interaction.response.send_message("Réservé aux administrateurs.", ephemeral=True)
            return
        statuses = {"ended"} if action == "reroll" else {"open"}
        item, error = STORE.resolve(interaction.guild_id or GUILD_ID, identifiant, statuses)
        if error == "introuvable":
            await interaction.response.send_message("Giveaway introuvable.", ephemeral=True)
            return
        if error == "aucun":
            await interaction.response.send_message("Aucun giveaway correspondant.", ephemeral=True)
            return
        if error == "plusieurs":
            await interaction.response.send_message(
                "Plusieurs giveaways. Indique l'identifiant.",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        updated = await apply_action(bot, item, action)
        if updated is None:
            await interaction.followup.send("Action impossible.", ephemeral=True)
            return
        await interaction.followup.send(f"Giveaway {updated['status']} : `{updated['id']}`", ephemeral=True)

    bot.tree.add_command(group, guild=discord.Object(id=GUILD_ID))


def _discord_embed(item: dict):
    data = embed_dict(item)
    embed = discord.Embed(title=data["title"], description=data["description"], color=data["color"])
    embed.set_footer(text=data["footer"]["text"])
    return embed


class JoinView:
    """Construit plus bas pour éviter l'import si les tests n'ont pas besoin de la vue."""


def _build_view_class():
    class _JoinView(discord.ui.View):
        def __init__(self, giveaway_id: str):
            super().__init__(timeout=None)
            self.giveaway_id = giveaway_id
            button = discord.ui.Button(
                label="Participer",
                style=discord.ButtonStyle.success,
                custom_id=JOIN_PREFIX + giveaway_id,
            )
            button.callback = self.join
            self.add_item(button)

        async def join(self, interaction):
            item = STORE.find(self.giveaway_id)
            if item is None or item.get("status") != "open":
                await interaction.response.send_message("Ce giveaway est terminé.", ephemeral=True)
                return
            if item.get("twitch_required"):
                linked = await _member_has_twitch(interaction)
                if not linked:
                    await interaction.response.send_message(
                        "Il faut un compte Twitch lié à ton profil Discord pour participer.",
                        ephemeral=True,
                    )
                    return
            updated, action = STORE.toggle(self.giveaway_id, interaction.user.id)
            if updated is None:
                await interaction.response.send_message("Ce giveaway est terminé.", ephemeral=True)
                return
            note = "Tu participes." if action == "joined" else "Tu ne participes plus."
            await interaction.response.edit_message(embed=_discord_embed(updated), view=self)
            await interaction.followup.send(note, ephemeral=True)

    return _JoinView


def JoinView(giveaway_id: str):  # noqa: N802 - factory used as the view
    return _build_view_class()(giveaway_id)


async def _member_has_twitch(interaction) -> bool:
    import json
    import urllib.request

    token = ""
    try:
        from zaeldryk_discord_env import bot_token  # type: ignore
        token = bot_token()
    except Exception:
        token = ""
    if not token:
        try:
            import os
            from pathlib import Path

            path = Path(os.environ.get("DISCORD_ENV_PATH", "/home/ubuntu/zaeldryk/config/discord.env"))
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DISCORD_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip().strip('"')
                    if token.lower().startswith("bot "):
                        token = token[4:].strip()
        except OSError:
            return False
    guild_id = getattr(interaction, "guild_id", None) or GUILD_ID
    url = f"https://discord.com/api/v10/users/{interaction.user.id}/profile?guild_id={guild_id}"
    request = urllib.request.Request(
        url,
        headers={"Authorization": "Bot " + token, "User-Agent": "zaeldryk-giveaway"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            profile = json.loads(response.read().decode())
    except Exception:
        return False
    return twitch_from_profile(profile)


async def apply_action(bot, item: dict, action: str, rng=None) -> dict | None:
    if action == "cancel":
        updated = STORE.cancel(item["id"])
    elif action == "reroll":
        updated = STORE.reroll(item["id"], rng)
    else:
        updated = STORE.finish(item["id"], rng)
    if updated is None:
        return None
    await _refresh_message(bot, updated, announce=action != "cancel")
    return updated


async def _refresh_message(bot, item: dict, announce: bool) -> None:
    channel = bot.get_channel(int(item["channel_id"])) if item.get("channel_id") else None
    if channel is None:
        try:
            channel = await bot.fetch_channel(int(item["channel_id"]))
        except Exception:
            return
    message = None
    if item.get("message_id"):
        try:
            message = await channel.fetch_message(int(item["message_id"]))
        except Exception:
            message = None
    view = JoinView(item["id"]) if item.get("status") == "open" else None
    if message is not None:
        await message.edit(embed=_discord_embed(item), view=view)
    if announce and item.get("status") == "ended":
        content, mentions = end_announcement(item)
        allowed = discord.AllowedMentions.none()
        if item.get("ping_everyone"):
            allowed = discord.AllowedMentions(everyone=True, roles=False, users=False)
        elif item.get("winners"):
            users = []
            for winner in item["winners"]:
                try:
                    users.append(await bot.fetch_user(int(winner)))
                except Exception:
                    continue
            allowed = discord.AllowedMentions(everyone=False, roles=False, users=users)
        await channel.send(content, embed=_discord_embed(item), allowed_mentions=allowed)


async def restore_giveaways(bot) -> int:
    count = 0
    for item in STORE.open_items():
        bot.add_view(JoinView(item["id"]))
        count += 1
    if not getattr(bot, "_giveaway_loop_started", False):
        bot._giveaway_loop_started = True
        bot.loop.create_task(_closer(bot))
    return count


async def _closer(bot) -> None:
    import asyncio

    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            for item in STORE.due(datetime.now(timezone.utc)):
                await apply_action(bot, item, "end")
        except Exception as exc:
            print(f"Giveaway closer error: {type(exc).__name__}", flush=True)
        await asyncio.sleep(30)
