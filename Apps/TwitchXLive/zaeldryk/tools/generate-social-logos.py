#!/usr/bin/env python3
"""Generate 128x128 brand PNGs for Discord channel icons."""
from pathlib import Path

from PIL import Image, ImageDraw

ASSETS = Path("/home/ubuntu/zaeldryk/discord/assets")
SIZE = 128


def twitch_logo() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    purple = (145, 70, 255, 255)
    s = SIZE / 24.0
    d.rectangle([11.5 * s, 4.7 * s, 13.2 * s, 9.8 * s], fill=purple)
    d.rectangle([16.3 * s, 4.7 * s, 18.0 * s, 9.8 * s], fill=purple)
    d.polygon(
        [
            (6 * s, 0),
            (1.7 * s, 4.3 * s),
            (1.7 * s, 19.7 * s),
            (6.7 * s, 24 * s),
            (10.3 * s, 24 * s),
            (14.5 * s, 19.7 * s),
            (17.9 * s, 19.7 * s),
            (21.3 * s, 16.3 * s),
            (21.3 * s, 0),
            (6 * s, 0),
        ],
        fill=purple,
    )
    return img


def youtube_logo() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    red = (255, 0, 0, 255)
    white = (255, 255, 255, 255)
    m = SIZE * 0.1
    d.rounded_rectangle(
        [m, m * 1.4, SIZE - m, SIZE - m * 1.4],
        radius=int(SIZE * 0.18),
        fill=red,
    )
    cx, cy = SIZE / 2, SIZE / 2
    w = SIZE * 0.2
    d.polygon(
        [(cx - w * 0.45, cy - w), (cx - w * 0.45, cy + w), (cx + w * 0.75, cy)],
        fill=white,
    )
    return img


def x_logo() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    black = (0, 0, 0, 255)
    pad = int(SIZE * 0.28)
    thick = max(8, SIZE // 10)
    d.line([pad, pad, SIZE - pad, SIZE - pad], fill=black, width=thick)
    d.line([SIZE - pad, pad, pad, SIZE - pad], fill=black, width=thick)
    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    twitch_logo().save(ASSETS / "twitch-logo.png")
    youtube_logo().save(ASSETS / "youtube-logo.png")
    x_logo().save(ASSETS / "x-logo.png")
    for name in ("twitch-logo.png", "youtube-logo.png", "x-logo.png"):
        p = ASSETS / name
        print(name, p.stat().st_size)


if __name__ == "__main__":
    main()
