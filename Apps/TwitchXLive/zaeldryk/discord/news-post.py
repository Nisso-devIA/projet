#!/usr/bin/env python3
"""Post gaming & tech news from RSS feeds to Discord #🔔-actualités."""
import asyncio
import json
import os
import re
import html
import xml.etree.ElementTree as ET
from datetime import datetime, date
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.request import Request, urlopen

import aiohttp

GUILD_ID = 867426693286461490
ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
NEWS_ENV = ZAEL_ROOT / "config" / "news.env"
STATE_FILE = ZAEL_ROOT / "state" / "posted-news.json"
LOG_FILE = ZAEL_ROOT / "logs" / "news-bot.log"
LOCK_FILE = ZAEL_ROOT / "state" / "news-post.lock"
API_BASE = "https://discord.com/api/v10"
USER_AGENT = "ZaelrysNewsBot/1.0 (+https://zaelrys.local)"
# Veille à partir du jour J — rien d'antérieur
DEFAULT_NEWS_MIN_DATE = "2026-08-26"

FEEDS = [
    {"name": "JeuxActu", "category": "Gaming", "url": "https://www.jeuxactu.com/rss/news.rss"},
    {"name": "JeuxVideo.com", "category": "Gaming", "url": "https://www.jeuxvideo.com/rss/rss.xml"},
    {"name": "IGN", "category": "Gaming", "url": "https://www.ign.com/rss/articles/feed"},
    {"name": "Frandroid", "category": "High-tech", "url": "https://www.frandroid.com/feed"},
    {"name": "Les Numériques", "category": "High-tech", "url": "https://www.lesnumeriques.com/rss.xml"},
    {"name": "Numerama", "category": "High-tech", "url": "https://www.numerama.com/feed/"},
]

CATEGORY_COLORS = {
    "Gaming": 0x9b59b6,
    "High-tech": 0x3498db,
}


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
    cfg.update(load_env_file(NEWS_ENV))
    if not cfg.get("DISCORD_BOT_TOKEN"):
        raise RuntimeError("DISCORD_BOT_TOKEN missing")
    if not cfg.get("NEWS_CHANNEL_ID"):
        raise RuntimeError("NEWS_CHANNEL_ID missing in news.env")
    return cfg


def load_posted() -> Set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return set(data.get("urls", []))
    except (json.JSONDecodeError, OSError):
        return set()


def acquire_lock() -> bool:
    ZAEL_ROOT.joinpath("state").mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            age = datetime.utcnow().timestamp() - LOCK_FILE.stat().st_mtime
            if age < 1800:
                log("SKIP — news bot déjà en cours (lock)")
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


def save_posted(urls: Set[str], max_keep: int) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ordered = list(urls)
    if len(ordered) > max_keep:
        ordered = ordered[-max_keep:]
    STATE_FILE.write_text(
        json.dumps({"urls": ordered, "updated_at": datetime.utcnow().isoformat()}, indent=2),
        encoding="utf-8",
    )


def clean_text(text: str, limit: int = 280) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def fetch_xml(url: str) -> ET.Element:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=25) as resp:
        data = resp.read()
    return ET.fromstring(data)


def parse_rss_items(root: ET.Element) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    channel = root.find("channel")
    if channel is not None:
        raw_items = channel.findall("item")
    else:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        raw_items = root.findall("a:entry", ns)
        if not raw_items:
            raw_items = root.findall("entry")

    for item in raw_items:
        title = item.findtext("title") or ""
        link = item.findtext("link")
        if not link:
            ln = item.find("link")
            if ln is not None and ln.get("href"):
                link = ln.get("href")
        desc = (
            item.findtext("description")
            or item.findtext("summary")
            or item.findtext("content")
            or ""
        )
        pub = item.findtext("pubDate") or item.findtext("published") or item.findtext("updated")
        thumb = None
        for tag in ("media:thumbnail", "media:content", "enclosure"):
            el = item.find(tag)
            if el is not None:
                thumb = el.get("url") or el.get("href")
                if thumb:
                    break
        if not link:
            continue
        try:
            dt = parsedate_to_datetime(pub) if pub else datetime.utcnow()
            # Normalize to naive UTC so sort() never mixes aware/naive
            if getattr(dt, "tzinfo", None) is not None:
                dt = datetime.utcfromtimestamp(dt.timestamp())
        except (TypeError, ValueError, OSError, OverflowError):
            dt = datetime.utcnow()
        items.append(
            {
                "url": link.strip(),
                "title": clean_text(title, 200),
                "summary": clean_text(desc, 300),
                "date": dt,
                "thumbnail": thumb,
            }
        )
    return items


