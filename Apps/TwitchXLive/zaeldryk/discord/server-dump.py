#!/usr/bin/env python3
"""Discord server dump via REST API (no second gateway session)."""
import asyncio
import json
import os
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

GUILD_ID = 867426693286461490
CONFIG_PATH = Path("/home/ubuntu/zaeldryk/config/discord.env")
LOG_PATH = Path("/home/ubuntu/zaeldryk/logs/discord-dump.log")
OUTPUT_ROOT = Path(os.environ.get("DISCORD_DUMP_ROOT", "/home/ubuntu/backups/discord-dumps"))
RETENTION_DAYS = int(os.environ.get("DISCORD_DUMP_RETENTION_DAYS", "14"))
MESSAGES_PER_CHANNEL = int(os.environ.get("DISCORD_DUMP_MSG_LIMIT", "200"))
API_BASE = "https://discord.com/api/v10"
USER_AGENT = "DiscordBot (https://zaelrys.local/dump, 1.0)"
LOCK_FILE = OUTPUT_ROOT / ".dump.lock"


def load_token() -> str:
    for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("DISCORD_BOT_TOKEN missing")


def log(msg: str) -> None:
    line = f"{datetime.utcnow():%Y-%m-%d %H:%M:%S} - {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def acquire_lock() -> bool:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            age = datetime.utcnow().timestamp() - LOCK_FILE.stat().st_mtime
            if age < 3600:
                log("SKIP — dump already running (lock file)")
                return False
        except OSError:
            pass
    LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock() -> None:
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass


async def api_request(
    session: aiohttp.ClientSession,
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    url = f"{API_BASE}{path}"
    async with session.request(method, url, params=params) as resp:
        if resp.status == 204:
            return None
        body = await resp.text()
        if resp.status >= 400:
            raise RuntimeError(f"{method} {path} HTTP {resp.status}: {body[:200]}")
        if not body:
            return None
        return json.loads(body)


async def fetch_members(session: aiohttp.ClientSession) -> List[dict]:
    members: List[dict] = []
    after = "0"
    while True:
        batch = await api_request(
            session,
            "GET",
            f"/guilds/{GUILD_ID}/members",
            {"limit": 1000, "after": after},
        )
        if not batch:
            break
        members.extend(batch)
        if len(batch) < 1000:
            break
        after = batch[-1]["user"]["id"]
    return members


async def fetch_channel_messages(
    session: aiohttp.ClientSession, channel_id: int, limit: int
) -> List[dict]:
    out: List[dict] = []
    before: Optional[str] = None
    while len(out) < limit:
        batch_size = min(100, limit - len(out))
        params: Dict[str, Any] = {"limit": batch_size}
        if before:
            params["before"] = before
        try:
            batch = await api_request(
                session, "GET", f"/channels/{channel_id}/messages", params
            )
        except RuntimeError as e:
            if "403" in str(e) or "404" in str(e):
                log(f"SKIP messages ch={channel_id}: {e}")
                break
            raise
        if not batch:
            break
        for msg in batch:
            out.append(
                {
                    "id": msg.get("id"),
                    "channel_id": channel_id,
                    "author_id": msg.get("author", {}).get("id"),
                    "author": msg.get("author", {}).get("username"),
                    "content": msg.get("content"),
                    "created_at": msg.get("timestamp"),
                    "attachments": [a.get("url") for a in msg.get("attachments", [])],
                }
            )
        before = batch[-1]["id"]
        if len(batch) < batch_size:
            break
    return out


async def run_dump() -> Path:
    token = load_token()
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": USER_AGENT,
    }

    stamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M")
    work_dir = OUTPUT_ROOT / stamp
    work_dir.mkdir(parents=True, exist_ok=True)

    async with aiohttp.ClientSession(headers=headers) as session:
        guild = await api_request(session, "GET", f"/guilds/{GUILD_ID}")
        roles = await api_request(session, "GET", f"/guilds/{GUILD_ID}/roles")
        channels = await api_request(session, "GET", f"/guilds/{GUILD_ID}/channels")
        members = await fetch_members(session)

        guild_data = {
            "id": guild.get("id"),
            "name": guild.get("name"),
            "member_count": guild.get("approximate_member_count"),
            "dumped_at": datetime.utcnow().isoformat(),
        }
        (work_dir / "guild.json").write_text(
            json.dumps(guild_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (work_dir / "roles.json").write_text(
            json.dumps(roles, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (work_dir / "channels.json").write_text(
            json.dumps(channels, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (work_dir / "members.json").write_text(
            json.dumps(members, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        msg_dir = work_dir / "messages"
        msg_dir.mkdir(exist_ok=True)
        msg_total = 0
        text_channels = [c for c in channels if c.get("type") == 0]
        for ch in text_channels:
            cid = int(ch["id"])
            name = ch.get("name") or str(cid)
            msgs = await fetch_channel_messages(session, cid, MESSAGES_PER_CHANNEL)
            if not msgs:
                continue
            safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
            path = msg_dir / f"{cid}_{safe}.jsonl"
            with path.open("w", encoding="utf-8") as f:
                for row in msgs:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            msg_total += len(msgs)

    manifest = {
        "guild_id": GUILD_ID,
        "stamp": stamp,
        "roles": len(roles),
        "channels": len(channels),
        "members": len(members),
        "messages": msg_total,
        "messages_per_channel_limit": MESSAGES_PER_CHANNEL,
    }
    (work_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    archive = OUTPUT_ROOT / f"{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(work_dir, arcname=stamp)
    shutil.rmtree(work_dir)

    log(
        f"OK {archive.name} — {len(members)} membres, "
        f"{len(channels)} salons, {msg_total} messages"
    )
    return archive


def prune_old() -> None:
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    removed = 0
    for p in OUTPUT_ROOT.glob("*.tar.gz"):
        try:
            part = p.stem.replace(".tar", "")
            dt = datetime.strptime(part, "%Y-%m-%d_%H%M")
            if dt < cutoff:
                p.unlink()
                removed += 1
        except ValueError:
            continue
    if removed:
        log(f"Pruned {removed} archive(s) older than {RETENTION_DAYS}d")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if not acquire_lock():
        return
    log("Discord dump start")
    try:
        asyncio.run(run_dump())
    except Exception as e:
        log(f"FAILED {e}")
        release_lock()
        raise SystemExit(1)
    prune_old()
    log("Discord dump finished")
    release_lock()


if __name__ == "__main__":
    main()
