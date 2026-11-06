#!/usr/bin/env python3
"""Calendrier hebdo du planning Twitch → image épinglée dans #📅-planning."""
from __future__ import annotations

import json
import uuid
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

CHANNEL_ID = "1568352153872109588"
PARIS = ZoneInfo("Europe/Paris")
STATE = Path("/home/ubuntu/zaeldryk/state/planning-calendar.json")
OUT = Path("/tmp/planning-calendar.png")
BANNER = Path("/home/ubuntu/zaeldryk/discord/assets/planning-oot-jeudi.jpg")
DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

BG = (10, 18, 40)
HEADER = (16, 28, 58)
COL = (18, 32, 66)
CARD = (28, 48, 96)
ZELDA = (32, 110, 68)
GOLD = (230, 193, 90)
TEXT = (242, 236, 220)
MUTED = (168, 178, 198)


def load_token() -> str:
    for line in Path("/home/ubuntu/zaeldryk/config/discord.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def fetch_segments() -> list[dict]:
    cfg = {}
    for line in Path("/home/ubuntu/zaeldryk/config/twitch.env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    token = Path(cfg.get("TWITCH_TOKEN_FILE", "/home/ubuntu/twitch_token.txt")).read_text(encoding="utf-8").strip()
    url = (
        "https://api.twitch.tv/helix/schedule?broadcaster_id="
        + cfg.get("TWITCH_BROADCASTER_ID", "426411773")
        + "&first=25"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Client-ID": cfg["TWITCH_CLIENT_ID"],
            "Authorization": f"Bearer {token}",
            "User-Agent": "ZaelrysPlanning/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    out = []
    for seg in (payload.get("data") or {}).get("segments") or []:
        if seg.get("cancelled_until") or not seg.get("start_time"):
            continue
        start = datetime.fromisoformat(seg["start_time"].replace("Z", "+00:00")).astimezone(PARIS)
        end_raw = seg.get("end_time") or seg["start_time"]
        end = datetime.fromisoformat(end_raw.replace("Z", "+00:00")).astimezone(PARIS)
        out.append(
            {
                "title": (seg.get("title") or "Live").strip(),
                "game": ((seg.get("category") or {}).get("name") or "").strip(),
                "start": start,
                "end": end,
                "recurring": bool(seg.get("is_recurring")),
            }
        )
    return out


def horizon(now: datetime) -> list[datetime]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return [start + timedelta(days=i) for i in range(7)]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    path = Path("/usr/share/fonts/truetype/dejavu") / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = w if not cur else cur + " " + w
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def is_zelda(slot: dict) -> bool:
    blob = f"{slot['title']} {slot['game']}".lower()
    return "zelda" in blob or "ocarina" in blob


def render(days: list[tuple[datetime, list[dict]]]) -> None:
    week = days[:7]
    margin = 18
    gap = 10
    col_w = 196
    card_h = 72
    col_head = 46
    max_n = max((len(s) for _, s in week), default=1)
    grid_h = col_head + max_n * (card_h + 8) + 16
    width = margin * 2 + 7 * col_w + 6 * gap

    banner = None
    banner_h = 0
    if BANNER.exists():
        src = Image.open(BANNER).convert("RGB")
        banner_h = max(1, int(src.height * (width / src.width)))
        banner = src.resize((width, banner_h), Image.Resampling.LANCZOS)

    height = banner_h + 16 + grid_h + margin
    img = Image.new("RGB", (width, height), BG)
    if banner is not None:
        img.paste(banner, (0, 0))
    draw = ImageDraw.Draw(img)
    day_f = font(16, True)
    time_f = font(15, True)
    name_f = font(13)
    y0 = banner_h + 16
    for i, (date, slots) in enumerate(week):
        x = margin + i * (col_w + gap)
        featured = any(is_zelda(s) for s in slots)
        draw.rounded_rectangle((x, y0, x + col_w, y0 + grid_h), 14, fill=(12, 24, 52))
        if featured and banner is not None:
            crop = banner.resize((col_w - 8, grid_h - 8), Image.Resampling.LANCZOS)
            dark = Image.new("RGB", crop.size, (0, 0, 0))
            crop = Image.blend(crop, dark, 0.45)
            img.paste(crop, (x + 4, y0 + 4))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle((x, y0, x + col_w, y0 + grid_h), 14, outline=GOLD, width=3)
        label = f"{DAYS[date.weekday()][:3].upper()} {date.day}"
        draw.text((x + 12, y0 + 12), label, font=day_f, fill=GOLD)
        if not slots:
            draw.text((x + 12, y0 + col_head), "—", font=name_f, fill=MUTED)
            continue
        for n, slot in enumerate(slots[:3]):
            cy = y0 + col_head + n * (card_h + 8)
            if not featured:
                draw.rounded_rectangle(
                    (x + 8, cy, x + col_w - 8, cy + card_h), 10, fill=CARD
                )
            t0 = slot["start"].strftime("%Hh%M")
            draw.text((x + 16, cy + 8), t0, font=time_f, fill=GOLD)
            lines = wrap(draw, slot["title"], name_f, col_w - 32)
            yy = cy + 30
            for line in lines[:2]:
                draw.text((x + 16, yy), line, font=name_f, fill=TEXT)
                yy += 16
    img.save(OUT, "PNG")


def api(token: str, method: str, path: str, data=None, headers=None):
    h = {"Authorization": f"Bot {token}", "User-Agent": "ZaelrysPlanning/1.1"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}", data=data, headers=h, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err[:400]}") from e


def multipart(payload: dict, png: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="payload_json"\r\n',
        b"Content-Type: application/json\r\n\r\n",
        json.dumps(payload, ensure_ascii=False).encode(),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="files[0]"; filename="oot-jeudi.jpg"\r\n',
        b"Content-Type: image/jpeg\r\n\r\n",
        png,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), boundary


def main() -> None:
    raise SystemExit("affiche planning: tools/render-planning-poster.py")
    if not BANNER.exists():
        raise SystemExit(f"affiche manquante: {BANNER}")
    token = load_token()
    caption = (
        "## ⚔️ Planning\n\n"
        "**Tous les jeudis · 22h30**\n"
        "The Legend of Zelda: Ocarina of Time — Remake\n\n"
        "👉 https://twitch.tv/zaeldryk"
    )
    payload = {
        "content": caption,
        "attachments": [{"id": 0, "filename": "oot-jeudi.jpg"}],
    }
    body, boundary = multipart(payload, BANNER.read_bytes())
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    mid = state.get("message_id")
    if mid:
        msg = api(token, "PATCH", f"/channels/{CHANNEL_ID}/messages/{mid}", body, headers)
        print("updated", msg["id"])
        return
    msg = api(token, "POST", f"/channels/{CHANNEL_ID}/messages", body, headers)
    api(token, "PUT", f"/channels/{CHANNEL_ID}/pins/{msg['id']}")
    recent = api(token, "GET", f"/channels/{CHANNEL_ID}/messages?limit=10") or []
    for old in recent:
        if old.get("id") == msg["id"]:
            continue
        text = old.get("content") or ""
        if text.startswith("## ⚔️ Rendez-vous") or text.startswith("📅 **Planning des lives**"):
            api(token, "DELETE", f"/channels/{CHANNEL_ID}/messages/{old['id']}")
            print("removed old", old["id"])
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"message_id": msg["id"]}), encoding="utf-8")
    print("posted", msg["id"])


if __name__ == "__main__":
    main()
