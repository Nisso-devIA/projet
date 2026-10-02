#!/usr/bin/env python3
"""Check real permissions for a member without Disciple; widen réglement if needed."""
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
intents.members = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    try:
        guild = client.get_guild(GUILD_ID)
        if guild is None:
            print("Guild not in cache — enable members intent / reinvite?")
            guild = await client.fetch_guild(GUILD_ID)

        # Ensure member cache
        try:
            await guild.chunk()
        except Exception as e:
            print(f"chunk warn: {e}")

        disciple = discord.utils.get(guild.roles, name=ROLE_DISCIPLE)
        reglement = discord.utils.get(guild.text_channels, name=CHANNEL_REGLEMENT)

        print(f"members cached: {len(guild.members)}")
        print(f"roles: {[r.name for r in guild.roles]}")

        # Find a non-bot member without Disciple
        sample = None
        for m in guild.members:
            if m.bot:
                continue
            if disciple and disciple in m.roles:
                continue
            sample = m
            break

        if sample is None:
            # fabricate check using default role only — pick any member and strip conceptually
            print("No member without Disciple found — checking @everyone resolution via overwrites only")
            for m in guild.members:
                if not m.bot:
                    sample = m
                    break

        if reglement is None:
            print("no réglement")
            return

        if sample:
            perms = reglement.permissions_for(sample)
            print(f"Sample member: {sample} roles={[r.name for r in sample.roles]}")
            print(f"permissions_for réglement: view={perms.view_channel} read_history={perms.read_message_history}")
            # List ALL text channels they can view
            visible = []
            for ch in guild.text_channels:
                if ch.permissions_for(sample).view_channel:
                    visible.append(f"#{ch.name}")
            print(f"Visible channels for sample ({len(visible)}): {visible}")

        # Nuclear open for réglement: clear conflicting role denials on this channel
        print("\n=== Overwrites on réglement ===")
        for target, ow in reglement.overwrites.items():
            name = getattr(target, "name", str(target))
            print(f"  {name}: view={ow.view_channel}")

        # Remove deny from any non-staff roles on réglement; keep staff as-is
        for target, ow in list(reglement.overwrites.items()):
            if isinstance(target, discord.Role) and ow.view_channel is False and target.name != ROLE_DISCIPLE:
                # Don't touch admin-looking roles harshly — only clear false denies for default-like
                if target.is_default() or target.name.lower() in ("unverified", "non vérifié", "new", "nouveau"):
                    await reglement.set_permissions(target, overwrite=None, reason="clear deny on réglement")
                    print(f"Cleared overwrite for role {target.name}")

        # Re-apply everyone allow with broader read perms
        await reglement.set_permissions(
            guild.default_role,
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            add_reactions=True,
            embed_links=True,
            attach_files=False,
            reason="ZAELDRYK réglement readable on join",
        )

        if sample:
            # refresh
            await asyncio.sleep(1)
            perms = reglement.permissions_for(sample)
            print(f"AFTER view={perms.view_channel} history={perms.read_message_history}")

        # Community / rules screening hint
        print(f"\nverification_level={guild.verification_level}")
        print(f"explicit_content_filter={guild.explicit_content_filter}")
    finally:
        await client.close()


async def main():
    await client.start(load_token())


if __name__ == "__main__":
    asyncio.run(main())
