#!/usr/bin/env python3
"""One-shot: move BOT_TOKEN from discord bot py into config/discord.env"""
from pathlib import Path

bot_path = Path("/home/ubuntu/zaeldryk/discord/zaeldryk-discord-bot.py")
env_path = Path("/home/ubuntu/zaeldryk/config/discord.env")

token = None
for line in bot_path.read_text(encoding="utf-8").splitlines():
    if line.startswith("BOT_TOKEN"):
        raw = line.split("=", 1)[1].strip()
        token = raw.strip().strip('"').strip("'")
        break

if not token:
    raise SystemExit("BOT_TOKEN not found")

env_path.parent.mkdir(parents=True, exist_ok=True)
env_path.write_text(f"DISCORD_BOT_TOKEN={token}\n", encoding="utf-8")
env_path.chmod(0o600)
print("discord.env written OK")
