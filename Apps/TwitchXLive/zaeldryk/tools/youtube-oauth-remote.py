#!/usr/bin/env python3
"""VPS-side OAuth helper: prints URL, listens on localhost (use SSH -L)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Unbuffered stdout for nohup logs
os.environ.setdefault("PYTHONUNBUFFERED", "1")
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:
    pass

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--client-secrets", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--port", type=int, default=8090)
    args = p.parse_args()

    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secrets), SCOPES)
    print(f"Listening on http://127.0.0.1:{args.port}/", flush=True)
    creds = flow.run_local_server(
        host="localhost",
        port=args.port,
        open_browser=False,
        bind_addr="127.0.0.1",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(creds.to_json(), encoding="utf-8")
    print(f"WROTE {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
