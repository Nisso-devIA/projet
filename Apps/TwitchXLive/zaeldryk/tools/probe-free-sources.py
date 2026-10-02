#!/usr/bin/env python3
from urllib.request import Request, urlopen
import json
import xml.etree.ElementTree as ET
import re
import html as htmlmod

UA = {"User-Agent": "Zaelrys/1.0"}


def get(url: str) -> bytes:
    with urlopen(Request(url, headers=UA), timeout=30) as r:
        return r.read()


print("=== RSSHUB PS monthly ===")
try:
    root = ET.fromstring(get("https://rsshub.app/ps/monthly-games"))
    items = root.findall(".//item")
    print("count", len(items))
    for it in items[:12]:
        print("-", (it.findtext("title") or "")[:90])
except Exception as e:
    print("ERR", type(e).__name__, e)

print("\n=== EPIC ===")
epic = json.loads(
    get(
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
        "?locale=fr-FR&country=FR&allowCountries=FR"
    )
)
els = epic["data"]["Catalog"]["searchStore"]["elements"]
n = 0
for g in els:
    if g.get("promotions"):
        n += 1
        print("-", g.get("title"))
print("count", n)

print("\n=== GOG ===")
gog = json.loads(
    get("https://www.gog.com/games/ajax/filtered?mediaType=game&isFree=true&sort=popularity")
)
prods = gog.get("products") or []
print("count", len(prods))
for p in prods[:8]:
    print("-", p.get("title"))

print("\n=== PS blog article parse ===")
try:
    root = ET.fromstring(get("https://blog.fr.playstation.com/category/ps-plus/feed/"))
    for item in root.findall(".//item")[:6]:
        t = (item.findtext("title") or "").lower()
        link = item.findtext("link") or ""
        if "jeux du mois" in t or ("jeux de" in t and "mois" in t):
            print("article", item.findtext("title"))
            print("link", link)
            page = get(link).decode("utf-8", errors="replace")
            # h2/h3 candidates
            titles = re.findall(r"<h[23][^>]*>(.*?)</h[23]>", page, flags=re.I | re.S)
            titles = [re.sub(r"<[^>]+>", "", htmlmod.unescape(x)).strip() for x in titles]
            titles = [x for x in titles if 2 < len(x) < 80]
            print("h2/h3 sample", titles[:15])
            break
except Exception as e:
    print("ERR", type(e).__name__, e)

print("\n=== Steam 100% ===")
st = json.loads(get("https://store.steampowered.com/api/featuredcategories/?l=french"))
for item in st.get("specials", {}).get("items", []):
    if (item.get("discount_percent") or 0) >= 100 or item.get("final_price") in (0, "0"):
        print("-", item.get("name"), item.get("discount_percent"))
