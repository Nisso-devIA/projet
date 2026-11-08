"""Encode un brouillon 720x1280 sans le son d'origine, sous 10 Mo."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .theme import Theme, WaitingMusic

WIDTH = 720
HEIGHT = 1280
DISCORD_LIMIT = 10 * 1024 * 1024
TARGET_MAX = 9_500_000
AUDIO_BPS = 64_000
MIN_VIDEO_BPS = 80_000
OVERHEAD = 1.08


class ClipTooLong(Exception):
    pass


class EncodeFailed(Exception):
    pass


def video_budget(duration: float, max_bytes: int = TARGET_MAX) -> int:
    if duration <= 0:
        raise ClipTooLong("durée nulle")
    total = int((max_bytes * 8) / (duration * OVERHEAD))
    video = total - AUDIO_BPS
    if video < MIN_VIDEO_BPS:
        raise ClipTooLong(
            f"durée {duration:.1f}s trop longue pour rester sous 10 Mo"
        )
    return video


def ffmpeg_cmd(
    source: Path,
    theme: Path,
    out: Path,
    duration: float,
    video_bps: int,
) -> list[str]:
    filt = (
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v];"
        "[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a]"
    )
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-stream_loop",
        "-1",
        "-i",
        str(theme),
        "-t",
        f"{duration:.3f}",
        "-filter_complex",
        filt,
        "-map",
        "[v]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-b:v",
        str(video_bps),
        "-maxrate",
        str(video_bps),
        "-bufsize",
        str(video_bps * 2),
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(out),
    ]


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip() or "0")


def encode_draft(source: Path, theme: Theme, out: Path) -> Path:
    if not theme.ready():
        raise WaitingMusic(theme.block_reason())
    assert theme.path is not None
    duration = probe_duration(source)
    video_bps = video_budget(duration)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ffmpeg_cmd(source, theme.path, out, duration, video_bps)
    if "0:a" in cmd:
        raise EncodeFailed("le son d'origine ne doit pas être mappé")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise EncodeFailed(proc.stderr[-500:])
    size = out.stat().st_size
    if size >= DISCORD_LIMIT or size > TARGET_MAX:
        lower = max(MIN_VIDEO_BPS, int(video_bps * 0.75))
        if lower < MIN_VIDEO_BPS or lower == video_bps:
            out.unlink(missing_ok=True)
            raise ClipTooLong(f"fichier {size} octets, limite {DISCORD_LIMIT}")
        proc = subprocess.run(
            ffmpeg_cmd(source, theme.path, out, duration, lower),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or out.stat().st_size >= DISCORD_LIMIT:
            out.unlink(missing_ok=True)
            raise ClipTooLong("impossible de rester sous 10 Mo")
    return out
