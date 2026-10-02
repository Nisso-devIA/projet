#!/usr/bin/env python3
"""One-shot local OAuth: create config/youtube-oauth.json with refresh token.

Usage (on a machine with browser):
  pip install -r youtube-clips/requirements.txt
  python3 tools/youtube-oauth-setup.py \\
    --client-secrets /path/to/client_secret.json \\
    --out /home/ubuntu/zaeldryk/config/youtube-oauth.json

Then copy youtube-oauth.json to the VPS (chmod 600).
"""
from __future__ import annotations

import argparse
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--client-secrets", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()

    from google_auth_oauthlib.flow import InstalledAppFlow

    if not args.client_secrets.exists():
        raise SystemExit(f"Missing {args.client_secrets}")

    flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secrets), SCOPES)
    creds = flow.run_local_server(port=0)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(creds.to_json(), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
