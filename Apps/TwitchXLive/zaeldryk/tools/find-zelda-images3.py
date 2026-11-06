#!/usr/bin/env python3
from urllib.request import Request, urlopen
import re

UA = "Mozilla/5.0"
url = "https://www.nintendo.com/us/store/products/the-legend-of-zelda-ocarina-of-time-switch-2/"
html = urlopen(Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")

# all assets.nintendo.com urls
all_imgs = sorted(set(re.findall(r'https://assets\.nintendo\.com/image/upload/[^"\'\\\s]+', html)))
print("count", len(all_imgs))
for i in all_imgs:
    if any(x in i.lower() for x in ("7001", "zelda", "ocarina", "40th", "system", "hardware", "hero", "product", "merch")):
        print(i)

# also try listing directory patterns
candidates = [
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/ncom/en_US/merchandising/feature-banner/2026/Zelda%2040th%20Anniversary/Switch2_System.jpg",
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/ncom/en_US/merchandising/feature-banner/2026/Zelda%2040th%20Anniversary/Nintendo_Switch_2.jpg",
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/ncom/en_US/merchandising/feature-banner/2026/Zelda%2040th%20Anniversary/Hardware.jpg",
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/ncom/en_US/merchandising/feature-banner/2026/Zelda%2040th%20Anniversary/Movie.jpg",
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/ncom/en_US/merchandising/feature-banner/2026/Zelda%2040th%20Anniversary/Film.jpg",
    "https://assets.nintendo.com/image/upload/f_auto/q_auto/ncom/en_US/merchandising/feature-banner/2026/Zelda%2040th%20Anniversary/The_Legend_of_Zelda_Movie.jpg",
]
print("\n=== probes ===")
for u in candidates:
    try:
        r = urlopen(Request(u, headers={"User-Agent": UA}), timeout=15)
        print("OK", r.status, u)
    except Exception as e:
        print("NO", getattr(e, "code", e), u.split("/")[-1])
