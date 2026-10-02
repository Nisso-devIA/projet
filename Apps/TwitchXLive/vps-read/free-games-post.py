#!/usr/bin/env python3
"""Announce free games from Epic, PSN, Xbox, GOG, Steam (when detectable)."""
import asyncio
import json
import os
import re
import html
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.request import Request, urlopen

import aiohttp

ZAEL_ROOT = Path(os.environ.get("ZAEL_ROOT", "/home/ubuntu/zaeldryk"))
DISCORD_ENV = ZAEL_ROOT / "config" / "discord.env"
FREEGAMES_ENV = ZAEL_ROOT / "config" / "freegames.env"
STATE_FILE = ZAEL_ROOT / "state" / "posted-freegames.json"
LOG_FILE = ZAEL_ROOT / "logs" / "freegames-bot.log"
LOCK_FILE = ZAEL_ROOT / "state" / "freegames-post.lock"
API_BASE = "https://discord.com/api/v10"
USER_AGENT = "ZaelrysFreeGames/1.0 (+https://zaelrys.local)"

STORE_COLORS = {
    "Epic Games": 0x2f2d2e,
    "PlayStation": 0x003087,
    "Xbox Game Pass": 0x107c10,
    "Steam": 0x1b2838,
    "GOG": 0x9c27b0,
    "Prime Gaming": 0x00a8e1,
    "EA App": 0xff4747,
}

XBOX_GP_FEEDS = [
    "https://news.xbox.com/fr-fr/feed/",
    "https://news.xbox.com/fr-fr/tag/xbox-game-pass/feed/",
]
XBOX_GP_MAX_AGE_DAYS = 60
XBOX_GP_TITLE_RE = re.compile(
    r"(prochainement dans le.*game\s*pass"
    r"|jours?\s+de\s+jeu\s+gratuit"
    r"|free\s+play\s+days?"
    r"|game\s*pass.*(promo|promotion|réduction|offre|cadeau|gratuit|essai)"
    r"|(promo|promotion|réduction|offre|cadeau|essai).*game\s*pass"
    r"|xbox\s+game\s+pass\s+(standard|pc|ultimate|console|essential))",
    re.IGNORECASE,
)

Offer = Dict[str, Any]  # store, title, url, description, image, key, ends_at?


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
    cfg.update(load_env_file(FREEGAMES_ENV))
    if not cfg.get("DISCORD_BOT_TOKEN"):
        raise RuntimeError("DISCORD_BOT_TOKEN missing")
    if not cfg.get("FREEGAMES_CHANNEL_ID"):
        raise RuntimeError("FREEGAMES_CHANNEL_ID missing — run create-free-games-channel.py")
    return cfg


def load_posted() -> Set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        keys = set(data.get("keys", []))
        # Normalise anciennes clés Epic (epic:gameId:offerId) → epic:game:gameId
        for k in list(keys):
            if k.startswith("epic:") and not k.startswith("epic:game:"):
                parts = k.split(":")
                if len(parts) >= 2 and parts[1]:
                    keys.add(f"epic:game:{parts[1]}")
        return keys
    except (json.JSONDecodeError, OSError):
        return set()


def acquire_lock() -> bool:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            age = datetime.utcnow().timestamp() - LOCK_FILE.stat().st_mtime
            if age < 1800:
                log("SKIP — free games bot déjà en cours (lock)")
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


def save_posted(keys: Set[str], max_keep: int = 500) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ordered = list(keys)
    if len(ordered) > max_keep:
        ordered = ordered[-max_keep:]
    STATE_FILE.write_text(
        json.dumps({"keys": ordered, "updated_at": datetime.utcnow().isoformat()}, indent=2),
        encoding="utf-8",
    )


def http_get(url: str, timeout: int = 25) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def clean_text(text: str, limit: int = 400) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def parse_rss(url: str) -> List[dict]:
    root = ET.fromstring(http_get(url))
    items = []
    channel = root.find("channel")
    raw = channel.findall("item") if channel is not None else root.findall(".//item")
    for item in raw:
        link = item.findtext("link")
        if not link:
            ln = item.find("link")
            if ln is not None and ln.get("href"):
                link = ln.get("href")
        pub = item.findtext("pubDate") or item.findtext("published")
        try:
            dt = parsedate_to_datetime(pub) if pub else datetime.utcnow()
        except (TypeError, ValueError, OSError):
            dt = datetime.utcnow()
        items.append(
            {
                "title": clean_text(item.findtext("title") or "", 200),
                "link": (link or "").strip(),
                "summary": clean_text(
                    item.findtext("description") or item.findtext("summary") or "", 500
                ),
                "date": dt,
            }
        )
    return items


