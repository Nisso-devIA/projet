#!/usr/bin/env python3
"""Disable Discord Membership Screening so joins open #règlement immediately."""
import asyncio
import json
from pathlib import Path

import aiohttp

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


async def main():
    headers = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        # Disable membership screening / rules gate
        async with session.put(
            f"{API}/guilds/{GUILD_ID}/member-verification",
            headers=headers,
            json={"enabled": False},
        ) as resp:
            text = await resp.text()
            print(f"PUT member-verification enabled=false -> {resp.status}")
            print(text[:1500] if text else "(empty)")

        async with session.get(
            f"{API}/guilds/{GUILD_ID}",
            headers={"Authorization": f"Bot {TOKEN}"},
        ) as resp:
            data = await resp.json()
            feats = data.get("features", [])
            print("MEMBER_VERIFICATION_GATE_ENABLED" in feats)
            print(f"features has gate: {'MEMBER_VERIFICATION_GATE_ENABLED' in feats}")


if __name__ == "__main__":
    asyncio.run(main())
