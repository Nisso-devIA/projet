#!/usr/bin/env python3
"""SQLite state for processed VODs and uploaded clips."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_vods (
  vod_id TEXT PRIMARY KEY,
  title TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  detail TEXT
);

CREATE TABLE IF NOT EXISTS uploaded_clips (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  vod_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  youtube_id TEXT,
  local_path TEXT,
  title TEXT,
  music_file TEXT,
  created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def is_vod_done(self, vod_id: str) -> bool:
        row = self._conn.execute(
            "SELECT status FROM processed_vods WHERE vod_id = ?", (vod_id,)
        ).fetchone()
        return bool(row and row["status"] == "done")

    def is_vod_known(self, vod_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM processed_vods WHERE vod_id = ?", (vod_id,)
        ).fetchone()
        return row is not None

    def mark_vod(
        self,
        vod_id: str,
        status: str,
        title: str = "",
        detail: str = "",
        now: Optional[str] = None,
    ) -> None:
        from datetime import datetime, timezone

        ts = now or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        existing = self._conn.execute(
            "SELECT created_at FROM processed_vods WHERE vod_id = ?", (vod_id,)
        ).fetchone()
        created = existing["created_at"] if existing else ts
        self._conn.execute(
            """
            INSERT INTO processed_vods (vod_id, title, status, created_at, updated_at, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(vod_id) DO UPDATE SET
              title=excluded.title,
              status=excluded.status,
              updated_at=excluded.updated_at,
              detail=excluded.detail
            """,
            (vod_id, title, status, created, ts, detail),
        )
        self._conn.commit()

    def add_upload(
        self,
        vod_id: str,
        kind: str,
        youtube_id: Optional[str],
        local_path: str,
        title: str,
        music_file: str,
    ) -> None:
        from datetime import datetime, timezone

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(
            """
            INSERT INTO uploaded_clips
              (vod_id, kind, youtube_id, local_path, title, music_file, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (vod_id, kind, youtube_id, local_path, title, music_file, ts),
        )
        self._conn.commit()
