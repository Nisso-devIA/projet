#!/usr/bin/env python3
"""Fetch VOD chat timestamps for highlight scoring."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def fetch_chat(vod_id: str, out_json: Path) -> List[Dict[str, Any]]:
    """Return list of {offset_seconds, message}."""
    out_json.parent.mkdir(parents=True, exist_ok=True)
    if out_json.exists():
        try:
            data = json.loads(out_json.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    messages: List[Dict[str, Any]] = []
    url = f"https://www.twitch.tv/videos/{vod_id}"

    # Prefer chat_downloader library
    try:
        from chat_downloader import ChatDownloader  # type: ignore

        chat = ChatDownloader().get_chat(url)
        for m in chat:
            offset = m.get("time_in_seconds")
            if offset is None:
                continue
            text = ""
            msg = m.get("message")
            if isinstance(msg, str):
                text = msg
            elif isinstance(msg, dict):
                text = str(msg.get("body") or msg.get("text") or "")
            messages.append({"offset_seconds": float(offset), "message": text})
    except Exception:
        # CLI fallback
        try:
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "chat_downloader",
                    url,
                    "--message_types",
                    "text_message",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=3600,
            )
            # chat_downloader CLI prints JSON lines sometimes; if fail, empty
            if proc.returncode == 0 and proc.stdout.strip():
                for line in proc.stdout.splitlines():
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    offset = obj.get("time_in_seconds")
                    if offset is None:
                        continue
                    messages.append(
                        {
                            "offset_seconds": float(offset),
                            "message": str(obj.get("message") or ""),
                        }
                    )
        except Exception:
            messages = []

    out_json.write_text(json.dumps(messages), encoding="utf-8")
    return messages