def epic_slug(element: dict) -> Optional[str]:
    mappings = element.get("offerMappings") or []
    if mappings:
        slug = mappings[0].get("pageSlug")
        if slug:
            return slug
    ps = element.get("productSlug") or ""
    if ps:
        return ps.split("/")[-1]
    return None


def fetch_epic() -> List[Offer]:
    url = (
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        "?locale=fr-FR&country=FR&allowCountries=FR"
    )
    data = json.loads(http_get(url))
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
    offers: List[Offer] = []
    for el in elements:
        promos = el.get("promotions") or {}
        title = el.get("title") or "Jeu gratuit"
        game_id = el.get("id")
        if not game_id:
            continue
        slug = epic_slug(el)
        store_url = (
            f"https://store.epicgames.com/fr/p/{slug}" if slug else "https://store.epicgames.com/fr/free-games"
        )
        images = el.get("keyImages") or []
        thumb = next(
            (i.get("url") for i in images if i.get("type") in ("Thumbnail", "OfferImageWide", "DieselStoreFrontWide")),
            None,
        )
        status_parts: List[str] = []
        end_hint = ""
        has_promo = False
        for bucket, status_label in (
            ("promotionalOffers", "Disponible maintenant"),
            ("upcomingPromotionalOffers", "Bientôt gratuit"),
        ):
            for group in promos.get(bucket) or []:
                for po in group.get("promotionalOffers") or []:
                    has_promo = True
                    end = po.get("endDate", "")
                    if end and not end_hint:
                        end_hint = end[:10]
                    if status_label not in status_parts:
                        status_parts.append(status_label)
        if not has_promo:
            continue
        desc = " · ".join(status_parts)
        if end_hint:
            desc += f" — jusqu'au {end_hint}"
        offers.append(
            {
                "store": "Epic Games",
                "title": title,
                "url": store_url,
                "description": desc,
                "image": thumb,
                "key": f"epic:game:{game_id}",
            }
        )
    return offers


def fetch_psn() -> List[Offer]:
    """Liste chaque jeu du mois PS Plus (Essential) depuis l'article officiel."""
    items = parse_rss("https://blog.fr.playstation.com/category/ps-plus/feed/")
    offers: List[Offer] = []
    article = None
    for it in items:
        title_lc = it["title"].lower()
        if "jeux du mois" in title_lc or ("jeux de" in title_lc and "mois" in title_lc):
            article = it
            break
    if not article:
        return offers

    article_url = article["link"]
    games: List[Tuple[str, str]] = []
    try:
        page = http_get(article_url).decode("utf-8", errors="replace")
        strongs = re.findall(r"<strong>(.*?)</strong>", page, flags=re.I | re.S)
        for raw in strongs:
            name = clean_text(raw, 120)
            # "Titre | PS5, PS4" ou "Titre | PS5"
            if "|" in name and re.search(r"\bPS[45]\b", name, re.I):
                title = name.split("|", 1)[0].strip()
                platforms = name.split("|", 1)[1].strip()
                if title and "pack playstation plus" not in title.lower():
                    games.append((title, platforms))
    except Exception as e:
        log(f"PSN article parse error: {e}")

    # Fallback : titres après ":" dans le titre de l'article
    if not games:
        m = re.search(r":\s*(.+)$", article["title"])
        if m:
            for part in re.split(r",| et ", m.group(1)):
                part = part.strip(" .–-")
                # retire suffixe blog
                part = re.sub(r"\s*[–-]\s*PlayStation Blog.*$", "", part, flags=re.I).strip()
                if 2 < len(part) < 90:
                    games.append((part, "PS Plus"))

    for title, platforms in games:
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
        offers.append(
            {
                "store": "PlayStation",
                "title": title,
                "url": article_url,
                "description": f"Jeux du mois PlayStation Plus — {platforms}",
                "image": None,
                "key": f"psn:game:{slug}",
            }
        )

    # Si parsing échoue : garder l'article (1 annonce)
    if not offers:
        offers.append(
            {
                "store": "PlayStation",
                "title": article["title"],
                "url": article_url,
                "description": article["summary"] or "Jeux PlayStation Plus du mois — voir l'article.",
                "image": None,
                "key": f"psn:{article_url}",
            }
        )
    return offers


