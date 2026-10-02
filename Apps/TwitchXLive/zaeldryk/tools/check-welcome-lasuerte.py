#!/usr/bin/env python3
"""Check welcome message for lasuerte + reglement message around join time."""
import json
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
BIENVENUE = "1541249720176082965"
REGLEMENT = "1541249727662784612"
TARGET = "142309723830484992"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no token")


def api(path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {load_token()}", "User-Agent": "Zaelrys/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> None:
    print("=== BIENVENUE ===")
    for m in api(f"/channels/{BIENVENUE}/messages?limit=10"):
        content = m.get("content") or ""
        embeds = m.get("embeds") or []
        mentions = m.get("mentions") or []
        print(m["timestamp"], (m.get("author") or {}).get("username"), content[:80])
        for e in embeds:
            print(" ", e.get("title"), (e.get("description") or "")[:120])
        for u in mentions:
            if u.get("id") == TARGET:
                print("  *** mentions lasuerte ***")

    print("\n=== REGLEMENT RECENT ===")
    for m in api(f"/channels/{REGLEMENT}/messages?limit=10"):
        print(
            m["timestamp"],
            (m.get("author") or {}).get("username"),
            "comps",
            bool(m.get("components")),
            repr((m.get("content") or "")[:80]),
        )


if __name__ == "__main__":
    main()
