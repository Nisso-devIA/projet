#!/usr/bin/env python3
"""Écoute OAuth Drive (drive.file) et écrit config/drive-oauth.json.

Le vérificateur PKCE est gardé à côté, en mode 600, jusqu'à l'échange.
Aucun secret n'est affiché.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("PYTHONUNBUFFERED", "1")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
PORT = 8090


def main() -> int:
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets = ROOT / "config" / "youtube-client-secrets.json"
    out = ROOT / "config" / "drive-oauth.json"
    verifier_path = ROOT / "config" / "drive-oauth.verifier"
    if out.is_file() and json.loads(out.read_text()).get("refresh_token"):
        print("jeton Drive déjà présent", flush=True)
        return 0
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    flow.redirect_uri = f"http://localhost:{PORT}/"
    auth_url, _state = flow.authorization_url(access_type="offline", prompt="consent")
    verifier_path.write_text(flow.code_verifier or "", encoding="utf-8")
    os.chmod(verifier_path, 0o600)
    print(auth_url, flush=True)
    holder: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path not in {"/", ""}:
                self.send_response(404)
                self.end_headers()
                return
            holder["code"] = (parse_qs(parsed.query).get("code") or [""])[0]
            body = "Autorisation Drive reçue. Tu peux fermer cette page.".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    server.handle_request()
    if not holder.get("code"):
        raise SystemExit("aucun code reçu")
    flow.fetch_token(code=holder["code"])
    out.write_text(flow.credentials.to_json(), encoding="utf-8")
    os.chmod(out, 0o600)
    verifier_path.unlink(missing_ok=True)
    print(f"WROTE {out.name}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
