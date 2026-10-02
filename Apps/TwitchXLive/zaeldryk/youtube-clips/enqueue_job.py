#!/usr/bin/env python3
"""Enqueue a youtube-clips job from live-orchestrator (or CLI)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Settings


def main() -> int:
    settings = Settings()
    if not settings.enabled:
        return 0

    title = os.environ.get("YOUTUBE_CLIPS_JOB_TITLE", "").strip()
    game = os.environ.get("YOUTUBE_CLIPS_JOB_GAME", "").strip()
    vod_id = os.environ.get("YOUTUBE_CLIPS_JOB_VOD_ID", "").strip()
    started_at = os.environ.get("YOUTUBE_CLIPS_JOB_STARTED_AT", "").strip()

    if not title and settings.last_good_title_file.exists():
        title = settings.last_good_title_file.read_text(encoding="utf-8").strip()
    if settings.last_good_meta_file.exists():
        try:
            meta = json.loads(settings.last_good_meta_file.read_text(encoding="utf-8"))
            game = game or str(meta.get("game") or "")
            started_at = started_at or str(meta.get("started_at") or "")
        except json.JSONDecodeError:
            pass

    if not title or settings.title_is_skipped(title):
        print(f"skip enqueue: bad/missing title={title!r}", flush=True)
        return 0

    settings.queue_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    job = {
        "title": title,
        "game": game,
        "vod_id": vod_id,
        "started_at": started_at,
        "source": "orchestrator",
        "enqueued_at": ts,
    }
    path = settings.queue_dir / f"{ts}.job"
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"enqueued {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
