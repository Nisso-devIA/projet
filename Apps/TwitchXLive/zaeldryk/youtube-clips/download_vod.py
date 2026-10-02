#!/usr/bin/env python3
"""Download Twitch VOD via yt-dlp."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from config import Settings


def download_vod(settings: Settings, vod_id: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tmpl = str(out_dir / f"{vod_id}.%(ext)s")
    final = out_dir / f"{vod_id}.mp4"
    if final.exists() and final.stat().st_size > 1_000_000:
        return final

    yt_dlp = shutil.which("yt-dlp") or shutil.which("yt-dlp_x86")
    if not yt_dlp:
        raise RuntimeError("yt-dlp not found in PATH")

    height = settings.vod_height
    fmt = f"best[height<=?{height}]/best"
    url = f"https://www.twitch.tv/videos/{vod_id}"
    cmd = [
        yt_dlp,
        "-f",
        fmt,
        "--merge-output-format",
        "mp4",
        "-o",
        out_tmpl,
        "--no-playlist",
        "--retries",
        "5",
        url,
    ]
    subprocess.run(cmd, check=True)

    # Resolve actual file
    candidates = sorted(out_dir.glob(f"{vod_id}.*"))
    for c in candidates:
        if c.suffix.lower() in {".mp4", ".mkv", ".webm"}:
            if c.suffix.lower() != ".mp4":
                remux = out_dir / f"{vod_id}.mp4"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(c),
                        "-c",
                        "copy",
                        str(remux),
                    ],
                    check=True,
                    capture_output=True,
                )
                return remux
            return c
    raise RuntimeError(f"VOD download produced no media for {vod_id}")
