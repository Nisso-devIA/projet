#!/usr/bin/env python3
"""Inspect/fix Discord Server Onboarding so joins land on #📖-règlement."""
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


async def api(method: str, path: str, payload=None):
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.request(method, f"{API}{path}", headers=headers, json=payload) as resp:
            text = await resp.text()
            try:
                data = json.loads(text) if text else {}
            except json.JSONDecodeError:
                data = {"raw": text}
            if resp.status >= 400:
                raise RuntimeError(f"{method} {path} -> {resp.status}: {text}")
            return data


intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    try:
        guild = client.get_guild(GUILD_ID) or await client.fetch_guild(GUILD_ID)
        await guild.fetch_channels()
        reglement = discord.utils.get(guild.text_channels, name=CHANNEL_REGLEMENT)
        if not reglement:
            print("reglement missing")
            return

        print(f"reglement id={reglement.id}")

        current = await api("GET", f"/guilds/{GUILD_ID}/onboarding")
        print("=== ONBOARDING NOW ===")
        print(f"enabled={current.get('enabled')}")
        print(f"mode={current.get('mode')}")
        print(f"default_channel_ids={current.get('default_channel_ids')}")
        print(f"prompts={len(current.get('prompts') or [])}")

        # Keep prompts as-is; force default channel = réglement only (visible pre-Disciple)
        payload = {
            "prompts": current.get("prompts") or [],
            "default_channel_ids": [str(reglement.id)],
            "enabled": current.get("enabled", True),
            "mode": current.get("mode", 0),
        }
        updated = await api("PUT", f"/guilds/{GUILD_ID}/onboarding", payload)
        print("=== ONBOARDING UPDATED ===")
        print(f"enabled={updated.get('enabled')}")
        print(f"default_channel_ids={updated.get('default_channel_ids')}")
        print("OK — default onboarding channel = réglement")
        print(
            "NOTE: le bandeau 'Terminer' vient de l'Onboarding Discord. "
            "Tant qu'il n'est pas fini, Discord peut afficher 'Aucun accès'."
        )
    finally:
        await client.close()


async def main():
    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
