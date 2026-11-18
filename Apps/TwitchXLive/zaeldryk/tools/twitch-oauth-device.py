#!/usr/bin/env python3
"""Twitch device-code OAuth to restore chat:read / chat:edit for IRC bots."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TWITCH_ENV = Path("/home/ubuntu/zaeldryk/config/twitch.env")
TOKEN_FILE = Path("/home/ubuntu/twitch_token.txt")
DEVICE_STATE = Path("/tmp/twitch_device.json")
SCOPES = [
    "chat:read",
    "chat:edit",
    "channel:manage:broadcast",
    "channel:manage:videos",
    "moderator:manage:chat_messages",
    "user:write:chat",
    "channel:manage:raids",
]


def load_env(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def http_form(url: str, fields: dict) -> dict:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:500]}") from e


def cmd_start() -> int:
    env = load_env(TWITCH_ENV)
    cid = env.get("TWITCH_CLIENT_ID") or ""
    if not cid:
        print("MISSING TWITCH_CLIENT_ID")
        return 1
    body = http_form(
        "https://id.twitch.tv/oauth2/device",
        {"client_id": cid, "scopes": " ".join(SCOPES)},
    )
    DEVICE_STATE.write_text(json.dumps(body), encoding="utf-8")
    print("DEVICE_FLOW_OK")
    print("verification_uri", body.get("verification_uri"))
    print("verification_uri_complete", body.get("verification_uri_complete") or "")
    print("user_code", body.get("user_code"))
    print("expires_in", body.get("expires_in"))
    print("interval", body.get("interval"))
    return 0


def upsert_env(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def cmd_poll() -> int:
    env = load_env(TWITCH_ENV)
    cid = env.get("TWITCH_CLIENT_ID") or ""
    secret = env.get("TWITCH_CLIENT_SECRET") or ""
    if not DEVICE_STATE.exists():
        print("NO_DEVICE_STATE — run start first")
        return 1
    device = json.loads(DEVICE_STATE.read_text(encoding="utf-8"))
    device_code = device.get("device_code")
    interval = int(device.get("interval") or 5)
    expires = int(device.get("expires_in") or 600)
    deadline = time.time() + expires
    print(f"POLLING interval={interval}s expires_in={expires}s")
    while time.time() < deadline:
        time.sleep(max(interval, 3))
        fields = {
            "client_id": cid,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
        if secret:
            fields["client_secret"] = secret
        try:
            body = http_form("https://id.twitch.tv/oauth2/token", fields)
        except RuntimeError as e:
            msg = str(e)
            if "authorization_pending" in msg:
                print("waiting…")
                continue
            if "slow_down" in msg:
                interval += 2
                print("slow_down → interval", interval)
                continue
            if "access_denied" in msg or "expired_token" in msg:
                print("FAIL", msg[:300])
                return 2
            print("FAIL", msg[:300])
            return 3

        access = body.get("access_token")
        refresh = body.get("refresh_token")
        if not access:
            print("FAIL no access_token", list(body.keys()))
            return 4

        # Backup then write
        stamp = time.strftime("%Y-%m-%d_%H%M")
        bak = Path(f"/home/ubuntu/backups/{stamp}_twitch-chat-oauth")
        bak.mkdir(parents=True, exist_ok=True)
        if TOKEN_FILE.exists():
            bak.joinpath("twitch_token.txt").write_bytes(TOKEN_FILE.read_bytes())
        bak.joinpath("twitch.env").write_bytes(TWITCH_ENV.read_bytes())

        TOKEN_FILE.write_text(access + "\n", encoding="utf-8")
        TOKEN_FILE.chmod(0o600)
        if refresh:
            upsert_env(TWITCH_ENV, "TWITCH_REFRESH_TOKEN", refresh)
            TWITCH_ENV.chmod(0o600)

        # Validate scopes
        req = urllib.request.Request(
            "https://id.twitch.tv/oauth2/validate",
            headers={"Authorization": f"OAuth {access}"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            val = json.loads(resp.read().decode())
        scopes = sorted(val.get("scopes") or [])
        print("TOKEN_OK")
        print("login", val.get("login"))
        print("scopes", scopes)
        need = {"chat:read", "chat:edit"}
        print("chat_scopes_ok", need.issubset(set(scopes)))
        DEVICE_STATE.unlink(missing_ok=True)
        return 0 if need.issubset(set(scopes)) else 5

    print("TIMEOUT waiting for user authorization")
    return 6


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("start", "poll"):
        print("usage: twitch-oauth-device.py start|poll")
        return 1
    return cmd_start() if sys.argv[1] == "start" else cmd_poll()


if __name__ == "__main__":
    raise SystemExit(main())
