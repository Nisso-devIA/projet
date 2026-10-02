#!/usr/bin/env python3
"""Validate Twitch token without printing secrets."""
from pathlib import Path
import json
import urllib.request
import subprocess

token_file = Path("/home/ubuntu/twitch_token.txt")
twitch_env = Path("/home/ubuntu/zaeldryk/config/twitch.env")

def load_env(path):
    out = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

env = load_env(twitch_env) if twitch_env.exists() else {}
raw = token_file.read_text(encoding="utf-8", errors="replace").strip() if token_file.exists() else ""
# token file may be oauth:xxxx or just xxxx
token = raw.replace("oauth:", "").strip().splitlines()[0] if raw else ""
print("token_file_exists", token_file.exists(), "len", len(token))
print("twitch.env keys", sorted(k for k in env if "SECRET" not in k.upper() and "TOKEN" not in k.upper() and "KEY" not in k.upper()))
for k in ("TWITCH_CLIENT_ID", "CLIENT_ID", "TWITCH_CHANNEL", "CHANNEL"):
    if k in env:
        print(k, "=", env[k][:20] + ("…" if len(env[k]) > 20 else ""))

# Validate via Helix
cid = env.get("TWITCH_CLIENT_ID") or env.get("CLIENT_ID") or ""
if token and cid:
    req = urllib.request.Request(
        "https://id.twitch.tv/oauth2/validate",
        headers={"Authorization": f"OAuth {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        print("validate_ok")
        print("login", data.get("login"))
        print("user_id", data.get("user_id"))
        print("expires_in", data.get("expires_in"))
        print("scopes_count", len(data.get("scopes") or []))
        print("scopes", sorted(data.get("scopes") or []))
        print("client_id_match", data.get("client_id") == cid)
    except Exception as e:
        print("validate_FAIL", type(e).__name__, str(e)[:120])
else:
    print("skip validate: missing token or client_id")

# Are bots crash-looping?
print("\nNRestarts:")
for u in ("moderation-bot", "offline-chatbot", "zaeldryk-discord", "whatsapp-bot", "twitch-offline"):
    out = subprocess.check_output(["systemctl", "show", u, "-p", "NRestarts", "-p", "ActiveEnterTimestamp"], text=True)
    print(u, out.replace("\n", " "))
