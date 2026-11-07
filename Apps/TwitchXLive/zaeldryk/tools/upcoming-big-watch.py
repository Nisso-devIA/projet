#!/usr/bin/env python3
"""Alertes privées — sorties Switch 2 / PS5 style Zelda / Odyssey / Witcher / Bananza.

Sources RSS gaming FR/EN. Filtre plateforme + vibe « gros titre aventure / 3D / RPG ».
Nouveautés seulement (après inventaire initial silencieux).
"""
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

TOKEN = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
CHANNEL_ID = (
    os.environ.get("DISCORD_UPCOMING_BIG_CHANNEL_ID")
    or os.environ.get("UPCOMING_BIG_CHANNEL_ID")
    or ""
).strip()
STATE_FILE = Path(
    os.environ.get("STATE_FILE") or "/home/ubuntu/zaeldryk/state/upcoming-big.json"
)
BOOTSTRAP_POST = os.environ.get("BOOTSTRAP_POST", "0").strip() in ("1", "true", "yes")
MAX_BOOTSTRAP = int(os.environ.get("MAX_BOOTSTRAP", "8"))
UA = "ZaelUpcomingBig/1.1 (+discord)"

FEEDS = [
    ("Nintendo Life", "https://www.nintendolife.com/feeds/latest"),
    ("Push Square", "https://www.pushsquare.com/feeds/latest"),
    ("Gematsu", "https://www.gematsu.com/feed"),
    ("JeuxActu", "https://www.jeuxactu.com/rss/news.rss"),
    ("JV.com", "https://www.jeuxvideo.com/rss/rss.xml"),
    ("PlayStation Blog FR", "https://blog.fr.playstation.com/feed/"),
]

# Au moins une plateforme cible
PLATFORM_RE = re.compile(
    r"\b("
    r"switch\s*2|nintendo\s*switch\s*2|nsw2|"
    r"ps5|playstation\s*5|play\s*station\s*5|ps\s*5"
    r")\b",
    re.I,
)

# Vibe « gros titre » — style demandé
STYLE_RE = re.compile(
    r"("
    r"zelda|witcher|odyssey|bananza|donkey\s*kong|"
    r"breath\s*of\s*the\s*wild|tears\s*of\s*the\s*kingdom|"
    r"open[\s\-]?world|monde\s+ouvert|"
    r"action[\s\-]?rpg|rpg\s+d['’]?action|"
    r"3d\s+platform|platform(?:er|e)?\s*3d|plateforme?\s*3d|"
    r"collectath|sandbox|aventure\s+narrative|story[\s\-]?driven|"
    r"exploration|metroidvania|soulslike|immersive\s+sim|"
    r"assassin'?s?\s*creed|horizon\s+(zero|forbidden|dawn)|"
    r"ghost\s+of\s+(tsushima|yōtei|yotei)|god\s+of\s+war|"
    r"elder\s+scrolls|final\s+fantasy|xenoblade|monster\s+hunter|"
    r"like\s+a\s+dragon|yakuza|spider[\s\-]?man|red\s+dead|"
    r"cyberpunk|elden\s+ring|hogwarts|kingdom\s+come|"
    r"super\s+mario\s+(odyssey|bros\.?\s*wonder|galaxy)|"
    r"legend\s+of\s+zelda|the\s+witcher|"
    r"banjo|crash\s+bandicoot|ratchet|astro\s+bot|"
    r"prince\s+of\s+persia|tomb\s+raider|uncharted|"
    r"death\s+stranding|hades\s*ii?|sea\s+of\s+thieves"
    r")",
    re.I,
)

# Signaux « sortie / annonce / trailer »
SIGNAL_RE = re.compile(
    r"("
    r"sortie|release\s+date|date\s+de\s+sortie|announc|"
    r"annonc|reveal|trailer|gameplay|coming\s+(to|soon)|"
    r"arriv(?:e|era)|disponible|launch|window|"
    r"direct|state\s+of\s+play|showcase"
    r")",
    re.I,
)

# Bruit
NOISE_RE = re.compile(
    r"("
    r"\bmobile\b|free[\s\-]?to[\s\-]?play|f2p|"
    r"fifa|ea\s*sports\s*fc|nba\s*2k|madden|nhl|"
    r"esport|twitch\s+drops|soldes|promo\s+code|"
    r"casque|headset|accessoire|dualsense\b(?!.*(game|jeu))"
    r")",
    re.I,
)


