#!/usr/bin/env python3
"""Inspect today's joins: roles, Disciple, captcha-related logs."""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
GUILD_ID = "867426693286461490"
LOGS_CHANNEL = "1541249740145172581"  # 📝-logs
DISCIPLE_ROLE = "1541249715973394473"


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
            "User-Agent": "ZaelrysJoinDiag/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> None:
    today = datetime.now(timezone.utc).date()
    print("UTC_TODAY", today)

    # Recent members (requires privileged intent; may fail)
    try:
        members = api(f"/guilds/{GUILD_ID}/members?limit=100")
        print("MEMBERS", len(members))
        for m in members:
            u = m.get("user") or {}
            if u.get("bot"):
                continue
            joined = m.get("joined_at") or ""
            try:
                jd = datetime.fromisoformat(joined.replace("Z", "+00:00")).date()
            except Exception:
                jd = None
            roles = m.get("roles") or []
            has_disciple = DISCIPLE_ROLE in roles
            flag = "TODAY" if jd == today else ("RECENT" if jd and (today - jd).days <= 2 else "")
            if flag or has_disciple:
                print(
                    f"{flag or 'MEMBER'} {u.get('username')} id={u.get('id')} "
                    f"joined={joined} disciple={has_disciple} roles={len(roles)}"
                )
                if flag == "TODAY" or (jd and (today - jd).days <= 1):
                    print("  roles_ids", roles)
    except Exception as e:
        print("MEMBERS_ERR", type(e).__name__, e)

    # Logs channel recent embeds
    print("\n=== LOGS CHANNEL ===")
    msgs = api(f"/channels/{LOGS_CHANNEL}/messages?limit=30")
    for m in msgs:
        embeds = m.get("embeds") or []
        ts = m.get("timestamp")
        content = (m.get("content") or "")[:80]
        if embeds:
            for e in embeds:
                title = e.get("title") or ""
                desc = (e.get("description") or "")[:180]
                print(ts, title, "|", desc)
        elif content:
            print(ts, "content", content)


if __name__ == "__main__":
    main()
