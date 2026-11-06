#!/usr/bin/env python3
from urllib.request import Request, urlopen
import re

UA = "Mozilla/5.0"
queries = [
    "https://www.nintendo.com/us/search/?q=zelda%20switch%202%20edition&p=1&cat=hardware",
    "https://www.nintendo.com/us/search/?q=ocarina&p=1",
    "https://www.nintendo.com/us/store/hardware/",
    "https://www.nintendo.com/us/whatsnew/",
]

def fetch(url):
    req = Request(url, headers={"User-Agent": UA})
    with urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

for u in queries:
    print("===", u[:80])
    try:
        html = fetch(u)
    except Exception as e:
        print("FAIL", e)
        continue
    for i in re.findall(r'https://assets\.nintendo\.com/image/upload/[^"\'\s]+', html):
        low = i.lower()
        if any(k in low for k in ("zelda", "ocarina", "40th", "anniversary", "movie", "film", "system", "hardware")):
            # clean trailing punctuation
            i = i.rstrip("\\").split("\\u")[0]
            if i.endswith(".jpg") or i.endswith(".png") or i.endswith(".webp") or "/store/" in i or "Zelda" in i:
                print(i[:220])
