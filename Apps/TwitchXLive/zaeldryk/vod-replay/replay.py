#!/usr/bin/env python3
"""Rediffusion Twitch → YouTube, le lendemain. Ne poste rien en --dry-run."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
JOURNAL_PATH = ROOT / "state" / "vod-replay.json"
LOG_PATH = ROOT / "logs" / "vod-replay.log"
WORK = ROOT / "state" / "vod-replay-work"
BROADCASTER_ID = "426411773"
YOUTUBE_CHANNEL_DISCORD = "1541251096763179181"
DISCORD_INVITE = "https://discord.gg/3vH2u7pme5"
TWITCH_URL = "https://www.twitch.tv/zaeldryk"
HD_WAIT = 3 * 60 * 60
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def log(message: str) -> None:
    stamp = datetime.now(PARIS).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} Europe/Paris {message}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_env(path: Path) -> dict:
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_duration(text: str) -> int:
    """Durée Helix du type 1h46m37s, en secondes."""
    total = 0
    for number, unit in re.findall(r"(\d+)([hms])", text or ""):
        value = int(number)
        total += value * {"h": 3600, "m": 60, "s": 1}[unit]
    return total


def stamp(seconds: int) -> str:
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def fallback_chapters(duration_s: int) -> list[tuple[int, str]]:
    """Au moins 3 chapitres, le premier à 0:00, écarts d'au moins 10 s."""
    duration_s = max(40, int(duration_s))
    names = [
        "Début du live",
        "Sur la route",
        "Dans le donjon",
        "Vers le boss",
        "Dernière ligne",
    ]
    count = 4 if duration_s >= 120 else 3
    count = min(count, len(names))
    step = max(10, duration_s // (count - 1))
    while (count - 1) * step >= duration_s and step > 10 and count > 3:
        count -= 1
    chapters = [(0, names[0])]
    for index in range(1, count):
        moment = min(duration_s - 1, index * step)
        if moment < chapters[-1][0] + 10:
            moment = chapters[-1][0] + 10
        if moment >= duration_s:
            break
        chapters.append((moment, names[index]))
    if len(chapters) < 3 and duration_s >= 30:
        chapters = [(0, names[0]), (10, names[1]), (20, names[2])]
    return chapters


def chapter_block(chapters: list[tuple[int, str]]) -> str:
    return "\n".join(f"{stamp(moment)} {name}" for moment, name in chapters)


DEFAULT_GAME = "Ocarina of Time remake"
GENERIC_CATEGORIES = {
    "just chatting",
    "music",
    "art",
    "asmr",
    "sports",
    "talk shows & podcasts",
    "special events",
    "pools, hot tubs, and beaches",
    "software and game development",
}


def keep_planned_game(planned: str, seen: str) -> str:
    """La vision ne remplace pas un Ocarina of Time déjà reconnu (ex. Echoes of Wisdom)."""
    planned_name = " ".join((planned or "").split())
    seen_name = " ".join((seen or "").split())
    if "ocarina of time" in planned_name.lower():
        return planned_name
    return (seen_name or planned_name)[:60]


def game_label(title: str, category: str = "") -> str:
    """Catégorie Twitch d'abord, puis le titre, sinon Ocarina of Time remake."""
    name = " ".join((category or "").split())
    if name and name.lower() not in GENERIC_CATEGORIES:
        if "ocarina" in name.lower():
            return DEFAULT_GAME
        return name
    text = (title or "").lower()
    if "ocarina" in text or "zelda" in text:
        return DEFAULT_GAME
    for word, label in (("mario", "Mario"), ("pokemon", "Pokémon"), ("pokémon", "Pokémon")):
        if word in text:
            return label
    return DEFAULT_GAME


def title_for(game: str, when: datetime) -> str:
    return f"Rediffusion live – {game} – {when.strftime('%d/%m/%Y')}"


def description_for(chapters: list[tuple[int, str]]) -> str:
    return (
        chapter_block(chapters)
        + "\n\n"
        + f"👉 {TWITCH_URL}\n"
        + f"Discord : {DISCORD_INVITE}\n"
    )


def discord_text(game: str, chapters: list[tuple[int, str]], url: str) -> str:
    steps = [name for _, name in chapters if name != "Début du live"][:4]
    trail = " · ".join(steps)
    body = f"@everyone La rediffusion du live est dispo sur YouTube ! 🎮 {game}"
    if trail:
        body += f" : {trail}"
    return f"{body} {url}"


def vod_end(vod: dict) -> datetime | None:
    created = vod.get("created_at") or ""
    try:
        start = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(PARIS)
    except ValueError:
        return None
    return start + timedelta(seconds=parse_duration(str(vod.get("duration") or "")))


def select_evening_vod(vods: list[dict], run_at: datetime) -> dict | None:
    """Archive dont la fin est après 20:00 Paris la veille, avant le passage du jour."""
    moment = run_at.astimezone(PARIS)
    start = (moment - timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
    chosen = None
    chosen_end = None
    for vod in vods:
        if (vod.get("type") or "archive") not in ("archive", ""):
            continue
        end = vod_end(vod)
        if end is None or end < start or end >= moment:
            continue
        if chosen_end is None or end > chosen_end:
            chosen = vod
            chosen_end = end
    return chosen


def load_journal() -> dict:
    if not JOURNAL_PATH.is_file():
        return {"vods": {}}
    try:
        data = json.loads(JOURNAL_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"vods": {}}
    if not isinstance(data.get("vods"), dict):
        data["vods"] = {}
    return data


def save_journal(data: dict) -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(JOURNAL_PATH, 0o600)


def journal_done(data: dict, vod_id: str) -> bool:
    row = (data.get("vods") or {}).get(vod_id) or {}
    return bool(row.get("youtube_id")) and row.get("status") in {"private", "public", "posted"}


def channel_game(client_id: str, token: str) -> str:
    """Catégorie actuelle de la chaîne. Vide si Helix ne la donne pas."""
    query = urllib.parse.urlencode({"broadcaster_id": BROADCASTER_ID})
    request = urllib.request.Request(
        "https://api.twitch.tv/helix/channels?" + query,
        headers={"Client-ID": client_id, "Authorization": "Bearer " + token},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError):
        return ""
    rows = payload.get("data") or []
    if not rows:
        return ""
    return str(rows[0].get("game_name") or "")


def helix_videos(client_id: str, token: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {"user_id": BROADCASTER_ID, "type": "archive", "first": "10"}
    )
    request = urllib.request.Request(
        "https://api.twitch.tv/helix/videos?" + query,
        headers={"Client-ID": client_id, "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    return list(payload.get("data") or [])


def helix_video(client_id: str, token: str, vod_id: str) -> dict | None:
    query = urllib.parse.urlencode({"id": vod_id})
    request = urllib.request.Request(
        "https://api.twitch.tv/helix/videos?" + query,
        headers={"Client-ID": client_id, "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode())
    rows = payload.get("data") or []
    return rows[0] if rows else None


def plain_token(value: str) -> str:
    token = (value or "").strip()
    if token.lower().startswith("oauth:"):
        return token.split(":", 1)[1]
    return token


def twitch_credentials() -> tuple[str, str]:
    env = load_env(ROOT / "twitch-bot" / ".env")
    client_id = env.get("TWITCH_CLIENT_ID", "")
    token = plain_token(
        env.get("TWITCH_BROADCASTER_ACCESS_TOKEN") or env.get("TWITCH_BOT_ACCESS_TOKEN") or ""
    )
    if not client_id or not token:
        raise RuntimeError("Jeton Twitch absent")
    return client_id, token


def xai_key_and_model() -> tuple[str, str]:
    env = load_env(ROOT / "config" / "xai.env")
    return env.get("XAI_API_KEY", ""), env.get("XAI_MODEL") or "grok-4.7"


def bot_token() -> str:
    env = load_env(ROOT / "config" / "discord.env")
    token = env.get("DISCORD_BOT_TOKEN", "")
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    return token


def normalize_chapters(raw: list, duration_s: int) -> list[tuple[int, str]] | None:
    chapters: list[tuple[int, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            moment = int(item.get("t"))
        except (TypeError, ValueError):
            continue
        name = " ".join(str(item.get("name") or "").split())
        if not name or moment < 0 or moment >= duration_s:
            continue
        chapters.append((moment, name[:40]))
    chapters.sort()
    if not chapters or chapters[0][0] != 0:
        chapters = [(0, "Début du live")] + [item for item in chapters if item[0] >= 10]
    cleaned = [chapters[0]]
    for moment, name in chapters[1:]:
        if moment < cleaned[-1][0] + 10:
            continue
        if name == cleaned[-1][1]:
            continue
        cleaned.append((moment, name))
    if len(cleaned) < 3:
        return None
    if cleaned[0][1] != "Début du live":
        cleaned[0] = (0, "Début du live")
    return cleaned[:12]


def frames_and_chapters(video: Path, duration_s: int, api_key: str, model: str) -> tuple[str, list[tuple[int, str]]]:
    if not api_key:
        raise RuntimeError("clé vision absente")
    folder = video.parent / "frames"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            "fps=1/45,scale=480:-1",
            str(folder / "f%04d.jpg"),
        ],
        check=True,
        capture_output=True,
    )
    shots = sorted(folder.glob("f*.jpg"))
    if len(shots) > 24:
        step = len(shots) / 24
        shots = [shots[min(len(shots) - 1, int(index * step))] for index in range(24)]
    content = [
        {
            "type": "text",
            "text": (
                "Tu regardes des images d'un live jeu, une toutes les ~45 s, dans l'ordre. "
                "Réponds UNIQUEMENT en JSON "
                '{"game":"nom court du jeu","chapters":[{"t":0,"name":"Début du live"}]}. '
                "t est en secondes, croissant, premier chapitre t=0 « Début du live », "
                "au moins 3 chapitres, écart d'au moins 10 s. Noms très courts en français, "
                "lieux ou étapes (donjon, village, temple, boss), dans le style « Jabu-Jabu »."
            ),
        }
    ]
    for index, shot in enumerate(shots):
        import base64

        encoded = base64.b64encode(shot.read_bytes()).decode()
        content.append({"type": "text", "text": f"image {index} t={index * 45}s"})
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": "data:image/jpeg;base64," + encoded},
            }
        )
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": content}],
    }
    request = urllib.request.Request(
        "https://api.x.ai/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        body = json.loads(response.read().decode())
    text = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError("vision illisible")
    parsed = json.loads(text[start : end + 1])
    chapters = normalize_chapters(parsed.get("chapters") or [], duration_s)
    if not chapters:
        raise RuntimeError("chapitres vision invalides")
    game = " ".join(str(parsed.get("game") or "").split()) or "Aventure"
    return game[:60], chapters


def missing_tools() -> list[str]:
    """Outils requis pour télécharger et découper la VOD."""
    missing = []
    for name in ("yt-dlp", "ffmpeg"):
        if shutil.which(name) is None:
            missing.append(name)
    return missing


def download(vod_id: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    yt_dlp = shutil.which("yt-dlp")
    if not yt_dlp:
        raise RuntimeError("yt-dlp absent")
    subprocess.run(
        [
            yt_dlp,
            "-f",
            "bestvideo[height>=1080][fps>=50]+bestaudio/bestvideo[height>=1080]+bestaudio/best",
            "--merge-output-format",
            "mp4",
            "-o",
            str(dest),
            "--no-playlist",
            "--retries",
            "5",
            f"https://www.twitch.tv/videos/{vod_id}",
        ],
        check=True,
    )
    if not dest.exists():
        raise RuntimeError("téléchargement vide")
    return dest


def youtube_client():
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    path = ROOT / "config" / "youtube-oauth.json"
    if not path.is_file():
        raise RuntimeError("fichier OAuth YouTube absent")
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    try:
        if not creds.valid:
            if not creds.refresh_token:
                raise RuntimeError("YouTube auth invalid_grant — rien publié")
            creds.refresh(Request())
            path.write_text(creds.to_json(), encoding="utf-8")
            os.chmod(path, 0o600)
    except RefreshError as exc:
        if "invalid_grant" in str(exc):
            raise RuntimeError("YouTube auth invalid_grant — rien publié") from exc
        raise
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def find_existing_video(youtube, title: str) -> str:
    request = youtube.search().list(part="snippet", forMine=True, q=title, type="video", maxResults=5)
    found = request.execute()
    for item in found.get("items") or []:
        if (item.get("snippet") or {}).get("title") == title:
            ident = (item.get("id") or {}).get("videoId") or ""
            if ident:
                return ident
    return ""


def upload_private(youtube, path: Path, title: str, description: str) -> str:
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "categoryId": "20",
        },
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = str((response or {}).get("id") or "")
    if not video_id:
        raise RuntimeError("upload YouTube sans id")
    return video_id


def hd_ready(youtube, video_id: str) -> bool:
    found = youtube.videos().list(part="processingDetails,fileDetails", id=video_id).execute()
    items = found.get("items") or []
    if not items:
        return False
    details = items[0]
    status = ((details.get("processingDetails") or {}).get("processingStatus") or "").lower()
    streams = ((details.get("fileDetails") or {}).get("videoStreams") or [])
    heights = [int(item.get("heightPixels") or 0) for item in streams]
    return status == "succeeded" and any(height >= 1080 for height in heights)


def make_public(youtube, video_id: str) -> None:
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}},
    ).execute()


def post_discord(text: str) -> str:
    token = bot_token()
    if not token:
        raise RuntimeError("jeton bot Discord absent")
    payload = {"content": text[:1900], "allowed_mentions": {"parse": ["everyone"]}}
    request = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{YOUTUBE_CHANNEL_DISCORD}/messages",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bot " + token,
            "Content-Type": "application/json",
            "User-Agent": "zaelbot",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode())
    return str(body.get("id") or "")


