#!/usr/bin/env python3
from urllib.request import Request, urlopen
import re
import html as htmlmod

url = "https://blog.fr.playstation.com/2026/07/28/les-jeux-du-mois-playstation-plus-pour-aout-dying-light-2-stay-human-big-walk-signalis/"
page = urlopen(Request(url, headers={"User-Agent": "Zaelrys/1.0"}), timeout=30).read().decode("utf-8", "replace")

# title colon parse
m = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
title = htmlmod.unescape(re.sub(r"<[^>]+>", "", m.group(1))) if m else ""
print("TITLE", title)

# strong tags / figcaption
for pat in [
    r"<strong>(.*?)</strong>",
    r'class="[^"]*game[^"]*"[^>]*>(.*?)<',
    r"<figcaption[^>]*>(.*?)</figcaption>",
    r'itemprop="name"[^>]*>(.*?)<',
]:
    found = re.findall(pat, page, flags=re.I | re.S)
    cleaned = [re.sub(r"<[^>]+>", "", htmlmod.unescape(x)).strip() for x in found]
    cleaned = [x for x in cleaned if 2 < len(x) < 90 and "Download" not in x]
    print(pat[:40], "->", cleaned[:20])

# After "Essential" / "Extra" / "Premium" sections
for label in ("Essential", "Extra", "Premium", "Jeux du mois"):
    idx = page.lower().find(label.lower())
    print(label, "idx", idx)
