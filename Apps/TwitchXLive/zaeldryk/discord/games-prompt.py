#!/usr/bin/env python3
"""Post a daily engagement prompt in #🎮-jeux (who's playing tonight?)."""
import asyncio
import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
PROMPTS_ENV = ZAEL_ROOT / "config" / "games-prompts.env"
STATE_FILE = ZAEL_ROOT / "state" / "games-prompt.json"
LOG_FILE = ZAEL_ROOT / "logs" / "games-prompt.log"
API_BASE = "https://discord.com/api/v10"
USER_AGENT = "ZaelrysGamesPrompt/1.0 (+https://zaelrys.local)"
DEFAULT_CHANNEL_ID = "1541249730993201354"

PROMPTS = [
    "🎮 **Entre vous** — qui joue ce soir ? Drop ton jeu en bas 👇 (vocal dispo).",
    "🔥 **Solo ou multi ce soir ?** Dis ce que tu lances — un autre membre peut te rejoindre.",
    "👾 **Vous cherchez un duo / une squad ?** Écris le jeu + plateforme (PC / Xbox / PS / Switch) — entre membres.",
    "🕹️ **C’est quoi ta session du soir ?** Ranked, chill, story… share pour trouver du monde.",
    "⚔️ **Qui est chaud pour une partie ?** Tag le jeu ici, un autre Disciple peut répondre.",
    "🌙 **Soirée gaming** — tu joues à quoi ce soir ? Réponds dans ce salon.",
    "🎯 **Une place libre dans ta partie ?** Propose ta session — c’est pour la communauté.",
]


def log(msg: str) -> None:
    line = f"{datetime.utcnow():%Y-%m-%d %H:%M:%S} - {msg}"
    print(line, flush=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def load_config() -> Dict[str, str]:
    cfg = load_env_file(DISCORD_ENV)
    cfg.update(load_env_file(PROMPTS_ENV))
    if not cfg.get("DISCORD_BOT_TOKEN"):
        raise RuntimeError("DISCORD_BOT_TOKEN missing")
    cfg.setdefault("GAMES_CHANNEL_ID", DEFAULT_CHANNEL_ID)
    return cfg


def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return {"used": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"used": []}


def save_state(data: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.utcnow().isoformat()
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def pick_prompt(custom: Optional[List[str]] = None) -> str:
    pool = custom if custom else PROMPTS
    state = load_state()
    used = set(state.get("used") or [])
    available = [p for p in pool if p not in used]
    if not available:
        available = list(pool)
        used = set()
    choice = random.choice(available)
    used.add(choice)
    # keep last N to avoid immediate repeats
    used_list = [p for p in pool if p in used]
    state["used"] = used_list[-max(1, len(pool) - 1) :]
    state["last_prompt"] = choice
    save_state(state)
    return choice


def load_custom_prompts(cfg: Dict[str, str]) -> Optional[List[str]]:
    raw = cfg.get("GAMES_PROMPTS", "").strip()
    if not raw:
        return None
    # Separated by ||
    parts = [p.strip() for p in raw.split("||") if p.strip()]
    return parts or None


async def post(session: aiohttp.ClientSession, channel_id: str, content: str) -> None:
    url = f"{API_BASE}/channels/{channel_id}/messages"
    async with session.post(url, json={"content": content}) as resp:
        body = await resp.text()
        if resp.status not in (200, 201):
            raise RuntimeError(f"Discord HTTP {resp.status}: {body[:300]}")


async def run() -> None:
    cfg = load_config()
    channel_id = cfg["GAMES_CHANNEL_ID"]
    custom = load_custom_prompts(cfg)
    content = pick_prompt(custom)
    headers = {
        "Authorization": f"Bot {cfg['DISCORD_BOT_TOKEN']}",
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        await post(session, channel_id, content)
    log(f"POST jeux: {content[:80]}")


def main() -> None:
    log("Games prompt start")
    try:
        asyncio.run(run())
        log("Done")
    except Exception as e:
        log(f"FAILED {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
