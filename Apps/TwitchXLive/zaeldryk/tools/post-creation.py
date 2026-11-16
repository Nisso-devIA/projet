#!/usr/bin/env python3
"""Poste une création du jour dans #🎨-créations. Jeton du bot uniquement."""
import json
import sys
import uuid
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CHANNEL_ID = "1541249733413314600"
ROOT = Path("/home/ubuntu/zaeldryk")
ENV_PATH = ROOT / "config" / "discord.env"
LOG_PATH = ROOT / "logs" / "creations.log"
POSTS = {
    "2026-11-16": "📚 Le libraire le plus doux du royaume… même s'il range les mangas avec sa queue 🐉 Et toi, tu lis quoi en ce moment ?",
    "2026-11-17": "☕ Premier jour au boulot pour le slime barista… Latte art en forme d'épée offert ⚔️ Tu commandes quoi ?",
    "2026-11-18": "🏁 La meute en mode rallye sur la route des nuages ! 🐺💨 Qui finit premier selon toi ?",
    "2026-11-19": "🎮 Le boss final, quand les héros ne sont pas encore arrivés… Pyjama, chips et manette 😴",
    "2026-11-20": "🍙 Le renard ninja prépare les onigiris avant la grande quête… Ce soir, on part à l'aventure en live ⚔️",
    "2026-11-21": "🌙 Deux lunes, un lac, un samouraï et son robot… Parfois, l'aventure, c'est juste pêcher ensemble 🎣",
    "2026-11-22": "🍄 Au village des champignons, on fête la fin de la semaine avec des lanternes ✨ Bon dimanche, la meute !",
}
PARIS = ZoneInfo("Europe/Paris")
UA = "ZaeldrykCreations/1.0"


def log(message: str) -> None:
    stamp = datetime.now(PARIS).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} Europe/Paris {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def bot_token() -> str:
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip().strip('"').strip("'")
            if token.lower().startswith("bot "):
                token = token[4:].strip()
            if token:
                return token
    raise SystemExit("DISCORD_BOT_TOKEN missing")


def api(token: str, method: str, path: str, data: bytes | None = None, headers: dict | None = None):
    head = {"Authorization": "Bot " + token, "User-Agent": UA}
    if headers:
        head.update(headers)
    request = urllib.request.Request(
        "https://discord.com/api/v10" + path,
        data=data,
        headers=head,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:240]
        raise RuntimeError(f"HTTP {exc.code} {method} {path}: {detail}") from exc


def already_posted(token: str, filename: str, content: str) -> str | None:
    before = None
    for _ in range(5):
        query = "/channels/%s/messages?limit=100" % CHANNEL_ID
        if before:
            query += "&before=" + before
        rows = api(token, "GET", query) or []
        if not rows:
            return None
        for row in rows:
            names = [item.get("filename") for item in row.get("attachments") or []]
            if filename in names or (row.get("content") or "") == content:
                return str(row.get("id") or "")
        before = str(rows[-1]["id"])
    return None


def post(token: str, content: str, image: Path, filename: str) -> str:
    payload = {
        "content": content,
        "allowed_mentions": {"parse": []},
        "attachments": [{"id": 0, "filename": filename}],
    }
    boundary = uuid.uuid4().hex
    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="payload_json"\r\n',
        b"Content-Type: application/json\r\n\r\n",
        json.dumps(payload, ensure_ascii=False).encode(),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: image/jpeg\r\n\r\n",
        image.read_bytes(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    message = api(
        token,
        "POST",
        f"/channels/{CHANNEL_ID}/messages",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    return str(message["id"])


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: post-creation.py YYYY-MM-DD")
    day = sys.argv[1]
    content = POSTS[day]
    image = ROOT / "creations" / f"{day}.jpg"
    filename = f"creation-{day}.jpg"
    if not image.is_file() or image.stat().st_size < 1000:
        log(f"{day} image absente, pas de publication")
        return 1
    token = bot_token()
    existing = already_posted(token, filename, content)
    if existing:
        log(f"{day} déjà dans le salon message_id={existing}")
        return 0
    message_id = post(token, content, image, filename)
    log(f"{day} publié message_id={message_id}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"échec {exc}")
        raise SystemExit(1)
