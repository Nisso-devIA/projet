import re, urllib.request
url = "https://www.nintendo.com/us/whatsnew/the-legend-of-zelda-40th-anniversary-celebration-revealed-in-new-nintendo-direct-presentation/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
print("len", len(html))
# cloudinary / assets
imgs = sorted(set(re.findall(r"https://assets\.nintendo\.com/image/upload[^\"'\s\\]+", html)))
for u in imgs:
    print(u)
print("--- next_data ---")
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
if m:
    import json
    data = json.loads(m.group(1))
    s = json.dumps(data)
    imgs2 = sorted(set(re.findall(r"https://assets\.nintendo\.com/image/upload[^\"'\\]+", s)))
    for u in imgs2:
        print(u)
    # also relative paths
    rel = sorted(set(re.findall(r'ncom/[^"\\]+\.(?:jpg|jpeg|png|webp)', s, re.I)))
    print("--- relative ---")
    for r in rel[:40]:
        print(r)
