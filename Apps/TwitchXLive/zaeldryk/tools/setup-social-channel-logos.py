#!/usr/bin/env python3
"""Official social logos → guild emojis + channel icons + channel names."""
import argparse
import base64
import json
import re
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

GUILD_ID = "867426693286461490"
ENV = Path("/home/ubuntu/zaeldryk/config/discord.env")
ASSETS = Path("/home/ubuntu/zaeldryk/discord/assets")

CHANNELS = {
    "twitch": {
        "id": "1541251095492435978",
        "svg_url": "https://raw.githubusercontent.com/simple-icons/simple-icons/11.4.0/icons/twitch.svg",
        "fill": "#9146FF",
        "emoji_name": "logo_twitch",
        "channel_name": "twitch",
    },
    "youtube": {
        "id": "1541251096763179181",
        "svg_url": "https://raw.githubusercontent.com/simple-icons/simple-icons/11.4.0/icons/youtube.svg",
        "fill": "#FF0000",
        "emoji_name": "logo_youtube",
        "channel_name": "youtube",
    },
    "x": {
        "id": "1541251097962877010",
        "svg_url": "https://raw.githubusercontent.com/simple-icons/simple-icons/11.4.0/icons/x.svg",
        "fill": "#000000",
        "emoji_name": "logo_x",
        "channel_name": "twitter",
    },
}

SVG_NS = "http://www.w3.org/2000/svg"


def load_token() -> str:
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(method: str, path: str, body=None):
    token = load_token()
    data = None
    headers = {"Authorization": f"Bot {token}", "User-Agent": "ZaelrysSocialLogos/1.0"}
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


def fetch_svg(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ZaelrysSocialLogos/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def svg_to_png(svg_text: str, fill: str, size: int = 128) -> bytes:
    """Rasterize simple-icons SVG via cairosvg if available, else Pillow paths."""
    try:
        import cairosvg  # type: ignore

        if "fill=" not in svg_text and fill:
            svg_text = re.sub(
                r"<svg ",
                f'<svg fill="{fill}" ',
                svg_text,
                count=1,
            )
        return cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=size, output_height=size)
    except Exception:
        pass

    # Fallback: download pre-colored PNG from jsdelivr simple-icons npm package path
    # (official vector baked into PNG by GitHub CDN renderer)
    slug = {
        "#9146FF": "twitch",
        "#FF0000": "youtube",
        "#000000": "x",
    }.get(fill.upper(), "x")
    png_url = f"https://cdn.jsdelivr.net/npm/simple-icons@v11.4.0/icons/{slug}.png"
    try:
        req = urllib.request.Request(png_url, headers={"User-Agent": "ZaelrysSocialLogos/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if data[:4] == b"\x89PNG":
                img = Image.open(BytesIO(data)).convert("RGBA")
                img = img.resize((size, size), Image.Resampling.LANCZOS)
                out = BytesIO()
                img.save(out, format="PNG")
                return out.getvalue()
    except Exception:
        pass

    raise SystemExit(f"Impossible de rasteriser le logo {fill}")


def image_data_uri(png_bytes: bytes) -> str:
    if len(png_bytes) > 256 * 1024:
        raise SystemExit("PNG > 256 KB")
    return f"data:image/png;base64,{base64.b64encode(png_bytes).decode('ascii')}"


def ensure_png(key: str, cfg: dict) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / f"{key}-logo.png"
    svg = fetch_svg(cfg["svg_url"])
    png_bytes = svg_to_png(svg, cfg["fill"], 128)
    out.write_bytes(png_bytes)
    print(f"saved {out} ({len(png_bytes)} bytes)")
    return out


def list_guild_emojis():
    _, emojis = api("GET", f"/guilds/{GUILD_ID}/emojis")
    return emojis or []


def delete_emoji(emoji_id: str):
    api("DELETE", f"/guilds/{GUILD_ID}/emojis/{emoji_id}")


def upload_emoji(name: str, png_bytes: bytes) -> dict:
    for em in list_guild_emojis():
        if em.get("name") == name:
            delete_emoji(em["id"])
    _, created = api(
        "POST",
        f"/guilds/{GUILD_ID}/emojis",
        {"name": name, "image": image_data_uri(png_bytes)},
    )
    print(f"emoji {name} id={created.get('id')}")
    return created


def emoji_id_to_tag(emoji_id: str) -> str:
    """Discord encodes custom emoji IDs with U+E0000 + ASCII codepoint per digit."""
    return "".join(chr(0xE0000 + ord(c)) for c in emoji_id)


def channel_name_with_emoji(emoji_id: str, base_name: str) -> str:
    return f"{emoji_id_to_tag(emoji_id)}-{base_name}"


def setup_channel(channel_id: str, png_bytes: bytes, display_name: str, emoji: dict) -> None:
    tagged_name = channel_name_with_emoji(emoji["id"], display_name)
    body = {"icon": image_data_uri(png_bytes), "name": tagged_name}
    status, ch = api("PATCH", f"/channels/{channel_id}", body)
    print(
        f"channel {channel_id} status={status} name={ch.get('name')} "
        f"icon={bool(ch.get('icon'))} tagged_len={len(tagged_name)}"
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--names-only", action="store_true", help="Fix channel names, reuse existing emojis")
    args = p.parse_args()

    _, guild = api("GET", f"/guilds/{GUILD_ID}")
    print("premium_tier", guild.get("premium_tier"))

    existing = {e.get("name"): e for e in list_guild_emojis()}
    emojis_created = {}

    if args.names_only:
        for key, cfg in CHANNELS.items():
            em = existing.get(cfg["emoji_name"])
            if not em:
                raise SystemExit(f"Emoji manquant: {cfg['emoji_name']}")
            emojis_created[key] = em
    else:
        for key, cfg in CHANNELS.items():
            png_path = ensure_png(key, cfg)
            png_bytes = png_path.read_bytes()
            emojis_created[key] = upload_emoji(cfg["emoji_name"], png_bytes)

    for key, cfg in CHANNELS.items():
        png_path = ASSETS / f"{key}-logo.png"
        if not png_path.exists() and not args.names_only:
            continue
        png_bytes = png_path.read_bytes() if png_path.exists() else b""
        if args.names_only and not png_bytes:
            # minimal 1x1 for icon field omitted
            setup_channel_names_only(cfg["id"], cfg["channel_name"], emojis_created[key])
        else:
            setup_channel(cfg["id"], png_bytes, cfg["channel_name"], emojis_created[key])

    print("done")


def setup_channel_names_only(channel_id: str, display_name: str, emoji: dict) -> None:
    tagged_name = channel_name_with_emoji(emoji["id"], display_name)
    status, ch = api("PATCH", f"/channels/{channel_id}", {"name": tagged_name})
    print(f"channel {channel_id} status={status} name={ch.get('name')}")


if __name__ == "__main__":
    main()
