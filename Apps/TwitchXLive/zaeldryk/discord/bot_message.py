"""Édition des messages du bot, réservée au propriétaire du serveur."""

from __future__ import annotations

import re

import discord
from discord import app_commands

GUILD_ID = 867426693286461490
OWNER_ID = 558595717610995712
CONTENT_LIMIT = 2000

_LINK = re.compile(r"channels/(\d+)/(\d+)/(\d+)")
_PAIR = re.compile(r"^(\d{17,20})[/\-](\d{17,20})$")
_SNOWFLAKE = re.compile(r"^(\d{17,20})$")


def is_guild_owner(user_id: int, guild_owner_id: int | None = None) -> bool:
    if int(user_id) != OWNER_ID:
        return False
    if guild_owner_id is None:
        return True
    return int(guild_owner_id) == OWNER_ID


def parse_message_ref(raw: str, guild_id: int, current_channel_id: int | None = None) -> tuple[int, int] | str:
    text = (raw or "").strip()
    link = _LINK.search(text)
    if link:
        found_guild, channel_id, message_id = (int(part) for part in link.groups())
        if found_guild != int(guild_id):
            return "autre_serveur"
        return channel_id, message_id
    pair = _PAIR.fullmatch(text)
    if pair:
        return int(pair.group(1)), int(pair.group(2))
    snowflake = _SNOWFLAKE.fullmatch(text)
    if snowflake and current_channel_id:
        return int(current_channel_id), int(snowflake.group(1))
    return "lien_invalide"


def can_edit_author(author_id: int, bot_id: int) -> bool:
    return int(author_id) == int(bot_id)


def edit_payload(content: str, allow_mentions: bool, has_embeds: bool) -> dict | str:
    text = content if content is not None else ""
    if len(text) > CONTENT_LIMIT:
        return "trop_long"
    if not text.strip() and not has_embeds:
        return "vide"
    mentions = {"parse": ["users", "roles", "everyone"]} if allow_mentions else {"parse": []}
    return {"content": text, "allowed_mentions": mentions}


def modal_custom_id(channel_id: int, message_id: int, allow_mentions: bool) -> str:
    return f"botmsg:{int(channel_id)}:{int(message_id)}:{1 if allow_mentions else 0}"


def parse_modal_custom_id(custom_id: str) -> tuple[int, int, bool] | None:
    parts = (custom_id or "").split(":")
    if len(parts) != 4 or parts[0] != "botmsg":
        return None
    try:
        return int(parts[1]), int(parts[2]), parts[3] == "1"
    except ValueError:
        return None


def register_bot_message(bot) -> None:
    """Enregistre /bot-message. N'édite rien tant que le propriétaire n'envoie pas le formulaire."""
    group = app_commands.Group(
        name="bot-message",
        description="Modifier un message du bot",
        default_permissions=discord.Permissions.none(),
    )

    @group.command(name="modifier", description="Ouvre le texte actuel d'un message du bot")
    @app_commands.describe(
        lien="Lien du message, id salon/id message, ou id du message dans ce salon",
        mentions="Autoriser les nouvelles mentions. Non par défaut",
    )
    async def modifier_cmd(interaction: discord.Interaction, lien: str, mentions: bool = False):
        if interaction.guild is None or not is_guild_owner(interaction.user.id, interaction.guild.owner_id):
            await interaction.response.send_message("Réservé au propriétaire du serveur.", ephemeral=True)
            return
        current_channel = interaction.channel.id if interaction.channel else None
        parsed = parse_message_ref(lien, interaction.guild.id, current_channel)
        if parsed == "autre_serveur":
            await interaction.response.send_message("Ce lien n'est pas de ce serveur.", ephemeral=True)
            return
        if parsed == "lien_invalide":
            await interaction.response.send_message(
                "Lien invalide. Colle le lien du message, ou l'id du salon et l'id du message.",
                ephemeral=True,
            )
            return
        channel_id, message_id = parsed
        channel = interaction.guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(channel_id)
            except discord.HTTPException:
                channel = None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Salon introuvable.", ephemeral=True)
            return
        try:
            message = await channel.fetch_message(message_id)
        except discord.HTTPException:
            await interaction.response.send_message("Message introuvable.", ephemeral=True)
            return
        if not can_edit_author(message.author.id, interaction.client.user.id):
            await interaction.response.send_message("Je ne modifie que mes propres messages.", ephemeral=True)
            return
        if len(message.content) > CONTENT_LIMIT:
            await interaction.response.send_message("Ce message est trop long pour le formulaire.", ephemeral=True)
            return
        await interaction.response.send_modal(EditModal(channel_id, message_id, message.content, mentions, bool(message.embeds)))

    bot.tree.add_command(group, guild=discord.Object(id=GUILD_ID))


class EditModal(discord.ui.Modal, title="Modifier le message"):
    texte = discord.ui.TextInput(
        label="Texte",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=CONTENT_LIMIT,
    )

    def __init__(self, channel_id: int, message_id: int, content: str, allow_mentions: bool, has_embeds: bool):
        super().__init__(custom_id=modal_custom_id(channel_id, message_id, allow_mentions))
        self.channel_id = channel_id
        self.message_id = message_id
        self.allow_mentions = allow_mentions
        self.has_embeds = has_embeds
        self.texte.default = content

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.guild is None or not is_guild_owner(interaction.user.id, interaction.guild.owner_id):
            await interaction.response.send_message("Réservé au propriétaire du serveur.", ephemeral=True)
            return
        prepared = edit_payload(str(self.texte.value or ""), self.allow_mentions, self.has_embeds)
        if prepared == "trop_long":
            await interaction.response.send_message("Le texte dépasse 2000 caractères.", ephemeral=True)
            return
        if prepared == "vide":
            await interaction.response.send_message(
                "Le message n'a pas d'embed : le texte ne peut pas être vide.",
                ephemeral=True,
            )
            return
        channel = interaction.guild.get_channel(self.channel_id)
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(self.channel_id)
            except discord.HTTPException:
                channel = None
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Salon introuvable.", ephemeral=True)
            return
        try:
            message = await channel.fetch_message(self.message_id)
        except discord.HTTPException:
            await interaction.response.send_message("Message introuvable.", ephemeral=True)
            return
        if interaction.client.user is None or not can_edit_author(message.author.id, interaction.client.user.id):
            await interaction.response.send_message("Je ne modifie que mes propres messages.", ephemeral=True)
            return
        kwargs = {"content": prepared["content"]}
        if self.allow_mentions:
            kwargs["allowed_mentions"] = discord.AllowedMentions(everyone=True, roles=True, users=True)
        else:
            kwargs["allowed_mentions"] = discord.AllowedMentions.none()
        await message.edit(**kwargs)
        await interaction.response.send_message("Message modifié.", ephemeral=True)
