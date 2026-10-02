#!/usr/bin/env python3
"""Check if #règlement still has the accept/captcha button message."""
import json
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
CHANNEL_REGLEMENT_ID = "1541249727662784612"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api_get(path: str):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={
            "Authorization": f"Bot {load_token()}",
            "User-Agent": "ZaelrysCaptchaCheck/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> None:
    msgs = api_get(f"/channels/{CHANNEL_REGLEMENT_ID}/messages?limit=30")
    found = False
    for m in msgs:
        comps = m.get("components") or []
        content = (m.get("content") or "")[:140]
        author = (m.get("author") or {}).get("username")
        print(m["id"], author, "comps", bool(comps), repr(content))
        for row in comps:
            for c in row.get("components", []):
                print("  btn", c.get("custom_id"), c.get("label"), "disabled", c.get("disabled"))
                if c.get("custom_id") == "accept_rules":
                    found = True
    print("ACCEPT_BUTTON", found)
    print("MSG_COUNT", len(msgs))


if __name__ == "__main__":
    main()
