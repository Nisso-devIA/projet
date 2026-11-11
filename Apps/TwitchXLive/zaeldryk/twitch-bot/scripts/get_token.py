#!/usr/bin/env python3
"""Obtient le jeton du compte bot et l'écrit dans .env.

Ne affiche jamais le jeton. Deux façons :
  python3 scripts/get_token.py --flow device
  python3 scripts/get_token.py --flow code

Le flux « code » ouvre une page Twitch puis écoute http://localhost:17563/callback.
Le flux « device » donne un code à saisir sur https://www.twitch.tv/activate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from zaelbot.auth import BROADCASTER_SCOPES, SCOPES, parse_token_response
ENV_PATH = ROOT / ".env"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"
DEVICE_URL = "https://id.twitch.tv/oauth2/device"
REDIRECT = "http://localhost:17563/callback"


def load_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_tokens(path: Path, access_token: str, refresh_token: str, who: str = "bot") -> None:
    current = load_env(path)
    if who == "broadcaster":
        current["TWITCH_BROADCASTER_ACCESS_TOKEN"] = access_token
        current["TWITCH_BROADCASTER_REFRESH_TOKEN"] = refresh_token
    else:
        current["TWITCH_BOT_ACCESS_TOKEN"] = access_token
        current["TWITCH_BOT_REFRESH_TOKEN"] = refresh_token
    lines = [f"{key}={value}" for key, value in current.items()]
    temporary = path.with_suffix(".env.tmp")
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(path)
    os.chmod(path, 0o600)


def post_form(url: str, fields: dict) -> dict:
    data = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:180]
        raise SystemExit(f"Twitch a répondu HTTP {exc.code} ({detail.split(chr(10))[0][:80]})") from exc


def client_credentials() -> tuple[str, str]:
    env = load_env(ENV_PATH)
    client_id = env.get("TWITCH_CLIENT_ID") or os.environ.get("TWITCH_CLIENT_ID", "")
    client_secret = env.get("TWITCH_CLIENT_SECRET") or os.environ.get("TWITCH_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise SystemExit("Renseigne TWITCH_CLIENT_ID et TWITCH_CLIENT_SECRET dans .env avant.")
    return client_id, client_secret


def scopes_for(who: str) -> list[str]:
    return BROADCASTER_SCOPES if who == "broadcaster" else SCOPES


def flow_device(who: str) -> int:
    client_id, client_secret = client_credentials()
    started = post_form(DEVICE_URL, {"client_id": client_id, "scopes": " ".join(scopes_for(who))})
    print("Ouvre", started.get("verification_uri") or "https://www.twitch.tv/activate")
    print("Code :", started.get("user_code"))
    interval = int(started.get("interval") or 5)
    device_code = started.get("device_code")
    import time

    while True:
        time.sleep(interval)
        try:
            payload = post_form(
                TOKEN_URL,
                {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                },
            )
        except SystemExit as exc:
            message = str(exc)
            if "authorization_pending" in message or "slow_down" in message:
                continue
            raise
        bundle = parse_token_response(payload)
        write_tokens(ENV_PATH, bundle.access_token, bundle.refresh_token, who)
        print("Jeton enregistré dans .env. Il n'est pas affiché.")
        return 0


def flow_code(who: str) -> int:
    client_id, client_secret = client_credentials()
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT,
            "response_type": "code",
            "scope": " ".join(scopes_for(who)),
        }
    )
    account = "COMPTE BROADCASTER (zaeldryk)" if who == "broadcaster" else "COMPTE BOT"
    print(f"Ouvre cette adresse avec le {account} :")
    print(f"https://id.twitch.tv/oauth2/authorize?{query}")
    code_holder: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/callback":
                self.send_response(404)
                self.end_headers()
                return
            params = urllib.parse.parse_qs(parsed.query)
            code_holder["code"] = (params.get("code") or [""])[0]
            body = "Autorisation reçue. Tu peux fermer cette page.".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", 17563), Handler)
    server.handle_request()
    if not code_holder.get("code"):
        raise SystemExit("Aucun code reçu.")
    payload = post_form(
        TOKEN_URL,
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code_holder["code"],
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT,
        },
    )
    bundle = parse_token_response(payload)
    write_tokens(ENV_PATH, bundle.access_token, bundle.refresh_token, who)
    print("Jeton enregistré dans .env. Il n'est pas affiché.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flow", choices=("code", "device"), default="code")
    parser.add_argument("--who", choices=("bot", "broadcaster"), default="bot")
    args = parser.parse_args()
    if args.flow == "device":
        return flow_device(args.who)
    return flow_code(args.who)


if __name__ == "__main__":
    raise SystemExit(main())
