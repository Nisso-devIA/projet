#!/usr/bin/env python3
"""Local NCS / royalty-free music library."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional


class MusicLibrary:
    def __init__(self, music_dir: Path) -> None:
        self.music_dir = music_dir
        self.manifest_path = music_dir / "manifest.json"
        self._tracks = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.manifest_path.exists():
            return []
        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("music/manifest.json must be a JSON array")
        tracks: List[Dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            fname = item.get("file")
            if not fname:
                continue
            path = self.music_dir / fname
            if not path.is_file():
                continue
            if not item.get("title") or not item.get("artist"):
                continue
            entry = dict(item)
            entry["path"] = path
            tracks.append(entry)
        return tracks

    def available(self) -> bool:
        return bool(self._tracks)

    def pick(self, rng: Optional[random.Random] = None) -> Dict[str, Any]:
        if not self._tracks:
            raise RuntimeError(
                f"No usable tracks in {self.manifest_path} "
                "(need file + title + artist, audio present on disk)"
            )
        r = rng or random.Random()
        return dict(r.choice(self._tracks))
