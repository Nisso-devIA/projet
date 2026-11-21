#!/usr/bin/env python3
"""Envoie les VODs Twitch de zaeldryk à la racine de Mon Drive.

Une à la fois : téléchargement, envoi résumable, contrôle de taille, suppression locale.
Aucun partage public. Aucun secret dans le journal.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
TOKEN_PATH = ROOT / "config" / "drive-oauth.json"
BOT_ENV = ROOT / "twitch-bot" / ".env"
STATE_PATH = ROOT / "state" / "drive-vods.json"
LOG_PATH = ROOT / "logs" / "drive-vods.log"
WORK = ROOT / "state" / "drive-vod-work"
BROADCASTER_ID = "426411773"
SKIP_IDS = {"2930809812"}
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def log(message: str) -> None:
    stamp = datetime.now(PARIS).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} Europe/Paris {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def plain_token(value: str) -> str:
    token = (value or "").strip()
    if token.lower().startswith("oauth:"):
        return token.split(":", 1)[1]
    return token


def wait_for_token() -> None:
    while not TOKEN_PATH.is_file():
        log("jeton Drive absent, attente")
        time.sleep(30)
    os.chmod(TOKEN_PATH, 0o600)


def drive_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        os.chmod(TOKEN_PATH, 0o600)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def helix_vods() -> list[dict]:
    env = load_env(BOT_ENV)
    token = plain_token(env.get("TWITCH_BOT_ACCESS_TOKEN", ""))
    client_id = env.get("TWITCH_CLIENT_ID", "")
    if not token or not client_id:
        raise RuntimeError("jeton Twitch absent")
    rows = []
    cursor = ""
    while True:
        query = {"user_id": BROADCASTER_ID, "type": "archive", "first": "100"}
        if cursor:
            query["after"] = cursor
        request = urllib.request.Request(
            "https://api.twitch.tv/helix/videos?" + urllib.parse.urlencode(query),
            headers={"Client-ID": client_id, "Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
        rows.extend(payload.get("data") or [])
        cursor = str((payload.get("pagination") or {}).get("cursor") or "")
        if not cursor:
            break
    return rows


def paris_start(vod: dict) -> datetime:
    created = str(vod.get("created_at") or "")
    return datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(PARIS)


def planned_names(vods: list[dict]) -> list[tuple[dict, str]]:
    chosen = [vod for vod in vods if str(vod.get("id") or "") not in SKIP_IDS]
    groups: dict[str, list[dict]] = {}
    for vod in chosen:
        groups.setdefault(paris_start(vod).date().isoformat(), []).append(vod)
    planned = []
    for day, items in groups.items():
        items.sort(key=paris_start)
        for index, vod in enumerate(items, start=1):
            suffix = f"_{index}" if len(items) > 1 else ""
            planned.append((vod, f"Zaeldryk_live_{day}{suffix}.mp4"))
    planned.sort(key=lambda item: paris_start(item[0]), reverse=True)
    return planned


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_drive_file(service, name: str) -> dict | None:
    safe = name.replace("'", "\\'")
    found = (
        service.files()
        .list(
            q=f"name = '{safe}' and trashed = false",
            spaces="drive",
            fields="files(id,name,size)",
            pageSize=5,
        )
        .execute()
    )
    files = found.get("files") or []
    return files[0] if files else None


def quota_free(service) -> int | None:
    about = service.about().get(fields="storageQuota").execute()
    quota = about.get("storageQuota") or {}
    limit = quota.get("limit")
    usage = quota.get("usage")
    if limit is None or usage is None:
        return None
    return int(limit) - int(usage)


def download(vod_id: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    subprocess.run(
        [
            "yt-dlp",
            "-f",
            "best",
            "--merge-output-format",
            "mp4",
            "--no-part",
            "-o",
            str(dest),
            f"https://www.twitch.tv/videos/{vod_id}",
        ],
        check=True,
    )
    if not dest.is_file() or dest.stat().st_size <= 0:
        raise RuntimeError(f"téléchargement vide {vod_id}")


def upload(service, path: Path, name: str) -> dict:
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(path), mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024)
    request = service.files().create(
        body={"name": name},
        media_body=media,
        fields="id,name,size",
    )
    response = None
    while response is None:
        _status, response = request.next_chunk()
    return response or {}


def cleanup(dest: Path) -> None:
    if dest.exists():
        dest.unlink()
    for extra in WORK.glob(dest.stem + "*"):
        if extra.is_file():
            extra.unlink()


def enough_disk(dest: Path, vod: dict) -> bool:
    free = shutil.disk_usage(dest.parent).free
    duration = 0
    raw = str(vod.get("duration") or "")
    # Helix duration like 2h53m59s is not parsed here; keep 12 GB headroom minimum.
    if free < 12 * 1024**3 and "h" in raw:
        log(f"disque libre {free // 1024**3} Go, pas assez pour {vod.get('id')}")
        return False
    return free > 1024**3


def main() -> int:
    wait_for_token()
    service = drive_service()
    free = quota_free(service)
    if free is not None:
        log(f"Drive libre {free // 1024**3} Go")
    else:
        log("quota Drive non chiffré")
    state = load_state()
    jobs = planned_names(helix_vods())
    log(f"{len(jobs)} VODs à traiter, 16/11 exclu")
    WORK.mkdir(parents=True, exist_ok=True)
    for vod, name in jobs:
        vod_id = str(vod.get("id") or "")
        saved = state.get(vod_id) or {}
        if saved.get("status") == "done" and saved.get("name") == name:
            log(f"déjà déposé {name}")
            continue
        existing = find_drive_file(service, name)
        if existing and int(existing.get("size") or 0) > 0:
            state[vod_id] = {
                "status": "done",
                "name": name,
                "drive_id": existing.get("id"),
                "size": int(existing.get("size") or 0),
            }
            save_state(state)
            log(f"déjà sur Drive {name}")
            continue
        dest = WORK / name
        if not enough_disk(dest, vod):
            raise SystemExit(1)
        log(f"téléchargement {vod_id} → {name}")
        try:
            download(vod_id, dest)
            local_size = dest.stat().st_size
            log(f"upload {name} {local_size} octets")
            remote = upload(service, dest, name)
            remote_size = int(remote.get("size") or 0)
            if remote_size != local_size:
                raise RuntimeError(f"taille Drive {remote_size} ≠ locale {local_size}")
            state[vod_id] = {
                "status": "done",
                "name": name,
                "drive_id": remote.get("id"),
                "size": remote_size,
            }
            save_state(state)
            log(f"déposé {name}")
        finally:
            cleanup(dest)
    log("terminé")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
