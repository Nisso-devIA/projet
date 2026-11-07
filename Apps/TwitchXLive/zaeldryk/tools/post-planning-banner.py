#!/usr/bin/env python3
"""Poste l'affiche planning dans #📅-planning et retire l'ancien texte brut."""
import json
import mimetypes
import uuid
import urllib.error
import urllib.request
from pathlib import Path

CHANNEL_ID = "1568352153872109588"
IMAGE = Path("/tmp/planning-oot-jeudi.jpg")

env = Path("/home/ubuntu/zaeldryk/config/discord.env")
token = None
for line in env.read_text(encoding="utf-8").splitlines():
    if line.startswith("DISCORD_BOT_TOKEN="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not token:
    raise SystemExit("DISCORD_BOT_TOKEN missing")

UA = "ZaelrysPlanning/1.0"


def api(method, path, body=None, data=None, headers=None):
    h = {"Authorization": f"Bot {token}", "User-Agent": UA}
    if headers:
        h.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=data,
        headers=h,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {method} {path}: {err[:500]}") from e


msgs = api("GET", f"/channels/{CHANNEL_ID}/messages?limit=10") or []
for m in msgs:
    content = m.get("content") or ""
    if content.startswith("📅 **Planning des lives**") and not m.get("attachments"):
        api("DELETE", f"/channels/{CHANNEL_ID}/messages/{m['id']}")
        print("deleted plain", m["id"])

payload = {
    "content": (
        "## ⚔️ Rendez-vous tous les jeudis\n\n"
        "**The Legend of Zelda: Ocarina of Time — Remake**\n"
        "🕐 **22h30** · sur Twitch\n\n"
        "👉 https://twitch.tv/zaeldryk"
    ),
    "attachments": [{"id": 0, "filename": "oot-jeudi.jpg"}],
}
raw_img = IMAGE.read_bytes()
boundary = uuid.uuid4().hex
parts = []
parts.append(f"--{boundary}\r\n".encode())
parts.append(b'Content-Disposition: form-data; name="payload_json"\r\n')
parts.append(b"Content-Type: application/json\r\n\r\n")
parts.append(json.dumps(payload, ensure_ascii=False).encode())
parts.append(b"\r\n")
parts.append(f"--{boundary}\r\n".encode())
parts.append(b'Content-Disposition: form-data; name="files[0]"; filename="oot-jeudi.jpg"\r\n')
parts.append(b"Content-Type: image/jpeg\r\n\r\n")
parts.append(raw_img)
parts.append(b"\r\n")
parts.append(f"--{boundary}--\r\n".encode())
body = b"".join(parts)
msg = api(
    "POST",
    f"/channels/{CHANNEL_ID}/messages",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
api("PUT", f"/channels/{CHANNEL_ID}/pins/{msg['id']}")
print("posted", msg["id"])
