#!/usr/bin/env python3
import json
from pathlib import Path

p = Path("/home/ubuntu/zaeldryk/config/youtube-oauth.json")
d = json.loads(p.read_text())
print("has_refresh", bool(d.get("refresh_token")))
print("has_token", bool(d.get("token")))
print("scopes", d.get("scopes"))
print("size", p.stat().st_size)
