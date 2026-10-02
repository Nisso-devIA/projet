#!/usr/bin/env python3
"""Audit log: who gave Disciple to today's joiner."""
import json
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
GUILD_ID = "867426693286461490"
DISCIPLE_ROLE = "1541249715973394473"
TARGET_USER = "142309723830484992"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={
            "Authorization": f"Bot {load_token()}",
            "User-Agent": "ZaelrysAudit/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> None:
    # MEMBER_ROLE_UPDATE = 25
    data = api(
        f"/guilds/{GUILD_ID}/audit-logs?action_type=25&limit=20"
    )
    print("=== ROLE UPDATE AUDIT ===")
    for e in data.get("audit_log_entries") or []:
        target = e.get("target_id")
        user_id = e.get("user_id")
        changes = e.get("changes") or []
        print(
            e.get("id"),
            "target",
            target,
            "by",
            user_id,
            "at",
            # snowflake timestamp approx not needed
        )
        for c in changes:
            print(" ", c.get("key"), "old", c.get("old_value"), "new", c.get("new_value"))
        if target == TARGET_USER:
            print("  *** MATCH lasuerte ***")

    users = {u["id"]: u.get("username") for u in (data.get("users") or [])}
    print("users", users)

    # Also MEMBER_UPDATE = 24 and MEMBER_KICK etc not needed
    # Check if bot user id
    me = api("/users/@me")
    print("BOT", me.get("id"), me.get("username"))


if __name__ == "__main__":
    main()
