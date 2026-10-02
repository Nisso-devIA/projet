#!/usr/bin/env python3
"""Inspect PS Plus Catalogue article HTML structure."""
import re
import importlib.util

spec = importlib.util.spec_from_file_location("fg", "/home/ubuntu/zaeldryk/discord/free-games-post.py")
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)

items = fg.parse_rss("https://blog.fr.playstation.com/category/ps-plus/feed/")
cat = None
for it in items:
    t = it["title"].lower()
    if "catalogue" in t and ("août" in t or "aout" in t or "mois" in t or "août" in it["title"]):
        cat = it
        break
if not cat:
    for it in items:
        if "catalogue" in it["title"].lower():
            cat = it
            break
print("CAT:", cat["title"] if cat else None)
print("URL:", cat["link"] if cat else None)
if not cat:
    raise SystemExit(0)
page = fg.http_get(cat["link"]).decode("utf-8", errors="replace")
print("strongs:")
for s in re.findall(r"<strong>(.*?)</strong>", page, flags=re.I | re.S)[:50]:
    print(" ", repr(fg.clean_text(s, 140)))
print("li:")
for s in re.findall(r"<li[^>]*>(.*?)</li>", page, flags=re.I | re.S)[:60]:
    name = fg.clean_text(s, 140)
    if name:
        print(" ", repr(name))
print("h2:")
for s in re.findall(r"<h2[^>]*>(.*?)</h2>", page, flags=re.I | re.S)[:30]:
    print(" ", repr(fg.clean_text(s, 140)))
