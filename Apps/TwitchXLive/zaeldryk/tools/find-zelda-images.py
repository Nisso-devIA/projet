#!/usr/bin/env python3
"""Find official Nintendo image URLs for Zelda products."""
from urllib.request import Request, urlopen
import re
import json

UA = "Mozilla/5.0 (compatible; ZaelrysBot/1.0)"
pages = [
    "https://www.nintendo.com/us/store/products/the-legend-of-zelda-ocarina-of-time-switch-2/",
    "https://www.nintendo.com/us/store/products/nintendo-switch-2-the-legend-of-zelda-edition/",
    "https://www.nintendo.com/us/whatsnew/the-legend-of-zelda-40th-anniversary-direct/",
]

def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

for u in pages:
    print("===", u)
    try:
        html = fetch(u)
    except Exception as e:
        print("FAIL", e)
        continue
    og = re.findall(r'property=["\']og:image["\'] content=["\']([^"\']+)["\']', html)
    tw = re.findall(r'name=["\']twitter:image["\'] content=["\']([^"\']+)["\']', html)
    # common Nintendo CDN patterns
    imgs = re.findall(
        r'https://[^"\'\s]+(?:ncom|assets|media|eshop)[^"\'\s]+\.(?:jpg|jpeg|png|webp)',
        html,
        re.I,
    )
    # also assets.nintendo.com
    imgs2 = re.findall(r'https://assets\.nintendo\.com[^"\'\s]+\.(?:jpg|jpeg|png|webp)', html, re.I)
    print("og:", og[:5])
    print("tw:", tw[:3])
    seen = set()
    for i in og + tw + imgs + imgs2:
        if i in seen:
            continue
        seen.add(i)
        low = i.lower()
        if any(k in low for k in ("zelda", "ocarina", "switch", "hero", "keyart", "product")):
            print(" IMG", i[:200])
    print("total unique imgs", len(seen))
