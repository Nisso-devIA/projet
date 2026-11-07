#!/usr/bin/env python3
from urllib.request import Request, urlopen
import re, json

UA = "Mozilla/5.0"
url = "https://www.nintendo.com/us/store/products/the-legend-of-zelda-ocarina-of-time-switch-2/"
html = urlopen(Request(url, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8", "replace")

# Extract __NEXT_DATA__ if present
m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
if m:
    data = json.loads(m.group(1))
    s = json.dumps(data)
    print("NEXT_DATA bytes", len(s))
    for u in sorted(set(re.findall(r'https://assets\.nintendo\.com/image/upload/[^"\\]+', s))):
        if any(k in u.lower() for k in ("7001", "zelda", "ocarina", "40th", "hardware", "system", "movie", "film")):
            print(u[:250])
else:
    print("no NEXT_DATA")
    # find media gallery titles
    for pat in ["Power up", "special edition", "amiibo", "movie", "trailer", "system"]:
        i = html.lower().find(pat.lower())
        if i != -1:
            print("--- context", pat, "---")
            print(html[i:i+500][:500])
