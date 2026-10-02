#!/usr/bin/env python3
"""Make #📖-règlement the top channel + welcome screen target for joins."""
import asyncio
import json
from pathlib import Path

import aiohttp
import discord

CONFIG = Path("/home/ubuntu/zaeldryk/config/discord.env")
CHANNEL_REGLEMENT = "📖-règlement"
GUILD_ID = 867426693286461490
API = "https://discord.com/api/v10"


def load_token() -> str:
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DISCORD_BOT_TOKEN missing")


TOKEN = load_token()
intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)


async def api(method, path, payload=None):
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.request(method, f"{API}{path}", headers=headers, json=payload) as resp:
            text = await resp.text()
            print(f"{method} {path} -> {resp.status} {text[:500]}")
            return resp.status, text


@client.event
async def on_ready():
    try:
        guild = client.get_guild(GUILD_ID) or await client.fetch_guild(GUILD_ID)
        await guild.fetch_channels()
        reglement = discord.utils.get(guild.text_channels, name=CHANNEL_REGLEMENT)
        if not reglement:
            print("missing réglement")
            return

        feats = list(guild.features)
        print(f"gate_enabled={'MEMBER_VERIFICATION_GATE_ENABLED' in feats}")
        print(f"system={guild.system_channel} rules={guild.rules_channel}")

        # Strong read access for @everyone (still no chat spam)
        await reglement.set_permissions(
            guild.default_role,
            view_channel=True,
            read_message_history=True,
            send_messages=False,
            add_reactions=True,
            embed_links=True,
            use_external_emojis=True,
            reason="join: read réglement",
        )

        # Put channel at top of its category
        await reglement.edit(position=0, reason="join: réglement first in list")
        print(f"reglement position now={reglement.position}")

        await guild.edit(system_channel=reglement, reason="join default system channel")

        # Welcome screen (community) — shown on join
        status, _ = await api(
            "PATCH",
            f"/guilds/{GUILD_ID}/welcome-screen",
            {
                "enabled": True,
                "description": "Bienvenue sur ZAELDRYK — commence par le règlement.",
                "welcome_channels": [
                    {
                        "channel_id": str(reglement.id),
                        "description": "Lis et accepte le règlement pour entrer",
                        "emoji_name": "📜",
                    }
                ],
            },
        )
        if status >= 400:
            # older endpoint
            await api(
                "PUT",
                f"/guilds/{GUILD_ID}/welcome-screen",
                {
                    "enabled": True,
                    "description": "Bienvenue sur ZAELDRYK — commence par le règlement.",
                    "welcome_channels": [
                        {
                            "channel_id": str(reglement.id),
                            "description": "Lis et accepte le règlement pour entrer",
                            "emoji_name": "📜",
                        }
                    ],
                },
            )

        print("DONE")
        if "MEMBER_VERIFICATION_GATE_ENABLED" in feats:
            print(
                "TOUJOURS ACTIF: Rules Screening Discord. "
                "Paramètres serveur → Sécurité → désactiver les règles/screening."
            )
    finally:
        await client.close()


async def main():
    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
