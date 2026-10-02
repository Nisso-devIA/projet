#!/usr/bin/env python3
import importlib.util

spec = importlib.util.spec_from_file_location("fg", "/home/ubuntu/zaeldryk/discord/free-games-post.py")
fg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fg)
offers = fg.fetch_psn()
print("TOTAL", len(offers))
for o in offers:
    print(f"- [{o['key']}] {o['title']} :: {o['description']}")
