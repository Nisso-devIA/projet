#!/usr/bin/env python3
"""Score VOD highlights from chat density."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


HOT_RE = re.compile(
    r"(!clip|pog|lul|kappa|gg|insane|wtf|omg|clip\s*it|ez\b|no way)",
    re.IGNORECASE,
)


@dataclass
class Segment:
    start: float
    end: float
    score: float
    hook: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _probe_duration(vod_path: str) -> float:
    import json
    import subprocess

    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                vod_path,
            ],
            text=True,
        )
        data = json.loads(out)
        return float(data.get("format", {}).get("duration") or 0)
    except Exception:
        return 0.0


def score_windows(
    messages: Sequence[Dict[str, Any]],
    *,
    window: float,
    vod_duration: float,
    step: float | None = None,
) -> List[Segment]:
    if vod_duration <= 0:
        if messages:
            vod_duration = max(m["offset_seconds"] for m in messages) + window
        else:
            return []

    step = step or max(5.0, window / 4)
    offsets = [float(m["offset_seconds"]) for m in messages]
    texts = [str(m.get("message") or "") for m in messages]

    segs: List[Segment] = []
    t = 0.0
    while t + window <= vod_duration + 1:
        end = t + window
        count = 0
        bonus = 0.0
        sample_msgs: List[str] = []
        for off, text in zip(offsets, texts):
            if t <= off < end:
                count += 1
                if HOT_RE.search(text):
                    bonus += 1.5
                if text and len(sample_msgs) < 3:
                    sample_msgs.append(text.strip()[:40])
        score = count + bonus
        hook = sample_msgs[0] if sample_msgs else f"@{int(t)}s"
        segs.append(Segment(start=t, end=end, score=score, hook=hook))
        t += step
    segs.sort(key=lambda s: s.score, reverse=True)
    return segs


def _overlaps(a: Segment, b: Segment, pad: float = 5.0) -> bool:
    return not (a.end + pad <= b.start or b.end + pad <= a.start)


def pick_non_overlapping(candidates: List[Segment], n: int) -> List[Segment]:
    picked: List[Segment] = []
    for c in candidates:
        if c.score <= 0 and picked:
            continue
        if any(_overlaps(c, p) for p in picked):
            continue
        picked.append(c)
        if len(picked) >= n:
            break
    return picked


def build_short_segments(
    messages: Sequence[Dict[str, Any]],
    *,
    vod_path: str,
    count: int,
    window: float,
) -> List[Segment]:
    duration = _probe_duration(vod_path)
    windows = score_windows(messages, window=window, vod_duration=duration)
    if not windows:
        # Fallback: evenly spaced
        if duration <= 0:
            return []
        out: List[Segment] = []
        for i in range(count):
            mid = duration * (i + 1) / (count + 1)
            start = max(0.0, mid - window / 2)
            end = min(duration, start + window)
            out.append(Segment(start=start, end=end, score=0, hook=f"Moment {i+1}"))
        return out
    picked = pick_non_overlapping(windows, count)
    # Chronological for readability in filenames only — keep score order for ranking
    return picked


def build_classic_segments(
    messages: Sequence[Dict[str, Any]],
    *,
    vod_path: str,
    segment_len: float,
    target: float,
    min_total: float,
    max_total: float,
) -> List[Segment]:
    duration = _probe_duration(vod_path)
    windows = score_windows(messages, window=segment_len, vod_duration=duration)
    if not windows or (windows and windows[0].score <= 0):
        # Continuous window around mid / best effort
        if duration <= 0:
            return []
        length = min(max_total, max(min_total, min(target, duration)))
        start = max(0.0, (duration - length) / 2)
        return [Segment(start=start, end=start + length, score=1.0, hook="Best of")]

    picked: List[Segment] = []
    total = 0.0
    for w in windows:
        if any(_overlaps(w, p, pad=2.0) for p in picked):
            continue
        if total + w.duration > max_total and total >= min_total:
            break
        if total + w.duration > max_total:
            remain = max_total - total
            if remain < 15:
                break
            w = Segment(start=w.start, end=w.start + remain, score=w.score, hook=w.hook)
        picked.append(w)
        total += w.duration
        if total >= target and total >= min_total:
            break

    if total < min_total and duration > 0:
        # Expand best single peak into continuous block
        best = windows[0]
        mid = (best.start + best.end) / 2
        length = min(max_total, max(min_total, min(target, duration)))
        start = max(0.0, mid - length / 2)
        end = min(duration, start + length)
        start = max(0.0, end - length)
        return [Segment(start=start, end=end, score=best.score, hook=best.hook)]

    # Return in chronological order for smoother classic watch
    picked.sort(key=lambda s: s.start)
    return picked
