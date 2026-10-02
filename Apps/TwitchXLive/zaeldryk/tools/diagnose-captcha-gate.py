#!/usr/bin/env python3
"""Diagnose why captcha gate may be skipped for new joins."""
import json
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
GUILD_ID = "867426693286461490"
CHANNEL_REGLEMENT_ID = "1541249727662784612"
MSG_ID = "1541280453942706267"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={
            "Authorization": f"Bot {load_token()}",
            "User-Agent": "ZaelrysCaptchaDiag/1.0",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def main() -> None:
    msg = api("GET", f"/channels/{CHANNEL_REGLEMENT_ID}/messages/{MSG_ID}")
    print("=== ACCEPT MESSAGE ===")
    print("content_len", len(msg.get("content") or ""))
    print("content", repr((msg.get("content") or "")[:300]))
    print("embeds", len(msg.get("embeds") or []))
    for e in msg.get("embeds") or []:
        print(" embed_title", e.get("title"))
        print(" embed_desc", (e.get("description") or "")[:200])
    print("components_rows", len(msg.get("components") or []))

    guild = api("GET", f"/guilds/{GUILD_ID}?with_counts=true")
    print("\n=== GUILD ===")
    print("verification_level", guild.get("verification_level"))
    print("features", sorted(guild.get("features") or []))

    # roles
    roles = api("GET", f"/guilds/{GUILD_ID}/roles")
    disciple = next((r for r in roles if "Disciple" in (r.get("name") or "")), None)
    everyone = next((r for r in roles if r.get("id") == GUILD_ID), None)
    print("\n=== ROLES ===")
    print("disciple", disciple and disciple.get("name"), disciple and disciple.get("id"))
    print("everyone_perms", everyone and everyone.get("permissions"))

    # channel overwrites for reglement + a few public channels
    channels = api("GET", f"/guilds/{GUILD_ID}/channels")
    interesting = {
        "📖-règlement",
        "📜-bienvenue",
        "💬-général",
        "📢-annonces",
        "🎤-présentations",
    }
    print("\n=== CHANNEL OVERWRITES (@everyone / Disciple) ===")
    for ch in channels:
        if ch.get("type") != 0:
            continue
        name = ch.get("name") or ""
        if name not in interesting and "général" not in name and "règlement" not in name:
            continue
        print(f"\n#{name} ({ch['id']})")
        for ow in ch.get("permission_overwrites") or []:
            tid = ow.get("id")
            label = "everyone" if tid == GUILD_ID else ("disciple" if disciple and tid == disciple.get("id") else tid)
            if label in ("everyone", "disciple") or (disciple and tid == disciple.get("id")):
                print(" ", label, "allow", ow.get("allow"), "deny", ow.get("deny"))

    # onboarding
    try:
        onboarding = api("GET", f"/guilds/{GUILD_ID}/onboarding")
        print("\n=== ONBOARDING ===")
        print("enabled", onboarding.get("enabled"))
        print("mode", onboarding.get("mode"))
        print("default_channel_ids", onboarding.get("default_channel_ids"))
        print("prompts", len(onboarding.get("prompts") or []))
    except Exception as e:
        print("\n=== ONBOARDING ERR ===", e)

    # member verification gate
    try:
        screening = api("GET", f"/guilds/{GUILD_ID}/member-verification")
        print("\n=== MEMBER SCREENING ===")
        print(json.dumps(screening, ensure_ascii=False)[:800])
    except Exception as e:
        print("\n=== MEMBER SCREENING ERR ===", type(e).__name__, e)


if __name__ == "__main__":
    main()
