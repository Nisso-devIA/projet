#!/usr/bin/env python3
"""ACCUEIL: @everyone sees only réglement; Disciple sees the rest."""
import asyncio
from pathlib import Path

import discord

CONFIG = Path("/home/ubuntu/zaeldryk/config/discord.env")
CHANNEL_REGLEMENT = "📖-règlement"
ROLE_DISCIPLE = "🐺 Disciple"
GUILD_ID = 867426693286461490
CATEGORY_NAME = "🏰 ACCUEIL"


def load_token() -> str:
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DISCORD_BOT_TOKEN missing")


intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    try:
        guild = client.get_guild(GUILD_ID) or await client.fetch_guild(GUILD_ID)
        categories = [c for c in await guild.fetch_channels() if isinstance(c, discord.CategoryChannel)]
        category = discord.utils.get(categories, name=CATEGORY_NAME)
        if not category:
            print(f"Catégorie introuvable: {CATEGORY_NAME}")
            return

        everyone = guild.default_role
        disciple = discord.utils.get(guild.roles, name=ROLE_DISCIPLE)
        if not disciple:
            print(f"Rôle introuvable: {ROLE_DISCIPLE}")
            return

        cat_ow = category.overwrites_for(everyone)
        cat_ow.view_channel = True
        await category.set_permissions(everyone, overwrite=cat_ow, reason="ZAELDRYK ACCUEIL")

        for ch in category.channels:
            ow_everyone = ch.overwrites_for(everyone)
            ow_disciple = ch.overwrites_for(disciple)

            if ch.name == CHANNEL_REGLEMENT:
                ow_everyone.view_channel = True
                ow_everyone.read_message_history = True
                ow_everyone.send_messages = False
                await ch.set_permissions(everyone, overwrite=ow_everyone, reason="ZAELDRYK réglement @everyone")
                print(f"OPEN  #{ch.name} (@everyone)")
            else:
                ow_everyone.view_channel = False
                await ch.set_permissions(everyone, overwrite=ow_everyone, reason="ZAELDRYK lock @everyone")
                ow_disciple.view_channel = True
                ow_disciple.read_message_history = True
                await ch.set_permissions(disciple, overwrite=ow_disciple, reason="ZAELDRYK Disciple access")
                print(f"LOCK  #{ch.name} (@everyone) / OPEN Disciple")

        print("OK — join → voit réglement ; après acceptation Disciple → voit le reste ACCUEIL.")
    finally:
        await client.close()


async def main():
    await client.start(load_token())


if __name__ == "__main__":
    asyncio.run(main())
