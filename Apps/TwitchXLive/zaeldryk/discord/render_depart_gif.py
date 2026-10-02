#!/usr/bin/env python3
"""Realistic goodbye GIF: fire/ice breath converges and writes the member name."""
from __future__ import annotations

import math
import random
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

BASE_IMG = Path("/home/ubuntu/zaeldryk/discord/assets/au_revoir_base.jpg")
WELCOME_IMG = Path("/home/ubuntu/zaeldryk/discord/assets/bienvenue_base.jpg")
FALLBACK_IMG = Path("/tmp/au_revoir_src.jpg")
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
OUT_DIR = Path("/home/ubuntu/zaeldryk/discord/assets/generated")


def _load_base(kind: str = "depart", max_w: int = 760) -> Image.Image:
    if kind == "welcome" and WELCOME_IMG.exists():
        src_path = WELCOME_IMG
    elif BASE_IMG.exists():
        src_path = BASE_IMG
    else:
        src_path = FALLBACK_IMG
    img = Image.open(src_path).convert("RGB")
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
    return img


def _font(size: int):
    try:
        return ImageFont.truetype(str(FONT_PATH), size=size)
    except OSError:
        return ImageFont.load_default()


def _fit_font(draw, text: str, max_width: int, max_size: int = 56, min_size: int = 18):
    for size in range(max_size, min_size - 1, -2):
        font = _font(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _font(min_size)


def _lerp(a, b, t):
    return a + (b - a) * t


def _fire_color(t: float, heat: float) -> tuple[int, int, int, int]:
    """t along plume 0=core source .. 1=tip; heat 0..1"""
    # white-yellow -> orange -> deep red -> smoke
    if t < 0.15:
        r, g, b = 255, 250, 220
    elif t < 0.4:
        u = (t - 0.15) / 0.25
        r, g, b = 255, int(_lerp(230, 140, u)), int(_lerp(160, 30, u))
    elif t < 0.75:
        u = (t - 0.4) / 0.35
        r, g, b = int(_lerp(255, 180, u)), int(_lerp(140, 40, u)), int(_lerp(30, 10, u))
    else:
        u = (t - 0.75) / 0.25
        r, g, b = int(_lerp(180, 40, u)), int(_lerp(40, 20, u)), int(_lerp(10, 15, u))
    alpha = int(255 * heat * (1.0 - t * 0.55))
    return r, g, b, max(0, min(255, alpha))


def _ice_color(t: float, heat: float) -> tuple[int, int, int, int]:
    if t < 0.2:
        r, g, b = 230, 250, 255
    elif t < 0.55:
        u = (t - 0.2) / 0.35
        r, g, b = int(_lerp(200, 80, u)), int(_lerp(240, 180, u)), 255
    else:
        u = (t - 0.55) / 0.45
        r, g, b = int(_lerp(80, 30, u)), int(_lerp(180, 90, u)), int(_lerp(255, 160, u))
    alpha = int(240 * heat * (1.0 - t * 0.5))
    return r, g, b, max(0, min(255, alpha))


def _plume(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    progress: float,
    kind: str,
    rng: random.Random,
    frame_i: int,
):
    """Draw a turbulent breath plume from start -> end."""
    if progress <= 0.01:
        return

    steps = 40
    for i in range(steps):
        t = i / (steps - 1)
        if t > progress:
            break

        # Turbulence / flicker
        wobble = math.sin(t * 14 + frame_i * 0.55 + (0 if kind == "fire" else 1.7)) * (18 * (1 - t))
        wobble += math.cos(t * 9 - frame_i * 0.4) * (10 * (1 - t))
        nx = - (end[1] - start[1])
        ny = end[0] - start[0]
        norm = math.hypot(nx, ny) or 1.0
        nx, ny = nx / norm, ny / norm

        x = int(start[0] + (end[0] - start[0]) * t + nx * wobble)
        y = int(start[1] + (end[1] - start[1]) * t + ny * wobble)

        # Width: thick near mouth, narrow then bloom at tip
        width = (22 * (1 - t) + 6) * (0.75 + 0.35 * math.sin(frame_i * 0.7 + t * 8))
        width *= 0.65 + 0.35 * progress
        heat = min(1.0, progress * 1.25) * (0.85 + 0.15 * abs(math.sin(frame_i * 0.9 + t * 5)))

        col = _fire_color(t, heat) if kind == "fire" else _ice_color(t, heat)
        r = max(2, int(width))
        draw.ellipse((x - r, y - r // 2, x + r, y + r // 2), fill=col)

        # Hot white core
        if t < 0.55:
            cr = max(1, int(r * 0.35))
            core_a = int(col[3] * 0.7)
            draw.ellipse(
                (x - cr, y - cr // 2, x + cr, y + cr // 2),
                fill=(255, 255, 255, core_a) if kind == "fire" else (220, 245, 255, core_a),
            )

    # Embers / ice shards
    n_bits = int(35 * progress)
    for _ in range(n_bits):
        t = rng.random() * progress
        wobble = rng.uniform(-22, 22) * (1 - t)
        nx = -(end[1] - start[1])
        ny = end[0] - start[0]
        norm = math.hypot(nx, ny) or 1
        nx, ny = nx / norm, ny / norm
        x = int(start[0] + (end[0] - start[0]) * t + nx * wobble)
        y = int(start[1] + (end[1] - start[1]) * t + ny * wobble + rng.uniform(-6, 6))
        rr = rng.randint(1, 3)
        if kind == "fire":
            c = (255, rng.randint(120, 220), rng.randint(20, 80), rng.randint(120, 220))
        else:
            c = (rng.randint(160, 230), rng.randint(210, 255), 255, rng.randint(120, 220))
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=c)


def _breath_layer(size: tuple[int, int], progress: float, frame_i: int) -> Image.Image:
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    rng = random.Random(1000 + frame_i)

    # Mouth-ish origins matching the artwork composition
    left = (int(w * 0.30), int(h * 0.42))
    right = (int(w * 0.70), int(h * 0.42))
    center = (int(w * 0.50), int(h * 0.40))

    _plume(draw, left, center, progress, "fire", rng, frame_i)
    _plume(draw, right, center, progress, "ice", rng, frame_i)

    # Impact bloom when breaths meet
    if progress > 0.55:
        bloom = (progress - 0.55) / 0.45
        br = int(28 + 40 * bloom)
        bloom_layer = Image.new("RGBA", size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(bloom_layer)
        bd.ellipse(
            (center[0] - br, center[1] - br // 2, center[0] + br, center[1] + br // 2),
            fill=(255, 230, 180, int(90 * bloom)),
        )
        bd.ellipse(
            (center[0] - br // 2, center[1] - br // 3, center[0] + br // 2, center[1] + br // 3),
            fill=(200, 240, 255, int(110 * bloom)),
        )
        bloom_layer = bloom_layer.filter(ImageFilter.GaussianBlur(radius=6 + 4 * bloom))
        layer = Image.alpha_composite(layer, bloom_layer)

    # Soft cinematic glow
    glow = layer.filter(ImageFilter.GaussianBlur(radius=2.8))
    layer = Image.alpha_composite(glow, layer)
    return layer


def _text_layer(size, text: str, font, cy: int, reveal: float, frame_i: int) -> Image.Image:
    w, h = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    if reveal <= 0 or not text:
        return layer

    n = max(1, len(text))
    chars = max(1, int(math.ceil(n * reveal)))
    shown = text[:chars]

    # Magical ink trail under letters
    ink = Image.new("RGBA", size, (0, 0, 0, 0))
    idraw = ImageDraw.Draw(ink)
    bbox = idraw.textbbox((0, 0), shown, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = cy - th // 2
    idraw.rounded_rectangle(
        (x - 14, y - 8, x + tw + 14, y + th + 10),
        radius=10,
        fill=(10, 15, 30, int(110 * min(1.0, reveal * 1.2))),
    )
    ink = ink.filter(ImageFilter.GaussianBlur(radius=1.2))
    layer = Image.alpha_composite(layer, ink)

    # Multi-pass metallic gold + frost rim
    passes = [
        (10, (255, 140, 40, 70)),
        (6, (80, 180, 255, 60)),
        (3, (255, 210, 90, 150)),
        (0, (255, 240, 190, 255)),
    ]
    for blur, fill in passes:
        tmp = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(tmp)
        d.text((x, y), shown, font=font, fill=fill)
        if blur:
            tmp = tmp.filter(ImageFilter.GaussianBlur(radius=blur))
        layer = Image.alpha_composite(layer, tmp)

    # Writing spark / breath tip
    if reveal < 0.98:
        tip = x + tw
        ty = y + th // 2
        spark = Image.new("RGBA", size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(spark)
        pulse = 0.6 + 0.4 * abs(math.sin(frame_i * 0.8))
        sd.ellipse((tip - 5, ty - 5, tip + 5, ty + 5), fill=(255, 255, 255, int(230 * pulse)))
        sd.ellipse((tip - 12, ty - 12, tip + 12, ty + 12), fill=(255, 180, 80, int(90 * pulse)))
        sd.ellipse((tip - 18, ty - 18, tip + 18, ty + 18), fill=(100, 200, 255, int(70 * pulse)))
        spark = spark.filter(ImageFilter.GaussianBlur(radius=1.5))
        layer = Image.alpha_composite(layer, spark)

    return layer


def _cover_baked_title(img: Image.Image, kind: str = "depart") -> Image.Image:
    """Hide fixed BIENVENUE / AU REVOIR gold text on the artwork."""
    w, h = img.size
    cover = img.copy()
    plate = Image.new("RGB", (w, h), (8, 12, 28))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    # Welcome title sits a bit higher with the crown
    if kind == "welcome":
        box = (int(w * 0.12), int(h * 0.14), int(w * 0.88), int(h * 0.48))
    else:
        box = (int(w * 0.18), int(h * 0.22), int(w * 0.82), int(h * 0.52))
    md.ellipse(box, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(12, w // 40)))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=8))
    blended = Image.composite(blurred, plate, Image.new("L", (w, h), 90))
    return Image.composite(blended, cover, mask)


def render_member_gif(member_name: str, kind: str = "depart", out_path: Path | None = None) -> Path:
    """kind: 'depart' -> Au revoir ; 'welcome' -> Bienvenue"""
    name = re.sub(r"\s+", " ", (member_name or "Voyageur").strip())[:22] or "Voyageur"
    if kind == "welcome":
        text = f"Bienvenue {name}"
        prefix = "welcome"
    else:
        text = f"Au revoir {name}"
        prefix = "depart"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", name)[:40] or "member"
    out = out_path or (OUT_DIR / f"{prefix}_{safe}.gif")

    base = _load_base(kind=kind)
    w, h = base.size

    base = ImageEnhance.Brightness(base).enhance(0.90 if kind == "welcome" else 0.82)
    base = ImageEnhance.Contrast(base).enhance(1.15)
    base = ImageEnhance.Color(base).enhance(1.08)
    base = _cover_baked_title(base, kind=kind)

    dark = ImageEnhance.Brightness(base).enhance(0.45)
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((-int(w * 0.08), -int(h * 0.12), int(w * 1.08), int(h * 1.12)), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(20, min(w, h) // 7)))
    base = Image.composite(base, dark, mask)

    probe = ImageDraw.Draw(Image.new("RGB", (w, h)))
    font = _fit_font(probe, text, max_width=int(w * 0.84), max_size=46, min_size=16)
    name_y = int(h * 0.40)

    frames = []
    n = 24
    for i in range(n):
        t = i / (n - 1)
        breath_p = min(1.0, (t / 0.50) ** 0.85)
        text_p = 0.0 if t < 0.32 else min(1.0, ((t - 0.32) / 0.58) ** 0.9)

        frame = base.convert("RGBA")
        flicker = 1.0 + 0.03 * math.sin(i * 0.9) + 0.02 * breath_p
        frame = ImageEnhance.Brightness(frame.convert("RGB")).enhance(flicker).convert("RGBA")

        breath = _breath_layer((w, h), breath_p, i)
        glow = breath.filter(ImageFilter.GaussianBlur(radius=3))
        frame = Image.alpha_composite(frame, Image.blend(
            Image.new("RGBA", (w, h), (0, 0, 0, 0)), glow, 0.65
        ))
        frame = Image.alpha_composite(frame, Image.blend(
            Image.new("RGBA", (w, h), (0, 0, 0, 0)), breath, 0.85
        ))

        written = _text_layer((w, h), text, font, name_y, text_p, i)
        frame = Image.alpha_composite(frame, written)
        frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=160))

    frames.extend([frames[-1], frames[-1]])
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=85,
        loop=0,
        optimize=True,
        disposal=2,
    )
    return out


def render_depart_gif(member_name: str, out_path: Path | None = None) -> Path:
    return render_member_gif(member_name, kind="depart", out_path=out_path)


def render_welcome_gif(member_name: str, out_path: Path | None = None) -> Path:
    return render_member_gif(member_name, kind="welcome", out_path=out_path)


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "Nisso"
    mode = sys.argv[2] if len(sys.argv) > 2 else "depart"
    path = render_member_gif(name, kind=mode)
    print(path, path.stat().st_size)
