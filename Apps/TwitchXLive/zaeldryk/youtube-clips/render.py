#!/usr/bin/env python3
"""FFmpeg render: Shorts 9:16, classic 16:9 compilation, music mix."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Sequence

from score_highlights import Segment


def _run(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def cut_segment(vod: Path, seg: Segment, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    dur = max(1.0, seg.duration)
    _run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{seg.start:.3f}",
            "-i",
            str(vod),
            "-t",
            f"{dur:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    return out


def mix_music(video: Path, music: Path, out: Path, music_volume: float) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    vol = max(0.01, min(0.5, music_volume))
    filt = (
        f"[1:a]volume={vol},aloop=loop=-1:size=2e+09[m];"
        f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(music),
            "-filter_complex",
            filt,
            "-map",
            "0:v",
            "-map",
            "[a]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ]
    )
    return out


def render_short(
    vod: Path,
    seg: Segment,
    music: Path,
    out: Path,
    music_volume: float,
) -> Path:
    """Center-crop vertical 1080x1920 + music."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.mp4")
    dur = max(1.0, seg.duration)
    vol = max(0.01, min(0.5, music_volume))
    vfilt = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1"
    )
    filt = (
        f"[0:v]{vfilt}[v];"
        f"[1:a]volume={vol},aloop=loop=-1:size=2e+09[m];"
        f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )
    _run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{seg.start:.3f}",
            "-i",
            str(vod),
            "-i",
            str(music),
            "-t",
            f"{dur:.3f}",
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
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(tmp),
        ]
    )
    tmp.replace(out)
    return out


def render_classic(
    vod: Path,
    segments: Sequence[Segment],
    music: Path,
    work: Path,
    out: Path,
    music_volume: float,
) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    parts: List[Path] = []
    for i, seg in enumerate(segments):
        part = work / f"classic_part_{i:02d}.mp4"
        cut_segment(vod, seg, part)
        parts.append(part)

    if not parts:
        raise RuntimeError("No classic segments to render")

    concat_list = work / "classic_concat.txt"
    concat_list.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n" for p in parts),
        encoding="utf-8",
    )
    joined = work / "classic_joined.mp4"
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(joined),
        ]
    )
    return mix_music(joined, music, out, music_volume)