def _extract_game_names_from_html(page: str) -> List[str]:
    """Extrait des titres de jeux depuis un article Xbox Wire (listes typiques)."""
    names: List[str] = []
    # Lignes du type : "Titre (Cloud, Console et PC) – 19 août"
    for raw in re.findall(r"<li[^>]*>(.*?)</li>", page, flags=re.I | re.S):
        name = clean_text(raw, 120)
        if re.search(r"\(.*?(cloud|console|pc).*?\)", name, re.I) or re.search(
            r"[–-]\s*\d{1,2}\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)",
            name,
            re.I,
        ):
            # retire la date / plateforme pour un titre plus propre
            title = re.split(r"\s*[–-]\s*\d", name, maxsplit=1)[0].strip()
            title = re.sub(r"\s*\((?:cloud|console|pc|game preview)[^)]*\)\s*$", "", title, flags=re.I).strip()
            # parfois plusieurs (Game Preview) (Cloud...)
            title = re.sub(r"\s*\([^)]*(?:cloud|console|pc)[^)]*\)\s*$", "", title, flags=re.I).strip()
            if 2 < len(title) < 90:
                names.append(title)

    for raw in re.findall(r"<strong>(.*?)</strong>", page, flags=re.I | re.S):
        name = clean_text(raw, 100)
        if re.search(r"\(.*?(cloud|console|pc).*?\)", name, re.I):
            title = re.sub(r"\s*\([^)]*(?:cloud|console|pc|game preview)[^)]*\)", "", name, flags=re.I).strip()
            if 2 < len(title) < 90:
                names.append(title)

    skip = re.compile(
        r"^(disponible|bientôt|à ne pas|coming|available|game\s*pass|xbox|lire|suite|promo)",
        re.I,
    )
    seen: Set[str] = set()
    out: List[str] = []
    for n in names:
        if skip.search(n):
            continue
        k = n.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(n)
    return out[:30]


def fetch_xbox_gamepass() -> List[Offer]:
    """Ajouts / promos Game Pass — 1 embed par jeu si listés dans l'article."""
    cutoff = datetime.utcnow() - timedelta(days=XBOX_GP_MAX_AGE_DAYS)
    seen_links: Set[str] = set()
    offers: List[Offer] = []

    for feed_url in XBOX_GP_FEEDS:
        try:
            items = parse_rss(feed_url)
        except Exception as e:
            log(f"Xbox GP RSS error {feed_url}: {e}")
            continue
        for it in items:
            link = it["link"]
            if not link or link in seen_links:
                continue
            title = it["title"].replace("\u00a0", " ").strip()
            if not XBOX_GP_TITLE_RE.search(title):
                continue
            if it["date"].replace(tzinfo=None) < cutoff:
                continue
            seen_links.add(link)

            games: List[str] = []
            try:
                page = http_get(link).decode("utf-8", errors="replace")
                games = _extract_game_names_from_html(page)
            except Exception as e:
                log(f"Xbox article parse error: {e}")

            if games:
                for gname in games:
                    slug = re.sub(r"[^a-z0-9]+", "-", gname.lower()).strip("-")[:60]
                    offers.append(
                        {
                            "store": "Xbox Game Pass",
                            "title": gname,
                            "url": link,
                            "description": f"Via : {title}",
                            "image": None,
                            "key": f"xbox-gp:game:{slug}",
                            "_date": it["date"].replace(tzinfo=None),
                        }
                    )
            else:
                offers.append(
                    {
                        "store": "Xbox Game Pass",
                        "title": title,
                        "url": link,
                        "description": it["summary"] or "Actu Xbox Game Pass — voir l'article.",
                        "image": None,
                        "key": f"xbox-gp:{link}",
                        "_date": it["date"].replace(tzinfo=None),
                    }
                )

    offers.sort(key=lambda o: o.get("_date") or datetime.utcnow(), reverse=True)
    for o in offers:
        o.pop("_date", None)
    return offers


def fetch_gog() -> List[Offer]:
    url = "https://www.gog.com/games/ajax/filtered?mediaType=game&isFree=true&sort=popularity"
    try:
        data = json.loads(http_get(url))
    except Exception as e:
        log(f"GOG fetch error: {e}")
        return []
    offers: List[Offer] = []
    for p in data.get("products", []):
        pid = p.get("id")
        slug = p.get("slug")
        title = p.get("title") or "Jeu GOG"
        if not pid:
            continue
        offers.append(
            {
                "store": "GOG",
                "title": title.strip(),
                "url": f"https://www.gog.com/game/{slug}" if slug else "https://www.gog.com/",
                "description": "Gratuit sur GOG — à récupérer sur le site.",
                "image": None,
                "key": f"gog:{pid}",
            }
        )
    return offers


