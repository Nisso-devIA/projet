#!/usr/bin/env python3
from pathlib import Path
import json
import urllib.request
import urllib.error
import subprocess

token = None
for line in Path("/home/ubuntu/zaeldryk/config/discord.env").read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

headers = {
    "Authorization": f"Bot {token}",
    "User-Agent": "DiscordBot (https://github.com/zaelrys/watchdog, 1.0)",
}

req = urllib.request.Request("https://discord.com/api/v10/users/@me", headers=headers)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        print("UA_OK", r.status, r.read()[:120])
except urllib.error.HTTPError as e:
    print("UA_HTTP", e.code, e.read()[:200])
except Exception as e:
    print("UA_ERR", type(e).__name__, e)

# curl
cmd = [
    "curl", "-s", "-o", "/tmp/me2.json", "-w", "%{http_code}",
    "-H", f"Authorization: Bot {token}",
    "-H", "User-Agent: DiscordBot (https://zaelrys.local, 1.0)",
    "https://discord.com/api/v10/users/@me",
]
code = subprocess.check_output(cmd, text=True).strip()
print("CURL", code, Path("/tmp/me2.json").read_text()[:200])

# aiohttp via discord.py stack if available
try:
    import asyncio
    import aiohttp

    async def main():
        async with aiohttp.ClientSession(
            headers={
                "Authorization": f"Bot {token}",
                "User-Agent": "DiscordBot (https://zaelrys.local, 1.0)",
            }
        ) as session:
            async with session.get("https://discord.com/api/v10/users/@me") as resp:
                body = await resp.text()
                print("AIO", resp.status, body[:150])
                if resp.status == 200:
                    async with session.get(
                        "https://discord.com/api/v10/guilds/867426693286461490/channels"
                    ) as r2:
                        chs = await r2.json()
                        print("CH", r2.status, len(chs) if isinstance(chs, list) else chs)
                        if isinstance(chs, list):
                            for c in chs:
                                n = c.get("name") or ""
                                if "log" in n.lower() or "📝" in n:
                                    print("HIT", c["id"], n)

    asyncio.run(main())
except Exception as e:
    print("AIO_ERR", type(e).__name__, e)
