#!/usr/bin/env python3
"""Quick test free game data sources."""
import json
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

UA = "ZaelrysBot/1.0"

def get(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=25) as r:
        return r.read()

# Epic
epic = json.loads(get(
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=fr-FR&country=FR&allowCountries=FR"
))
els = epic["data"]["Catalog"]["searchStore"]["elements"]
for g in els[:5]:
    promos = g.get("promotions")
    if not promos:
        continue
    po = promos.get("promotionalOffers") or []
    if po:
        print("EPIC", g.get("title"))

# PS RSSHub
try:
    data = get("https://rsshub.app/ps/monthly-games")
    root = ET.fromstring(data)
    for item in root.findall(".//item")[:3]:
        print("PS", item.findtext("title"))
except Exception as e:
    print("PS err", e)

# PS blog FR
try:
    data = get("https://blog.fr.playstation.com/feed/")
    root = ET.fromstring(data)
    for item in root.findall(".//item")[:5]:
        t = item.findtext("title") or ""
        if "plus" in t.lower() or "gratuit" in t.lower():
            print("PSBLOG", t[:80])
except Exception as e:
    print("PSBLOG err", e)

# Xbox wire FR
try:
    data = get("https://news.xbox.com/fr-fr/feed/")
    root = ET.fromstring(data)
    for item in root.findall(".//item")[:8]:
        t = item.findtext("title") or ""
        if any(x in t.lower() for x in ("gratuit", "gold", "games with", "jeux")):
            print("XBOX", t[:80])
except Exception as e:
    print("XBOX err", e)

# Steam featured
try:
    st = json.loads(get("https://store.steampowered.com/api/featuredcategories/?l=french"))
    for key in ("specials", "top_sellers"):
        items = st.get(key, {}).get("items", [])[:3]
        for it in items:
            print("STEAM", key, it.get("name"))
except Exception as e:
    print("STEAM err", e)
