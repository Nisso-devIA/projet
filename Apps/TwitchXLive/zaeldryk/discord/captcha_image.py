"""Image captcha for the Zaeldryk join gate.

Six characters, no ambiguous glyphs, drawn with noise so a plain text
question is not enough. The gate itself is in-memory: three tries, then
a short cooldown, and each image expires on its own.
"""

from __future__ import annotations

import io
import math
import random
import secrets
import time
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
AMBIGUOUS = set("0O1Il")
CODE_LENGTH = 6
TTL_SECONDS = 300
MAX_ATTEMPTS = 3
COOLDOWN_SECONDS = 120

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
)


class CooldownError(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(retry_after)


@dataclass
class CaptchaSession:
    captcha_id: str
    code: str
    expires_at: float
    attempts: int = 0


@dataclass
class SubmitResult:
    status: str
    attempts: int = 0
    left: int = 0
    retry_after: float = 0


def codes_match(given: str, expected: str) -> bool:
    def normalize(value: str) -> str:
        return "".join(value.split()).casefold()

    return normalize(given) == normalize(expected)


class CaptchaGate:
    def __init__(self) -> None:
        self.sessions: dict[int, CaptchaSession] = {}
        self.cooldowns: dict[int, float] = {}

    def cooldown_remaining(self, user_id: int, now: float | None = None) -> float:
        moment = time.time() if now is None else now
        return max(0.0, self.cooldowns.get(user_id, 0.0) - moment)

    def issue(self, user_id: int, now: float | None = None) -> CaptchaSession:
        moment = time.time() if now is None else now
        remaining = self.cooldown_remaining(user_id, moment)
        if remaining > 0:
            raise CooldownError(remaining)
        code = "".join(secrets.choice(CHARSET) for _ in range(CODE_LENGTH))
        session = CaptchaSession(
            captcha_id=secrets.token_hex(8),
            code=code,
            expires_at=moment + TTL_SECONDS,
        )
        self.sessions[user_id] = session
        return session

    def submit(
        self,
        user_id: int,
        captcha_id: str,
        answer: str,
        now: float | None = None,
    ) -> SubmitResult:
        moment = time.time() if now is None else now
        session = self.sessions.get(user_id)
        if session is None or session.captcha_id != captcha_id:
            return SubmitResult("stale")
        if moment >= session.expires_at:
            self.sessions.pop(user_id, None)
            return SubmitResult("expired")
        session.attempts += 1
        if codes_match(answer, session.code):
            attempts = session.attempts
            self.clear(user_id)
            return SubmitResult("ok", attempts=attempts)
        left = MAX_ATTEMPTS - session.attempts
        if left <= 0:
            attempts = session.attempts
            self.sessions.pop(user_id, None)
            self.cooldowns[user_id] = moment + COOLDOWN_SECONDS
            return SubmitResult("locked", attempts=attempts, retry_after=COOLDOWN_SECONDS)
        return SubmitResult("wrong", attempts=session.attempts, left=left)

    def clear(self, user_id: int) -> None:
        self.sessions.pop(user_id, None)
        self.cooldowns.pop(user_id, None)


def _font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _ink() -> tuple[int, int, int, int]:
    return (
        random.randint(236, 255),
        random.randint(198, 228),
        random.randint(96, 150),
        255,
    )


def _noise() -> tuple[int, int, int]:
    return (
        random.randint(90, 170),
        random.randint(70, 130),
        random.randint(30, 70),
    )


def _wave(image: Image.Image) -> Image.Image:
    width, height = image.size
    warped = Image.new("RGB", (width, height), (42, 32, 22))
    source = image.load()
    target = warped.load()
    phase_x = random.random() * math.tau
    phase_y = random.random() * math.tau
    for y in range(height):
        shift_x = int(round(3.0 * math.sin(y / 12.0 + phase_x)))
        for x in range(width):
            shift_y = int(round(2.0 * math.sin(x / 18.0 + phase_y)))
            sample_x = min(width - 1, max(0, x + shift_x))
            sample_y = min(height - 1, max(0, y + shift_y))
            target[x, y] = source[sample_x, sample_y]
    return warped


def render_captcha_png(code: str) -> bytes:
    if any(char not in CHARSET for char in code):
        raise ValueError("captcha code uses a glyph outside the charset")
    width, height = 380, 140
    image = Image.new("RGB", (width, height), (42, 32, 22))
    draw = ImageDraw.Draw(image)
    for _ in range(14):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        draw.line(
            (x0, y0, x0 + random.randint(-80, 80), y0 + random.randint(-36, 36)),
            fill=_noise(),
            width=random.choice((1, 1, 2)),
        )
    for _ in range(140):
        draw.point((random.randint(0, width - 1), random.randint(0, height - 1)), fill=_noise())

    font = _font(48)
    resample = getattr(getattr(Image, "Resampling", Image), "BICUBIC")
    for index, char in enumerate(code):
        tile = Image.new("RGBA", (70, 86), (0, 0, 0, 0))
        pen = ImageDraw.Draw(tile)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            pen.text((12 + dx, 8 + dy), char, font=font, fill=(24, 14, 8, 230))
        pen.text((12, 8), char, font=font, fill=_ink())
        tile = tile.rotate(random.uniform(-24, 24), resample=resample, expand=True)
        x = 14 + index * 58 + random.randint(-4, 4)
        y = 18 + random.randint(-8, 10)
        image.paste(tile, (x, y), tile)

    draw = ImageDraw.Draw(image)
    for _ in range(3):
        draw.arc(
            [
                random.randint(-20, 80),
                random.randint(-10, 40),
                random.randint(260, 400),
                random.randint(90, 160),
            ],
            start=random.randint(0, 80),
            end=random.randint(180, 320),
            fill=(196, 154, 64),
            width=1,
        )
    image = _wave(image)
    draw = ImageDraw.Draw(image)
    for _ in range(70):
        draw.point((random.randint(0, width - 1), random.randint(0, height - 1)), fill=_noise())

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
