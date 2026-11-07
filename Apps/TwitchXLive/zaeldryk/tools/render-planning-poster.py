#!/usr/bin/env python3
"""Affiche planning semaine : le visuel fixe, le texte suit le planning Twitch."""
from __future__ import annotations

import json
import sys
import uuid
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ROOT = Path("/home/ubuntu/zaeldryk")
TEMPLATE = ROOT / "discord" / "assets" / "planning-week-template.jpg"
OUT = ROOT / "discord" / "assets" / "planning-poster.png"
STATE = ROOT / "state" / "planning-calendar.json"
FONT = Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf")
FONT_REG = Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf")
CHANNEL_ID = "1568352153872109588"
PARIS = ZoneInfo("Europe/Paris")
# Zone sous le nom du jour (lundi → dimanche), sur le visuel 687×1024.
BOXES = (
    (392, 452),
    (486, 540),
    (570, 622),
    (654, 710),
    (744, 800),
    (830, 890),
    (922, 972),
)
TEXT_X = 168
TEXT_RIGHT = 530
GOLD = (214, 176, 96)
CREAM = (236, 220, 176)
MUTED = (164, 158, 124)
CAPTION = (
    "## ⚔️ Planning\n\n"
    "Semaine du lundi au dimanche\n"
    "👉 <https://twitch.tv/zaeldryk>"
)


def ensure_fonts() -> None:
    if not FONT.exists() or not FONT_REG.exists():
        raise SystemExit(f"police manquante: {FONT}")


def load_env(path: Path) -> dict:
    cfg = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def fetch_slots() -> list[dict | None]:
    cfg = load_env(ROOT / "config" / "twitch.env")
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
            "Authorization": "Bearer " + token,
            "User-Agent": "ZaelrysPlanning/1.3",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    by_day: list[list[dict]] = [[] for _ in range(7)]
    for seg in (payload.get("data") or {}).get("segments") or []:
        if seg.get("cancelled_until") or not seg.get("start_time"):
            continue
        start = datetime.fromisoformat(seg["start_time"].replace("Z", "+00:00")).astimezone(PARIS)
        title = " ".join((seg.get("title") or "Live").split())
        by_day[start.weekday()].append({"title": title, "start": start})
    slots: list[dict | None] = []
    for items in by_day:
        if not items:
            slots.append(None)
            continue
        items.sort(key=lambda s: s["start"])
        nxt = items[0]
        slots.append({"title": nxt["title"], "hm": f"{nxt['start'].hour}h{nxt['start'].minute:02d}"})
    return slots


def fingerprint(slots: list[dict | None]) -> str:
    packed = [None if s is None else {"title": s["title"], "hm": s["hm"]} for s in slots]
    return json.dumps(packed, ensure_ascii=False)


def fit(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1].rstrip()
    return (text or "…") + "…"


def blank(im: Image.Image, box: tuple[int, int, int, int]) -> None:
    """Recouvre l'ancien texte avec le fond de la ligne, pas un aplat noir."""
    x0, y0, x1, y1 = box
    src = im.crop((548, y0 + 2, 572, max(y0 + 8, y1 - 2)))
    src = src.resize((x1 - x0, y1 - y0), Image.Resampling.BILINEAR)
    im.paste(src, (x0, y0))


def render(slots: list[dict | None]) -> None:
    ensure_fonts()
    im = Image.open(TEMPLATE).convert("RGB")
    draw = ImageDraw.Draw(im)
    title_font = ImageFont.truetype(str(FONT), 18)
    sub_font = ImageFont.truetype(str(FONT_REG), 15)
    max_w = TEXT_RIGHT - TEXT_X
    for slot, (y0, y1) in zip(slots, BOXES):
        blank(im, (TEXT_X - 4, y0, TEXT_RIGHT, y1))
        if slot is None:
            draw.text((TEXT_X, y0 + 8), "Aucun stream prévu", font=sub_font, fill=MUTED)
            continue
        title = fit(draw, slot["title"], title_font, max_w)
        draw.text((TEXT_X, y0), title, font=title_font, fill=CREAM)
        draw.text((TEXT_X, y0 + 22), slot["hm"], font=sub_font, fill=GOLD)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT, "PNG", optimize=True)


def load_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def token() -> str:
    for line in (ROOT / "config" / "discord.env").read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(tok: str, method: str, path: str, data: bytes | None, headers: dict) -> dict:
    h = {"Authorization": "Bot " + tok, "User-Agent": "ZaelrysPlanning/1.3"}
    h.update(headers)
    req = urllib.request.Request("https://discord.com/api/v10" + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {path}: {err[:300]}") from e


def post(state: dict) -> str:
    png = OUT.read_bytes()
    payload = {
        "content": CAPTION,
        "flags": 4,
        "attachments": [{"id": 0, "filename": "planning-semaine.png"}],
    }
    boundary = uuid.uuid4().hex
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="payload_json"\r\n',
            b"Content-Type: application/json\r\n\r\n",
            json.dumps(payload, ensure_ascii=False).encode(),
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="files[0]"; filename="planning-semaine.png"\r\n',
            b"Content-Type: image/png\r\n\r\n",
            png,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    tok = token()
    mid = state.get("message_id")
    if mid:
        msg = api(tok, "PATCH", f"/channels/{CHANNEL_ID}/messages/{mid}", body, headers)
        return msg["id"]
    msg = api(tok, "POST", f"/channels/{CHANNEL_ID}/messages", body, headers)
    api(tok, "PUT", f"/channels/{CHANNEL_ID}/pins/{msg['id']}", None, {})
    return msg["id"]


def main() -> None:
    slots = fetch_slots()
    fp = fingerprint(slots)
    state = load_state()
    posting = "--post" in sys.argv
    if posting and state.get("fingerprint") == fp and "--force" not in sys.argv:
        print("unchanged")
        return
    render(slots)
    print("rendered", OUT)
    if not posting:
        return
    mid = post(state)
    state["message_id"] = mid
    state["fingerprint"] = fp
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state), encoding="utf-8")
    print("updated", mid)


if __name__ == "__main__":
    main()