def plan(vod: dict) -> tuple[str, str, list[tuple[int, str]]]:
    end = vod_end(vod)
    when = end or datetime.now(PARIS)
    game = game_label(
        str(vod.get("title") or ""),
        str(vod.get("game_name") or vod.get("category") or ""),
    )
    chapters = fallback_chapters(parse_duration(str(vod.get("duration") or "")))
    return game, title_for(game, when), chapters


def run(dry_run: bool, vod_id: str = "") -> int:
    missing = missing_tools()
    if missing:
        for name in missing:
            log(f"dépendance manquante : {name}")
        return 1
    now = datetime.now(PARIS)
    client_id, token = twitch_credentials()
    if vod_id:
        vod = helix_video(client_id, token, vod_id)
        if vod is None:
            log(f"VOD {vod_id} introuvable")
            return 1
    else:
        vods = helix_videos(client_id, token)
        vod = select_evening_vod(vods, now)
    if vod is not None and not (vod.get("game_name") or vod.get("category")):
        vod["game_name"] = channel_game(client_id, token)
    if vod is None:
        log("aucune rediffusion de la veille après 20:00, rien à faire")
        return 0
    vod_id = str(vod.get("id") or "")
    game, title, chapters = plan(vod)
    log(f"VOD {vod_id} fin {vod_end(vod).isoformat()} titre prévu {title}")
    log("chapitres prévus (repli, la vision ne tourne qu'à l'upload)\n" + chapter_block(chapters))
    journal = load_journal()
    if journal_done(journal, vod_id):
        log(f"VOD {vod_id} déjà au journal, rien à faire")
        return 0
    if dry_run:
        log("dry-run : pas de téléchargement, pas d'upload, pas de message Discord")
        return 0
    try:
        youtube = youtube_client()
    except RuntimeError as exc:
        log(str(exc))
        return 1
    existing = ""
    try:
        existing = find_existing_video(youtube, title)
    except Exception as exc:
        if "invalid_grant" in str(exc):
            log("YouTube auth invalid_grant — rien publié")
            return 1
        log(f"recherche YouTube indisponible ({type(exc).__name__}), suite avec le journal")
    if existing:
        journal["vods"][vod_id] = {"status": "private", "youtube_id": existing, "title": title}
        save_journal(journal)
        log(f"VOD {vod_id} déjà sur la chaîne ({existing}), pas de second upload")
        return finish_public(youtube, journal, vod_id, game, chapters)
    path = download(vod_id, WORK / f"{vod_id}.mp4")
    duration_s = parse_duration(str(vod.get("duration") or "")) or 0
    api_key, model = xai_key_and_model()
    try:
        seen_game, seen_chapters = frames_and_chapters(path, duration_s, api_key, model)
        game = keep_planned_game(game, seen_game)
        chapters = seen_chapters
        end = vod_end(vod) or now
        title = title_for(game, end)
        log("chapitres vision\n" + chapter_block(chapters))
    except Exception as exc:
        log(f"chapitres vision en échec ({type(exc).__name__}), repli générique")
        chapters = fallback_chapters(duration_s)
    description = description_for(chapters)
    if "tiktok" in description.lower():
        raise RuntimeError("description interdite")
    journal["vods"][vod_id] = {"status": "uploading", "title": title}
    save_journal(journal)
    try:
        video_id = upload_private(youtube, path, title, description)
    except Exception as exc:
        if "invalid_grant" in str(exc):
            log("YouTube auth invalid_grant — rien publié")
            return 1
        log(f"upload en échec ({type(exc).__name__})")
        return 1
    journal["vods"][vod_id] = {"status": "private", "youtube_id": video_id, "title": title}
    save_journal(journal)
    log(f"upload privé {video_id}")
    return finish_public(youtube, journal, vod_id, game, chapters)


