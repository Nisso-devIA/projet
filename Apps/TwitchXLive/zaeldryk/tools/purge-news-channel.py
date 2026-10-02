#!/usr/bin/env python3
"""Purge messages in #🔔-actualités (news channel)."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

CHANNEL_ID = "1541251086005047390"
env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("no token")

UA = "ZaelrysPurge/1.0"


def api(method, path, body=None):
    data = None
    headers = {"Authorization": f"Bot {token}", "User-Agent": UA}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err}") from e


deleted = 0
while True:
    _, msgs = api("GET", f"/channels/{CHANNEL_ID}/messages?limit=100")
    if not msgs:
        break
    ids = [m["id"] for m in msgs]
    if len(ids) == 1:
        api("DELETE", f"/channels/{CHANNEL_ID}/messages/{ids[0]}")
        deleted += 1
        time.sleep(0.4)
        continue
    # bulk delete (2–100), messages must be < 14 days
    try:
        api("POST", f"/channels/{CHANNEL_ID}/messages/bulk-delete", {"messages": ids})
        deleted += len(ids)
    except SystemExit as e:
        # fallback one by one
        print("bulk failed, fallback:", e)
        for mid in ids:
            try:
                api("DELETE", f"/channels/{CHANNEL_ID}/messages/{mid}")
                deleted += 1
            except SystemExit as e2:
                print("skip", mid, e2)
            time.sleep(0.35)
    time.sleep(1.0)

print("deleted_messages", deleted)
