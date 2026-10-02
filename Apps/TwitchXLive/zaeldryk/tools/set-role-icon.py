#!/usr/bin/env python3
"""Set Discord role icon from PNG (base64 via API)."""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

GUILD_ID = "867426693286461490"
DEFAULT_ROLE_ID = "1541249416374259863"  # BOT_modération
ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str, body=None):
    token = load_token()
    data = None
    headers = {"Authorization": f"Bot {token}", "User-Agent": "ZaelrysRoleIcon/1.0"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


def image_to_data_uri(path: Path) -> str:
    raw = path.read_bytes()
    if len(raw) > 256 * 1024:
        raise SystemExit("Image trop lourde (>256 KB) — redimensionne (128×128 recommandé)")
    suffix = path.suffix.lower()
    mime = "image/png" if suffix == ".png" else "image/jpeg"
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def main() -> None:
    p = argparse.ArgumentParser(description="Set Discord role icon from PNG/JPG")
    p.add_argument("image", type=Path, help="Chemin vers PNG ou JPG")
    p.add_argument("--role-id", default=DEFAULT_ROLE_ID)
    p.add_argument("--name", help="Renommer le rôle aussi")
    args = p.parse_args()
    if not args.image.exists():
        raise SystemExit(f"Fichier introuvable: {args.image}")

    guild = api("GET", f"/guilds/{GUILD_ID}")[1]
    print("premium_tier", guild.get("premium_tier"))

    body = {"icon": image_to_data_uri(args.image)}
    if args.name:
        body["name"] = args.name

    status, role = api("PATCH", f"/guilds/{GUILD_ID}/roles/{args.role_id}", body)
    print("OK", status, role.get("name"), "icon_set", bool(role.get("icon")))


if __name__ == "__main__":
    main()
