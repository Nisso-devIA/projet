#!/usr/bin/env python3
"""Force #📖-règlement fully readable for @everyone (join gate)."""
import asyncio
from pathlib import Path

import discord

CONFIG = Path("/home/ubuntu/zaeldryk/config/discord.env")
CHANNEL_REGLEMENT = "📖-règlement"
ROLE_DISCIPLE = "🐺 Disciple"
GUILD_ID = 867426693286461490


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
        guild = client.get_guild(GUILD_ID)
        if guild is None:
            guild = await client.fetch_guild(GUILD_ID)
            await guild.fetch_channels()

        everyone = guild.default_role
        disciple = discord.utils.get(guild.roles, name=ROLE_DISCIPLE)
        reglement = discord.utils.get(guild.text_channels, name=CHANNEL_REGLEMENT)
        if reglement is None:
            for ch in await guild.fetch_channels():
                if getattr(ch, "name", None) == CHANNEL_REGLEMENT:
                    reglement = ch
                    break

        print(f"@everyone guild view_channel={everyone.permissions.view_channel}")
        print(f"reglement={reglement}")

        if reglement is None:
            print("MISSING CHANNEL")
            return

        if reglement.category:
            await reglement.category.set_permissions(
                everyone,
                view_channel=True,
                reason="open category for join gate",
            )
            print(f"category {reglement.category.name} opened for @everyone")

        # Full clear then set — avoid leftover denies
        await reglement.set_permissions(everyone, overwrite=None)
        await reglement.set_permissions(
            everyone,
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            add_reactions=True,
            embed_links=True,
            attach_files=False,
            use_external_emojis=True,
            reason="join gate: réglement visible",
        )
        print("reglement overwrite set")

        if disciple and reglement.category:
            for ch in reglement.category.channels:
                if not isinstance(ch, discord.TextChannel):
                    continue
                if ch.id == reglement.id:
                    continue
                await ch.set_permissions(everyone, view_channel=False, reason="lock until Disciple")
                await ch.set_permissions(
                    disciple,
                    view_channel=True,
                    read_message_history=True,
                    reason="Disciple access",
                )
                print(f"locked #{ch.name} for @everyone / open Disciple")

        ow = reglement.overwrites_for(everyone)
        print(f"FINAL réglement view={ow.view_channel} history={ow.read_message_history}")
    finally:
        await client.close()


async def main():
    await client.start(load_token())


if __name__ == "__main__":
    asyncio.run(main())
