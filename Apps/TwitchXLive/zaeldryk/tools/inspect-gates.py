#!/usr/bin/env python3
"""Inspect membership verification / gates that block new joins."""
import asyncio
import json
from pathlib import Path

import aiohttp
import discord

CONFIG = Path("/home/ubuntu/zaeldryk/config/discord.env")
GUILD_ID = 867426693286461490
API = "https://discord.com/api/v10"


def load_token() -> str:
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DISCORD_BOT_TOKEN missing")


TOKEN = load_token()


async def api(method: str, path: str, payload=None):
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.request(method, f"{API}{path}", headers=headers, json=payload) as resp:
            text = await resp.text()
            print(f"{method} {path} -> {resp.status}")
            print(text[:2000] if text else "(empty)")
            return resp.status, text


intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    try:
        guild = client.get_guild(GUILD_ID) or await client.fetch_guild(GUILD_ID)
        print(f"features={list(guild.features)}")
        print(f"verification_level={guild.verification_level}")
        print(f"rules_channel={guild.rules_channel}")
        print(f"system_channel={guild.system_channel}")
        await api("GET", f"/guilds/{GUILD_ID}/member-verification")
        await api("GET", f"/guilds/{GUILD_ID}/onboarding")
    finally:
        await client.close()


async def main():
    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
