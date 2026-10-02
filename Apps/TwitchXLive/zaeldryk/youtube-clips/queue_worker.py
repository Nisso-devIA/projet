#!/usr/bin/env python3
"""Main worker: drain queue + discover recent VODs → Shorts + classic → YouTube."""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Allow running as script from module dir
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Settings
from db import Database
from download_vod import download_vod
from fetch_chat import fetch_chat
from music import MusicLibrary
from render import render_classic, render_short
from score_highlights import build_classic_segments, build_short_segments
from titles import classic_title, description, short_title
from twitch_api import TwitchAPI
from youtube_upload import upload_video


def log(settings: Settings, msg: str) -> None:
    line = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} - {msg}"
    print(line, flush=True)
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    with settings.log_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_job(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_queue_jobs(settings: Settings) -> List[Path]:
    settings.queue_dir.mkdir(parents=True, exist_ok=True)
    return sorted(settings.queue_dir.glob("*.job"))


def discover_jobs(settings: Settings, api: TwitchAPI, db: Database) -> List[Dict[str, Any]]:
    """Build job list from queue files + newest non-skipped archive (timer path)."""
    jobs: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for path in list_queue_jobs(settings):
        try:
            job = load_job(path)
            job["_queue_path"] = str(path)
            jobs.append(job)
        except Exception as e:
            log(settings, f"Bad job file {path}: {e}")

    # Timer discovery: newest archives
    try:
        for vod in api.list_archives(first=5):
            vod_id = str(vod.get("id") or "")
            title = vod.get("title") or ""
            if not vod_id or vod_id in seen:
                continue
            if db.is_vod_done(vod_id) or db.is_vod_known(vod_id):
                continue
            # Skip bad titles unless a queued job already claims this VOD
            queued_claim = any(str(j.get("vod_id") or "") == vod_id for j in jobs)
            if settings.title_is_skipped(title) and not queued_claim:
                log(settings, f"Skip VOD {vod_id} title={title!r} (skip pattern)")
                continue
            jobs.append(
                {
                    "vod_id": vod_id,
                    "title": title,
                    "game": vod.get("game_name") or "",
                    "source": "discover",
                    "created_at": vod.get("created_at") or "",
                }
            )
            seen.add(vod_id)
    except Exception as e:
        log(settings, f"Discover archives failed: {e}")

    return jobs


def resolve_vod(settings: Settings, api: TwitchAPI, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    vod_id = str(job.get("vod_id") or "").strip()
    if vod_id:
        vod = api.get_video(vod_id)
        if vod:
            return vod

    prefer_title = str(job.get("title") or "")
    from_orchestrator = job.get("source") == "orchestrator"
    timeout = settings.vod_wait_seconds
    if job.get("source") == "discover":
        timeout = min(settings.vod_wait_seconds, 120)

    return api.wait_for_latest_archive(
        prefer_title=prefer_title,
        timeout=timeout,
        poll=45,
        allow_skipped_title=from_orchestrator,
    )


def process_vod(
    settings: Settings,
    db: Database,
    music: MusicLibrary,
    api: TwitchAPI,
    job: Dict[str, Any],
) -> None:
    vod = resolve_vod(settings, api, job)
    if not vod:
        raise RuntimeError("No VOD available yet for job")

    vod_id = str(vod["id"])
    helix_title = vod.get("title") or ""
    # Prefer good title from job (last_good_live_title)
    stream_title = str(job.get("title") or helix_title)
    game = str(job.get("game") or vod.get("game_name") or "Live")

    if settings.title_is_skipped(stream_title) and not job.get("force"):
        # Job from orchestrator should carry good title; if still skipped, abort
        if settings.title_is_skipped(helix_title) and settings.title_is_skipped(stream_title):
            log(settings, f"Abort VOD {vod_id}: skipped title {stream_title!r}")
            db.mark_vod(vod_id, "skipped", title=stream_title, detail="title_skip")
            return

    if db.is_vod_done(vod_id):
        log(settings, f"VOD {vod_id} already done")
        return

    db.mark_vod(vod_id, "processing", title=stream_title)
    work = settings.work_dir / vod_id
    work.mkdir(parents=True, exist_ok=True)

    if not music.available():
        raise RuntimeError(
            f"No music tracks ready in {settings.music_dir}/manifest.json"
        )

    log(settings, f"Download VOD {vod_id}")
    vod_path = download_vod(settings, vod_id, work)

    log(settings, f"Fetch chat {vod_id}")
    chat = fetch_chat(vod_id, work / "chat.json")
    log(settings, f"Chat messages: {len(chat)}")

    shorts = build_short_segments(
        chat,
        vod_path=str(vod_path),
        count=settings.short_count,
        window=float(settings.short_seconds),
    )
    classic_segs = build_classic_segments(
        chat,
        vod_path=str(vod_path),
        segment_len=float(settings.segment_seconds),
        target=float(settings.classic_target),
        min_total=float(settings.classic_min),
        max_total=float(settings.classic_max),
    )
    log(settings, f"Shorts={len(shorts)} classic_parts={len(classic_segs)}")

    out_dir = work / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Shorts
    for i, seg in enumerate(shorts, start=1):
        track = music.pick()
        music_path = Path(track["path"])
        out = out_dir / f"short_{i:02d}.mp4"
        log(settings, f"Render short {i} @{seg.start:.0f}s music={track['file']}")
        render_short(vod_path, seg, music_path, out, settings.music_volume)
        title = short_title(game, seg.hook)
        desc = description(
            kind="short",
            game=game,
            stream_title=stream_title,
            twitch_url=settings.twitch_url,
            track=track,
        )
        yt_id = None
        if settings.dry_run:
            log(settings, f"DRY_RUN skip upload short {out.name} title={title!r}")
        else:
            yt_id = upload_video(
                settings,
                file_path=out,
                title=title,
                description=desc,
                tags=["Shorts", "Twitch", "Gaming", game],
            )
            log(settings, f"Uploaded short https://youtu.be/{yt_id}")
        db.add_upload(
            vod_id,
            "short",
            yt_id,
            str(out),
            title,
            track.get("file", ""),
        )

    # Classic compilation
    track = music.pick()
    music_path = Path(track["path"])
    classic_out = out_dir / "classic_bestof.mp4"
    log(settings, f"Render classic ({len(classic_segs)} parts) music={track['file']}")
    render_classic(
        vod_path,
        classic_segs,
        music_path,
        work / "classic_parts",
        classic_out,
        settings.music_volume,
    )
    ctitle = classic_title(game)
    cdesc = description(
        kind="classic",
        game=game,
        stream_title=stream_title,
        twitch_url=settings.twitch_url,
        track=track,
    )
    yt_id = None
    if settings.dry_run:
        log(settings, f"DRY_RUN skip upload classic {classic_out.name} title={ctitle!r}")
    else:
        yt_id = upload_video(
            settings,
            file_path=classic_out,
            title=ctitle,
            description=cdesc,
            tags=["Twitch", "Gaming", "Highlights", "BestOf", game],
        )
        log(settings, f"Uploaded classic https://youtu.be/{yt_id}")
    db.add_upload(
        vod_id,
        "classic",
        yt_id,
        str(classic_out),
        ctitle,
        track.get("file", ""),
    )

    # Cleanup heavy VOD
    try:
        if vod_path.exists():
            vod_path.unlink()
            log(settings, f"Deleted VOD file {vod_path.name}")
    except OSError as e:
        log(settings, f"VOD cleanup warning: {e}")

    db.mark_vod(vod_id, "done", title=stream_title, detail="ok")
    log(settings, f"Done VOD {vod_id}")


def main() -> int:
    settings = Settings()
    if not settings.enabled:
        log(settings, "YOUTUBE_CLIPS_ENABLED=0 — exit")
        return 0

    settings.queue_dir.mkdir(parents=True, exist_ok=True)
    settings.work_dir.mkdir(parents=True, exist_ok=True)
    settings.state_dir.mkdir(parents=True, exist_ok=True)

    if not settings.twitch_client_id:
        log(settings, "TWITCH_CLIENT_ID missing")
        return 1
    if not settings.twitch_token_file.exists():
        log(settings, f"Twitch token missing: {settings.twitch_token_file}")
        return 1

    db = Database(settings.db_path)
    music = MusicLibrary(settings.music_dir)
    api = TwitchAPI(settings)

    jobs = discover_jobs(settings, api, db)
    if not jobs:
        log(settings, "No jobs / new VODs")
        db.close()
        return 0

    # Dedupe by eventual vod_id when present
    errors = 0
    for job in jobs:
        qpath = job.pop("_queue_path", None)
        try:
            process_vod(settings, db, music, api, job)
            if qpath:
                Path(qpath).unlink(missing_ok=True)
        except Exception as e:
            errors += 1
            log(settings, f"Job failed: {e}")
            log(settings, traceback.format_exc())
            vod_id = str(job.get("vod_id") or "")
            if vod_id:
                db.mark_vod(vod_id, "error", title=str(job.get("title") or ""), detail=str(e)[:500])

    db.close()
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
