#!/usr/bin/env python3
"""Deals PS FR — DualSense + cartes PSN, alertes nouveau prix bas uniquement.

Sources prioritaires = comparateurs / bons plans (Les Numériques Offers, Dealabs),
pas les pages catalogue magasin (MSRP).
Fetch via netns WireGuard Freebox (IP maison) puis fallback direct curl_cffi.
Discord only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from curl_cffi import requests

TOKEN = (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()
CHANNEL_ID = (os.environ.get("DISCORD_DEALS_PS_CHANNEL_ID") or "").strip()
STATE_FILE = Path(
    os.environ.get("STATE_FILE")
    or "/home/ubuntu/zaeldryk/state/deals-ps-fr.json"
)
NS_FETCH = Path(os.environ.get("NS_FETCH") or "/opt/sentinelle/ns-fetch.sh")
USE_NS = os.environ.get("USE_FREEBOX_NS", "1").strip() not in ("0", "false", "no")
RESET_BEST = os.environ.get("RESET_BEST", "0").strip() in ("1", "true", "yes")

HEADERS = {
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml",
}

# Comparateur = bas de marché réel (schema.org Offer)
LN_PRODUCTS = [
    (
        "dualsense",
        "DualSense",
        "https://www.lesnumeriques.com/joypad/sony-dualsense-p57451.html",
    ),
    (
        "dualsense",
        "DualSense Edge",
        "https://www.lesnumeriques.com/joypad/sony-dualsense-edge-p70579.html",
    ),
    (
        "dualsense",
        "DualSense 30th Anniversary",
        "https://www.lesnumeriques.com/joypad/playstation-dualsense-30th-anniversary-limited-edition-p75637.html",
    ),
]

DEALABS_SEARCHES = [
    ("dualsense", "https://www.dealabs.com/search?q=manette+sony+dualsense&hide_expired=true"),
    ("dualsense", "https://www.dealabs.com/search?q=dualsense+edge&hide_expired=true"),
    ("psn", "https://www.dealabs.com/search?q=%22carte+PSN%22&hide_expired=true"),
    ("psn", "https://www.dealabs.com/search?q=carte+cadeau+playstation+store&hide_expired=true"),
    ("psn", "https://www.dealabs.com/search?q=carte+playstation+store+-fid%C3%A9lit%C3%A9&hide_expired=true"),
]

# Magasins en secours (souvent MSRP) — strict Sony only
RETAILER_SEARCHES = [
    ("dualsense", "https://www.boulanger.com/resultats?tr=sony+dualsense"),
    ("dualsense", "https://www.rueducommerce.fr/recherche/sony+dualsense"),
    ("psn", "https://www.boulanger.com/resultats?tr=carte+playstation+store"),
]


def sleep(s: float) -> None:
    time.sleep(s)


def _fetch_direct(url: str) -> str:
    r = requests.get(url, impersonate="chrome131", timeout=35, headers=HEADERS)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code} len={len(r.text)}")
    if len(r.text) < 2000:
        raise RuntimeError(f"HTML trop court ({len(r.text)})")
    return r.text


def _fetch_via_freebox(url: str) -> str:
    if not NS_FETCH.exists():
        raise RuntimeError(f"ns-fetch absent: {NS_FETCH}")
    proc = subprocess.run(
        ["sudo", "-n", str(NS_FETCH), url, "chrome131"],
        capture_output=True,
        timeout=50,
        check=False,
    )
    html = proc.stdout.decode("utf-8", "replace")
    err = (proc.stderr.decode("utf-8", "replace") or "").strip()
    if len(html) < 2000:
        raise RuntimeError(f"ns {err or f'exit {proc.returncode}'} len={len(html)}")
    return html


def fetch(url: str) -> str:
    if USE_NS:
        try:
            return _fetch_via_freebox(url)
        except Exception as e:
            print(f"  freebox-ns fail ({e}) — fallback direct")
    return _fetch_direct(url)


def parse_price(raw: str) -> float | None:
    s = raw.replace("\xa0", " ").strip()
    if re.match(r"^\d{1,3}(\.\d{3})+,\d{2}$", s):
        s = s.replace(".", "").replace(",", ".")
    elif re.match(r"^\d+,\d{2}$", s):
        s = s.replace(",", ".")
    s = re.sub(r"[^\d.]", "", s)
    try:
        n = float(s)
    except ValueError:
        return None
    if n <= 0:
        return None
    return round(n, 2)


def extract_prices(text: str) -> list[float]:
    out: list[float] = []
    for m in re.finditer(r"(\d{1,4}(?:[.,]\d{2})?)\s*€", text):
        p = parse_price(m.group(1))
        if p is not None:
            out.append(p)
    for m in re.finditer(r"(?<![\d.,])(\d{2,3})\s*€", text):
        p = parse_price(m.group(1) + ".00")
        if p is not None and p not in out:
            out.append(p)
    return out


def json_str(raw: str) -> str:
    try:
        return json.loads(f'"{raw}"')
    except Exception:
        return raw.encode("utf-8").decode("unicode_escape", "replace")


def is_accessory(title: str) -> bool:
    return bool(
        re.search(
            r"coque|étui|etui|housse|chargeur|dock|station|câble|cable|grip|skin|"
            r"sticker|verre|protection|sacoche|support|thumb|capuchon|batterie\s*externe|"
            r"socle|stand|kit\s*de\s*custom|console|tv\b|pack\s*fortnite",
            title,
            re.I,
        )
    )


def is_dualsense(title: str) -> bool:
    if not re.search(r"dual\s*-?\s*sense", title, re.I):
        return False
    # exclure clones / autres marques
    if re.search(r"\bnacon\b|\bhori\b|\bras1ution\b|\b8bitdo\b|\bgamesir\b", title, re.I):
        return False
    if is_accessory(title) and not re.search(r"manette|controller|pad|dualsense", title, re.I):
        return False
    if re.search(r"\bconsole\b", title, re.I) and not re.search(
        r"manette|dualsense", title, re.I
    ):
        return False
    return True


def is_psn_card(title: str) -> bool:
    if re.search(
        r"fid[eé]lit[eé]|via\s+la\s+carte|sur\s+la\s+carte|avantage\s+imm[eé]diat|"
        r"ps\s*plus|playstation\s*plus|abonnement|bracelet|carte\s*graphique",
        title,
        re.I,
    ):
        return False
    return bool(
        re.search(
            r"(?:carte|card|wallet|cr[eé]dit|code|gift|cadeau).{0,40}"
            r"(?:psn|playstation\s*store|ps\s*store)",
            title,
            re.I,
        )
        or re.search(
            r"(?:psn|playstation\s*store|ps\s*store).{0,40}"
            r"(?:carte|card|wallet|cr[eé]dit|cadeau|\d+\s*€)",
            title,
            re.I,
        )
    )


def normalize_dualsense(title: str, hint: str | None = None) -> str:
    t = f"{hint or ''} {title}".lower()
    if "edge" in t:
        return "DualSense Edge"
    if "30th" in t or "anniversary" in t or "anniversaire" in t:
        return "DualSense 30th Anniversary"
    colors = [
        ("midnight black", "Midnight Black"),
        ("cosmic red", "Cosmic Red"),
        ("sterling silver", "Sterling Silver"),
        ("galactic purple", "Galactic Purple"),
        ("nova pink", "Nova Pink"),
        ("starlight blue", "Starlight Blue"),
        ("volcanic red", "Volcanic Red"),
        ("cobalt blue", "Cobalt Blue"),
        ("chroma teal", "Chroma Teal"),
        ("chroma indigo", "Chroma Indigo"),
        ("chroma pearl", "Chroma Pearl"),
        ("techno red", "Techno Red"),
        ("wolverine", "Wolverine"),
        ("blanc", "White"),
        ("white", "White"),
        ("noir", "Black"),
        ("black", "Black"),
    ]
    for needle, label in colors:
        if needle in t:
            return f"DualSense {label}"
    return "DualSense Standard"


def normalize_psn(title: str, price: float) -> str | None:
    m = re.search(r"(?:valeur\s*de\s*)?(\d{2,3})\s*€", title, re.I)
    face = int(m.group(1)) if m else None
    if face is None:
        m2 = re.search(r"(?:psn|store|carte|card|wallet|cadeau)\D{0,12}(\d{2,3})", title, re.I)
        if m2:
            face = int(m2.group(1))
    if face is None:
        for f in (10, 20, 25, 50, 70, 75, 80, 100, 150):
            if abs(f - price) < 0.5:
                # prix = face → pas un deal
                return None
            if f * 0.7 <= price < f:
                face = f
                break
    if face is None:
        return None
    # Exiger une vraie promo (< 97 % de la face)
    if price >= face * 0.97:
        return None
    return f"PSN {face}€"


def product_key(category: str, model: str) -> str:
    return f"{category}|{model.lower().strip()}"


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "unknown").replace("www.", "")
    except Exception:
        return "unknown"


def abs_url(href: str, base: str) -> str:
    from urllib.parse import urljoin

    return urljoin(base, href)


def unwrap_affiliate(url: str) -> str:
    """Garde une URL exploitable ; déplie ued=/url= si possible."""
    try:
        if "ued=" in url:
            return unquote(url.split("ued=", 1)[1])
        if "url=" in url and ("effi.redir" in url or "awin" in url):
            return unquote(url.split("url=", 1)[1].split("&", 1)[0])
    except Exception:
        pass
    return url


def make_offer(
    category: str,
    model: str,
    title: str,
    price: float,
    url: str,
    merchant: str,
    source: str,
) -> dict:
    return {
        "category": category,
        "model": model,
        "title": title,
        "price": round(price, 2),
        "url": url,
        "merchant": merchant,
        "source": source,
    }


def parse_ln_offers(html: str, page_url: str, category: str, model_hint: str) -> list[dict]:
    """Les Numériques — liste schema.org Offer = vrai bas de marché."""
    offers: list[dict] = []
    # AggregateOffer lowPrice
    low = re.search(r'"lowPrice"\s*:\s*"?([\d.]+)"?', html)
    if low:
        price = float(low.group(1))
        if 35 <= price <= 280:
            offers.append(
                make_offer(
                    category,
                    model_hint,
                    f"{model_hint} — bas marché LN",
                    price,
                    page_url,
                    "Les Numériques (min)",
                    "lesnumeriques.com",
                )
            )

    for m in re.finditer(r'"@type"\s*:\s*"Offer"', html):
        blob = html[m.start() : m.start() + 900]
        price_m = re.search(r'"price"\s*:\s*"?([\d.]+)"?', blob)
        if not price_m:
            continue
        price = float(price_m.group(1))
        if price < 35 or price > 280:
            continue
        url_m = re.search(r'"url"\s*:\s*"((?:[^"\\]|\\.)*)"', blob)
        seller_m = re.search(
            r'"seller"\s*:\s*\{[^}]*?"name"\s*:\s*"((?:[^"\\]|\\.)*)"',
            blob,
        )
        raw_url = json_str(url_m.group(1)) if url_m else page_url
        url = unwrap_affiliate(raw_url)
        merchant = json_str(seller_m.group(1)) if seller_m else host_of(url)
        title_bit = f"{model_hint} @ {merchant}"
        # color from destination URL
        model = normalize_dualsense(f"{model_hint} {unquote(url)}", model_hint)
        if "Edge" in model_hint:
            model = "DualSense Edge"
        elif "30th" in model_hint:
            model = "DualSense 30th Anniversary"
        offers.append(
            make_offer(category, model, title_bit, price, url or page_url, merchant, "lesnumeriques.com")
        )
    return offers


def parse_dealabs(html: str, page_url: str, category: str) -> list[dict]:
    offers: list[dict] = []
    for m in re.finditer(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', html):
        title = json_str(m.group(1))
        window = html[max(0, m.start() - 700) : m.start() + 2200]
        if re.search(r'"isExpired"\s*:\s*true', window):
            continue
        prices = [float(x) for x in re.findall(r'"price"\s*:\s*([\d.]+)', window) if float(x) > 5]
        if not prices:
            continue
        price = prices[0]
        merch_m = re.search(r'"merchantName"\s*:\s*"((?:[^"\\]|\\.)*)"', window)
        link_m = re.search(r'"link"\s*:\s*"(https?://www\.dealabs\.com/[^"]+)"', window)
        merchant = json_str(merch_m.group(1)) if merch_m else "Dealabs"
        url = link_m.group(1) if link_m else page_url

        if category == "dualsense":
            if not is_dualsense(title):
                continue
            if is_accessory(title):
                continue
            if price < 35 or price > 280:
                continue
            model = normalize_dualsense(title)
            offers.append(make_offer(category, model, title, price, url, merchant, "dealabs.com"))
        elif category == "psn":
            if not is_psn_card(title):
                continue
            model = normalize_psn(title, price)
            if not model:
                continue
            if price < 5 or price > 150:
                continue
            offers.append(make_offer(category, model, title, price, url, merchant, "dealabs.com"))
    return offers


def parse_jsonld_products(html: str, page_url: str, category: str) -> list[dict]:
    offers: list[dict] = []
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for obj in items:
            if not isinstance(obj, dict):
                continue
            graph = obj.get("@graph")
            if isinstance(graph, list):
                items.extend(graph)
            typ = obj.get("@type")
            types = typ if isinstance(typ, list) else [typ]
            if "Product" not in (types or []) and "ProductGroup" not in (types or []):
                continue
            name = (obj.get("name") or "").strip()
            if not name:
                continue
            url = obj.get("url") or page_url
            off = obj.get("offers") or {}
            price = None
            if isinstance(off, list) and off:
                off = off[0]
            if isinstance(off, dict):
                price = off.get("lowPrice") or off.get("price")
                if not url:
                    url = off.get("url") or url
            try:
                price_f = float(str(price).replace(",", ".")) if price is not None else None
            except ValueError:
                price_f = None
            if price_f is None:
                continue
            offers.extend(classify_retail(name, price_f, str(url), page_url, category))
    return offers


def classify_retail(
    title: str, price: float, url: str, page_url: str, category: str
) -> list[dict]:
    out: list[dict] = []
    merchant = host_of(page_url)
    if category == "dualsense":
        if not is_dualsense(title):
            return out
        # exiger Sony dans le titre magasin (évite Nacon etc.)
        if not re.search(r"\bsony\b|\bplaystation\b", title, re.I) and "edge" not in title.lower():
            return out
        if price < 35 or price > 280:
            return out
        model = normalize_dualsense(title)
        out.append(
            make_offer(category, model, title, price, abs_url(url, page_url), merchant, merchant)
        )
    elif category == "psn":
        if not is_psn_card(title):
            return out
        model = normalize_psn(title, price)
        if not model:
            return out
        if price < 5 or price > 150:
            return out
        out.append(
            make_offer(category, model, title, price, abs_url(url, page_url), merchant, merchant)
        )
    return out


def parse_anchor_offers(html: str, page_url: str, category: str) -> list[dict]:
    offers: list[dict] = []
    cleaned = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.I)
    for m in re.finditer(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([\s\S]{0,300}?)</a>',
        cleaned,
        re.I,
    ):
        href, inner = m.group(1), m.group(2)
        title = re.sub(r"<[^>]+>", " ", inner)
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) < 8:
            continue
        window = cleaned[m.start() : m.start() + 500]
        prices = extract_prices(window) or extract_prices(title)
        if not prices:
            continue
        offers.extend(classify_retail(title, prices[0], href, page_url, category))
    return offers


def collect_offers() -> list[dict]:
    all_offers: list[dict] = []

    for category, model_hint, url in LN_PRODUCTS:
        try:
            print(f"fetch ln {model_hint} {url}")
            html = fetch(url)
            found = parse_ln_offers(html, url, category, model_hint)
            print(f"  -> {len(found)} offers")
            all_offers.extend(found)
        except Exception as e:
            print(f"  ERR {url}: {e}")
        sleep(1.0)

    for category, url in DEALABS_SEARCHES:
        try:
            print(f"fetch dealabs {category} {url}")
            html = fetch(url)
            found = parse_dealabs(html, url, category)
            print(f"  -> {len(found)} offers")
            all_offers.extend(found)
        except Exception as e:
            print(f"  ERR {url}: {e}")
        sleep(1.0)

    for category, url in RETAILER_SEARCHES:
        try:
            print(f"fetch retail {category} {url}")
            html = fetch(url)
            found = parse_jsonld_products(html, url, category)
            found += parse_anchor_offers(html, url, category)
            uniq = {}
            for o in found:
                uniq[(o["model"], o["price"], o["merchant"])] = o
            found = list(uniq.values())
            print(f"  -> {len(found)} offers")
            all_offers.extend(found)
        except Exception as e:
            print(f"  ERR {url}: {e}")
        sleep(1.0)

    return all_offers


def pick_best(offers: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for o in offers:
        key = product_key(o["category"], o["model"])
        prev = best.get(key)
        if not prev or o["price"] < prev["price"]:
            best[key] = o
    return best


def send_discord(content: str, embeds: list | None = None) -> None:
    if not TOKEN or not CHANNEL_ID:
        print("[discord] missing", content)
        return
    payload: dict = {"content": content}
    if embeds:
        payload["embeds"] = embeds
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
        data=data,
        headers={
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "ZaelDealsPS/1.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        print("[discord] ok", resp.status)


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"best": {}, "bootNotified": False}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    if not TOKEN or not CHANNEL_ID:
        raise SystemExit("DISCORD_BOT_TOKEN / DISCORD_DEALS_PS_CHANNEL_ID requis")

    print(f"deals-ps-fr — freebox-ns={USE_NS} — channel={CHANNEL_ID}")
    state = load_state()
    state.setdefault("best", {})
    if RESET_BEST:
        print("RESET_BEST=1 — clear previous best prices")
        state["best"] = {}

    if not state.get("bootNotified"):
        send_discord(
            "🟢 Watcher **deals-ps** (marché FR via Freebox).\n"
            "Sources : **Les Numériques** (comparateur) + **Dealabs** (+ magasins en secours).\n"
            "DualSense + cartes PSN **en promo** (sous la face).\n"
            "Alertes = **nouveau prix bas** uniquement."
        )
        state["bootNotified"] = True
        save_state(state)

    offers = collect_offers()
    best_now = pick_best(offers)
    print(f"models tracked this run: {len(best_now)}")
    for k, o in sorted(best_now.items(), key=lambda kv: kv[1]["price"]):
        print(f"  BEST {o['price']:7.2f} € | {o['merchant'][:22]:22} | {o['model']} | {o['source']}")

    alerts = []
    for key, offer in best_now.items():
        prev = state["best"].get(key)
        is_new = (
            not prev
            or not isinstance(prev.get("price"), (int, float))
            or offer["price"] < float(prev["price"]) - 0.009
        )
        if is_new:
            alerts.append({"offer": offer, "oldPrice": prev.get("price") if prev else None})
            state["best"][key] = {
                "category": offer["category"],
                "model": offer["model"],
                "price": offer["price"],
                "merchant": offer["merchant"],
                "url": offer["url"],
                "title": offer["title"],
                "source": offer["source"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            state["best"][key] = {
                **prev,
                "price": offer["price"],
                "merchant": offer["merchant"],
                "url": offer["url"],
                "title": offer["title"],
                "source": offer["source"],
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    # drop stale models no longer seen? keep history for new-low detection
    state["lastRunAt"] = datetime.now(timezone.utc).isoformat()
    state["lastOfferCount"] = len(offers)
    save_state(state)

    first = len(alerts) > 0 and all(a["oldPrice"] is None for a in alerts)
    to_send = sorted(alerts, key=lambda a: a["offer"]["price"])
    if first:
        send_discord(
            f"📊 Inventaire marché : **{len(alerts)}** refs (bas de prix comparateur). "
            "Ensuite : alertes seulement si un prix descend."
        )
        to_send = to_send[:12]

    for a in to_send:
        offer = a["offer"]
        old = a["oldPrice"]
        drop = (
            f"\nAncien best : **{old:.2f} €** → **{offer['price']:.2f} €**"
            if old is not None
            else f"\nBest marché : **{offer['price']:.2f} €**"
        )
        send_discord(
            f"💸 **Nouveau prix bas** — {offer['model']}",
            [
                {
                    "title": offer["model"],
                    "description": (
                        f"**{offer['price']:.2f} €** chez **{offer['merchant']}**"
                        f" _(via {offer['source']})_"
                        f"{drop}\n\n[{offer['title'][:120]}]({offer['url']})"
                    ),
                    "url": offer["url"],
                    "color": 0x00A651,
                    "footer": {"text": "deals-ps-fr · market low only"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        sleep(0.8)

    print(f"alerts sent: {len(to_send)}")


if __name__ == "__main__":
    main()
