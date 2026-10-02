#!/usr/bin/env python3
"""YouTube Data API upload helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config import Settings


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _build_youtube(settings: Settings):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    token_path = settings.youtube_oauth_file
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError(
                f"YouTube OAuth token missing/invalid at {token_path}. "
                "Run tools/youtube-oauth-setup.py once."
            )

    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_video(
    settings: Settings,
    *,
    file_path: Path,
    title: str,
    description: str,
    tags: Optional[list] = None,
) -> str:
    """Upload and return YouTube video id."""
    from googleapiclient.http import MediaFileUpload

    youtube = _build_youtube(settings)
    body: Dict[str, Any] = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags or ["twitch", "gaming", "highlights"],
            "categoryId": settings.youtube_category_id,
        },
        "status": {
            "privacyStatus": settings.youtube_privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(file_path), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError(f"YouTube upload failed: {json.dumps(response)[:500]}")
    return video_id
