import asyncio
import json
import os
import random
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Set

import discord
from discord import app_commands
from discord.ext import commands

CONFIG_PATH = Path("/home/ubuntu/zaeldryk/config/discord.env")
XAI_ENV_PATH = Path("/home/ubuntu/zaeldryk/config/xai.env")
XAI_API_URL = "https://api.x.ai/v1/chat/completions"
XAI_MODEL_DEFAULT = "grok-4.7"


def load_discord_env(path: Path = CONFIG_PATH) -> dict:
    env = {}
    if not path.exists():
        raise FileNotFoundError(f"Missing Discord config: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_cfg = load_discord_env()
BOT_TOKEN = _cfg.get("DISCORD_BOT_TOKEN") or os.environ.get("DISCORD_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN missing in discord.env")

GUILD_ID = 867426693286461490

ROLE_DISCIPLE = "🐺 Disciple"
ROLE_STAFF = "⚔️ Sentinelle"
CHANNEL_REGLEMENT = "📖-règlement"
CHANNEL_BIENVENUE = "📜-bienvenue"
CHANNEL_LOGS = "📝-logs"
CHANNEL_MEMBERS_ID = 1541534998488813659  # ID salon 👥 Membres
CHANNEL_BOTS_ID = 1541534999549837402     # ID salon 🤖 Bots
CHANNEL_DEPARTS = "🚪-départs"  # nom exact du salon
CHANNEL_SONDAGES_ID = 1542633689840877579  # 📊-sondages
CHANNEL_ANNONCES_ID = 1541249724902809692  # 📢-annonces
TWITCH_URL = "https://twitch.tv/zaeldryk"
POLL_STATE_FILE = Path("/home/ubuntu/zaeldryk/state/live-polls.json")
PENDING_POLL_FILE = Path("/home/ubuntu/zaeldryk/state/pending-poll.json")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Évite le spam #📝-logs quand /clear purge un salon
_purge_in_progress: Set[int] = set()
intents.guilds = True
intents.moderation = True
intents.invites = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ─── Sondages live (pourcentages visibles + recalcul à chaque vote) ───

POLL_DURATION_HOURS = 24


def _load_polls() -> dict:
    if not POLL_STATE_FILE.exists():
        return {}
    try:
        return json.loads(POLL_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_polls(data: dict) -> None:
    POLL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    POLL_STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _bar(pct: float, width: int = 12) -> str:
    filled = int(round(pct / 100 * width))
    filled = max(0, min(width, filled))
    return "█" * filled + "░" * (width - filled)


def format_anonymous_results(poll: dict) -> str:
    """Résultats publics : options + % + counts, sans noms de votants."""
    question = poll.get("question") or "Sondage"
    options = poll.get("options") or []
    votes = poll.get("votes") or {}
    counts = [0] * len(options)
    for opt_idx in votes.values():
        try:
            i = int(opt_idx)
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(options):
            counts[i] += 1
    total = sum(counts)
    lines = [
        "@everyone",
        f"**📊 Résultats — {question}**",
        f"_{total} vote(s) · anonymes (sans noms)_",
        "",
    ]
    ranked = sorted(range(len(options)), key=lambda i: counts[i], reverse=True)
    for i in ranked:
        n = counts[i]
        pct = (n / total * 100.0) if total else 0.0
        medal = "🥇 " if ranked and i == ranked[0] and total else ""
        lines.append(f"{medal}**{options[i]}**")
        lines.append(f"`{_bar(pct)}` **{pct:.0f}%** · {n} vote(s)")
        lines.append("")
    return "\n".join(lines).strip()


def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def is_poll_closed(poll: dict) -> bool:
    if poll.get("closed"):
        return True
    ends = _parse_iso(poll.get("ends_at") or "")
    if ends and datetime.utcnow() >= ends:
        return True
    return False


def build_poll_embed(question: str, options: list, votes: dict, poll: dict = None) -> discord.Embed:
    counts = [0] * len(options)
    for opt_idx in votes.values():
        try:
            i = int(opt_idx)
        except (TypeError, ValueError):
            continue
        if 0 <= i < len(options):
            counts[i] += 1
    total = sum(counts)
    lines = []
    for i, opt in enumerate(options):
        n = counts[i]
        pct = (n / total * 100.0) if total else 0.0
        lines.append(f"**{opt}**\n`{_bar(pct)}` **{pct:.0f}%** · {n} vote(s)")

    closed = bool(poll and is_poll_closed(poll))
    ends = _parse_iso((poll or {}).get("ends_at") or "") if poll else None
    if closed:
        title = f"📊 {question} — terminé"
        color = discord.Color.dark_grey()
        footer = f"{total} vote(s) · sondage clos (24 h)"
    else:
        title = f"📊 {question}"
        color = discord.Color.blurple()
        footer = f"{total} vote(s) · durée 24 h"
        if ends:
            unix = int(ends.replace(tzinfo=timezone.utc).timestamp())
            lines.append(f"_Clôture <t:{unix}:R>_")

    embed = discord.Embed(
        title=title,
        description="\n\n".join(lines),
        color=color,
        timestamp=datetime.utcnow(),
    )
    embed.set_footer(text=footer)
    return embed


def make_poll_view(poll_id: str, options: list, closed: bool = False) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    for i, opt in enumerate(options):
        label = (opt[:78] + "…") if len(opt) > 79 else opt
        btn = discord.ui.Button(
            label=label,
            style=discord.ButtonStyle.primary,
            custom_id=f"livepoll:{poll_id}:{i}",
            row=0 if i < 5 else 1,
            disabled=closed,
        )

        async def _cb(interaction: discord.Interaction, index: int = i, pid: str = poll_id):
            await handle_live_poll_vote(interaction, pid, index)

        btn.callback = _cb
        view.add_item(btn)

    reveal = discord.ui.Button(
        label="🔐 Voir les votes",
        style=discord.ButtonStyle.secondary,
        custom_id=f"livepoll:{poll_id}:voters",
        row=1,
        disabled=False,  # owner peut toujours voir après clôture
    )

    async def _reveal(interaction: discord.Interaction, pid: str = poll_id):
        await handle_live_poll_reveal(interaction, pid)

    reveal.callback = _reveal
    view.add_item(reveal)
    return view


async def handle_live_poll_reveal(interaction: discord.Interaction, poll_id: str):
    """Liste des votants — propriétaire du serveur uniquement (éphémère)."""
    guild = interaction.guild
    if guild is None or interaction.user.id != guild.owner_id:
        await interaction.response.send_message(
            "⛔ Réservé au **propriétaire** du serveur.",
            ephemeral=True,
        )
        return

    data = _load_polls()
    poll = data.get(poll_id)
    if not poll:
        await interaction.response.send_message("Ce sondage n’existe plus.", ephemeral=True)
        return

    options = poll.get("options") or []
    votes = poll.get("votes") or {}
    if not votes:
        await interaction.response.send_message("Aucun vote pour l’instant.", ephemeral=True)
        return

    by_opt: Dict[int, list] = {i: [] for i in range(len(options))}
    saved_names = poll.get("voter_names") or {}
    for uid, opt_idx in votes.items():
        try:
            i = int(opt_idx)
        except (TypeError, ValueError):
            continue
        if i not in by_opt:
            continue
        member = guild.get_member(int(uid))
        if member is None:
            try:
                member = await guild.fetch_member(int(uid))
            except Exception:
                member = None
        label = (
            member.display_name
            if member
            else (saved_names.get(uid) or f"ID `{uid}`")
        )
        by_opt[i].append(label)

    lines = [f"**Votes — {poll.get('question', 'Sondage')}** _(visible toi seul)_", ""]
    for i, opt in enumerate(options):
        names = by_opt.get(i) or []
        if names:
            lines.append(f"**{opt}** ({len(names)})\n" + ", ".join(names))
        else:
            lines.append(f"**{opt}** (0)\n—")
        lines.append("")

    text = "\n".join(lines).strip()
    if len(text) > 1900:
        text = text[:1900] + "\n…"
    await interaction.response.send_message(text, ephemeral=True)


async def handle_live_poll_vote(interaction: discord.Interaction, poll_id: str, index: int):
    data = _load_polls()
    poll = data.get(poll_id)
    if not poll:
        await interaction.response.send_message("Ce sondage n’existe plus.", ephemeral=True)
        return
    if is_poll_closed(poll):
        await interaction.response.send_message(
            "⏰ Ce sondage est **terminé** (durée 24 h).",
            ephemeral=True,
        )
        return
    options = poll.get("options") or []
    if index < 0 or index >= len(options):
        await interaction.response.send_message("Option invalide.", ephemeral=True)
        return

    votes = poll.setdefault("votes", {})
    uid = str(interaction.user.id)
    prev = votes.get(uid)
    votes[uid] = index
    names = poll.setdefault("voter_names", {})
    names[uid] = getattr(interaction.user, "display_name", None) or str(interaction.user)
    _save_polls(data)

    closed = is_poll_closed(poll)
    embed = build_poll_embed(poll["question"], options, votes, poll)
    view = make_poll_view(poll_id, options, closed=closed)
    await interaction.response.edit_message(embed=embed, view=view)

    if prev == index:
        tip = f"Vote déjà enregistré : **{options[index]}**"
    elif prev is not None:
        tip = f"Vote changé → **{options[index]}**"
    else:
        tip = f"Vote enregistré : **{options[index]}**"
    try:
        await interaction.followup.send(tip, ephemeral=True)
    except Exception:
        pass


async def close_expired_polls() -> int:
    """Ferme les sondages > 24 h : désactive les boutons de vote, met à jour l'embed."""
    data = _load_polls()
    closed_n = 0
    changed = False
    for poll_id, poll in list(data.items()):
        if not poll.get("ends_at"):
            created = _parse_iso(poll.get("created_at") or "") or datetime.utcnow()
            poll["ends_at"] = (created + timedelta(hours=POLL_DURATION_HOURS)).isoformat()
            if not poll.get("created_at"):
                poll["created_at"] = created.isoformat()
            changed = True
        if poll.get("closed"):
            continue
        if not is_poll_closed(poll):
            continue
        poll["closed"] = True
        changed = True
        options = poll.get("options") or []
        mid = poll.get("message_id")
        ch_id = poll.get("channel_id")
        if mid and ch_id and len(options) >= 2:
            try:
                channel = bot.get_channel(int(ch_id)) or await bot.fetch_channel(int(ch_id))
                msg = await channel.fetch_message(int(mid))
                embed = build_poll_embed(poll["question"], options, poll.get("votes") or {}, poll)
                await msg.edit(embed=embed, view=make_poll_view(poll_id, options, closed=True))
                if not poll.get("results_posted"):
                    await channel.send(
                        format_anonymous_results(poll),
                        allowed_mentions=discord.AllowedMentions(everyone=True),
                    )
                    poll["results_posted"] = True
                closed_n += 1
            except Exception as e:
                print(f"close poll {poll_id}: {e}", flush=True)
    if changed:
        _save_polls(data)
    return closed_n


async def refresh_live_poll_messages() -> None:
    """Réapplique les boutons / état (ouvert ou clos) sur les sondages existants."""
    data = _load_polls()
    changed = False
    for poll_id, poll in data.items():
        # Migration : durée 24 h si absente
        if not poll.get("ends_at"):
            created = _parse_iso(poll.get("created_at") or "")
            if created is None and poll.get("message_id"):
                try:
                    # timestamp Discord snowflake
                    ms = (int(poll["message_id"]) >> 22) + 1420070400000
                    created = datetime.utcfromtimestamp(ms / 1000.0)
                except Exception:
                    created = datetime.utcnow()
            if created is None:
                created = datetime.utcnow()
            poll["ends_at"] = (created + timedelta(hours=POLL_DURATION_HOURS)).isoformat()
            if not poll.get("created_at"):
                poll["created_at"] = created.isoformat()
            changed = True
        options = poll.get("options") or []
        mid = poll.get("message_id")
        ch_id = poll.get("channel_id")
        if not mid or not ch_id or len(options) < 2:
            continue
        closed = is_poll_closed(poll)
        if closed and not poll.get("closed"):
            poll["closed"] = True
            changed = True
        try:
            channel = bot.get_channel(int(ch_id)) or await bot.fetch_channel(int(ch_id))
            msg = await channel.fetch_message(int(mid))
            embed = build_poll_embed(poll["question"], options, poll.get("votes") or {}, poll)
            await msg.edit(embed=embed, view=make_poll_view(poll_id, options, closed=closed))
        except Exception as e:
            print(f"refresh poll {poll_id}: {e}", flush=True)
    if changed:
        _save_polls(data)


async def create_live_poll(channel: discord.TextChannel, question: str, options: list) -> discord.Message:
    import uuid

    options = [o.strip() for o in options if o and o.strip()]
    if len(options) < 2 or len(options) > 5:
        raise ValueError("Il faut entre 2 et 5 options")
    poll_id = uuid.uuid4().hex[:12]
    now = datetime.utcnow()
    ends = now + timedelta(hours=POLL_DURATION_HOURS)
    data = _load_polls()
    data[poll_id] = {
        "question": question,
        "options": options,
        "votes": {},
        "voter_names": {},
        "channel_id": str(channel.id),
        "created_at": now.isoformat(),
        "ends_at": ends.isoformat(),
        "closed": False,
    }
    embed = build_poll_embed(question, options, {}, data[poll_id])
    view = make_poll_view(poll_id, options, closed=False)
    msg = await channel.send(
        content="@everyone",
        embed=embed,
        view=view,
        allowed_mentions=discord.AllowedMentions(everyone=True),
    )
    data[poll_id]["message_id"] = str(msg.id)
    _save_polls(data)
    bot.add_view(view)
    return msg


def register_live_poll_views() -> int:
    data = _load_polls()
    n = 0
    for poll_id, poll in data.items():
        options = poll.get("options") or []
        if len(options) < 2:
            continue
        bot.add_view(make_poll_view(poll_id, options, closed=is_poll_closed(poll)))
        n += 1
    return n


def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator or member.guild_permissions.manage_messages:
        return True
    return any(r.name == ROLE_STAFF for r in member.roles)


def is_owner(member: discord.Member) -> bool:
    return member.guild is not None and member.id == member.guild.owner_id


def can_announce(member: discord.Member) -> bool:
    return is_owner(member) or is_staff(member)


def parse_embed_color(raw: str) -> int | None:
    s = (raw or "").strip().lstrip("#")
    if not s:
        return None
    try:
        n = int(s, 16)
    except ValueError:
        return None
    if 0 <= n <= 0xFFFFFF:
        return n
    return None


def load_xai() -> tuple[str, str]:
    env = {}
    if XAI_ENV_PATH.exists():
        env.update(load_discord_env(XAI_ENV_PATH))
    key = (env.get("XAI_API_KEY") or os.environ.get("XAI_API_KEY") or "").strip()
    model = (env.get("XAI_MODEL") or os.environ.get("XAI_MODEL") or XAI_MODEL_DEFAULT).strip()
    return key, model


ANNONCE_SYSTEM = """Tu rédiges des annonces Discord pour le serveur Zaelrys / chaîne Twitch Zaeldryk.
Style obligatoire (message texte, pas un article) :
- Titre en markdown : ## … avec un emoji cohérent (⚔️ si neutre, univers du jeu sinon)
- Paragraphe d’accroche, **gras** sur les infos clés (jeu, horaire, action)
- Puces • **…** s’il y a plusieurs infos
- Lien : 👉 **Chaîne Twitch :** URL  (ou 👉 **Lien :** si ce n’est pas Twitch)
- Clôture courte avec 🐺 ou un emoji de l’univers (une fois)
- Ton communautaire FR, direct, pas corporate, pas de hashtags
- N’invente PAS de date, prix, ni URL d’image. Si le brief ne donne pas l’heure, dis « ce soir » ou l’horaire habituel 22h–23h30 seulement s’il s’agit d’un live.
- Si un thème / univers est donné (ex. Zelda Ocarina of Time), imprègne le texte ET propose 2 ou 3 embeds aux couleurs de cet univers (hex 6 caractères, sans #).
Réponds UNIQUEMENT en JSON :
{"content":"texte discord SANS @everyone","embeds":[{"title":"...","description":"...","color":"00A651"}]}
embeds peut être [] si aucun thème visuel. Max 3 embeds. description <= 400 caractères. Pas de champ image."""


def _grok_generate(brief: str, theme: str, link: str) -> dict:
    key, model = load_xai()
    if not key:
        raise RuntimeError(
            "Clé xAI absente. Ajoute XAI_API_KEY dans /home/ubuntu/zaeldryk/config/xai.env"
        )
    user = (
        f"Brief : {brief}\n"
        f"Thème / univers : {theme or 'aucun — annonce serveur classique'}\n"
        f"Lien à inclure : {link}\n"
    )
    payload = {
        "model": model,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": ANNONCE_SYSTEM},
            {"role": "user", "content": user},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        XAI_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "ZaelrysAnnounce/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"xAI HTTP {e.code}: {detail}") from e
    text = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError("Réponse Grok illisible")
    parsed = json.loads(text[start : end + 1])
    content = (parsed.get("content") or "").strip()
    if not content:
        raise RuntimeError("Grok n’a pas renvoyé de texte")
    embeds: list[discord.Embed] = []
    for item in (parsed.get("embeds") or [])[:3]:
        if not isinstance(item, dict):
            continue
        color = parse_embed_color(str(item.get("color") or "")) or 0x5865F2
        emb = discord.Embed(
            title=(str(item.get("title") or "")[:256] or None),
            description=(str(item.get("description") or "")[:500] or None),
            color=color,
            url=link if link.startswith("http") else None,
        )
        emb.set_footer(text="Zaeldryk — Annonce")
        embeds.append(emb)
    return {"content": content[:1900], "embeds": embeds}


class AnnonceConfirmView(discord.ui.View):
    def __init__(self, content: str, embeds: list, ping_everyone: bool):
        super().__init__(timeout=600)
        self.content = content
        self.embeds = embeds
        self.ping_everyone = ping_everyone

    async def _disable(self, interaction: discord.Interaction, note: str):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=note[:2000], view=self, embeds=[])

    @discord.ui.button(label="Publier", style=discord.ButtonStyle.success)
    async def publish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member) or not can_announce(interaction.user):
            await interaction.response.send_message("⛔ Réservé owner / staff.", ephemeral=True)
            return
        guild = interaction.guild
        channel = guild.get_channel(CHANNEL_ANNONCES_ID) if guild else None
        if channel is None and guild:
            channel = await guild.fetch_channel(CHANNEL_ANNONCES_ID)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Salon #annonces introuvable.", ephemeral=True)
            return
        text = self.content
        if self.ping_everyone and "@everyone" not in text:
            text = f"@everyone\n\n{text}"
        msg = await channel.send(
            content=text,
            embeds=self.embeds or None,
            allowed_mentions=discord.AllowedMentions(everyone=self.ping_everyone),
        )
        await self._disable(interaction, f"✅ Publié : {msg.jump_url}")

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._disable(interaction, "Annonce annulée.")


class AnnonceModal(discord.ui.Modal, title="Annonce (générée par Grok)"):
    brief = discord.ui.TextInput(
        label="De quoi parler ?",
        style=discord.TextStyle.paragraph,
        placeholder="Live ce soir sur Ocarina of Time remake, vers 22h",
        max_length=800,
        required=True,
    )
    theme = discord.ui.TextInput(
        label="Thème / univers (optionnel)",
        placeholder="Zelda Ocarina of Time — vert Kokiri, or Triforce",
        max_length=200,
        required=False,
    )
    lien = discord.ui.TextInput(
        label="Lien (vide = Twitch)",
        placeholder=TWITCH_URL,
        max_length=200,
        required=False,
    )

    def __init__(self, ping_everyone: bool = True):
        super().__init__()
        self.ping_everyone = ping_everyone

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not can_announce(interaction.user):
            await interaction.response.send_message("⛔ Réservé owner / staff.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        brief = str(self.brief.value).strip()
        theme = str(self.theme.value).strip() if self.theme.value else ""
        link = (str(self.lien.value).strip() if self.lien.value else "") or TWITCH_URL
        try:
            generated = await asyncio.to_thread(_grok_generate, brief, theme, link)
        except Exception as e:
            await interaction.followup.send(f"❌ Génération : {e}", ephemeral=True)
            return
        preview = generated["content"]
        if len(preview) > 1700:
            preview = preview[:1700] + "…"
        view = AnnonceConfirmView(
            generated["content"], generated["embeds"], self.ping_everyone
        )
        await interaction.followup.send(
            "**Aperçu** — Publier ou Annuler\n\n" + preview,
            embeds=generated["embeds"][:1] or None,
            view=view,
            ephemeral=True,
        )


CAPTCHA_MAX_ATTEMPTS = 3
_captcha_failures: Dict[int, int] = {}


async def grant_disciple_access(interaction: discord.Interaction) -> bool:
    """Give Disciple role, welcome message, counters. Returns True on success."""
    guild = interaction.guild
    user = interaction.user
    if guild is None or not isinstance(user, discord.Member):
        return False

    role = discord.utils.get(guild.roles, name=ROLE_DISCIPLE)
    if role is None:
        await interaction.followup.send("Rôle introuvable.", ephemeral=True)
        return False
    if role in user.roles:
        await interaction.followup.send("Tu as déjà accepté le règlement.", ephemeral=True)
        return False

    await user.add_roles(role)

    bienvenue = discord.utils.get(guild.text_channels, name=CHANNEL_BIENVENUE)
    if bienvenue:
        embed = discord.Embed(
            title="⚔️ Bienvenue chez les Zaelrys",
            description=(
                f"Salut {user.mention} ! Content de t’avoir parmi nous ✨\n\n"
                f"Tu as maintenant accès au serveur.\n"
                f"👉 Présente-toi dans le salon <#1541274991197159444> pour qu’on fasse connaissance 🐺🐉"
            ),
            color=discord.Color.gold(),
        )
        welcome_img = Path("/home/ubuntu/zaeldryk/discord/assets/bienvenue_base.jpg")
        if welcome_img.exists():
            file = discord.File(welcome_img, filename="bienvenue.jpg")
            embed.set_image(url="attachment://bienvenue.jpg")
            await bienvenue.send(embed=embed, file=file)
        else:
            embed.set_image(url="https://i.imgur.com/tCDZtsy.jpeg")
            await bienvenue.send(embed=embed)

    await interaction.followup.send("✅ Accès débloqué", ephemeral=True)

    try:
        await update_member_counters(guild)
    except Exception:
        pass

    _captcha_failures.pop(user.id, None)
    return True


class CaptchaModal(discord.ui.Modal, title="Vérification anti-bot"):
    def __init__(self, a: int, b: int):
        super().__init__()
        self._expected = a + b
        self.answer_input = discord.ui.TextInput(
            label=f"Combien font {a} + {b} ?",
            placeholder="Entre le résultat (nombre entier)",
            min_length=1,
            max_length=4,
            required=True,
        )
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.answer_input.value.strip()
        try:
            given = int(raw)
        except ValueError:
            await interaction.response.send_message(
                "❌ Réponse invalide — entre un nombre.",
                ephemeral=True,
            )
            return

        if given != self._expected:
            fails = _captcha_failures.get(interaction.user.id, 0) + 1
            _captcha_failures[interaction.user.id] = fails
            if fails >= CAPTCHA_MAX_ATTEMPTS:
                await interaction.response.send_message(
                    "❌ Trop d’échecs. Réessaie dans quelques minutes ou contacte le staff.",
                    ephemeral=True,
                )
                try:
                    await send_log(
                        interaction.guild,
                        "🤖 Captcha échoué",
                        f"{interaction.user.mention} — {fails} échecs",
                        discord.Color.red(),
                    )
                except Exception:
                    pass
            else:
                await interaction.response.send_message(
                    f"❌ Incorrect. Il reste {CAPTCHA_MAX_ATTEMPTS - fails} tentative(s).",
                    ephemeral=True,
                )
            return

        await interaction.response.defer(ephemeral=True)
        await grant_disciple_access(interaction)


class AcceptRulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅ J'accepte le règlement",
        style=discord.ButtonStyle.green,
        custom_id="accept_rules"
    )
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Erreur membre.", ephemeral=True)
            return

        role = discord.utils.get(interaction.guild.roles, name=ROLE_DISCIPLE)
        if role and role in interaction.user.roles:
            await interaction.response.send_message(
                "Tu as déjà accepté le règlement.",
                ephemeral=True,
            )
            return

        a, b = random.randint(2, 12), random.randint(2, 12)
        await interaction.response.send_modal(CaptchaModal(a, b))


@bot.event
async def on_ready():
    print(f"Zaelrys Discord Bot connecté : {bot.user}", flush=True)
    bot.add_view(AcceptRulesView())
    n_polls = register_live_poll_views()
    print(f"Live polls registered: {n_polls}", flush=True)
    try:
        await refresh_live_poll_messages()
        print("Live poll messages refreshed", flush=True)
    except Exception as e:
        print(f"Live poll refresh error: {e}", flush=True)
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Slash commands synced: {len(synced)}", flush=True)
    except Exception as e:
        print(f"Slash sync error: {e}", flush=True)

    # Traite un sondage en attente (fichier state/pending-poll.json)
    if PENDING_POLL_FILE.exists():
        try:
            pending = json.loads(PENDING_POLL_FILE.read_text(encoding="utf-8"))
            ch_id = int(pending.get("channel_id") or CHANNEL_SONDAGES_ID)
            channel = bot.get_channel(ch_id)
            if channel is None:
                channel = await bot.fetch_channel(ch_id)
            delete_ids = pending.get("delete_message_ids") or []
            for mid in delete_ids:
                try:
                    msg = await channel.fetch_message(int(mid))
                    await msg.delete()
                except Exception:
                    pass
            await create_live_poll(
                channel,
                pending.get("question") or "Sondage",
                pending.get("options") or [],
            )
            PENDING_POLL_FILE.unlink(missing_ok=True)
            print("Pending live poll posted", flush=True)
        except Exception as e:
            print(f"Pending poll error: {e}", flush=True)

    async def counter_loop():
        await bot.wait_until_ready()
        await asyncio.sleep(5)
        while not bot.is_closed():
            for g in bot.guilds:
                try:
                    await update_member_counters(g)
                except Exception as e:
                    print(f"Compteur erreur: {e}", flush=True)
            await asyncio.sleep(300)

    async def poll_closer_loop():
        await bot.wait_until_ready()
        await asyncio.sleep(8)
        while not bot.is_closed():
            try:
                n = await close_expired_polls()
                if n:
                    print(f"Closed {n} expired poll(s)", flush=True)
            except Exception as e:
                print(f"Poll closer error: {e}", flush=True)
            await asyncio.sleep(60)

    bot.loop.create_task(counter_loop())
    bot.loop.create_task(poll_closer_loop())


@bot.tree.command(
    name="annonce",
    description="Grok rédige une annonce Zaelrys, tu valides, ça part dans #annonces",
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.describe(ping="Mention @everyone ?")
@app_commands.choices(
    ping=[
        app_commands.Choice(name="Oui — @everyone", value="yes"),
        app_commands.Choice(name="Non — sans ping", value="no"),
    ]
)
async def annonce_cmd(
    interaction: discord.Interaction,
    ping: app_commands.Choice[str],
):
    if not isinstance(interaction.user, discord.Member) or not can_announce(interaction.user):
        await interaction.response.send_message(
            "⛔ Réservé à l’owner / staff (⚔️ Sentinelle).",
            ephemeral=True,
        )
        return
    await interaction.response.send_modal(
        AnnonceModal(ping_everyone=(ping.value == "yes"))
    )


@bot.tree.command(
    name="sondage",
    description="Crée un sondage live (pourcentages visibles) — staff uniquement",
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.describe(
    question="Titre du sondage",
    options="Options séparées par | (2 à 5)",
)
async def sondage_cmd(interaction: discord.Interaction, question: str, options: str):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        await interaction.response.send_message("⛔ Réservé au staff.", ephemeral=True)
        return
    opts = [o.strip() for o in options.split("|") if o.strip()]
    if len(opts) < 2 or len(opts) > 5:
        await interaction.response.send_message(
            "Donne **2 à 5** options séparées par `|`.",
            ephemeral=True,
        )
        return
    channel = interaction.channel
    if CHANNEL_SONDAGES_ID:
        ch = interaction.guild.get_channel(CHANNEL_SONDAGES_ID) if interaction.guild else None
        if ch is not None:
            channel = ch
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Salon invalide.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        msg = await create_live_poll(channel, question.strip(), opts)
        await interaction.followup.send(f"✅ Sondage posté : {msg.jump_url}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ {e}", ephemeral=True)


@bot.tree.command(
    name="clear",
    description="Supprime des messages dans ce salon (staff uniquement)",
    guild=discord.Object(id=GUILD_ID),
)
@app_commands.describe(nombre="Nombre de messages à supprimer (1-100)")
async def clear_cmd(interaction: discord.Interaction, nombre: app_commands.Range[int, 1, 100] = 10):
    if not isinstance(interaction.user, discord.Member) or not is_staff(interaction.user):
        await interaction.response.send_message(
            "⛔ Réservé au staff (⚔️ Sentinelle / Gérer les messages).",
            ephemeral=True,
        )
        return

    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        await interaction.response.send_message(
            "Cette commande fonctionne uniquement dans un salon texte.",
            ephemeral=True,
        )
        return

    perms = interaction.channel.permissions_for(interaction.guild.me)
    if not perms.manage_messages:
        await interaction.response.send_message(
            "Je n’ai pas la permission **Gérer les messages** ici.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    _purge_in_progress.add(interaction.channel.id)
    try:
        deleted = await interaction.channel.purge(
            limit=nombre,
            reason=f"/clear par {interaction.user}",
        )
    finally:
        _purge_in_progress.discard(interaction.channel.id)
    count = len(deleted)

    notice = await interaction.channel.send(
        f"🧹 **{count}** message(s) supprimé(s) par {interaction.user.mention}.\n"
        f"_(ce message disparaît dans 5 min)_"
    )
    # Pas de log #📝-logs ni followup ephemeral — clear sans trace persistante

    async def _remove_notice(delay: int = 300):
        await asyncio.sleep(delay)
        try:
            await notice.delete()
        except Exception:
            pass

    bot.loop.create_task(_remove_notice(300))


@bot.event
async def on_member_join(member):
    await send_log(
        member.guild,
        "📥 Nouveau membre",
        f"{member.mention} (`{member}`) a rejoint",
        discord.Color.green()
    )
    try:
        await update_member_counters(member.guild)
    except Exception:
        pass


@bot.event
async def on_member_remove(member):
    ch = discord.utils.get(member.guild.text_channels, name="🚪-départs")
    if ch:
        embed = discord.Embed(
            title="👋 Départ",
            description=f"**{member}** a quitté le serveur.\nL'aventure s'arrête ici pour cette fois.",
            color=discord.Color.dark_grey()
        )
        embed.set_footer(text=f"ID : {member.id}")
        bye_img = Path("/home/ubuntu/zaeldryk/discord/assets/au_revoir_base.jpg")
        if bye_img.exists():
            file = discord.File(bye_img, filename="au_revoir.jpg")
            embed.set_image(url="attachment://au_revoir.jpg")
            await ch.send(embed=embed, file=file)
        else:
            embed.set_image(url="https://i.imgur.com/sfgLTXY.jpeg")
            await ch.send(embed=embed)

    await send_log(
        member.guild,
        "📤 Membre parti",
        f"**{member}** (`{member.id}`) a quitté",
        discord.Color.orange()
    )

    try:
        await update_member_counters(member.guild)
    except Exception:
        pass


@bot.event
async def on_member_ban(guild, user):
    await send_log(guild, "🔨 Bannissement", f"**{user}** a été banni", discord.Color.red())


@bot.event
async def on_member_unban(guild, user):
    await send_log(guild, "♻️ Débannissement", f"**{user}** a été débanni", discord.Color.blue())


@bot.event
async def on_member_update(before, after):
    if before.roles != after.roles:
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added:
            await send_log(after.guild, "➕ Rôle ajouté", f"{after.mention} a reçu : {', '.join(r.mention for r in added)}", discord.Color.green())
        if removed:
            await send_log(after.guild, "➖ Rôle retiré", f"{after.mention} a perdu : {', '.join(r.mention for r in removed)}", discord.Color.orange())
    if before.nick != after.nick:
        await send_log(after.guild, "📝 Pseudo changé", f"{after.mention} : `{before.nick}` → `{after.nick}`", discord.Color.blue())


@bot.event
async def on_message_delete(message):
    if message.guild and message.channel.id in _purge_in_progress:
        return
    if message.guild and message.author and not message.author.bot:
        content = message.content[:500] if message.content else "*contenu vide*"
        await send_log(message.guild, "🗑️ Message supprimé", f"**{message.author}** dans {message.channel.mention} :\n{content}", discord.Color.red())


@bot.event
async def on_message_edit(before, after):
    if after.guild and after.author and not after.author.bot and before.content != after.content:
        await send_log(after.guild, "✏️ Message modifié", f"**{after.author}** dans {after.channel.mention}\n**Avant :** {before.content[:300]}\n**Après :** {after.content[:300]}", discord.Color.gold())


@bot.event
async def on_guild_channel_create(channel):
    await send_log(channel.guild, "📁 Salon créé", f"**{channel.name}**", discord.Color.green())


@bot.event
async def on_guild_channel_delete(channel):
    await send_log(channel.guild, "📁 Salon supprimé", f"**{channel.name}**", discord.Color.red())


@bot.event
async def on_invite_create(invite):
    inviter = invite.inviter or "Inconnu"
    await send_log(invite.guild, "🔗 Invitation créée", f"Par **{inviter}** | code `{invite.code}`", discord.Color.blue())


async def send_log(guild, title, description, color):
    channel = discord.utils.get(guild.text_channels, name=CHANNEL_LOGS)
    if not channel:
        for c in guild.text_channels:
            if "log" in c.name.lower():
                channel = c
                break
    if channel:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow(),
        )
        return await channel.send(embed=embed)
    return None


async def update_member_counters(guild):
    members = sum(1 for m in guild.members if not m.bot)
    bots = sum(1 for m in guild.members if m.bot)
    ch_m = guild.get_channel(CHANNEL_MEMBERS_ID)
    ch_b = guild.get_channel(CHANNEL_BOTS_ID)
    if ch_m:
        new_name = f"👥 Membres : {members}"
        if ch_m.name != new_name:
            await ch_m.edit(name=new_name)
    if ch_b:
        new_name = f"🤖 Bots : {bots}"
        if ch_b.name != new_name:
            await ch_b.edit(name=new_name)


bot.run(BOT_TOKEN)
