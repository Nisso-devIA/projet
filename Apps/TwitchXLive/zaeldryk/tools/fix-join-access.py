#!/usr/bin/env python3
"""Diagnose + fix: new joins must see #📖-règlement (nothing else required)."""
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


def fmt_ow(ow: discord.PermissionOverwrite) -> str:
    return f"view={ow.view_channel}"


@client.event
async def on_ready():
    try:
        guild = client.get_guild(GUILD_ID)
        if guild is None:
            guild = await client.fetch_guild(GUILD_ID)
            await guild.fetch_channels()

        everyone = guild.default_role
        disciple = discord.utils.get(guild.roles, name=ROLE_DISCIPLE)

        print("=== @everyone base permissions (guild) ===")
        print(f"view_channel={everyone.permissions.view_channel}")

        print("\n=== Channels / overwrites (relevant) ===")
        reglement = None
        visible_guess = []
        for ch in sorted(guild.channels, key=lambda c: (c.position if hasattr(c, "position") else 0)):
            if not isinstance(ch, (discord.TextChannel, discord.ForumChannel)):
                continue
            ow = ch.overwrites_for(everyone)
            cat = ch.category.name if ch.category else "-"
            # Rough visibility: explicit False = hidden; None inherits guild/category
            print(f"#{ch.name} | cat={cat} | @everyone {fmt_ow(ow)} | sync={getattr(ch, 'permissions_synced', '?')}")
            if ch.name == CHANNEL_REGLEMENT:
                reglement = ch
            # Heuristic for report
            if ow.view_channel is True or (ow.view_channel is None and everyone.permissions.view_channel):
                if ow.view_channel is not False:
                    visible_guess.append(ch.name)

        if reglement is None:
            print("REGLEMENT NOT FOUND")
            return

        print(f"\n=== FIX {reglement.name} ===")
        # Break sync with category if needed, then force open for @everyone
        try:
            if reglement.permissions_synced:
                # editing overwrites breaks sync automatically in discord API
                pass
        except Exception:
            pass

        # Open category enough for channel to be reachable
        if reglement.category:
            cat = reglement.category
            cow = cat.overwrites_for(everyone)
            print(f"Category {cat.name} before: {fmt_ow(cow)}")
            cow.view_channel = True
            await cat.set_permissions(everyone, overwrite=cow, reason="ZAELDRYK open ACCUEIL for réglement")

        # Explicit allow on réglement (overrides category/channel denials for this channel)
        ow = discord.PermissionOverwrite()
        ow.view_channel = True
        ow.read_message_history = True
        ow.send_messages = False
        ow.add_reactions = False
        ow.create_public_threads = False
        ow.create_private_threads = False
        ow.send_messages_in_threads = False
        await reglement.set_permissions(everyone, overwrite=ow, reason="ZAELDRYK force réglement visible on join")

        # Make sure Disciple still sees sibling channels in same category
        if disciple and reglement.category:
            for ch in reglement.category.channels:
                if ch.id == reglement.id:
                    continue
                if not isinstance(ch, discord.TextChannel):
                    continue
                # keep @everyone locked
                eow = ch.overwrites_for(everyone)
                eow.view_channel = False
                await ch.set_permissions(everyone, overwrite=eow, reason="ZAELDRYK lock until Disciple")
                dow = ch.overwrites_for(disciple)
                dow.view_channel = True
                dow.read_message_history = True
                await ch.set_permissions(disciple, overwrite=dow, reason="ZAELDRYK Disciple open")

        # Re-check
        await asyncio.sleep(1)
        ow2 = reglement.overwrites_for(everyone)
        me_perms = reglement.permissions_for(guild.me)
        print(f"Après réglement @everyone: view={ow2.view_channel} history={ow2.read_message_history}")
        print(f"Bot can manage channels: {me_perms.manage_channels}")

        # Simulate: can @everyone theoretically see it?
        # Build a fake Member-less check via overwrites resolution is hard; print final map for ACCUEIL
        print("\n=== ACCUEIL final ===")
        if reglement.category:
            for ch in reglement.category.channels:
                if isinstance(ch, discord.TextChannel):
                    print(f"#{ch.name}: @everyone view={ch.overwrites_for(everyone).view_channel} | Disciple view={ch.overwrites_for(disciple).view_channel if disciple else 'n/a'}")

        print("\nDONE — rejoin test: only réglement should appear before accept.")
    finally:
        await client.close()


async def main():
    await client.start(load_token())


if __name__ == "__main__":
    asyncio.run(main())
