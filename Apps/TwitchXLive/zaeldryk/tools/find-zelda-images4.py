#!/usr/bin/env python3
from urllib.request import Request, urlopen
import re

UA = "Mozilla/5.0"
# hardware product id found near Zelda page
ids = ["70010000122824", "70010000130792"]
# try store product slug search via nintendo graphql-ish pages
pages = [
    "https://www.nintendo.com/us/store/products/nintendo-switch-2-system-zelda-edition-bundle/",
    "https://www.nintendo.com/us/store/hardware/nintendo-switch-2/",
]
# scrape from hardware image hash page by constructing from known hash path
hashes = [
    "cf587e01f6f115398f411f280dba21e025795eb69f234a41722341ea999d170d",
]
for h in hashes:
    u = f"https://assets.nintendo.com/image/upload/f_auto/q_auto/store/software/switch2/70010000122824/{h}.jpg"
    try:
        r = urlopen(Request(u, headers={"User-Agent": UA}), timeout=15)
        print("OK hardware?", u, r.status)
    except Exception as e:
        print("NO", e)

# Try French news
fr_pages = [
    "https://www.nintendo.com/fr-fr/Actualites/The-Legend-of-Zelda-Direct-des-40-ans-2871367.html",
    "https://www.nintendo.com/fr-fr/Jeux/Jeux-Nintendo-Switch-2/The-Legend-of-Zelda-Ocarina-of-Time-2870000.html",
    "https://www.nintendo.fr/",
]
for u in fr_pages:
    try:
        html = urlopen(Request(u, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8","replace")
        print("PAGE OK", u, len(html))
        for i in sorted(set(re.findall(r'https://[^"\']+\.(?:jpg|jpeg|png|webp)', html, re.I))):
            if any(k in i.lower() for k in ("zelda", "ocarina", "switch", "movie", "film", "40")):
                print(" ", i[:200])
    except Exception as e:
        print("PAGE NO", u, getattr(e,"code",e))

# Probe Zelda 40th folder listing via common names
base = "https://assets.nintendo.com/image/upload/f_auto/q_auto/ncom/en_US/merchandising/feature-banner/2026/Zelda%2040th%20Anniversary/"
names = [
    "Ocarina_of_Time.jpg",
    "Hardware_Bundle.jpg",
    "NS2_Zelda.jpg",
    "Switch_2_Zelda.jpg",
    "Zelda_Switch_2.jpg",
    "System.jpg",
    "Console.jpg",
    "Pro_Controller.jpg",
    "Movie_Trailer.jpg",
    "Live_Action.jpg",
    "Zelda_Movie.jpg",
    "Key_Art.jpg",
    "Hero.jpg",
    "Banner.jpg",
]
print("\n=== folder probes ===")
for n in names:
    u = base + n
    try:
        r = urlopen(Request(u, method="HEAD", headers={"User-Agent": UA}), timeout=10)
        print("OK", n, r.status)
    except Exception as e:
        print("NO", n, getattr(e,"code",""))
