#!/usr/bin/env python3
"""YouTube title / description builders + NCS credit."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional


def _safe(s: str, n: int = 90) -> str:
    s = " ".join((s or "").split())
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "…"


def music_credit_line(track: Dict[str, Any]) -> str:
    title = track.get("title") or "Unknown"
    artist = track.get("artist") or "Unknown"
    url = track.get("credit_url") or ""
    license_name = track.get("license") or "NCS"
    line = f"Music: {title} — {artist}"
    if license_name.upper() == "NCS":
        line += " [NCS Release]"
    if url:
        line += f" {url}"
    return line


def short_title(game: str, hook: str = "") -> str:
    game = game or "Live"
    hook = hook or "Moment fort"
    base = f"{game} — {hook} #Shorts"
    return _safe(base, 100)


def classic_title(game: str, when: Optional[datetime] = None) -> str:
    game = game or "Live"
    d = (when or datetime.utcnow()).strftime("%Y-%m-%d")
    return _safe(f"Best of {game} — {d}", 100)


def description(
    *,
    kind: str,
    game: str,
    stream_title: str,
    twitch_url: str,
    track: Dict[str, Any],
    extra: str = "",
) -> str:
    lines = [
        stream_title.strip() if stream_title else f"Highlights — {game}",
        "",
        f"Jeu : {game}" if game else "",
        f"Live Twitch : {twitch_url}",
        "",
    ]
    if kind == "short":
        lines.append("#Shorts #Twitch #Gaming")
    else:
        lines.append("Compilation des meilleurs moments du live.")
        lines.append("#Twitch #Gaming #Highlights")
    if extra:
        lines.extend(["", extra])
    lines.extend(["", music_credit_line(track)])
    return "\n".join(x for x in lines if x is not None)
