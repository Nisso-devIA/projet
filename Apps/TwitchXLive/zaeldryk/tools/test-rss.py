#!/usr/bin/env python3
import sys
try:
    import feedparser
    print("feedparser", feedparser.__version__)
except ImportError:
    print("no feedparser")
    sys.exit(1)

feeds = [
    "https://www.gamekult.com/feed/actu.xml",
    "https://www.frandroid.com/feed",
    "https://www.jeuxvideo.com/rss/rss.xml",
    "https://www.lesnumeriques.com/rss.xml",
    "https://www.ign.com/rss/articles/feed",
]
for u in feeds:
    d = feedparser.parse(u)
    print(u, "entries", len(d.entries), d.bozo and "bozo" or "ok")
