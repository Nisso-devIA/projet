#!/usr/bin/env python3
"""Delete social branding pinned messages by ID."""
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")

TO_DELETE = [
    ("1541251095492435978", "1542195553981698151"),
    ("1541251096763179181", "1542195557039210598"),
    ("1541251097962877010", "1542195559715176500"),
]


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def delete(path: str) -> None:
    token = load_token()
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        headers={"Authorization": f"Bot {token}", "User-Agent": "Zaelrys/1.0"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("ok", path, resp.status)
    except urllib.error.HTTPError as e:
        print("skip", path, e.code)


def main() -> None:
    for ch, mid in TO_DELETE:
        delete(f"/channels/{ch}/pins/{mid}")
        delete(f"/channels/{ch}/messages/{mid}")


if __name__ == "__main__":
    main()