def fetch_url(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def strip_html(text: str) -> str:
    t = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    t = re.sub(r"(?is)<style.*?>.*?</style>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return html.unescape(re.sub(r"\s+", " ", t)).strip()


def parse_rss(xml_text: str) -> list[dict]:
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    # RSS 2.0
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or ""
        pub = item.findtext("pubDate") or ""
        if title and link:
            items.append({"title": title, "link": link, "summary": strip_html(desc)[:500], "pub": pub})
    # Atom
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
        link_el = entry.find("a:link[@rel='alternate']", ns) or entry.find("a:link", ns)
        link = (link_el.get("href") if link_el is not None else "") or ""
        summary = entry.findtext("a:summary", default="", namespaces=ns) or entry.findtext("a:content", default="", namespaces=ns) or ""
        pub = entry.findtext("a:published", default="", namespaces=ns) or entry.findtext("a:updated", default="", namespaces=ns) or ""
        if title and link:
            items.append({"title": title, "link": link, "summary": strip_html(summary)[:500], "pub": pub})
    return items


def platforms_in(text: str) -> list[str]:
    out = []
    if re.search(r"switch\s*2|nintendo\s*switch\s*2|nsw2", text, re.I):
        out.append("Switch 2")
    if re.search(r"\bps5\b|playstation\s*5|play\s*station\s*5", text, re.I):
        out.append("PS5")
    return out


def matches(item: dict) -> bool:
    blob = f"{item['title']}\n{item.get('summary') or ''}"
    if NOISE_RE.search(blob) and not STYLE_RE.search(blob):
        return False
    if not PLATFORM_RE.search(blob):
        return False
    if not STYLE_RE.search(blob):
        return False
    if not SIGNAL_RE.search(blob):
        # titre très « jeu + plateforme » peut passer sans signal explicite
        if not re.search(r"\b(jeu|game|remake|sequel|suite)\b", blob, re.I):
            return False
    return True


def item_key(item: dict) -> str:
    return (item.get("link") or item["title"]).strip().lower()


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"seen": {}, "bootstrapped": False}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def send_discord(content: str, embeds: list | None = None) -> None:
    if not TOKEN or not CHANNEL_ID:
        print("[discord] missing config", content[:120])
        return
    payload: dict = {"content": content}
    if embeds:
        payload["embeds"] = embeds[:10]
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
        data=data,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        print("[discord]", resp.status)


def collect() -> list[dict]:
    found: list[dict] = []
    seen_links: set[str] = set()
    for name, url in FEEDS:
        try:
            print(f"feed {name}")
            xml_text = fetch_url(url)
            items = parse_rss(xml_text)
            n = 0
            for it in items:
                if not matches(it):
                    continue
                k = item_key(it)
                if k in seen_links:
                    continue
                seen_links.add(k)
                plats = platforms_in(f"{it['title']} {it.get('summary')}")
                it2 = {
                    **it,
                    "source": name,
                    "platforms": plats or ["Switch 2/PS5"],
                    "key": k,
                }
                found.append(it2)
                n += 1
            print(f"  -> {n} match / {len(items)} items")
        except Exception as e:
            print(f"  ERR {name}: {e}")
    return found


def embed_for(item: dict) -> dict:
    plats = ", ".join(item.get("platforms") or [])
    desc = (item.get("summary") or "")[:280]
    return {
        "title": item["title"][:240],
        "description": (
            f"**Plateforme :** {plats}\n"
            f"**Source :** {item.get('source')}\n\n"
            f"{desc}\n\n"
            f"[Lire l’article]({item['link']})"
        ),
        "url": item["link"],
        "color": 0x5865F2,
        "footer": {"text": "sorties-big · Switch 2 / PS5"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    if not TOKEN or not CHANNEL_ID:
        raise SystemExit("DISCORD_BOT_TOKEN / DISCORD_UPCOMING_BIG_CHANNEL_ID requis")

    print(f"upcoming-big — channel={CHANNEL_ID}")
    state = load_state()
    state.setdefault("seen", {})

    offers = collect()
    print(f"matched this run: {len(offers)}")

    new_items = [o for o in offers if o["key"] not in state["seen"]]

    if not state.get("bootstrapped"):
        # Premier passage : mémoriser sans spammer (sauf BOOTSTRAP_POST=1)
        for o in offers:
            state["seen"][o["key"]] = {
                "title": o["title"],
                "link": o["link"],
                "at": datetime.now(timezone.utc).isoformat(),
            }
        state["bootstrapped"] = True
        state["lastRunAt"] = datetime.now(timezone.utc).isoformat()
        save_state(state)
        if BOOTSTRAP_POST and new_items:
            to_show = new_items[:MAX_BOOTSTRAP]
            send_discord(
                f"📊 Inventaire initial **sorties-big** : {len(to_show)} articles récents "
                f"(filtre Switch 2 / PS5 · style aventure / 3D / RPG). "
                f"Ensuite : alertes **nouveautés seulement**."
            )
            for o in to_show:
                send_discord("", [embed_for(o)])
            print(f"bootstrap posted: {len(to_show)}")
        else:
            send_discord(
                "🟢 Watcher **sorties-big** actif.\n"
                "Filtre : **Switch 2** / **PS5** + style Zelda / Odyssey / Witcher / Bananza…\n"
                "Alertes = **nouveaux articles** uniquement."
            )
            print(f"bootstrap silent: remembered {len(offers)}")
        return

    alerts = []
    for o in new_items:
        alerts.append(o)
        state["seen"][o["key"]] = {
            "title": o["title"],
            "link": o["link"],
            "at": datetime.now(timezone.utc).isoformat(),
        }

    # prune seen > 800 entries
    if len(state["seen"]) > 800:
        ordered = sorted(state["seen"].items(), key=lambda kv: kv[1].get("at") or "")
        state["seen"] = dict(ordered[-600:])

    state["lastRunAt"] = datetime.now(timezone.utc).isoformat()
    state["lastMatchCount"] = len(offers)
    save_state(state)

    for o in alerts[:12]:
        plats = " / ".join(o.get("platforms") or [])
        send_discord(
            f"🎮 **Nouvelle piste** — {plats}",
            [embed_for(o)],
        )
    print(f"alerts sent: {min(len(alerts), 12)}")


if __name__ == "__main__":
    main()
