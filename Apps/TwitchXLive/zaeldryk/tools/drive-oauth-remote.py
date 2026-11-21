#!/usr/bin/env python3
"""Écoute OAuth Drive (drive.file) et écrit config/drive-oauth.json. N'affiche aucun secret."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYTHONUNBUFFERED", "1")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))


def main() -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets = ROOT / "config" / "youtube-client-secrets.json"
    out = ROOT / "config" / "drive-oauth.json"
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    creds = flow.run_local_server(
        host="localhost",
        port=8090,
        open_browser=False,
        bind_addr="127.0.0.1",
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(creds.to_json(), encoding="utf-8")
    os.chmod(out, 0o600)
    print(f"WROTE {out.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