def finish_public(youtube, journal: dict, vod_id: str, game: str, chapters: list[tuple[int, str]]) -> int:
    row = journal["vods"][vod_id]
    if row.get("discord_id"):
        log(f"message Discord déjà envoyé pour {vod_id}")
        return 0
    video_id = row["youtube_id"]
    deadline = time.time() + HD_WAIT
    while time.time() < deadline:
        try:
            if hd_ready(youtube, video_id):
                log("1080p prêt")
                break
        except Exception as exc:
            if "invalid_grant" in str(exc):
                log("YouTube auth invalid_grant — la vidéo reste privée, pas de message")
                return 1
        time.sleep(180)
    else:
        log("3 h écoulées, publication même sans confirmation 1080p")
    try:
        make_public(youtube, video_id)
    except Exception as exc:
        if "invalid_grant" in str(exc):
            log("YouTube auth invalid_grant — la vidéo reste privée, pas de message")
        else:
            log(f"passage en public impossible ({type(exc).__name__})")
        return 1
    row["status"] = "public"
    save_journal(journal)
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        message_id = post_discord(discord_text(game, chapters, url))
    except Exception as exc:
        log(f"message Discord en échec ({type(exc).__name__})")
        return 1
    row["status"] = "posted"
    row["discord_id"] = message_id
    save_journal(journal)
    log(f"message Discord {message_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--vod-id", default="")
    args = parser.parse_args()
    try:
        return run(args.dry_run, args.vod_id.strip())
    except Exception as exc:
        if "invalid_grant" in str(exc):
            log("YouTube auth invalid_grant — rien publié")
            return 1
        log(f"arrêt {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
