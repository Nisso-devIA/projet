"""Commandes owner, réponses éphémères. Ne publie pas tant que le drapeau est à 0."""
from __future__ import annotations

import os
from pathlib import Path

import discord
from discord import app_commands

from .drafts import CHANNEL_ID, GUILD_ID, DraftStore

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DB_PATH = ZAEL_ROOT / "state" / "clip-drafts.sqlite"


def publish_enabled() -> bool:
    path = ZAEL_ROOT / "config" / "clip-publish.env"
    if not path.is_file():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("CLIP_PUBLISH_ENABLED="):
            return line.split("=", 1)[1].strip() in {"1", "true", "yes"}
    return False


def register_clip_commands(bot: discord.Client) -> None:
    tree = bot.tree

    @tree.command(
        name="clip",
        description="Aperçu privé d'un brouillon de clip. Ne publie pas tout seul.",
        guild=discord.Object(id=int(GUILD_ID)),
    )
    @app_commands.describe(brouillon="Identifiant du brouillon importé")
    async def clip_cmd(interaction: discord.Interaction, brouillon: str):
        member = interaction.user
        is_owner = (
            isinstance(member, discord.Member)
            and interaction.guild is not None
            and member.id == interaction.guild.owner_id
        )
        if not is_owner:
            await interaction.response.send_message(
                "Réservé au propriétaire du serveur.", ephemeral=True
            )
            return
        store = DraftStore(DB_PATH)
        try:
            draft = store.get(brouillon.strip())
            if draft is None:
                await interaction.response.send_message(
                    "Brouillon introuvable.", ephemeral=True
                )
                return
            note = (
                "Publication coupée. Approuver enregistre seulement ta décision."
                if not publish_enabled()
                else "Publication armée : le bouton Publier enverra ce fichier précis."
            )
            view = _ClipView(brouillon.strip(), member.id)
            await interaction.response.send_message(
                "\n".join(
                    [
                        note,
                        f"id {draft.draft_id}",
                        f"sha256 {draft.sha256}",
                        f"salon {draft.channel_id}",
                        f"statut {draft.status}",
                        "texte :",
                        draft.text,
                    ]
                )[:1900],
                ephemeral=True,
                view=view,
            )
        finally:
            store.close()


class _ClipView(discord.ui.View):
    def __init__(self, draft_id: str, owner_id: int):
        super().__init__(timeout=600)
        self.draft_id = draft_id
        self.owner_id = owner_id

    async def _owner(self, interaction: discord.Interaction) -> bool:
        member = interaction.user
        return (
            isinstance(member, discord.Member)
            and interaction.guild is not None
            and member.id == interaction.guild.owner_id
            and member.id == self.owner_id
        )

    @discord.ui.button(label="Approuver", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._owner(interaction):
            await interaction.response.send_message(
                "Réservé au propriétaire.", ephemeral=True
            )
            return
        store = DraftStore(DB_PATH)
        try:
            draft = store.get(self.draft_id)
            if draft is None:
                await interaction.response.send_message("Brouillon introuvable.", ephemeral=True)
                return
            updated = store.decide(
                self.draft_id,
                actor_is_owner=True,
                actor_id=str(interaction.user.id),
                sha256=draft.sha256,
                text=draft.text,
                guild_id=GUILD_ID,
                channel_id=CHANNEL_ID,
                approve=True,
            )
            await interaction.response.send_message(
                f"Décision enregistrée : {updated.status}. Rien n'est publié tant que CLIP_PUBLISH_ENABLED=0.",
                ephemeral=True,
            )
        finally:
            store.close()

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.secondary)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._owner(interaction):
            await interaction.response.send_message(
                "Réservé au propriétaire.", ephemeral=True
            )
            return
        store = DraftStore(DB_PATH)
        try:
            draft = store.get(self.draft_id)
            if draft is None:
                await interaction.response.send_message("Brouillon introuvable.", ephemeral=True)
                return
            updated = store.decide(
                self.draft_id,
                actor_is_owner=True,
                actor_id=str(interaction.user.id),
                sha256=draft.sha256,
                text=draft.text,
                guild_id=GUILD_ID,
                channel_id=CHANNEL_ID,
                approve=False,
            )
            await interaction.response.send_message(
                f"Décision enregistrée : {updated.status}. Rien n'est publié.",
                ephemeral=True,
            )
        finally:
            store.close()
