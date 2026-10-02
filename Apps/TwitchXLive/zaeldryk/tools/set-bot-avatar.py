#!/usr/bin/env python3
"""Set Discord bot user avatar from PNG/JPG."""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def image_to_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise SystemExit("Image trop lourde (>8 MB)")
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def main() -> None:
    p = argparse.ArgumentParser(description="Set bot avatar from image")
    p.add_argument("image", type=Path)
    args = p.parse_args()
    if not args.image.exists():
        raise SystemExit(f"Fichier introuvable: {args.image}")

    token = load_token()
    body = json.dumps({"avatar": image_to_data_uri(args.image)}).encode("utf-8")
    req = urllib.request.Request(
        "https://discord.com/api/v10/users/@me",
        data=body,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "ZaelrysBotAvatar/1.0",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            user = json.loads(resp.read())
            print("OK avatar set for", user.get("username"), user.get("id"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code}: {err}") from e


if __name__ == "__main__":
    main()
