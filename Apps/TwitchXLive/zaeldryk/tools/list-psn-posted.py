#!/usr/bin/env python3
import json
from pathlib import Path

state = json.loads(Path("/home/ubuntu/zaeldryk/state/posted-freegames.json").read_text())
# state may be list or set-like
if isinstance(state, dict):
    keys = list(state.get("keys") or state.keys())
else:
    keys = list(state)
psn = sorted(k for k in keys if str(k).startswith("psn:"))
print("posted total", len(keys))
print("psn keys", len(psn))
for k in psn:
    print(" ", k)
