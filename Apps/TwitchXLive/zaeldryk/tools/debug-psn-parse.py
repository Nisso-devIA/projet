#!/usr/bin/env python3
"""Debug PSN jeux du mois parsing."""
import re
import sys
from pathlib import Path

sys.path.insert(0, "/home/ubuntu/zaeldryk/discord")
import importlib.util

spec = importlib.util.spec_from_file_location(
    "fg", "/home/ubuntu/zaeldryk/discord/free-games-post.py"
)
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

items = fg.parse_rss("https://blog.fr.playstation.com/category/ps-plus/feed/")
print("RSS items:", len(items))
for it in items[:8]:
    print(" -", it["title"][:100])

offers = fg.fetch_psn()
print("\nfetch_psn offers:", len(offers))
for o in offers:
    print(" *", o["title"], "|", o.get("description"), "|", o["key"])

# Also dump strongs from latest article
article = None
for it in items:
    t = it["title"].lower()
    if "jeux du mois" in t or ("jeux de" in t and "mois" in t):
        article = it
        break
if article:
    print("\nArticle:", article["title"])
    print("URL:", article["link"])
    page = fg.http_get(article["url"] if False else article["link"]).decode("utf-8", errors="replace")
    strongs = re.findall(r"<strong>(.*?)</strong>", page, flags=re.I | re.S)
    print("strongs:", len(strongs))
    for s in strongs[:40]:
        name = fg.clean_text(s, 120)
        print("  STRONG:", repr(name[:100]))
    # h2/h3 too
    for tag in ("h2", "h3", "h4"):
        found = re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", page, flags=re.I | re.S)
        print(f"{tag}:", len(found))
        for x in found[:15]:
            print(f"  {tag.upper()}:", repr(fg.clean_text(x, 120)[:100]))