def fetch_steam() -> List[Offer]:
    """Jeux Steam à 100 % / gratuits (featured + recherche free specials)."""
    offers: List[Offer] = []
    seen: Set[str] = set()

    def add(appid, name, desc, image=None, discount=100):
        key = f"steam:{appid}"
        if not appid or key in seen:
            return
        seen.add(key)
        offers.append(
            {
                "store": "Steam",
                "title": name or "Jeu Steam",
                "url": f"https://store.steampowered.com/app/{appid}",
                "description": desc,
                "image": image,
                "key": key,
            }
        )

    try:
        data = json.loads(
            http_get("https://store.steampowered.com/api/featuredcategories/?l=french&cc=FR")
        )
        for item in data.get("specials", {}).get("items", []):
            discount = item.get("discount_percent", 0) or 0
            final = item.get("final_price")
            if discount < 100 and final not in (0, "0"):
                continue
            add(
                item.get("id"),
                item.get("name"),
                f"Promo Steam ({discount}% — gratuit).",
                item.get("header_image"),
                discount,
            )
    except Exception as e:
        log(f"Steam featured error: {e}")

    # Recherche store : gratuits en promo
    try:
        search = json.loads(
            http_get(
                "https://store.steampowered.com/search/results/"
                "?query&start=0&count=50&maxprice=free&specials=1&infinite=1&l=french&cc=FR"
            )
        )
        html_chunk = search.get("results_html") or ""
        for m in re.finditer(
            r'data-ds-appid="(\d+)"[^>]*>.*?class="title"[^>]*>(.*?)</span>',
            html_chunk,
            flags=re.I | re.S,
        ):
            appid, name = m.group(1), clean_text(m.group(2), 120)
            add(appid, name, "Gratuit / 100 % sur Steam en ce moment.")
    except Exception as e:
        log(f"Steam search error: {e}")

    return offers


PROVIDERS: List[Tuple[str, Any]] = [
    ("Epic Games", fetch_epic),
    ("PlayStation", fetch_psn),
    ("Xbox Game Pass", fetch_xbox_gamepass),
    ("GOG", fetch_gog),
    ("Steam", fetch_steam),
]


def build_embed(offer: Offer) -> dict:
    color = STORE_COLORS.get(offer["store"], 0x95a5a6)
    embed = {
        "title": offer["title"],
        "url": offer["url"],
        "description": offer.get("description") or "Récupérer sur le store ↗",
        "color": color,
        "footer": {"text": offer["store"]},
    }
    img = offer.get("image")
    if img and isinstance(img, str) and img.startswith(("http://", "https://")):
        embed["thumbnail"] = {"url": img}
    return embed


async def post_store_batch(
    session: aiohttp.ClientSession,
    channel_id: str,
    store: str,
    offers: List[Offer],
) -> int:
    """Poste tous les jeux (messages de max 10 embeds Discord)."""
    if not offers:
        return 0
    posted_n = 0
    url = f"{API_BASE}/channels/{channel_id}/messages"
    for start in range(0, len(offers), 10):
        chunk = offers[start : start + 10]
        embeds = [build_embed(o) for o in chunk]
        part = ""
        if len(offers) > 10:
            page = start // 10 + 1
            pages = (len(offers) + 9) // 10
            part = f" ({page}/{pages})"
        header = f"🎁 **{store}** — jeux gratuits / offerts{part}"
        payload = {"content": header, "embeds": embeds}
        async with session.post(url, json=payload) as resp:
            body = await resp.text()
            if resp.status not in (200, 201):
                raise RuntimeError(f"Discord HTTP {resp.status}: {body[:300]}")
        posted_n += len(embeds)
        await asyncio.sleep(1.2)
    return posted_n


async def run() -> int:
    cfg = load_config()
    token = cfg["DISCORD_BOT_TOKEN"]
    channel_id = cfg["FREEGAMES_CHANNEL_ID"]
    # 0 = pas de limite artificielle
    max_per_store = int(cfg.get("FREEGAMES_MAX_PER_STORE", "0"))

    posted = load_posted()
    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
    }

    total = 0
    async with aiohttp.ClientSession(headers=headers) as session:
        for store_name, fetcher in PROVIDERS:
            try:
                all_offers = fetcher()
            except Exception as e:
                log(f"{store_name} error: {e}")
                continue
            new_offers = [o for o in all_offers if o["key"] not in posted]
            if not new_offers:
                log(f"{store_name}: rien de nouveau ({len(all_offers)} trouvé(s))")
                continue
            batch = new_offers if max_per_store <= 0 else new_offers[:max_per_store]
            try:
                n = await post_store_batch(session, channel_id, store_name, batch)
                for o in batch:
                    posted.add(o["key"])
                save_posted(posted)
                total += n
                log(f"POST {store_name}: {n} jeu(x) / {len(all_offers)} détecté(s)")
                await asyncio.sleep(1.5)
            except Exception as e:
                log(f"POST fail {store_name}: {e}")

    save_posted(posted)
    log(f"Done — {total} embed(s) publié(s)")
    return total


def main() -> None:
    if not acquire_lock():
        return
    log("Free games bot start")
    try:
        asyncio.run(run())
    except Exception as e:
        log(f"FAILED {e}")
        release_lock()
        raise SystemExit(1)
    release_lock()


if __name__ == "__main__":
    main()
