#!/usr/bin/env python3
"""Twitch Helix helpers for VOD discovery."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from config import Settings


class TwitchAPI:
    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def _token(self) -> str:
        return self.s.twitch_token_file.read_text(encoding="utf-8").strip()

    def helix_get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        qs = urllib.parse.urlencode(params or {})
        url = f"https://api.twitch.tv/helix{path}"
        if qs:
            url = f"{url}?{qs}"
        req = urllib.request.Request(
            url,
            headers={
                "Client-ID": self.s.twitch_client_id,
                "Authorization": f"Bearer {self._token()}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Helix {path} HTTP {e.code}: {body}") from e

    def list_archives(self, first: int = 10) -> List[Dict[str, Any]]:
        data = self.helix_get(
            "/videos",
            {
                "user_id": self.s.twitch_broadcaster_id,
                "type": "archive",
                "first": str(first),
            },
        )
        return list(data.get("data") or [])

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        data = self.helix_get("/videos", {"id": video_id})
        items = data.get("data") or []
        return items[0] if items else None

    def wait_for_latest_archive(
        self,
        *,
        prefer_title: str = "",
        timeout: Optional[int] = None,
        poll: int = 60,
        allow_skipped_title: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Poll Helix until a usable archive appears (newest first)."""
        deadline = time.time() + (timeout or self.s.vod_wait_seconds)
        while time.time() < deadline:
            archives = self.list_archives(first=8)
            if not archives:
                time.sleep(poll)
                continue
            # Orchestrator jobs: take newest archive even if Helix title is "ending"
            if prefer_title or allow_skipped_title:
                return archives[0]
            for vod in archives:
                title = vod.get("title") or ""
                if self.s.title_is_skipped(title):
                    continue
                return vod
            time.sleep(poll)
        return None
