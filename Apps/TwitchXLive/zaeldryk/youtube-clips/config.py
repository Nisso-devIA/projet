#!/usr/bin/env python3
"""Shared config/paths for youtube-clips pipeline."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict


ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_SKIP = r"ending|offline|test|\bend\b"


def load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_config() -> Dict[str, str]:
    cfg: Dict[str, str] = {}
    cfg.update(load_env_file(ZAEL_ROOT / "config" / "twitch.env"))
    cfg.update(load_env_file(ZAEL_ROOT / "config" / "youtube-clips.env"))
    # Process env overrides
    for k, v in os.environ.items():
        if k.startswith("YOUTUBE_") or k.startswith("TWITCH_"):
            cfg[k] = v
    return cfg


class Settings:
    def __init__(self, cfg: Dict[str, str] | None = None) -> None:
        c = cfg or load_config()
        self.enabled = c.get("YOUTUBE_CLIPS_ENABLED", "1") == "1"
        self.dry_run = c.get("YOUTUBE_CLIPS_DRY_RUN", "0") == "1"
        self.skip_pattern = re.compile(
            c.get("YOUTUBE_CLIPS_SKIP_TITLE_PATTERN", DEFAULT_SKIP),
            re.IGNORECASE,
        )
        self.twitch_client_id = c.get("TWITCH_CLIENT_ID", "")
        self.twitch_broadcaster_id = c.get("TWITCH_BROADCASTER_ID", "426411773")
        self.twitch_login = c.get("TWITCH_LOGIN", "zaeldryk")
        self.twitch_token_file = Path(
            c.get("TWITCH_TOKEN_FILE", "/home/ubuntu/twitch_token.txt")
        )
        self.youtube_oauth_file = Path(
            c.get(
                "YOUTUBE_OAUTH_FILE",
                str(ZAEL_ROOT / "config" / "youtube-oauth.json"),
            )
        )
        self.youtube_client_secrets = Path(
            c.get(
                "YOUTUBE_CLIENT_SECRETS",
                str(ZAEL_ROOT / "config" / "youtube-client-secrets.json"),
            )
        )
        self.youtube_privacy = c.get("YOUTUBE_PRIVACY", "public")
        self.youtube_category_id = c.get("YOUTUBE_CATEGORY_ID", "20")
        self.short_count = int(c.get("YOUTUBE_CLIPS_SHORT_COUNT", "5"))
        self.short_seconds = int(c.get("YOUTUBE_CLIPS_SHORT_SECONDS", "40"))
        self.classic_target = int(c.get("YOUTUBE_CLIPS_CLASSIC_TARGET_SECONDS", "720"))
        self.classic_min = int(c.get("YOUTUBE_CLIPS_CLASSIC_MIN_SECONDS", "600"))
        self.classic_max = int(c.get("YOUTUBE_CLIPS_CLASSIC_MAX_SECONDS", "900"))
        self.segment_seconds = int(c.get("YOUTUBE_CLIPS_SEGMENT_SECONDS", "35"))
        self.vod_height = int(c.get("YOUTUBE_CLIPS_VOD_HEIGHT", "720"))
        self.vod_wait_seconds = int(c.get("YOUTUBE_CLIPS_VOD_WAIT_SECONDS", "7200"))
        self.music_volume = float(c.get("YOUTUBE_CLIPS_MUSIC_VOLUME", "0.16"))
        self.twitch_url = c.get(
            "YOUTUBE_CLIPS_TWITCH_URL", f"https://www.twitch.tv/{self.twitch_login}"
        )
        self.work_dir = Path(
            c.get("YOUTUBE_CLIPS_WORK_DIR", str(MODULE_DIR / "work"))
        )
        self.music_dir = Path(
            c.get("YOUTUBE_CLIPS_MUSIC_DIR", str(MODULE_DIR / "music"))
        )
        self.db_path = Path(
            c.get("YOUTUBE_CLIPS_DB", str(ZAEL_ROOT / "state" / "youtube-clips.sqlite"))
        )
        self.queue_dir = ZAEL_ROOT / "state" / "youtube-clips-queue"
        self.state_dir = ZAEL_ROOT / "state"
        self.log_file = ZAEL_ROOT / "logs" / "youtube-clips.log"
        self.last_good_title_file = self.state_dir / "last_good_live_title.txt"
        self.last_good_meta_file = self.state_dir / "last_good_live_meta.json"

    def title_is_skipped(self, title: str) -> bool:
        return bool(self.skip_pattern.search(title or ""))