def fetch_entries(feed_cfg: dict) -> List[dict]:
    try:
        root = fetch_xml(feed_cfg["url"])
        parsed = parse_rss_items(root)
    except Exception as e:
        log(f"RSS error {feed_cfg['name']}: {e}")
        return []
    out = []
    for row in parsed[:15]:
        row["source"] = feed_cfg["name"]
        row["category"] = feed_cfg["category"]
        out.append(row)
    return out


def build_embed(article: dict) -> dict:
    color = CATEGORY_COLORS.get(article["category"], 0x95a5a6)
    embed = {
        "title": article["title"] or "Actualité",
        "url": article["url"],
        "description": article["summary"] or "Voir l'article ↗",
        "color": color,
        "footer": {"text": f"{article['category']} · {article['source']}"},
        "timestamp": article["date"].isoformat(),
    }
    if article.get("thumbnail"):
        thumb = article["thumbnail"]
        if isinstance(thumb, str) and thumb.startswith(("http://", "https://")):
            embed["thumbnail"] = {"url": thumb}
    return embed


async def post_message(session: aiohttp.ClientSession, channel_id: str, embed: dict) -> None:
    payload = {"embeds": [embed]}
    url = f"{API_BASE}/channels/{channel_id}/messages"
    async with session.post(url, json=payload) as resp:
        body = await resp.text()
        if resp.status not in (200, 201):
            raise RuntimeError(f"Discord HTTP {resp.status}: {body[:300]}")


async def run() -> int:
    cfg = load_config()
    token = cfg["DISCORD_BOT_TOKEN"]
    channel_id = cfg["NEWS_CHANNEL_ID"]
    max_per_run = int(cfg.get("NEWS_MAX_PER_RUN", "3"))
    state_max = int(cfg.get("NEWS_STATE_MAX", "400"))
    min_date_raw = cfg.get("NEWS_MIN_DATE", DEFAULT_NEWS_MIN_DATE).strip()
    try:
        min_date = date.fromisoformat(min_date_raw)
    except ValueError:
        min_date = date.fromisoformat(DEFAULT_NEWS_MIN_DATE)
        log(f"NEWS_MIN_DATE invalide ({min_date_raw!r}) — fallback {DEFAULT_NEWS_MIN_DATE}")

    posted = load_posted()
    candidates: List[dict] = []

    for feed in FEEDS:
        candidates.extend(fetch_entries(feed))

    candidates = [
        a
        for a in candidates
        if a["url"] not in posted and a["date"].date() >= min_date
    ]
    candidates.sort(key=lambda a: a["date"], reverse=True)
    log(
        f"Filtre veille ≥ {min_date.isoformat()} — "
        f"{len(candidates)} candidat(s) (hors déjà postés / trop anciens)"
    )

    if not candidates:
        log("Aucune nouvelle actu (après filtre jour J)")
        return 0

    to_post = candidates[:max_per_run]
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
    }

    count = 0
    async with aiohttp.ClientSession(headers=headers) as session:
        for article in to_post:
            embed = build_embed(article)
            try:
                await post_message(session, channel_id, embed)
                posted.add(article["url"])
                save_posted(posted, state_max)
                count += 1
                log(f"POST {article['source']}: {article['title'][:80]}")
                await asyncio.sleep(1.2)
            except Exception as e:
                log(f"POST fail {article['url']}: {e}")

    save_posted(posted, state_max)
    log(f"Done — {count} article(s) publié(s)")
    return count


def main() -> None:
    if not acquire_lock():
        return
    log("News bot start")
    try:
        asyncio.run(run())
    except Exception as e:
        log(f"FAILED {e}")
        release_lock()
        raise SystemExit(1)
    release_lock()


if __name__ == "__main__":
    main()
