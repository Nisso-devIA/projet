#!/usr/bin/env python3
"""Point system/rules channels to #📖-règlement for new joins."""
import asyncio
from pathlib import Path

import discord

CONFIG = Path("/home/ubuntu/zaeldryk/config/discord.env")
CHANNEL_REGLEMENT = "📖-règlement"
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
        guild = client.get_guild(GUILD_ID) or await client.fetch_guild(GUILD_ID)
        await guild.fetch_channels()
        reglement = discord.utils.get(guild.text_channels, name=CHANNEL_REGLEMENT)
        print(f"system_channel before: {guild.system_channel}")
        print(f"rules_channel before: {getattr(guild, 'rules_channel', None)}")
        print(f"reglement: {reglement}")
        if reglement is None:
            return

        kwargs = {"system_channel": reglement}
        # rules_channel only on community guilds
        try:
            kwargs["rules_channel"] = reglement
            await guild.edit(**kwargs, reason="ZAELDRYK join lands on réglement")
        except discord.HTTPException as e:
            print(f"rules_channel edit failed ({e}) — trying system_channel only")
            await guild.edit(system_channel=reglement, reason="ZAELDRYK join lands on réglement")

        # refresh
        guild = client.get_guild(GUILD_ID)
        print(f"system_channel after: {guild.system_channel}")
        print(f"rules_channel after: {getattr(guild, 'rules_channel', None)}")
    finally:
        await client.close()


async def main():
    await client.start(load_token())


if __name__ == "__main__":
    asyncio.run(main())
